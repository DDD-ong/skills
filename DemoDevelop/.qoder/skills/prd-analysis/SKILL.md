---
name: prd-analysis
version: 1.0.0
description: >
  Parse Alta Lex PRD documents to extract structured requirements.
  Use when analyzing product requirements, breaking down features into user stories,
  or extracting acceptance criteria from PRD files.
description_zh: >
  解析 Alta Lex PRD 文档，提取结构化需求。
  当需要分析产品需求、将功能拆解为用户故事、或从 PRD 中提取验收标准时使用。
---

# PRD Analysis

## 触发条件

当出现以下场景时使用此技能：
- 需要从 PRD 文档中提取结构化需求
- 将产品功能拆解为可执行的用户故事
- 生成验收标准和测试条件
- 分析跨模块依赖关系

## 执行流程

1. **文档读取**: 读取 PRD 文档（支持 `.docx` 和 `.md` 格式），如为 docx 格式则先转换为可读文本
2. **域识别**: 按 Alta Lex 六大业务域分类：
   - 官网 (Marketing Website)
   - AI法律工作台 (Alta Lex AI)
   - 企业Dashboard (Enterprise Dashboard)
   - 平台管理员后台 (Platform Admin)
   - Credits 计费系统 (Credits System)
   - 认证授权系统 (Auth System)
3. **层级拆解**: 对每个域按 Epic > Feature > User Story 进行层级拆解
4. **验收标准**: 为每个 User Story 生成 Given/When/Then 格式的验收标准
5. **依赖标注**: 识别并标注跨域依赖（如 Credits 贯穿官网、AI平台、Dashboard）
6. **优先级标注**: 根据业务影响标注 P0/P1/P2 优先级
7. **文件产出**: 按域分文件输出到 `docs/requirements/` 目录

## 输入要求

- PRD 文档文件路径（如 `Alta_Lex_PRD_v3.2.docx`）
- 可选：特定功能模块的分析范围限定

## 输出规范

每个域产出一个独立的需求文件，格式如下：

```markdown
---
artifact_type: requirement
produced_by: product-manager
version: "1.0"
status: draft
depends_on: []
---

# Epic: [域名称]

## Feature 1: [功能名]

### US-001: [用户故事标题]

**As a** [角色],
**I want to** [目标],
**So that** [价值].

**Priority**: P0/P1/P2

**Acceptance Criteria**:
- **Given** [前置条件], **When** [操作], **Then** [预期结果]
- **Given** [前置条件], **When** [操作], **Then** [预期结果]

**Dependencies**: [跨域依赖列表]
```

输出文件命名约定：
- `docs/requirements/epic-marketing-website.md`
- `docs/requirements/epic-alta-lex-ai.md`
- `docs/requirements/epic-enterprise-dashboard.md`
- `docs/requirements/epic-platform-admin.md`
- `docs/requirements/epic-credits-system.md`
- `docs/requirements/epic-auth-system.md`

## 质量检查

- [ ] 每个 User Story 都有至少一条验收标准
- [ ] 跨域依赖已识别并标注
- [ ] 优先级已按 P0/P1/P2 标注
- [ ] 所有账户类型（纯个人/纯组织/双池）的场景都已覆盖
- [ ] 权限矩阵（Owner/Admin/User/平台管理员）的操作都已纳入
- [ ] Credits 相关的业务规则（双池隔离、额度分配、过期处理）完整覆盖
