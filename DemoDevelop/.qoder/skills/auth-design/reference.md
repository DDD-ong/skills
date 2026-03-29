# 认证授权设计参考知识

## 1. FastAPI JWT 认证

### 基本设置
```python
# app/core/auth.py
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_session
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (await session.execute(
        select(User).where(User.id == user_id, User.status == "active")
    )).scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user
```

### 认证流程实现

```python
# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, Response
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.core.auth import create_access_token, create_refresh_token
from app.models import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=TokenResponse)
async def register(
    req: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    # 检查邮箱是否已注册
    existing = await session.execute(
        select(User).where(User.email == req.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=req.email,
        display_name=req.display_name,
        password_hash=pwd_context.hash(req.password),
    )
    session.add(user)
    await session.commit()

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    user = (await session.execute(
        select(User).where(User.email == req.email)
    )).scalar_one_or_none()

    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is inactive")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
```

## 2. 密码策略

| 要求 | 规则 |
|------|------|
| 最小长度 | 8 位 |
| 大写字母 | 至少 1 个 |
| 小写字母 | 至少 1 个 |
| 数字 | 至少 1 个 |
| 特殊符号 | 至少 1 个 (!@#$%^&*) |

```python
# app/schemas/auth.py
from pydantic import BaseModel, field_validator
import re

class RegisterRequest(BaseModel):
    email: str
    display_name: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少8位")
        if not re.search(r"[A-Z]", v):
            raise ValueError("需要至少一个大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("需要至少一个小写字母")
        if not re.search(r"[0-9]", v):
            raise ValueError("需要至少一个数字")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("需要至少一个特殊符号")
        return v
```

## 3. 权限矩阵详情

### 企业 Dashboard 权限

| 功能 | Owner | Admin | User |
|------|:-----:|:-----:|:----:|
| 查看 Overview | Yes | Yes | No |
| 查看 Accounts 列表 | Yes | Yes | No |
| 创建账号 | Yes | Yes | No |
| 批量创建账号 | Yes | Yes | No |
| Link Existing Account | Yes | No | No |
| 分配 Credits | Yes | Yes | No |
| Edit Password (User) | Yes | Yes | No |
| Edit Password (Admin) | No | No | No |
| 设为 Admin | Yes | No | No |
| 取消 Admin | Yes | No | No |
| Link to Order | Yes | No | No |
| 查看 Usage | Yes | Yes | No |
| 查看成员 Usage Details | Yes | Yes | No |

### 平台管理员专有操作

| 功能 | Platform Admin | Root Admin |
|------|:-------------:|:----------:|
| 创建组织 | Yes | Yes |
| 创建订单 | Yes | Yes |
| 创建账号 | Yes | Yes |
| Set Inactive | Yes | Yes |
| Reactivate | Yes | Yes |
| 修改账号邮箱/姓名 | Yes | Yes |
| 管理其他管理员 | No | Yes |

## 4. 应用层权限检查（FastAPI Dependencies）

### 角色检查 Dependency
```python
# app/core/permissions.py
from functools import wraps
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.auth import get_current_user
from app.core.database import get_session
from app.models import User, OrganizationMember

def require_role(*allowed_roles: str):
    """检查用户在指定组织中的角色"""
    async def dependency(
        org_id: str,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ):
        # 平台管理员 bypass
        if current_user.is_platform_admin:
            return current_user

        member = (await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == current_user.id,
            )
        )).scalar_one_or_none()

        if not member or member.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return dependency

def require_platform_admin():
    """限制仅平台管理员可访问"""
    async def dependency(
        current_user: User = Depends(get_current_user),
    ):
        if not current_user.is_platform_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform admin access required",
            )
        return current_user
    return dependency
```

### 使用示例
```python
# app/api/v1/organizations.py
from fastapi import APIRouter, Depends
from app.core.permissions import require_role, require_platform_admin

router = APIRouter(prefix="/organizations", tags=["organizations"])

@router.get("/{org_id}/members")
async def list_members(
    org_id: str,
    current_user = Depends(require_role("owner", "admin")),
):
    """Owner 和 Admin 可查看成员列表"""
    ...

@router.post("/{org_id}/members/{user_id}/set-admin")
async def set_admin(
    org_id: str,
    user_id: str,
    current_user = Depends(require_role("owner")),
):
    """仅 Owner 可设置 Admin"""
    ...

@router.post("/")
async def create_organization(
    current_user = Depends(require_platform_admin()),
):
    """仅平台管理员可创建组织"""
    ...
```

### 数据隔离查询模式
```python
# app/services/base.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User

async def get_org_filtered_query(
    session: AsyncSession,
    model,
    org_id: str,
    current_user: User,
):
    """应用层数据隔离：自动过滤 organization_id"""
    stmt = select(model)
    if not current_user.is_platform_admin:
        stmt = stmt.where(model.organization_id == org_id)
    return await session.execute(stmt)
```

## 5. Session / Token 管理

### 跨应用 Token 共享
```
官网 (marketing.altalex.com)
AI 平台 (app.altalex.com)          ← 共享 JWT Token
企业 Dashboard (dashboard.altalex.com)

方案: 使用顶级域 Cookie (.altalex.com)
- JWT Access Token 存储在 HttpOnly Cookie
- Cookie domain 设为 .altalex.com
- Refresh Token 用于续签
- 三端共享同一套 JWT 密钥验证
```

### FastAPI Cookie 设置
```python
# 登录成功后设置 Cookie
from fastapi import Response

@router.post("/login")
async def login(req: LoginRequest, response: Response, ...):
    ...
    access_token = create_access_token({"sub": str(user.id)})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        domain=".altalex.com",
        max_age=86400,  # 24h
    )
    return {"message": "Login successful"}
```

### React 前端路由守卫
```typescript
// frontend/src/components/AuthGuard.tsx
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

interface AuthGuardProps {
  children: React.ReactNode
  requiredRole?: string[]
}

export function AuthGuard({ children, requiredRole }: AuthGuardProps) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <PageLoading />

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requiredRole && !requiredRole.includes(user.role)) {
    return <Navigate to="/403" replace />
  }

  return <>{children}</>
}
```

## 6. 速率限制

```python
# app/middleware/rate_limit.py
from fastapi import Request, HTTPException
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)

async def rate_limit(request: Request, limit: int = 60, window: int = 60):
    """基于 IP 的速率限制"""
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}:{request.url.path}"

    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window)

    if current > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
        )
```
