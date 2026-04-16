# Legal AI Assistant - OpenClaw 集成 API 文档

> **版本**: v1.0  
> **更新日期**: 2026-04-08  
> **适用对象**: OpenClaw 开发团队  
> **基础URL**: `https://api.alta-lex.ai/api`

---

## 目录

1. [项目概述](#1-项目概述)
2. [认证机制](#2-认证机制)
3. [通用规范](#3-通用规范)
4. [功能模块接口](#4-功能模块接口)
   - 4.1 [合同起草 (Contract Draft)](#41-合同起草-contract-draft)
   - 4.2 [合同审查 (Contract Review)](#42-合同审查-contract-review)
   - 4.3 [合同比对 (Contract Compare)](#43-合同比对-contract-compare)
   - 4.4 [法律研究 (Legal Research)](#44-法律研究-legal-research)
   - 4.5 [IPO支持 (IPO Support)](#45-ipo支持-ipo-support)
   - 4.6 [谈判策略 (Negotiation Playbook)](#46-谈判策略-negotiation-playbook)
   - 4.7 [文档翻译 (Document Translation)](#47-文档翻译-document-translation)
   - 4.8 [尽职调查 (Due Diligence)](#48-尽职调查-due-diligence)
   - 4.9 [合规审查 (Legal Compliance)](#49-合规审查-legal-compliance)
   - 4.10 [脱敏处理 (Desensitization)](#410-脱敏处理-desensitization)
   - 4.11 [表格处理 (Tabular Analysis)](#411-表格处理-tabular-analysis)
5. [SSE 流式响应规范](#5-sse-流式响应规范)
6. [错误码说明](#6-错误码说明)
7. [调用流程示例](#7-调用流程示例)
8. [性能与限制](#8-性能与限制)

---

## 1. 项目概述

Legal AI Assistant 是一个基于 FastAPI 的法律领域 AI 应用系统，为律师和法务人员提供专业的 AI 辅助服务。

### 核心功能模块

| 模块 | 功能描述 | 适用场景 | 业务价值 |
|------|----------|----------|----------|
| **合同起草** | 基于模板和参数智能生成合同文档 | 快速生成标准合同、基于模板定制合同 | 提升合同起草效率 80% 以上 |
| **合同审查** | AI 智能审查合同条款和风险点 | 合同风险评估、条款合规检查 | 自动识别潜在法律风险 |
| **合同比对** | 多版本合同差异分析和对比 | 合同版本管理、修订追踪 | 精准定位合同变更内容 |
| **法律研究** | 法律条文检索和深度分析 | 法规查询、案例研究 | 快速获取权威法律依据 |
| **IPO支持** | IPO 检查清单生成和审核 | 上市合规检查、披露文件审核 | 确保 IPO 流程合规 |
| **谈判策略** | 生成谈判手册和策略建议 | 商业谈判准备、条款博弈 | 提供数据驱动的谈判建议 |
| **文档翻译** | 法律文档多语言翻译 | 跨境合同、国际法律文件 | 保持法律术语准确性 |
| **尽职调查** | 尽职调查分析和报告生成 | 并购尽调、投资审查 | 系统化识别目标公司风险 |
| **合规审查** | 法规合规性检查和风险评估 | 合规审计、法规变更应对 | 自动化合规检查流程 |
| **脱敏处理** | 敏感信息识别和脱敏处理 | 文档共享、隐私保护 | 自动识别并脱敏敏感信息 |
| **表格处理** | 表格数据提取和结构化分析 | 财务数据分析、统计报表 | 从文档中提取结构化数据 |

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        OpenClaw Client                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Legal AI Assistant                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Controllers │→ │  Services   │→ │   Integration       │  │
│  │   (API)     │  │  (Business) │  │ (Dify/Third-party)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌──────────┐
   │  MySQL  │   │  Redis  │   │   OSS    │
   │(Session)│   │ (Auth)  │   │ (Files)  │
   └─────────┘   └─────────┘   └──────────┘
```

---

## 2. 认证机制

### 2.1 认证方式

系统使用 **Redis Session** 进行身份验证，支持以下两种方式传递 Session ID：

#### 方式一：Cookie 认证（推荐浏览器端使用）
```http
Cookie: auth={session_id}
```

#### 方式二：Authorization Header 认证（推荐服务端/API 调用）
```http
Authorization: {session_id}
```

### 2.2 Session 获取流程

OpenClaw 系统需要先从用户认证服务获取有效的 Session ID，然后调用本系统 API。

```
┌──────────────┐         ┌──────────────┐         ┌──────────────────┐
│   用户登录    │────────▶│  认证服务     │────────▶│  获取 Session ID │
└──────────────┘         └──────────────┘         └──────────────────┘
                                                            │
                                                            ▼
┌──────────────┐         ┌──────────────────────────────────────────┐
│  返回结果    │◀────────│  调用 Legal AI API (带 Session ID)       │
└──────────────┘         └──────────────────────────────────────────┘
```

### 2.3 认证响应

**认证失败响应** (HTTP 200，业务错误):
```json
{
  "status": "error",
  "error": {
    "code": "A01001",
    "message": "Not logged in or session expired. Please log in again.",
    "timestamp": "2026-04-08T10:30:00+08:00",
    "path": "/api/createDraftSession"
  },
  "traceId": "1706355600000-a1b2c3d4"
}
```

---

## 3. 通用规范

### 3.1 请求规范

- **基础URL**: `https://api.alta-lex.ai/api`
- **协议**: HTTPS
- **字符编码**: UTF-8
- **Content-Type**: `application/json`

### 3.2 响应规范

所有 API 响应统一使用以下格式：

**成功响应**:
```json
{
  "status": "success",
  "message": "Operation successful",
  "data": { ... },
  "traceId": "1706355600000-a1b2c3d4"
}
```

**错误响应**:
```json
{
  "status": "error",
  "error": {
    "code": "A02002",
    "message": "Required parameters are missing",
    "timestamp": "2026-04-08T10:30:00+08:00",
    "path": "/api/createDraftSession"
  },
  "traceId": "1706355600000-a1b2c3d4"
}
```

### 3.3 Trace ID 追踪

每个请求都会返回唯一的 `traceId`，用于全链路追踪和问题排查。

**请求头传递**:
```http
X-Trace-ID: {trace_id}
```

### 3.4 文件 URL 规范

文件上传后返回的 URL 格式：
- **OSS 模式**: `https://{bucket}.oss.aliyuncs.com/{path}/{filename}`
- **本地模式**: `https://api.alta-lex.ai/api/preview/{filename}`

---

## 4. 功能模块接口

### 4.1 合同起草 (Contract Draft)

基于业务参数和可选模板生成合同文档，支持 SSE 流式响应。

#### 4.1.1 创建起草会话

**接口**: `POST /api/createDraftSession`

**功能**: 创建合同起草会话，保存业务参数，返回 sessionId

**请求参数**:
```json
{
  "industry": "Technology",
  "position": "Buyer",
  "scenario": "Software Licensing",
  "contractType": "License Agreement",
  "governingLaw": "PRC",
  "language": "Chinese",
  "templateFileUrl": "https://xxx/template.docx",
  "customerRequest": "Generate a software license agreement for enterprise use"
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| industry | string | 是 | 行业类型，如 Technology, Finance, Healthcare |
| position | string | 是 | 立场，如 Buyer, Seller, Lender, Borrower |
| scenario | string | 是 | 业务场景描述 |
| contractType | string | 是 | 合同类型 |
| governingLaw | string | 是 | 适用法律，如 PRC, HK, US, UK |
| language | string | 是 | 输出语言，如 Chinese, English |
| templateFileUrl | string | 否 | 模板文件 URL，提供则基于模板生成 |
| customerRequest | string | 否 | 用户自定义需求描述 |

**响应示例**:
```json
{
  "status": "success",
  "message": "",
  "sessionId": "sess_abc123def456",
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.1.2 流式生成合同

**接口**: `GET /api/commonGenerateSse?sessionId={sessionId}&chatId={chatId}`

**功能**: SSE 流式生成合同内容

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sessionId | string | 是 | 会话 ID，由 createDraftSession 返回 |
| chatId | string | 否 | 聊天 ID，首次调用可不传，系统自动生成 |

**SSE 响应格式**:
```
data: {"message": "合同条款内容...", "is_finished": false}

data: {"message": "更多内容...", "is_finished": false}

: heartbeat

data: {"message": "", "is_finished": true, "metadata": {"usage": {...}}}
```

#### 4.1.3 获取会话历史

**接口**: `GET /api/getDraftSessionHistory?sessionId={sessionId}`

**响应示例**:
```json
{
  "status": "success",
  "title": "Software License Agreement",
  "chats": [
    {
      "chatId": "chat_xyz789",
      "query": "Generate a software license agreement for enterprise use",
      "answer": "完整的合同内容...",
      "status": "completed",
      "editDocument": "",
      "editStatus": "0"
    }
  ],
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.1.4 获取会话列表

**接口**: `GET /api/getDraftSessionList`

**响应示例**:
```json
{
  "status": "success",
  "chats": [
    {
      "sessionId": "sess_abc123",
      "sessionName": "",
      "title": "Software License Agreement"
    }
  ],
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.1.5 删除会话

**接口**: `POST /api/removeDraftSession`

**请求参数**:
```json
{
  "sessionId": "sess_abc123def456"
}
```

---

### 4.2 合同审查 (Contract Review)

上传合同文件进行 AI 智能审查，支持 Summary（摘要）和 Edit（编辑）两种模式。

#### 4.2.1 提交审查任务

**接口**: `POST /api/common_review`

**功能**: 提交合同文件进行审查，返回任务标识

**请求参数**:
```json
{
  "industry": "Technology",
  "position": "Buyer",
  "scenario": "Software Licensing",
  "contractType": "License Agreement",
  "governingLaw": "PRC",
  "language": "Chinese",
  "customerRequest": "Please review the liability clauses",
  "fileUrl": "https://xxx/contract.docx",
  "reviewType": "1"
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| industry | string | 是 | 行业类型 |
| position | string | 是 | 立场 |
| scenario | string | 是 | 业务场景 |
| contractType | string | 是 | 合同类型 |
| fileUrl | string | 是 | 待审查文件 URL |
| reviewType | string | 是 | "1"=Summary 形式，"2"=Edit 形式 |
| governingLaw | string | 否 | 适用法律 |
| language | string | 否 | 输出语言 |
| customerRequest | string | 否 | 自定义审查要求 |

**响应示例**:
```json
{
  "status": "success",
  "message": "File is being processed",
  "task_data": "https://xxx/contract.docx",
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.2.2 获取审查结果

**接口**: `POST /api/getReviewAnswer`

**请求参数**:
```json
{
  "type": "contract_review",
  "filename": "contract.docx"
}
```

**响应示例** (Summary 形式):
```json
{
  "status": "success",
  "file_name": "contract.docx",
  "status": "completed",
  "processing_result": "<html>审查结果 HTML 内容</html>",
  "url": "https://api.alta-lex.ai/api/preview/contract.docx",
  "edit_document": null,
  "edit_status": null,
  "review_type": "1",
  "sub_session_id": null
}
```

**响应示例** (Edit 形式):
```json
{
  "status": "success",
  "file_name": "contract.docx",
  "status": "completed",
  "processing_result": "<html>原始合同 HTML</html>",
  "url": "https://api.alta-lex.ai/api/preview/contract.docx",
  "edit_document": "<html>AI 编辑后的合同 HTML</html>",
  "edit_status": "1",
  "review_type": "2",
  "sub_session_id": "sess_sub_123"
}
```

#### 4.2.3 获取文件列表

**接口**: `POST /api/listFiles`

**请求参数**:
```json
{
  "type": "contract_review"
}
```

#### 4.2.4 删除文件

**接口**: `POST /api/deleteFile`

**请求参数**:
```json
{
  "filename": "contract.docx"
}
```

---

### 4.3 合同比对 (Contract Compare)

对比两个合同版本的差异，生成详细的变更分析。

#### 4.3.1 创建比对会话

**接口**: `POST /api/createContractCompare`

**请求参数**:
```json
{
  "title": "Contract Version Comparison",
  "industry": "Technology",
  "position": "Buyer",
  "contractType": "License Agreement",
  "language": "Chinese",
  "originalContractUrl": "https://xxx/contract_v1.docx",
  "revisedContractUrl": "https://xxx/contract_v2.docx",
  "governingLaw": "PRC",
  "customerRequest": "Compare the liability clauses between versions"
}
```

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_compare_123",
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.3.2 流式生成比对结果

**接口**: `GET /api/commonGenerateSse/contractCompare?sessionId={sessionId}&chatId={chatId}`

**SSE 响应**: 流式返回差异分析结果

#### 4.3.3 获取比对历史

**接口**: `GET /api/getSessionHistory/contractCompare?sessionId={sessionId}`

---

### 4.4 法律研究 (Legal Research)

提供法律条文检索和深度分析，支持 Quick（快速）和 Search（深度研究）两种模式。

#### 4.4.1 创建分析会话

**接口**: `POST /api/createAnalysisSession`

**请求参数**:
```json
{
  "query": "Analyze the data protection requirements for fintech companies in Hong Kong",
  "researchType": "search",
  "fileUrls": [
    "https://xxx/document1.pdf",
    "https://xxx/document2.docx"
  ]
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 研究问题 |
| researchType | string | 是 | "quick"=快速分析，"search"=深度研究 |
| fileUrls | array | 否 | 参考文件 URL 列表，最多 5 个 |

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_research_123",
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.4.2 流式法律分析

**接口**: `POST /api/legalAnalysisSse`

**请求参数**:
```json
{
  "sessionId": "sess_research_123",
  "chatId": "chat_456",
  "query": "Additional question for follow-up",
  "fileUrls": [],
  "researchType": "search"
}
```

**说明**:
- 第一轮对话：query 和 fileUrls 从 session 中获取，请求体中可不传
- 后续对话：必须提供 query 参数，fileUrls 可选
- 深度研究模式 (search) 最多支持 10 轮对话

#### 4.4.3 获取会话列表和历史

**接口**: `GET /api/getAnalysisSessionList`

**接口**: `GET /api/getAnalysisSessionHistory?sessionId={sessionId}`

#### 4.4.4 删除会话

**接口**: `POST /api/removeAnalysisSession`

**请求参数**:
```json
{
  "sessionId": "sess_research_123"
}
```

---

### 4.5 IPO支持 (IPO Support)

针对香港联交所 IPO 流程生成检查清单和合规审核。

#### 4.5.1 创建 IPO 检查清单会话

**接口**: `POST /api/createIpoCheckListSession`

**请求参数**:
```json
{
  "title": "IPO Compliance Check",
  "connectedPerson": "Director",
  "connectTransactClass": "Share Transfer",
  "transactionClassification": "Connected Transaction",
  "involvesGuaranteesSecurity": true,
  "shareholderApproval": true,
  "circularRequirements": true,
  "otherRelevantFacts": "Company is planning IPO on HKEX",
  "fileUrl": "https://xxx/prospectus_draft.pdf"
}
```

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_ipo_123",
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.5.2 流式生成检查清单

**接口**: `GET /api/commonGenerateSse/ipoCheckList?sessionId={sessionId}&chatId={chatId}`

#### 4.5.3 获取检查清单历史

**接口**: `GET /api/getSessionHistory/ipoCheckList?sessionId={sessionId}`

---

### 4.6 谈判策略 (Negotiation Playbook)

基于合同类型和业务场景生成谈判手册和策略建议。

#### 4.6.1 创建谈判手册会话

**接口**: `POST /api/createNegotiationPlaybook`

**请求参数**:
```json
{
  "title": "Software License Negotiation",
  "industry": "Technology",
  "position": "Buyer",
  "scenario": "Enterprise Software Licensing",
  "contractType": "License Agreement",
  "language": "Chinese",
  "customerRequest": "Generate negotiation strategies for pricing and liability clauses",
  "fileUrl": "https://xxx/draft_contract.docx"
}
```

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_playbook_123",
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.6.2 流式生成谈判手册

**接口**: `GET /api/commonGenerateSse/negotiationPlaybook?sessionId={sessionId}&chatId={chatId}`

#### 4.6.3 获取谈判手册历史

**接口**: `GET /api/getSessionHistory/negotiationPlaybook?sessionId={sessionId}`

---

### 4.7 文档翻译 (Document Translation)

支持法律文档的多语言翻译，保持术语准确性。

#### 4.7.1 创建翻译会话

**接口**: `POST /api/createTranslateSession`

**请求参数**:
```json
{
  "sourceLanguage": "English",
  "targetLanguage": "Chinese",
  "contractType": "License Agreement",
  "gawLaw": "PRC",
  "fileUrl": "https://xxx/contract_en.docx"
}
```

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_translate_123",
  "traceId": "1706355600000-a1b2c3d4"
}
```

#### 4.7.2 流式翻译文档

**接口**: `POST /api/textTranslate`

**请求参数**:
```json
{
  "sessionId": "sess_translate_123",
  "chatId": "chat_456"
}
```

#### 4.7.3 通用快速翻译（无状态）

**接口**: `POST /api/genaralTranslate`

**请求参数**:
```json
{
  "sourceLanguage": "English",
  "targetLanguage": "Chinese",
  "contractType": "NDA",
  "gawLaw": "PRC",
  "query": "This Agreement shall be governed by the laws of the People's Republic of China."
}
```

**说明**: 此接口为无状态翻译，不保存会话记录，适合短文本快速翻译。

#### 4.7.4 获取翻译会话列表和历史

**接口**: `GET /api/getTranslateSessionList`

**接口**: `GET /api/getTranslateSessionHistory?sessionId={sessionId}`

#### 4.7.5 删除翻译会话

**接口**: `POST /api/removeTranslateSession`

---

### 4.8 尽职调查 (Due Diligence)

系统化尽职调查分析，支持多文件批量处理。

#### 4.8.1 生成检查清单

**接口**: `POST /api/generateDueDiligenceChecklist`

**请求参数**:
```json
{
  "documentType": "Financial Documents",
  "position": "Investor",
  "industry": "Technology",
  "jurisdiction": "PRC",
  "language": "Chinese",
  "customerRequest": "Generate checklist for Series B investment due diligence"
}
```

**SSE 响应**: 返回生成的检查清单（JSON 格式）

#### 4.8.2 编辑检查清单

**接口**: `POST /api/editDueDiligenceChecklist`

**请求参数**:
```json
{
  "documentType": "Financial Documents",
  "position": "Investor",
  "checklist": [
    {"title": "Financial Statements", "scope": "Review last 3 years audited financials"},
    {"title": "Tax Compliance", "scope": "Verify tax filing status"}
  ],
  "customerRequest": "Add ESG compliance check"
}
```

#### 4.8.3 单文件检查

**接口**: `POST /api/checkDueDiligenceFile`

**请求参数**:
```json
{
  "sessionId": "sess_dd_123",
  "fileUrl": "https://xxx/financial_report.pdf",
  "checklist": "检查清单内容（可选，不传使用 session 中的）"
}
```

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_dd_123",
  "chatId": "chat_456",
  "fileName": "financial_report.pdf",
  "fileUrl": "https://api.alta-lex.ai/api/preview/financial_report.pdf",
  "riskLevel": "Medium Risk",
  "issueCount": 3,
  "summary": "发现 3 个潜在风险点...",
  "fields": [...],
  "complianceMatrix": [...],
  "redFlags": [...]
}
```

#### 4.8.4 启动批量分析任务

**接口**: `POST /api/analyzeDocuments`

**请求参数**:
```json
{
  "sessionId": "sess_dd_123",
  "fileUrls": [
    "https://xxx/doc1.pdf",
    "https://xxx/doc2.docx"
  ],
  "checklist": "检查清单内容"
}
```

#### 4.8.5 获取分析结果

**接口**: `GET /api/getDueDiligenceResult?sessionId={sessionId}&chatId={chatId}`

---

### 4.9 合规审查 (Legal Compliance)

三步工作流合规审查：法条检索 → 审查清单 → 最终分析。

#### 4.9.1 启动合规审查任务

**接口**: `POST /api/legal_compliance/startComplianceAnalysis`

**请求参数**:
```json
{
  "fileUrls": [
    "https://xxx/privacy_policy.pdf",
    "https://xxx/data_processing_agreement.docx"
  ],
  "jurisdiction": "PRC",
  "domains": ["DATA_PRIVACY", "CYBERSECURITY"],
  "title": "Data Compliance Review",
  "startDate": "2024-01-01",
  "endDate": "2024-12-31",
  "outputLanguage": "zh",
  "prioritySources": ["https://www.cac.gov.cn"],
  "entityType": "Technology Company",
  "regulatedStatus": "Data Processor",
  "dataScope": "Personal Information",
  "businessRegions": ["Mainland China"]
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| fileUrls | array | 是 | 待审查文件 URL 列表，最多 20 个 |
| jurisdiction | string | 是 | 司法管辖区，如 PRC, HK, US |
| domains | array | 是 | 法规领域列表 |
| title | string | 否 | 项目标题 |
| outputLanguage | string | 否 | 输出语言，默认 "zh" |
| prioritySources | array | 否 | 优先来源 URL 列表 |

**domains 可选值**:
- `DATA_PRIVACY`: 数据隐私
- `CYBERSECURITY`: 网络安全
- `FINANCIAL_REGULATION`: 金融监管
- `ANTITRUST`: 反垄断
- `INTELLECTUAL_PROPERTY`: 知识产权
- `LABOR_LAW`: 劳动法
- `ENVIRONMENTAL`: 环境保护
- `CONSUMER_PROTECTION`: 消费者保护

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_compliance_123",
  "chatId": "chat_456",
  "message": "Compliance analysis task started. Use getComplianceTaskResult to query results."
}
```

#### 4.9.2 获取任务结果

**接口**: `GET /api/legal_compliance/getComplianceTaskResult?sessionId={sessionId}&chatId={chatId}`

**响应示例** (处理中):
```json
{
  "status": "processing",
  "sessionId": "sess_compliance_123",
  "chatId": "chat_456",
  "title": "Data Compliance Review",
  "message": "Task is still running, please wait...",
  "progress": {
    "current_phase": "step_1_search",
    "phase_name": "法规检索",
    "current_step": 1,
    "total_steps": 3,
    "progress_percentage": 35,
    "phase_message": "正在检索相关法规..."
  },
  "result": null
}
```

**响应示例** (完成):
```json
{
  "status": "completed",
  "sessionId": "sess_compliance_123",
  "chatId": "chat_456",
  "title": "Data Compliance Review",
  "message": "Task completed successfully",
  "result": {
    "steps": {
      "step_1_search": {
        "status": "completed",
        "data": {
          "regulations": [...],
          "workflow_summary": {...}
        }
      },
      "step_2_issue_list": {
        "status": "completed",
        "data": {
          "issue_list": [...]
        }
      },
      "step_3_analysis": {
        "status": "completed",
        "data": {
          "findings": [...],
          "recommendations": [...]
        }
      }
    }
  }
}
```

#### 4.9.3 导出 Excel 报告

**接口**: `POST /api/legal_compliance/export/excel`

**请求参数**:
```json
{
  "analysis_id": "sess_compliance_123"
}
```

**响应示例**:
```json
{
  "status": "success",
  "url": "https://api.alta-lex.ai/api/preview/compliance_report_xxx.xlsx"
}
```

---

### 4.10 脱敏处理 (Desensitization)

自动识别并脱敏文档中的敏感信息。

#### 4.10.1 运行脱敏工作流

**接口**: `POST /api/runDesensitize`

**请求参数**:
```json
{
  "fileUrl": "https://xxx/confidential_contract.docx",
  "title": "Confidential Contract Desensitization",
  "entity_types": ["PERSON", "ORGANIZATION", "EMAIL", "PHONE", "ID_NUMBER"]
}
```

**entity_types 可选值**:
- `PERSON`: 人名
- `ORGANIZATION`: 组织机构名
- `EMAIL`: 邮箱地址
- `PHONE`: 电话号码
- `ID_NUMBER`: 身份证号
- `ADDRESS`: 地址
- `BANK_CARD`: 银行卡号
- `DATE`: 日期

**响应示例**:
```json
{
  "status": "success",
  "message": "Desensitization task submitted successfully",
  "sessionId": "sess_desensitize_123",
  "data": null
}
```

#### 4.10.2 获取脱敏结果

**接口**: `GET /api/getWorkflowDetail/desensitize?sessionId={sessionId}`

**响应示例** (完成):
```json
{
  "status": "completed",
  "message": "",
  "data": {
    "sessionId": "sess_desensitize_123",
    "chatId": "chat_456",
    "title": "Confidential Contract Desensitization",
    "fileUrl": "https://xxx/confidential_contract.docx",
    "original_filename": "confidential_contract.docx",
    "entity_types": ["PERSON", "ORGANIZATION", "EMAIL"],
    "result": {
      "ext": ".docx",
      "spend_time": 12.5,
      "size": 45678,
      "original_filename": "confidential_contract.docx",
      "desensitized_filename": "confidential_contract_脱敏.docx",
      "preview_url": "https://api.alta-lex.ai/api/preview/xxx_desensitized.docx"
    },
    "created_at": "2026-04-08T10:30:00"
  }
}
```

---

### 4.11 表格处理 (Tabular Analysis)

从文档中提取表格数据并进行结构化分析。

#### 4.11.1 生成检查清单

**接口**: `POST /api/generateTabularChecklist`

**请求参数**:
```json
{
  "documentType": "Financial Statements",
  "position": "Analyst",
  "industry": "Finance",
  "jurisdiction": "PRC",
  "language": "Chinese",
  "customerRequest": "Generate checklist for financial data extraction"
}
```

#### 4.11.2 启动表格分析任务

**接口**: `POST /api/startTabularAnalysis`

**请求参数**:
```json
{
  "title": "Q1 Financial Data Extraction",
  "documentType": "Financial Statements",
  "position": "Analyst",
  "industry": "Finance",
  "jurisdiction": "PRC",
  "language": "Chinese",
  "customerRequest": "Extract revenue and expense data",
  "fileUrls": [
    "https://xxx/q1_report.pdf",
    "https://xxx/q2_report.pdf"
  ],
  "checklist": [
    {"title": "Revenue", "scope": "Extract total revenue by quarter"},
    {"title": "Expenses", "scope": "Extract operating expenses"}
  ]
}
```

**注意**: `checklist` 和 `checklistFile` 二选一，不能同时提供。

**响应示例**:
```json
{
  "status": "success",
  "sessionId": "sess_tabular_123",
  "chatId": "chat_456",
  "message": "Analysis task started. Use getTabularTaskResult to query results."
}
```

#### 4.11.3 获取分析结果

**接口**: `GET /api/getTabularTaskResult?sessionId={sessionId}&chatId={chatId}`

**响应示例** (完成):
```json
{
  "status": "completed",
  "sessionId": "sess_tabular_123",
  "chatId": "chat_456",
  "title": "Q1 Financial Data Extraction",
  "message": "Task completed successfully",
  "result": {
    "title": "Q1 Financial Data Extraction",
    "summary": "Successfully extracted data from 2 files",
    "fileCount": 2,
    "successCount": 2,
    "failedCount": 0
  }
}
```

---

## 5. SSE 流式响应规范

### 5.1 SSE 连接建立

```http
GET /api/commonGenerateSse?sessionId={sessionId} HTTP/1.1
Host: api.alta-lex.ai
Authorization: {session_id}
Accept: text/event-stream
Cache-Control: no-cache
```

### 5.2 SSE 事件格式

```
# 数据事件
data: {"message": "生成的内容片段", "is_finished": false}

# 心跳事件（保持连接）
: heartbeat

# 完成事件
data: {"message": "", "is_finished": true, "metadata": {"usage": {"prompt_tokens": 100, "completion_tokens": 500}}}

# 错误事件
data: {"error": "Error message", "message": "", "is_finished": true}
```

### 5.3 SSE 客户端实现示例 (JavaScript)

```javascript
const eventSource = new EventSource(
  `https://api.alta-lex.ai/api/commonGenerateSse?sessionId=${sessionId}`,
  {
    headers: {
      'Authorization': sessionId
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.error) {
    console.error('Error:', data.error);
    eventSource.close();
    return;
  }
  
  if (data.is_finished) {
    console.log('Generation completed');
    console.log('Usage:', data.metadata?.usage);
    eventSource.close();
    return;
  }
  
  // 追加内容
  appendContent(data.message);
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

### 5.4 SSE 重连机制

- 心跳间隔: 15 秒
- 超时时间: 无限制（AI 生成可能需要 10-15 分钟）
- 自动重连: 客户端应根据业务需求实现重连逻辑

---

## 6. 错误码说明

### 6.1 错误码格式

错误码格式: `[责任归属][模块][序号]` (6位)
- 责任归属(1位): A=用户端错误, B=系统错误, C=第三方错误
- 模块(2位): 00-09 功能模块
- 序号(3位): 001-999 具体错误

### 6.2 错误码列表

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| **A01001** | 未登录或 Session 过期 | 重新登录获取新 Session |
| **A01007** | 禁止访问 | 检查用户权限 |
| **A02002** | 参数缺失或无效 | 检查请求参数完整性 |
| **A02004** | 参数验证失败 | 检查参数格式和值 |
| **A03001** | 资源不存在 | 检查资源 ID 是否正确 |
| **A03002** | 会话不存在 | 检查 sessionId 是否有效 |
| **A03003** | 聊天记录不存在 | 检查 chatId 是否有效 |
| **A03004** | 文件不存在 | 检查文件 URL 是否有效 |
| **A04006** | Credit 余额不足 | 联系管理员充值 |
| **B00001** | 系统内部错误 | 稍后重试或联系技术支持 |
| **B05001** | 文件处理失败 | 检查文件格式和内容 |
| **B06001** | 数据库操作失败 | 稍后重试 |
| **C07002** | API 调用超时 | 稍后重试 |
| **C07003** | 第三方服务错误 | 稍后重试或联系技术支持 |

### 6.3 业务状态码 (RecordStatus)

| 状态码 | 说明 |
|--------|------|
| 0 | 已创建 (CREATED) |
| 1 | 处理中 (PROCESSING) |
| 2 | 已完成 (COMPLETED) |
| -1 | 错误 (ERROR) |

---

## 7. 调用流程示例

### 7.1 合同起草完整流程

```
┌─────────┐    POST /api/createDraftSession    ┌─────────────┐
│  OpenClaw│ ─────────────────────────────────▶ │ Legal AI    │
│  Client  │                                    │ Assistant   │
└─────────┘    ◀──────────────────────────────── └─────────────┘
               {sessionId: "sess_123"}
                      │
                      ▼
┌─────────┐    GET /api/commonGenerateSse    ┌─────────────┐
│  OpenClaw│ ─────────────────────────────────▶ │ Legal AI    │
│  Client  │    (SSE Stream)                    │ Assistant   │
└─────────┘    ◀──────────────────────────────── └─────────────┘
               data: {message: "...", is_finished: false}
               data: {message: "...", is_finished: false}
               data: {message: "", is_finished: true}
```

### 7.2 合同审查完整流程

```
┌─────────┐    POST /api/common_review       ┌─────────────┐
│  OpenClaw│ ─────────────────────────────────▶ │ Legal AI    │
│  Client  │    {fileUrl, reviewType, ...}      │ Assistant   │
└─────────┘    ◀──────────────────────────────── └─────────────┘
               {status: "success", task_data: "..."}
                      │
                      │ 轮询查询
                      ▼
┌─────────┐    POST /api/getReviewAnswer     ┌─────────────┐
│  OpenClaw│ ─────────────────────────────────▶ │ Legal AI    │
│  Client  │    {type, filename}                │ Assistant   │
└─────────┘    ◀──────────────────────────────── └─────────────┘
               {status: "completed", processing_result: "..."}
```

### 7.3 合规审查完整流程

```
┌─────────┐    POST /api/legal_compliance/    ┌─────────────┐
│  OpenClaw│    startComplianceAnalysis       │ Legal AI    │
│  Client  │ ─────────────────────────────────▶ │ Assistant   │
└─────────┘    {fileUrls, jurisdiction, ...}   └─────────────┘
               ◀────────────────────────────────
               {sessionId: "sess_123", chatId: "chat_456"}
                      │
                      │ 轮询查询 (每 5-10 秒)
                      ▼
┌─────────┐    GET /api/legal_compliance/    ┌─────────────┐
│  OpenClaw│    getComplianceTaskResult       │ Legal AI    │
│  Client  │ ─────────────────────────────────▶ │ Assistant   │
└─────────┘                                      └─────────────┘
               ◀────────────────────────────────
               {status: "processing", progress: {...}}
                      │
                      │ 直到 status = "completed"
                      ▼
               {status: "completed", result: {...}}
```

---

## 8. 性能与限制

### 8.1 通用限制

| 限制项 | 限制值 | 说明 |
|--------|--------|------|
| 文件大小 | 50 MB | 单个文件最大大小 |
| 文件数量 | 20 个 | 单次请求最多文件数 |
| 会话历史 | 100 条 | 单个会话最多聊天记录 |
| 请求频率 | 10 次/分钟 | 普通接口频率限制 |

### 8.2 各功能限制

| 功能 | 特殊限制 |
|------|----------|
| 法律研究 | Search 模式最多 10 轮对话 |
| 文档翻译 | 最多 5 个参考文件 |
| 合规审查 | 最多 20 个文件，3 步工作流 |
| 尽职调查 | 单文件内容限制 100000 字符 |
| 表格处理 | 最多 20 个文件 |

### 8.3 性能指标

| 功能 | 平均响应时间 | 最大响应时间 |
|------|--------------|--------------|
| 创建会话 | < 100ms | < 500ms |
| SSE 首字节 | < 2s | < 5s |
| 合同生成 | 30-60s | 300s |
| 文件审查 | 60-120s | 600s |
| 合规审查 | 5-15min | 30min |
| 脱敏处理 | 10-30s | 120s |

### 8.4 超时配置

- **API 超时**: 无限制（SSE 流式响应）
- **文件解析超时**: 60 秒
- **第三方 API 超时**: 120 秒
- **数据库连接超时**: 30 秒

### 8.5 重试策略建议

| 错误类型 | 重试次数 | 重试间隔 |
|----------|----------|----------|
| 网络超时 | 3 次 | 5 秒 |
| 服务繁忙 (503) | 5 次 | 10 秒 |
| 第三方错误 | 3 次 | 30 秒 |
| 认证失败 | 不重试 | - |
| 参数错误 | 不重试 | - |

---

## 附录

### A. 支持的文件格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| Word 文档 | .doc, .docx | 推荐格式 |
| PDF | .pdf | 支持文本型和扫描件 |
| 文本 | .txt | 纯文本 |
| 图片 | .png, .jpg, .jpeg | OCR 识别 |

### B. 支持的语言

| 语言 | 代码 |
|------|------|
| 简体中文 | Chinese, zh, zh-CN |
| 繁体中文 | Traditional Chinese, zh-TW, zh-HK |
| 英语 | English, en |
| 日语 | Japanese, ja |
| 韩语 | Korean, ko |

### C. 适用法律代码

| 代码 | 说明 |
|------|------|
| PRC | 中华人民共和国法律 |
| HK | 香港特别行政区法律 |
| US | 美国联邦法律 |
| UK | 英国法律 |
| EU | 欧盟法律 |
| SG | 新加坡法律 |

---

**文档维护**: Legal AI Assistant 团队  
**问题反馈**: support@alta-lex.ai
