# 测试生成参考知识

## 1. Alta Lex 高优先级测试场景

### Credits 系统测试矩阵

| 场景 | 测试类型 | 优先级 |
|------|---------|--------|
| 正常扣减 Credits | Unit | P0 |
| 余额不足时拒绝扣减 | Unit | P0 |
| 并发扣减（多请求同时） | Integration | P0 |
| 个人池和组织池隔离 | Integration | P0 |
| 双池账号切换消耗池 | Integration | P1 |
| Credits 过期自动标记 | Unit | P1 |
| 额度分配（Owner 操作） | Integration | P1 |
| 额度分配（Admin 操作） | Integration | P1 |
| Inactive 账号冻结额度 | Integration | P1 |
| Reactivate 恢复额度 | Integration | P1 |
| Credits 为 0 时的 UI 提示 | E2E | P1 |
| 即将到期 Credits 警告 | E2E | P2 |

### 权限矩阵测试

| 操作 | Owner | Admin | User | Platform Admin |
|------|:-----:|:-----:|:----:|:--------------:|
| 查看组织概览 | ALLOW | ALLOW | DENY | ALLOW |
| 创建账号 | ALLOW | ALLOW | DENY | ALLOW |
| 分配 Credits | ALLOW | ALLOW | DENY | ALLOW |
| 设为 Admin | ALLOW | DENY | DENY | ALLOW |
| Set Inactive | DENY | DENY | DENY | ALLOW |
| Reactivate | DENY | DENY | DENY | ALLOW |
| Link to Order | ALLOW | DENY | DENY | ALLOW |
| Edit Password (User) | ALLOW | ALLOW | DENY | ALLOW |
| Edit Password (Admin) | DENY | DENY | DENY | ALLOW |
| 删除账号 | DENY | DENY | DENY | DENY |

每个单元格需要一个测试用例验证。

### 支付流测试场景

| 场景 | 测试类型 | Mock 策略 |
|------|---------|----------|
| Stripe Checkout 成功 | Integration | Mock Stripe SDK |
| Stripe Checkout 失败 | Integration | Mock Stripe SDK |
| Webhook: checkout.session.completed | Integration | Mock Webhook payload |
| Webhook: invoice.paid (续费) | Integration | Mock Webhook payload |
| Webhook: customer.subscription.deleted | Integration | Mock Webhook payload |
| Webhook 幂等性（重复事件） | Integration | Mock Webhook payload |
| Webhook 签名验证失败 | Integration | Invalid signature |
| GST 计税 (新加坡 9%) | Unit | - |

## 2. 后端测试工具配置参考

### pytest 配置
```ini
# backend/pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --cov=app --cov-report=term-missing"

[tool.coverage.run]
source = ["app"]
omit = ["app/core/config.py", "app/main.py"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

### pytest conftest.py（核心 Fixtures）
```python
# backend/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.core.database import get_session
from app.models import Base

TEST_DATABASE_URL = "mysql+aiomysql://root:testpass@localhost:3306/altalex_test"

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(session):
    """FastAPI 测试客户端，注入测试数据库 session"""
    def override_get_session():
        return session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

### 测试数据工厂（factory_boy）
```python
# backend/tests/factories.py
import factory
from factory import fuzzy
from app.models import User, Organization, CreditPool

class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    display_name = factory.Faker("name")
    password_hash = "$2b$12$test_hash"
    status = "active"
    is_platform_admin = False

class OrganizationFactory(factory.Factory):
    class Meta:
        model = Organization

    name = factory.Faker("company")
    status = "active"

class CreditPoolFactory(factory.Factory):
    class Meta:
        model = CreditPool

    pool_type = "personal"
    total_credits = 1500.0
    used_credits = 0.0
    expired_credits = 0.0
    status = "active"
```

### 后端单元测试示例
```python
# backend/tests/unit/services/test_credits_service.py
import pytest
from decimal import Decimal
from app.services.credits import CreditService
from tests.factories import CreditPoolFactory, UserFactory

class TestCreditServiceConsume:
    async def test_consume_success(self, session):
        """正常扣减应成功"""
        pool = CreditPoolFactory(total_credits=1500, used_credits=300)
        session.add(pool)
        await session.flush()

        service = CreditService(session)
        result = await service.consume(
            pool_id=str(pool.id),
            user_id="test-user-id",
            amount=Decimal("100"),
        )

        assert result["success"] is True
        assert result["remaining"] == 1100.0

    async def test_consume_insufficient_balance(self, session):
        """余额不足时应拒绝扣减"""
        pool = CreditPoolFactory(total_credits=100, used_credits=90)
        session.add(pool)
        await session.flush()

        service = CreditService(session)
        result = await service.consume(
            pool_id=str(pool.id),
            user_id="test-user-id",
            amount=Decimal("50"),
        )

        assert result["success"] is False
        assert result["error"] == "INSUFFICIENT_CREDITS"

    async def test_consume_inactive_pool(self, session):
        """冻结池应拒绝消耗"""
        pool = CreditPoolFactory(status="inactive", total_credits=1000)
        session.add(pool)
        await session.flush()

        service = CreditService(session)
        result = await service.consume(
            pool_id=str(pool.id),
            user_id="test-user-id",
            amount=Decimal("10"),
        )

        assert result["success"] is False
        assert result["error"] == "POOL_NOT_FOUND_OR_INACTIVE"
```

### 后端集成测试示例（API 测试）
```python
# backend/tests/integration/api/test_auth.py
import pytest
from httpx import AsyncClient

class TestAuthAPI:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "display_name": "Test User",
            "password": "StrongPass1!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        # 第一次注册
        await client.post("/api/v1/auth/register", json={
            "email": "dup@test.com",
            "display_name": "User 1",
            "password": "StrongPass1!",
        })
        # 重复注册
        response = await client.post("/api/v1/auth/register", json={
            "email": "dup@test.com",
            "display_name": "User 2",
            "password": "StrongPass1!",
        })
        assert response.status_code == 409

    async def test_login_wrong_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@test.com",
            "password": "WrongPass1!",
        })
        assert response.status_code == 401

class TestPermissions:
    async def test_user_cannot_access_admin_endpoint(self, client: AsyncClient, user_token):
        """普通用户不应能访问管理员端点"""
        response = await client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"name": "New Org"},
        )
        assert response.status_code == 403
```

## 3. 前端测试工具配置参考

### Vitest 配置
```typescript
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        statements: 80,
        branches: 75,
        functions: 80,
        lines: 80,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

### Playwright 配置
```typescript
// frontend/playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
  ],
})
```

### MSW Mock 示例（前端 API Mock）
```typescript
// frontend/tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/v1/credits/balance', () => {
    return HttpResponse.json({
      success: true,
      data: {
        personal: { total: 1500, used: 300, remaining: 1200 },
        organization: null,
      },
    })
  }),
  http.post('/api/v1/credits/consume', async ({ request }) => {
    const body = await request.json() as { amount: number }
    return HttpResponse.json({
      success: true,
      data: { remaining: 1190, consumed: body.amount },
    })
  }),
]
```

## 4. 关键 E2E 用户路径

1. **个人注册到首次使用**: 注册 → 选择方案 → Stripe 支付 → 进入 AI 平台 → 使用功能 → 查看余额
2. **企业开户流程**: 管理员登录 → 创建组织 → 创建订单 → 批量创建账号 → 分配 Credits
3. **Credits 全链路**: 登录 → 使用 AI 功能 → Credits 扣减 → 余额更新 → 查看用量记录
4. **权限验证**: User 角色登录 → 尝试访问 Admin 功能 → 验证权限拒绝
