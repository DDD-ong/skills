# Credits 计费系统参考知识

## 1. Credits 双池模型

### 池类型
- **个人池 (Personal Pool)**: 用户通过官网自主购买获得，仅该用户可使用
- **组织池 (Organization Pool)**: 企业订单分配，由 Owner/Admin 分配给成员

### 消耗优先级（双池账号）
1. **Free Trial Credits** - 试用期赠送
2. **Subscription Credits** - 订阅方案包含
3. **Credit Package Credits** - 加油包购买

### 池状态管理
```
创建池 → 充值（订单绑定） → 正常消耗 → 余额为0或过期
                                ↓
                         分配额度（组织池）
                                ↓
                         冻结（Inactive）→ 解冻（Reactivate）
```

### 关键公式
- `remaining = total_credits - used_credits - expired_credits`
- `unallocated = total_credits - SUM(allocated_credits for all members)`
- `usage_rate = used_credits / allocated_credits * 100%`

## 2. Stripe 集成详情

### 产品和价格体系
```
Products:
├── Alta Lex Individual Trial
│   └── Price: $240 (one-time) → 1,500 Credits, 30天
├── Alta Lex Individual Annual
│   └── Price: $2,800/year (recurring) → 18,000 Credits/年
├── Alta Lex Credit Package
│   └── Price: $10 (one-time) → 100 Credits
└── Alta Lex Enterprise
    └── Price: Custom (平台管理员手动创建订单)
```

### FastAPI Checkout 流程
```python
# app/api/v1/payments.py
from fastapi import APIRouter, Depends, HTTPException
import stripe
from app.core.config import settings
from app.core.auth import get_current_user
from app.schemas.payment import CheckoutRequest

router = APIRouter(prefix="/payments", tags=["payments"])
stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/checkout")
async def create_checkout_session(
    req: CheckoutRequest,
    current_user = Depends(get_current_user),
):
    session = stripe.checkout.Session.create(
        mode="subscription" if req.is_recurring else "payment",
        customer_email=current_user.email,
        line_items=[{
            "price": req.price_id,
            "quantity": 1,
        }],
        success_url=f"{settings.FRONTEND_URL}/settings?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/pricing",
        metadata={
            "user_id": str(current_user.id),
            "plan_type": req.plan_type,
        },
        automatic_tax={"enabled": True},
    )
    return {"checkout_url": session.url}
```

### Webhook 事件处理

| 事件 | 处理逻辑 |
|------|---------|
| `checkout.session.completed` | 创建 Subscription 记录、创建 Credit Pool、分配 Credits |
| `invoice.paid` | 续费成功、新增 Credits 到池 |
| `invoice.payment_failed` | 标记订阅为 past_due、发送通知 |
| `customer.subscription.updated` | 同步订阅状态变更 |
| `customer.subscription.deleted` | 标记订阅为 cancelled、Credits 到期处理 |

### FastAPI Webhook 幂等性实现
```python
# app/api/v1/webhooks.py
from fastapi import APIRouter, Request, HTTPException
import stripe
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_session
from app.models import ProcessedEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    async with get_session() as session:
        # 幂等检查
        existing = await session.execute(
            select(ProcessedEvent).where(
                ProcessedEvent.stripe_event_id == event["id"]
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "already_processed"}

        # 处理事件
        await process_stripe_event(session, event)

        # 记录已处理
        session.add(ProcessedEvent(stripe_event_id=event["id"]))
        await session.commit()

    return {"status": "ok"}
```

## 3. Credits 消耗服务（SQLAlchemy 事务）

```python
# app/services/credits.py
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CreditPool, CreditTransaction, AuditLog

class CreditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def consume(
        self,
        pool_id: str,
        user_id: str,
        amount: Decimal,
        description: str | None = None,
    ) -> dict:
        """事务安全的 Credits 扣减，使用 SELECT FOR UPDATE"""
        stmt = (
            select(CreditPool)
            .where(CreditPool.id == pool_id, CreditPool.status == "active")
            .with_for_update()
        )
        pool = (await self.session.execute(stmt)).scalar_one_or_none()

        if pool is None:
            return {"success": False, "error": "POOL_NOT_FOUND_OR_INACTIVE"}

        remaining = pool.total_credits - pool.used_credits - pool.expired_credits
        if remaining < amount:
            return {"success": False, "error": "INSUFFICIENT_CREDITS"}

        # 更新池余额
        pool.used_credits += amount
        new_balance = remaining - amount

        # 创建交易记录
        self.session.add(CreditTransaction(
            credit_pool_id=pool_id,
            user_id=user_id,
            transaction_type="consume",
            amount=amount,
            balance_after=new_balance,
            description=description,
        ))

        # 审计日志
        self.session.add(AuditLog(
            user_id=user_id,
            action="credits.consume",
            resource_type="credit_pool",
            resource_id=pool_id,
            details={"amount": str(amount), "remaining": str(new_balance)},
        ))

        return {"success": True, "remaining": float(new_balance)}

    async def allocate(
        self,
        pool_id: str,
        member_user_id: str,
        amount: Decimal,
        operator_id: str,
    ) -> dict:
        """组织池额度分配"""
        stmt = (
            select(CreditPool)
            .where(CreditPool.id == pool_id, CreditPool.pool_type == "organization")
            .with_for_update()
        )
        pool = (await self.session.execute(stmt)).scalar_one_or_none()

        if pool is None:
            return {"success": False, "error": "ORG_POOL_NOT_FOUND"}

        unallocated = pool.total_credits - pool.allocated_credits
        if unallocated < amount:
            return {"success": False, "error": "INSUFFICIENT_UNALLOCATED"}

        pool.allocated_credits += amount

        self.session.add(CreditTransaction(
            credit_pool_id=pool_id,
            user_id=member_user_id,
            transaction_type="allocate",
            amount=amount,
            balance_after=float(pool.total_credits - pool.allocated_credits),
            description=f"Allocated by {operator_id}",
        ))

        return {"success": True, "allocated": float(amount)}
```

## 4. 财务对账流程

### Stripe → OCBC → Xero 数据流
```
Stripe Payment
  → Stripe 手续费扣除 (2.9% + $0.30)
  → Stripe Clearing Account (T+2)
  → OCBC 银行入账 (Payout)
  → Xero Invoice 同步
```

### 对账数据映射
| Stripe 字段 | Xero 字段 | 说明 |
|-------------|-----------|------|
| charge.amount | Invoice.Total | 交易总额 |
| charge.amount - fee | Payment.Amount | 净额（扣手续费） |
| customer.email | Contact.EmailAddress | 客户标识 |
| metadata.org_id | Invoice.Reference | 组织关联 |

### 收入确认规则
- 按 Credit 消耗确认收入（非按付款时点）
- 当月收入 = SUM(消耗点数 x 平均单价)
- 平均单价 = 订单金额 / 订单 Credits 数量
- 不使用加权平均法

## 5. 额度分配逻辑

### 新建账号时的额度分配
```python
# 系统预填建议额度
suggested_credits = order.remaining_unallocated // order.remaining_seats

# Owner/Admin 可修改后提交
await credit_service.allocate(
    pool_id=pool_id,
    member_user_id=new_member_id,
    amount=confirmed_amount,
    operator_id=current_user.id,
)
```

### Set Inactive 时的额度处理
- 冻结已分配额度，**不释放回池**
- 账号消耗权限关闭
- 占用的席位仍然计数

### Reactivate 时的额度处理
- 恢复消耗权限
- 已分配额度恢复可用
- 无需重新分配
