---
name: credits-billing
version: 1.0.0
description: >
  Design and implement the Credits billing system and Stripe payment integration.
  Use when working on Credits pool management, payment flows,
  subscription lifecycle, or financial reconciliation.
description_zh: >
  设计和实现 Credits 计费系统和 Stripe 支付集成。
  当处理 Credits 池管理、支付流程、订阅生命周期、或财务对账时使用。
---

# Credits & Billing

## 触发条件

当出现以下场景时使用此技能：
- 设计或修改 Credits 池管理逻辑
- 实现 Credits 扣减/充值/分配功能
- 集成 Stripe 支付（Checkout、Subscription、Webhook）
- 设计订阅生命周期管理
- 处理财务对账（Stripe → OCBC → Xero）

## 执行流程

1. **需求分析**: 确认涉及的 Credits 操作类型
2. **数据模型**: 确认 credit_pools 和 credit_transactions 的 SQLAlchemy 模型
3. **业务逻辑**: 实现基于 SQLAlchemy 异步事务的 Credits 操作
4. **Stripe 集成**: FastAPI 路由处理支付和 Webhook 事件
5. **测试用例**: 为边界场景设计 pytest 测试
6. **代码产出**: 输出到 `backend/app/` 目录

## 输入要求

- 架构文档（`docs/architecture/*.md`）
- 数据库设计（`docs/database/*.md`）
- PRD 中 Credits 和支付相关章节

## 输出规范

### Credits 操作的事务安全要求

所有 Credits 变更必须通过 SQLAlchemy 异步事务执行，使用 SELECT FOR UPDATE 确保原子性：

```python
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CreditPool, CreditTransaction

async def consume_credits(
    session: AsyncSession,
    pool_id: str,
    user_id: str,
    amount: float,
    description: str | None = None,
) -> dict:
    """事务安全的 Credits 扣减"""
    async with session.begin():
        # 获取锁并检查余额
        stmt = (
            select(CreditPool)
            .where(CreditPool.id == pool_id)
            .with_for_update()
        )
        pool = (await session.execute(stmt)).scalar_one_or_none()
        if pool is None:
            return {"success": False, "error": "POOL_NOT_FOUND"}

        remaining = pool.total_credits - pool.used_credits - pool.expired_credits
        if remaining < amount:
            return {"success": False, "error": "INSUFFICIENT_CREDITS"}

        # 扣减
        pool.used_credits += amount
        new_balance = remaining - amount

        # 记录交易
        tx = CreditTransaction(
            credit_pool_id=pool_id,
            user_id=user_id,
            transaction_type="consume",
            amount=amount,
            balance_after=new_balance,
            description=description,
        )
        session.add(tx)

    return {"success": True, "remaining": new_balance}
```

### Stripe Webhook 处理要求

- 使用 FastAPI 路由接收 Webhook，验证签名后处理事件
- 实现幂等性（记录已处理的 event ID 到数据库）
- 关键事件: `checkout.session.completed`, `invoice.paid`, `customer.subscription.deleted`

## 质量检查

- [ ] Credits 操作使用 SQLAlchemy 异步事务 + SELECT FOR UPDATE，防止竞态条件
- [ ] 双池（个人/组织）隔离逻辑正确
- [ ] 所有 Credits 变更记录到 credit_transactions
- [ ] Stripe Webhook 签名验证且幂等
- [ ] 异常路径处理（余额不足、池不存在、账号冻结）
- [ ] 审计日志覆盖所有关键操作
