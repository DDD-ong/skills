# 代码审查参考知识

## 1. Alta Lex 安全审查重点

### SQL 注入防护
```python
# BAD - 字符串拼接 SQL
from sqlalchemy import text
result = await session.execute(
    text(f"SELECT * FROM users WHERE email = '{user_input}'")  # 危险！
)

# GOOD - 使用 SQLAlchemy ORM 参数化
from sqlalchemy import select
from app.models import User
result = await session.execute(
    select(User).where(User.email == user_input)  # ORM 自动参数化
)

# GOOD - 使用 text() 绑定参数
result = await session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": user_input},
)
```

### 权限绕过检查
```python
# BAD - 未检查权限直接操作
@router.get("/organizations/{org_id}/members")
async def list_members(org_id: str):
    # 任何人都能查看！
    return await get_members(org_id)

# GOOD - 使用 FastAPI Dependency 权限检查
@router.get("/organizations/{org_id}/members")
async def list_members(
    org_id: str,
    current_user = Depends(require_role("owner", "admin")),
):
    return await get_members(org_id)
```

### Credits 竞态条件
```python
# BAD - 先读后写，存在竞态
async def consume_bad(session, pool_id, amount):
    pool = await session.get(CreditPool, pool_id)
    remaining = pool.total_credits - pool.used_credits
    if remaining >= amount:
        pool.used_credits += amount  # 可能被并发请求超扣
        await session.commit()

# GOOD - 使用 SELECT FOR UPDATE 加锁
async def consume_good(session, pool_id, amount):
    stmt = (
        select(CreditPool)
        .where(CreditPool.id == pool_id)
        .with_for_update()
    )
    pool = (await session.execute(stmt)).scalar_one()
    remaining = pool.total_credits - pool.used_credits - pool.expired_credits
    if remaining < amount:
        raise InsufficientCreditsError()
    pool.used_credits += amount
    await session.commit()
```

### Stripe Webhook 安全
```python
# 必须验证 Webhook 签名
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 必须处理幂等性（检查事件是否已处理）
    ...
```

### XSS 防护（React 前端）
```tsx
// BAD - 使用 dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// GOOD - React 自动转义
<div>{userInput}</div>

// 如必须渲染 HTML，使用 DOMPurify 消毒
import DOMPurify from 'dompurify'
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(htmlContent) }} />
```

## 2. 性能审查检查项

### 数据库查询（SQLAlchemy）
- 避免 `SELECT *`，只查询需要的字段：`select(User.id, User.email)`
- 关联查询使用 eager loading 避免 N+1：
  ```python
  from sqlalchemy.orm import joinedload, selectinload

  # 一对一/多对一 用 joinedload
  stmt = select(User).options(joinedload(User.organization))

  # 一对多 用 selectinload
  stmt = select(Organization).options(selectinload(Organization.members))
  ```
- 列表接口必须分页（page + page_size）
- 排序字段必须有 MySQL 索引
- 避免在循环中执行查询

### FastAPI 后端
- 异步端点使用 `async def`，同步操作使用 `def`
- 数据库 session 通过 Dependency 注入，不手动管理生命周期
- 长耗时操作使用后台任务：`BackgroundTasks`
- 响应模型使用 Pydantic `response_model` 过滤敏感字段

### React 组件
- 大列表使用虚拟滚动（@tanstack/react-virtual）
- 避免在渲染中创建新对象/函数（使用 useMemo/useCallback）
- 图片使用懒加载
- 避免组件不必要的 re-render
- API 数据使用 React Query 缓存，避免重复请求

## 3. 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| React 组件 | PascalCase | `CreditBalanceCard` |
| React 组件文件 | PascalCase | `CreditBalanceCard.tsx` |
| 前端函数/变量 | camelCase | `fetchCreditBalance` |
| 前端常量 | UPPER_SNAKE | `MAX_CREDITS_PER_POOL` |
| TypeScript 类型 | PascalCase | `CreditPool`, `UserRole` |
| 前端工具文件 | kebab-case | `credit-utils.ts` |
| Python 类 | PascalCase | `CreditService` |
| Python 函数/变量 | snake_case | `consume_credits` |
| Python 常量 | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| Python 文件 | snake_case | `credit_service.py` |
| 数据库表 | snake_case 复数 | `credit_pools` |
| 数据库列 | snake_case | `total_credits` |
| API 路径 | kebab-case | `/api/v1/credit-pools` |
| 环境变量 | UPPER_SNAKE | `STRIPE_SECRET_KEY` |

## 4. FastAPI 代码规范检查

### Pydantic Schema 规范
```python
# GOOD - 使用 Pydantic BaseModel 做请求/响应校验
from pydantic import BaseModel, Field

class CreditConsumeRequest(BaseModel):
    pool_id: str
    amount: float = Field(gt=0, description="扣减数量，必须大于0")
    description: str | None = None

class CreditConsumeResponse(BaseModel):
    success: bool
    remaining: float | None = None
    error: str | None = None
```

### 错误处理规范
```python
# GOOD - 统一异常处理
from fastapi import HTTPException

# 业务异常使用 HTTPException
raise HTTPException(status_code=400, detail="INSUFFICIENT_CREDITS")

# 全局异常处理器
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 记录日志
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```
