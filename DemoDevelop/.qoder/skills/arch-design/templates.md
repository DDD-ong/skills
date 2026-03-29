# 架构文档模板

## ADR (Architecture Decision Record) 模板

```markdown
---
artifact_type: architecture
produced_by: system-architect
version: "1.0"
status: draft
depends_on: []
---

# ADR-NNN: [决策标题]

## 状态
Proposed / Accepted / Deprecated / Superseded by ADR-XXX

## 上下文 (Context)
描述问题背景和驱动因素。什么业务或技术需求推动了此决策？

## 决策 (Decision)
我们决定采用 [方案]。

### 考虑的备选方案
1. **方案 A**: [描述] - 优点: ... / 缺点: ...
2. **方案 B**: [描述] - 优点: ... / 缺点: ...

## 影响 (Consequences)

### 正面影响
- ...

### 负面影响
- ...

### 风险
- ...
```

## System Context 文档模板

```markdown
---
artifact_type: architecture
produced_by: system-architect
version: "1.0"
status: draft
depends_on:
  - docs/requirements/epic-*.md
---

# System Context Diagram

## 概述
[系统整体描述]

## 系统上下文

### 内部系统
| 系统 | 描述 | 技术 |
|------|------|------|
| ... | ... | ... |

### 外部系统
| 系统 | 关系 | 协议 |
|------|------|------|
| ... | ... | ... |

### 用户角色
| 角色 | 描述 | 交互方式 |
|------|------|---------|
| ... | ... | ... |

## 数据流
[描述主要数据流向]

## 安全边界
[定义信任边界和认证点]
```

## Container Diagram 文档模板

```markdown
---
artifact_type: architecture
produced_by: system-architect
version: "1.0"
status: draft
depends_on:
  - docs/architecture/system-context.md
---

# Container Diagram

## 容器列表

### [容器名称]
- **技术**: [使用的技术栈]
- **职责**: [核心职责描述]
- **通信**: [与其他容器的通信方式]

## 容器间通信
| 来源 | 目标 | 协议 | 数据 |
|------|------|------|------|
| ... | ... | ... | ... |
```

## Tech Stack 文档模板

```markdown
---
artifact_type: architecture
produced_by: system-architect
version: "1.0"
status: draft
depends_on: []
---

# Technology Stack

## 选型总览

### 前端
| 需求 | 选型 | 理由 |
|------|------|------|
| ... | ... | ... |

### 后端
| 需求 | 选型 | 理由 |
|------|------|------|
| ... | ... | ... |

### 基础设施
| 需求 | 选型 | 理由 |
|------|------|------|
| ... | ... | ... |

## 版本锁定
[关键依赖的版本要求]

## 兼容性矩阵
[各组件间的兼容性说明]
```
