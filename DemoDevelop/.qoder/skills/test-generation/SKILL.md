---
name: test-generation
version: 1.0.0
description: >
  Generate test plans and automated test code for Alta Lex platform features.
  Use when creating test strategies, writing unit/integration/E2E tests,
  or verifying permission matrices.
description_zh: >
  为 Alta Lex 平台功能生成测试计划和自动化测试代码。
  当创建测试策略、编写单元/集成/E2E 测试、或验证权限矩阵时使用。
---

# Test Generation

## 触发条件

当出现以下场景时使用此技能：
- 为新功能生成测试计划和用例
- 编写单元测试、集成测试或 E2E 测试代码
- 验证权限矩阵的完整覆盖
- 评估测试覆盖率并补充缺失用例

## 执行流程

1. **需求分析**: 读取需求文档中的验收标准（AC）
2. **代码分析**: 读取被测代码的实现逻辑
3. **用例设计**: 设计正向、反向、边界测试用例
4. **测试编码**: 按测试金字塔层级编写测试代码
5. **Mock 设计**: 为外部依赖设计 Mock 策略
6. **文件产出**: 后端测试输出到 `backend/tests/`，前端测试输出到 `frontend/tests/`

## 输入要求

- 需求文档（`docs/requirements/epic-*.md`）中的验收标准
- 后端被测代码（`backend/app/**/*.py`）
- 前端被测代码（`frontend/src/**/*.ts(x)`）
- 可选：特定模块的测试覆盖要求

## 输出规范

### 测试目录结构
```
backend/tests/
├── unit/                    # 单元测试（pytest）
│   ├── services/
│   ├── models/
│   └── utils/
├── integration/             # 集成测试（pytest + httpx）
│   ├── api/
│   └── services/
├── conftest.py              # pytest fixtures
└── factories.py             # 测试数据工厂（factory_boy）

frontend/tests/
├── unit/                    # 单元测试（Jest / Vitest）
│   ├── components/
│   ├── hooks/
│   └── utils/
├── integration/             # 集成测试（Jest + MSW）
│   └── pages/
├── e2e/                     # E2E 测试（Playwright）
│   ├── auth.spec.ts
│   ├── credits.spec.ts
│   ├── dashboard.spec.ts
│   └── admin.spec.ts
└── setup.ts                 # 测试环境配置
```

### 测试文件命名
- 后端: `test_*.py`（pytest 约定）
- 前端单元/集成: `*.test.ts` 或 `*.test.tsx`
- 前端 E2E: `*.spec.ts`
- 与源文件同名: `credits_service.py` → `test_credits_service.py`

### 后端测试结构约定
```python
# pytest 风格
class TestCreditService:
    """Credits 服务测试"""

    async def test_consume_success(self, session, credit_pool):
        """正常扣减应成功并返回新余额"""
        # Arrange
        # Act
        # Assert

    async def test_consume_insufficient_balance(self, session, credit_pool):
        """余额不足时应拒绝扣减"""
        ...
```

### 前端测试结构约定
```typescript
describe('ModuleName', () => {
  describe('functionName', () => {
    it('should [expected behavior] when [condition]', () => {
      // Arrange
      // Act
      // Assert
    })
  })
})
```

## 质量检查

- [ ] 每个验收标准至少有一个测试用例覆盖
- [ ] 边界条件已测试（空值、最大值、并发）
- [ ] 异常路径已测试（网络错误、权限拒绝、余额不足）
- [ ] Mock 策略合理，不过度依赖 Mock
- [ ] E2E 测试覆盖关键用户路径
- [ ] 测试可独立运行，无顺序依赖
