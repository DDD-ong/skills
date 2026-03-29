---
name: db-schema-design
version: 1.0.0
description: >
  Design MySQL database schemas with application-level access control for Alta Lex.
  Use when creating or modifying database tables, designing permission strategies,
  or generating Alembic migration files.
description_zh: >
  为 Alta Lex 设计 MySQL 数据库表结构和应用层访问控制策略。
  当创建或修改数据库表、设计权限策略、或生成 Alembic 迁移文件时使用。
---

# Database Schema Design

## 触发条件

当出现以下场景时使用此技能：
- 设计新的数据库表或修改现有表结构
- 设计应用层权限校验策略
- 生成 Alembic 迁移文件
- 设计索引和性能优化方案

## 执行流程

1. **实体识别**: 基于需求和架构文档识别业务实体
2. **表结构设计**: 设计 MySQL 表（列、类型、约束、默认值）
3. **关系设计**: 设计表间关系（外键、联合表）
4. **索引设计**: 为查询热点设计索引
5. **权限策略**: 为每张表设计应用层权限检查（FastAPI Dependencies）
6. **触发器设计**: 设计必要的业务逻辑触发（如 Credits 余额更新）
7. **迁移文件**: 生成 Alembic Migration
8. **ER 图产出**: 使用 Mermaid 格式产出 ER 图

## 输入要求

- 需求文档（`docs/requirements/epic-*.md`）
- 架构文档（`docs/architecture/*.md`）

## 输出规范

文档输出到 `docs/database/`，迁移文件到 `backend/alembic/versions/`。

所有文档使用 YAML frontmatter：
```yaml
---
artifact_type: schema
produced_by: system-architect
version: "1.0"
status: draft
depends_on:
  - docs/architecture/container-diagram.md
---
```

### 表命名约定
- 使用 snake_case 复数形式：`users`, `organizations`, `credit_pools`
- 联合表：`organization_members`, `order_accounts`
- 审计表：`audit_logs`
- 所有表必须包含 `id`, `created_at`, `updated_at` 字段

### Migration 文件命名
- 使用 Alembic 自动生成的版本号格式
- 示例：`backend/alembic/versions/a1b2c3d4_create_users_table.py`

## 质量检查

- [ ] 所有实体都有对应的表
- [ ] 外键关系完整且有级联策略
- [ ] 查询热点有索引覆盖
- [ ] 应用层权限校验规则完整覆盖所有敏感操作
- [ ] Credits 相关表支持事务安全操作（SELECT FOR UPDATE）
- [ ] 审计日志表结构能记录所有关键操作
- [ ] ER 图与实际 Schema 一致
- [ ] MySQL 特有类型使用正确（如 JSON 代替 JSONB, DATETIME 代替 TIMESTAMPTZ）
