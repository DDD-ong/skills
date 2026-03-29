---
name: arch-design
version: 1.0.0
description: >
  Design system architecture for Alta Lex platform using C4 model.
  Use when making architectural decisions, defining system boundaries,
  or creating ADR documents.
description_zh: >
  基于 C4 模型为 Alta Lex 平台设计系统架构。
  当需要做架构决策、定义系统边界、或创建 ADR 文档时使用。
---

# Architecture Design

## 触发条件

当出现以下场景时使用此技能：
- 进行系统级架构设计或重构
- 做技术选型决策并记录 ADR
- 定义系统边界、模块划分和组件职责
- 评估跨模块变更的影响范围

## 执行流程

1. **需求读入**: 读取 `docs/requirements/` 下的需求文档
2. **约束确认**: 确认技术栈约束（见 reference.md）
3. **架构建模**: 使用 C4 模型产出三层视图：
   - **System Context**: 系统与外部系统的关系（Stripe, Xero, OpenAI）
   - **Container**: 内部容器划分（React SPA, FastAPI Backend, MySQL, Redis）
   - **Component**: 关键模块的组件设计（Credits Engine, Auth Module）
4. **决策记录**: 对每个关键技术决策产出 ADR 文档
5. **影响分析**: 评估架构变更对现有模块的影响
6. **文件产出**: 输出到 `docs/architecture/` 目录

## 输入要求

- 需求文档（`docs/requirements/epic-*.md`）
- 可选：特定变更的影响分析请求

## 输出规范

架构文档使用 YAML frontmatter：
```yaml
---
artifact_type: architecture
produced_by: system-architect
version: "1.0"
status: draft
depends_on:
  - docs/requirements/epic-*.md
---
```

输出文件：
- `docs/architecture/system-context.md` - 系统上下文图
- `docs/architecture/container-diagram.md` - 容器图
- `docs/architecture/tech-stack.md` - 技术栈决策
- `docs/architecture/adr/NNN-title.md` - 架构决策记录

使用 [templates.md](templates.md) 中的模板格式。

## 质量检查

- [ ] 所有外部系统依赖已识别（Stripe, Xero, OpenAI, Email Service）
- [ ] 容器边界清晰，职责单一
- [ ] 数据流方向已标注
- [ ] 安全边界已定义（认证、应用层权限控制、API Gateway）
- [ ] 性能关键路径已识别（Credits 扣减、实时同步）
- [ ] ADR 格式完整（Context, Decision, Consequences）
