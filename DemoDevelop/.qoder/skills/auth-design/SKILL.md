---
name: auth-design
version: 1.0.0
description: >
  Design and implement unified authentication and authorization for Alta Lex.
  Use when working on user auth, JWT tokens, organization roles,
  or multi-tenant data isolation with application-layer access control.
description_zh: >
  设计和实现 Alta Lex 的统一认证和授权体系。
  当处理用户认证、JWT Token、组织角色、或基于应用层的多租户数据隔离时使用。
---

# Auth Design

## 触发条件

当出现以下场景时使用此技能：
- 设计或修改用户认证流程（FastAPI JWT）
- 实现组织角色和权限管理
- 设计应用层数据隔离策略（替代 RLS）
- 处理跨应用的 Session/Token 共享
- 实现密码策略和安全要求

## 执行流程

1. **需求确认**: 确认认证和权限相关需求
2. **Auth 设计**: 设计 FastAPI JWT 认证方案
3. **权限模型**: 设计基于角色的权限矩阵
4. **数据隔离**: 为每个资源设计应用层权限检查（FastAPI Dependencies）
5. **Session 管理**: 设计跨应用的 Token 共享方案
6. **安全加固**: 实现密码策略、速率限制等安全措施
7. **代码产出**: 输出 Auth 中间件和权限检查代码

## 输入要求

- 需求文档中的认证相关章节
- 数据库设计（`docs/database/*.md`）

## 输出规范

### 认证流程设计
```
注册: Email + Password → FastAPI 端点 → 创建 users 记录 → 发送验证邮件
登录: Email + Password → FastAPI 端点 → 验证 → 签发 JWT Token → HttpOnly Cookie
OTP:  Email → 发送验证码 → 验证码校验 → JWT Token
SSO:  OAuth Provider → FastAPI OAuth 回调 → 关联/创建用户 → JWT Token
```

### 权限检查模式
```python
# FastAPI Dependency 权限检查
async def check_permission(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    session: AsyncSession = ...,
) -> bool:
    # 1. 检查是否为平台管理员
    # 2. 检查组织角色 (owner/admin/user)
    # 3. 基于角色和操作匹配权限矩阵
```

### 应用层数据隔离要求
- 所有涉及组织数据的查询必须在 WHERE 条件中过滤 organization_id
- 平台管理员可跳过组织过滤
- 通过 FastAPI Dependencies 统一注入权限检查逻辑

## 质量检查

- [ ] 密码策略满足要求（8位+大小写+数字+特殊符号）
- [ ] JWT Token 过期策略合理
- [ ] 应用层权限检查覆盖所有资源的 CRUD
- [ ] 权限矩阵与 PRD 一致
- [ ] 跨应用 Token 共享方案可行
- [ ] 敏感操作记录到审计日志
