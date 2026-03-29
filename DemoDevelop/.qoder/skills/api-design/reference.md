# API 设计参考知识

## 1. API 端点域划分

### 认证 (Auth)
| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | /api/v1/auth/signup | 邮箱注册 | Public |
| POST | /api/v1/auth/login | 邮箱+密码登录 | Public |
| POST | /api/v1/auth/login/otp | 邮箱验证码登录 | Public |
| POST | /api/v1/auth/logout | 登出 | Authenticated |
| POST | /api/v1/auth/password/reset | 重置密码 | Public |
| PUT | /api/v1/auth/password | 修改密码 | Authenticated |

### 用户 (Users)
| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /api/v1/users/me | 获取当前用户信息 | Authenticated |
| PUT | /api/v1/users/me | 更新个人信息 | Authenticated |
| GET | /api/v1/users/me/credits | 获取个人 Credits 概览 | Authenticated |

### 组织 (Organizations)
| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /api/v1/organizations | 获取用户所属组织列表 | Authenticated |
| GET | /api/v1/organizations/:id | 获取组织详情 | Org Member |
| GET | /api/v1/organizations/:id/credits | 获取组织 Credits 概览 | Owner/Admin |
| GET | /api/v1/organizations/:id/members | 获取成员列表 | Owner/Admin |
| POST | /api/v1/organizations/:id/members | 批量添加成员 | Owner/Admin |
| PUT | /api/v1/organizations/:id/members/:uid | 更新成员信息 | Owner/Admin |
| PUT | /api/v1/organizations/:id/members/:uid/role | 设置成员角色 | Owner |
| PUT | /api/v1/organizations/:id/members/:uid/credits | 分配 Credits | Owner/Admin |

### 订单 (Orders)
| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /api/v1/orders | 获取订单列表 | Authenticated |
| GET | /api/v1/orders/:id | 获取订单详情 | Order Owner |
| POST | /api/v1/orders/checkout | 创建支付会话 (Stripe Checkout) | Authenticated |

### Credits
| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /api/v1/credits/balance | 获取当前余额（含个人池和组织池） | Authenticated |
| GET | /api/v1/credits/transactions | 获取 Credits 交易记录 | Authenticated |
| POST | /api/v1/credits/consume | 消耗 Credits（AI 功能调用） | Authenticated |

### 平台管理 (Admin)
| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /api/v1/admin/overview | 平台概览数据 | Platform Admin |
| GET | /api/v1/admin/organizations | 全平台组织列表 | Platform Admin |
| POST | /api/v1/admin/organizations | 创建组织 | Platform Admin |
| GET | /api/v1/admin/accounts | 全平台账号列表 | Platform Admin |
| PUT | /api/v1/admin/accounts/:id/status | 设置账号状态(Active/Inactive) | Platform Admin |
| POST | /api/v1/admin/orders | 创建订单（企业端） | Platform Admin |
| GET | /api/v1/admin/audit-log | 审计日志 | Platform Admin |

### Stripe Webhooks
| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | /api/v1/webhooks/stripe | Stripe 事件回调 | Stripe Signature |

## 2. 错误码体系

| 错误码 | HTTP Status | 描述 |
|--------|-------------|------|
| AUTH_REQUIRED | 401 | 未认证 |
| FORBIDDEN | 403 | 无权限 |
| NOT_FOUND | 404 | 资源不存在 |
| VALIDATION_ERROR | 422 | 请求参数验证失败 |
| INSUFFICIENT_CREDITS | 402 | Credits 余额不足 |
| ACCOUNT_INACTIVE | 403 | 账号已被冻结 |
| ACCOUNT_EXPIRED | 403 | 账号已过期 |
| CREDITS_ACCESS_DISABLED | 403 | Credits 消耗权限已关闭 |
| DUPLICATE_EMAIL | 409 | 邮箱已注册 |
| RATE_LIMITED | 429 | 请求频率超限 |
| INTERNAL_ERROR | 500 | 服务内部错误 |

## 3. FastAPI 路由组织参考

```python
# backend/app/main.py
from fastapi import FastAPI
from app.api.v1 import auth, users, organizations, credits, orders, admin, webhooks

app = FastAPI(title="Alta Lex API", version="1.0.0")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["Organizations"])
app.include_router(credits.router, prefix="/api/v1/credits", tags=["Credits"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
```

### FastAPI 端点示例
```python
# backend/app/api/v1/credits.py
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.schemas.credits import CreditBalanceResponse, ConsumeRequest

router = APIRouter()

@router.get("/balance", response_model=CreditBalanceResponse)
async def get_balance(current_user: User = Depends(get_current_user)):
    """获取当前用户的 Credits 余额（含个人池和组织池）"""
    ...

@router.post("/consume")
async def consume_credits(
    data: ConsumeRequest,
    current_user: User = Depends(get_current_user),
):
    """消耗 Credits（AI 功能调用时使用）"""
    ...
```

### Pydantic Schema 示例
```python
# backend/app/schemas/credits.py
from pydantic import BaseModel
from decimal import Decimal

class PoolBalance(BaseModel):
    total: Decimal
    used: Decimal
    remaining: Decimal
    expired: Decimal

class CreditBalanceResponse(BaseModel):
    success: bool = True
    data: dict  # { personal: PoolBalance | None, organization: PoolBalance | None }
```
