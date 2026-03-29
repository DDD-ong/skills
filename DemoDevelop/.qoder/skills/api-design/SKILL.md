---
name: api-design
version: 1.0.0
description: >
  Design RESTful API contracts for Alta Lex platform in OpenAPI 3.0 format.
  Use when creating new API endpoints, reviewing API design,
  or updating API specifications.
description_zh: >
  以 OpenAPI 3.0 格式为 Alta Lex 平台设计 RESTful API 契约。
  当创建新 API 端点、审查 API 设计、或更新 API 规范时使用。
---

# API Design

## 触发条件

当出现以下场景时使用此技能：
- 设计新的 API 端点
- 审查或更新现有 API 设计
- 需要前后端对齐 API 契约
- 设计错误码体系或通用响应格式

## 执行流程

1. **需求分析**: 读取相关需求文档和架构文档
2. **端点识别**: 基于功能需求识别所需的 API 端点
3. **路由设计**: 按 RESTful 规范设计路径和 HTTP 方法
4. **Schema 定义**: 定义请求体、响应体、查询参数的 JSON Schema
5. **错误码设计**: 为每个端点定义可能的错误响应
6. **认证标注**: 标注每个端点的认证和权限要求
7. **文档产出**: 产出 OpenAPI 3.0 Spec 到 `docs/api/`（FastAPI 自动生成基础 Spec，手动补充业务文档）

## 输入要求

- 需求文档（`docs/requirements/epic-*.md`）
- 架构文档（`docs/architecture/*.md`）

## 输出规范

主要输出文件：
- `docs/api/openapi-spec.yaml` - OpenAPI 3.0 规范文件
- `docs/api/api-changelog.md` - API 变更日志

### API 设计约定

- **Base Path**: `/api/v1/`
- **认证**: JWT Bearer Token (`Authorization: Bearer <token>`)，FastAPI OAuth2PasswordBearer
- **内容类型**: `application/json`
- **分页**: `?page=1&page_size=20`（默认20，最大100）
- **排序**: `?sort_by=created_at&sort_order=desc`
- **过滤**: `?status=active&role=admin`

### 通用响应格式

```json
{
  "success": true,
  "data": {},
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "Not enough credits to perform this action",
    "details": {}
  }
}
```

## 质量检查

- [ ] 所有端点都有明确的 HTTP 方法和路径
- [ ] 请求/响应 Schema 完整定义
- [ ] 认证和权限要求已标注
- [ ] 错误码体系一致且有文档
- [ ] 分页、排序、过滤参数遵循统一约定
- [ ] 与需求文档中的功能点一一对应
