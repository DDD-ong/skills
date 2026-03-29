# 数据库设计参考知识

## 1. 核心实体清单（MySQL + SQLAlchemy）

### users
```python
# backend/app/models/user.py
class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(100))
    username = Column(String(50))                        # 兼容存量字母数字 username
    password_hash = Column(Text)
    status = Column(String(20), default="active")        # active / inactive / expired
    is_platform_admin = Column(Boolean, default=False)
    personal_credit_pool_id = Column(CHAR(36), ForeignKey("credit_pools.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### organizations
```python
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### organization_members
```python
class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = Column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="user")            # owner / admin / user
    org_credit_pool_id = Column(CHAR(36), ForeignKey("credit_pools.id"))
    credits_access = Column(Boolean, default=True)       # 可消耗 Credits 开关
    allocated_credits = Column(DECIMAL(12, 2), default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)
```

### credit_pools
```python
class CreditPool(Base):
    __tablename__ = "credit_pools"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    pool_type = Column(String(20), nullable=False)       # personal / organization
    owner_user_id = Column(CHAR(36), ForeignKey("users.id"))
    organization_id = Column(CHAR(36), ForeignKey("organizations.id"))
    total_credits = Column(DECIMAL(12, 2), default=0)
    used_credits = Column(DECIMAL(12, 2), default=0)
    expired_credits = Column(DECIMAL(12, 2), default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # remaining = total - used - expired (计算字段)
```

### credit_transactions
```python
class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    credit_pool_id = Column(CHAR(36), ForeignKey("credit_pools.id"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id"))
    transaction_type = Column(String(30), nullable=False) # consume / allocate / expire / refund / topup
    amount = Column(DECIMAL(12, 2), nullable=False)
    balance_after = Column(DECIMAL(12, 2), nullable=False)
    description = Column(Text)
    metadata = Column(JSON, default={})                   # MySQL JSON 类型
    created_at = Column(DateTime, default=func.now())
```

### orders
```python
class Order(Base):
    __tablename__ = "orders"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    order_type = Column(String(30), nullable=False)      # individual_subscription / enterprise / credit_package
    organization_id = Column(CHAR(36), ForeignKey("organizations.id"))
    user_id = Column(CHAR(36), ForeignKey("users.id"))
    stripe_subscription_id = Column(String(255))
    stripe_checkout_session_id = Column(String(255))
    status = Column(String(20), default="active")        # active / expired / cancelled
    total_credits = Column(DECIMAL(12, 2))
    seats = Column(Integer, default=1)
    amount_paid = Column(DECIMAL(12, 2))
    currency = Column(String(3), default="USD")
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### audit_logs
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id = Column(CHAR(36), ForeignKey("users.id"))
    actor_type = Column(String(20), nullable=False)      # user / admin / system
    action = Column(String(50), nullable=False)          # create_account / set_inactive / allocate_credits
    target_type = Column(String(50))                     # user / organization / order
    target_id = Column(CHAR(36))
    details = Column(JSON, default={})
    ip_address = Column(String(45))                      # IPv4/IPv6
    created_at = Column(DateTime, default=func.now())
```

## 2. 应用层权限隔离（替代 RLS）

```python
# backend/app/dependencies/auth.py
from fastapi import Depends, HTTPException, status

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """解码 JWT Token 获取当前用户"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user = await user_repo.get_by_id(payload["sub"])
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="Invalid or inactive user")
    return user

async def require_org_role(
    org_id: str,
    roles: list[str],
    current_user: User = Depends(get_current_user)
) -> OrganizationMember:
    """检查用户在指定组织中的角色"""
    member = await org_member_repo.get(org_id=org_id, user_id=current_user.id)
    if not member or member.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return member

async def require_platform_admin(current_user: User = Depends(get_current_user)):
    """要求平台管理员权限"""
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform admin required")
    return current_user
```

### 数据隔离查询模式
```python
# 所有组织数据查询自动加 organization_id 过滤
async def get_org_members(org_id: str, db: AsyncSession):
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org_id)
    )
    return result.scalars().all()
```

## 3. 索引建议

```sql
-- 高频查询索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_org_members_user ON organization_members(user_id);
CREATE INDEX idx_org_members_org ON organization_members(organization_id);
CREATE INDEX idx_credit_transactions_pool ON credit_transactions(credit_pool_id);
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id);
CREATE INDEX idx_orders_org ON orders(organization_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id);
CREATE INDEX idx_audit_logs_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
```

## 4. Credits 扣减事务模式（MySQL + SQLAlchemy）

```python
# backend/app/services/credits.py
async def consume_credits(
    db: AsyncSession,
    pool_id: str,
    user_id: str,
    amount: Decimal,
    description: str | None = None,
) -> dict:
    """事务安全的 Credits 扣减"""
    async with db.begin():
        # SELECT FOR UPDATE 获取行锁
        result = await db.execute(
            select(CreditPool)
            .where(CreditPool.id == pool_id)
            .with_for_update()
        )
        pool = result.scalar_one_or_none()
        if not pool:
            raise ValueError("Credit pool not found")

        remaining = pool.total_credits - pool.used_credits - pool.expired_credits
        if remaining < amount:
            raise InsufficientCreditsError(f"Remaining: {remaining}, Required: {amount}")

        # 扣减
        pool.used_credits += amount
        pool.updated_at = func.now()

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
        db.add(tx)

    return {"success": True, "remaining": float(new_balance)}
```

## 5. Alembic 迁移配置

```python
# backend/alembic/env.py 关键配置
from app.models import Base
target_metadata = Base.metadata

# 生成新迁移
# alembic revision --autogenerate -m "create users table"

# 执行迁移
# alembic upgrade head

# 回滚
# alembic downgrade -1
```

## 6. MySQL vs PostgreSQL 注意事项

| 特性 | PostgreSQL | MySQL 替代方案 |
|------|-----------|---------------|
| UUID 类型 | `UUID` | `CHAR(36)` |
| JSONB | `JSONB` | `JSON` |
| TIMESTAMPTZ | `TIMESTAMPTZ` | `DATETIME` |
| INET | `INET` | `VARCHAR(45)` |
| gen_random_uuid() | 内置函数 | 应用层 `uuid4()` |
| RLS | `CREATE POLICY` | 应用层 FastAPI Dependencies |
| 存储过程 | PL/pgSQL | MySQL Stored Procedure 或应用层 |
