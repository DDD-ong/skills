# Alta Lex AI 平台 — API 技术调研报告

## 1. 目标

1. 网站地址：https://test.alta-lex.ai/login （类似 OpenAI Chat 的法律 AI 平台）
2. 调研目的：构建封装好的 Python 脚本，实现登录认证、会话管理和 API 交互
3. 最终目标：将脚本作为可复用的 skill，集成到 GPT 等系统中调用

## 2. 具体要求

1. 首先进行 API 接口调研，选择一个简单场景制作 demo
2. 用户名密码可通过命令行参数输入，支持配置化
3. 提供完整的 Python 代码示例，包含错误处理
4. 代码模块化设计，便于后续集成

---

## 3. 技术调研结果

### 3.1 网站技术栈

| 项目 | 详情 |
|------|------|
| **前端框架** | Umi.js (基于 React 的企业级框架) |
| **构建工具** | Webpack (代码分割、异步加载) |
| **Web 服务器** | Nginx 1.25.5 |
| **API 风格** | RESTful JSON API |
| **实时通信** | Server-Sent Events (SSE) |
| **部署** | HTTPS，启用 HSTS |

### 3.2 登录认证机制 — JWT Token (Cookie-Based)

**认证方式: JWT Token，通过 Cookie 传递**

```
┌─────────┐     POST /api/login        ┌─────────┐
│  Client  │ ──── {username, password} ───▶│  Server  │
│          │                              │          │
│          │◀── Set-Cookie: auth=<JWT> ───│          │
│          │    Set-Cookie: acw_tc=...    │          │
│          │    Body: {status, data}      │          │
└─────────┘                              └─────────┘
```

**JWT Token 结构:**

```
Header:  {"alg": "HS256", "typ": "JWT"}
Payload: {"uid": "fd007687-...", "exp": 1773584860, "iat": 1773574060}
```

- **签名算法**: HS256 (HMAC-SHA256)
- **有效期**: 约 3 小时 (exp - iat ≈ 10800 秒)
- **Cookie 名称**: `auth`
- **Cookie 属性**: HTTP-only (前端 JavaScript 无法读取)
- **附加 Cookie**: `acw_tc` (CDN/负载均衡跟踪 Cookie)

**登录响应示例:**

```json
{
  "status": "success",
  "message": "登录成功",
  "data": {
    "uid": "fd007687-53b5-4847-a376-8b70c48e9e9a",
    "username": "***",
    "role": "user",
    "status": "1",
    "parent_uid": "123456",
    "expires": "2026-03-15T22:19:37.940208+08:00"
  },
  "traceId": "1773573577492-0de56eb6"
}
```

### 3.3 会话保持和 Token 管理策略

| 机制 | 说明 |
|------|------|
| **Token 存储** | 服务端通过 `Set-Cookie` 头设置 JWT 到 `auth` Cookie |
| **自动发送** | 浏览器/requests.Session 自动在后续请求中携带 Cookie |
| **Token 刷新** | 每次调用 `/api/login` 获取新 Token；无显式 refresh 机制 |
| **会话验证** | 通过 `POST /api/getUserInfo` 验证 Token 有效性 |
| **过期处理** | 返回错误码 `A01001`："Not logged in or session expired" |
| **登出** | `POST /api/logout` 清除服务端会话 |

### 3.4 安全验证措施

| 安全措施 | 状态 | 说明 |
|----------|------|------|
| **CSRF Token** | ❌ 未发现 | 页面中无隐藏 CSRF 字段 |
| **验证码 (CAPTCHA)** | ❌ 无 | 登录无验证码验证 |
| **速率限制** | ⚠️ 未检测到提示 | 无明显的频率限制错误 |
| **CSP (内容安全策略)** | ✅ 已启用 | `default-src 'self'` |
| **HSTS** | ✅ 已启用 | `max-age=63072000; includeSubDomains; preload` |
| **X-Frame-Options** | ✅ DENY | 防止 Clickjacking |
| **X-XSS-Protection** | ✅ `1; mode=block` | XSS 防护 |
| **HTTP-only Cookie** | ✅ 已启用 | 前端 JS 无法读取 auth Cookie |
| **Referrer-Policy** | ✅ `strict-origin-when-cross-origin` | 限制 Referer 泄露 |

**对 Python 客户端的影响:**
- 无 CSRF Token → 简化了 API 调用（无需提取隐藏字段）
- 无 CAPTCHA → 可直接程序化登录
- JWT Cookie 自动管理 → `requests.Session` 天然支持

---

## 4. API 接口文档

### 4.1 统一响应格式

**成功响应:**
```json
{
  "status": "success",
  "message": "...",
  "data": { ... },
  "traceId": "1773574060260-980fda11"
}
```

**错误响应:**
```json
{
  "status": "error",
  "error": {
    "code": "A01001",
    "message": "Not logged in or session expired. Please log in again.",
    "details": null,
    "timestamp": "2026-03-15T19:06:34.839149",
    "path": "..."
  },
  "traceId": ""
}
```

### 4.2 认证 API

#### POST /api/login
- **请求体**: `{"username": "...", "password": "..."}`
- **响应**: 用户信息 + Set-Cookie (auth JWT)
- **失败消息**: "Incorrect username or password"

#### POST /api/logout
- **请求体**: `{}`
- **响应**: `{"status": "success", "message": "登出成功"}`

#### POST /api/getUserInfo
- **请求体**: `{}`
- **响应**: 完整用户信息（uid, username, role, status, expiry_date, credit 等）

### 4.3 法律研究 API (Legal Research) — 核心功能

#### POST /api/createAnalysisSession
创建新的分析会话。

- **请求体**: `{"query": "查询描述"}`
- **响应**:
```json
{
  "status": "success",
  "message": "",
  "data": null,
  "traceId": "...",
  "sessionId": "56116b50-f16f-4180-b1b7-abde5a8f78be"
}
```

#### POST /api/legalAnalysisSse
发起法律分析，以 SSE 流式返回结果。

- **请求体**:
```json
{
  "sessionId": "UUID",
  "query": "法律问题",
  "practiceArea": "Contract Law",
  "jurisdiction": "Hong Kong",
  "outputLanguage": "English",
  "background": "背景信息",
  "legalResearchPro": false
}
```
- **响应类型**: `text/event-stream; charset=utf-8`
- **SSE 数据流格式**:

```
: init                                          ← 初始化信号 (SSE 注释)

: heartbeat 1                                   ← 心跳保活 (SSE 注释)

data: {"message": "### L", "is_finished": false} ← 文本片段

data: {"message": "egal ", "is_finished": false} ← 文本片段

data: {"message": "...",  "is_finished": true}   ← 最后一个片段
```

**SSE 事件 data 字段:**
| 字段 | 类型 | 说明 |
|------|------|------|
| `message` | string | 文本片段（约 5 个字符一个 chunk） |
| `is_finished` | boolean | `true` 表示流结束 |

**注意**: 分析过程通常需要 **5-8 分钟**，在此期间持续发送心跳。

#### GET /api/getAnalysisSessionList
获取所有分析会话列表。

- **响应**:
```json
{
  "status": "success",
  "chats": [
    {"sessionId": "UUID", "sessionName": "...", "title": "..."},
    ...
  ]
}
```

#### GET /api/getAnalysisSessionHistory?sessionId=UUID
获取指定会话的完整聊天历史。

- **响应**:
```json
{
  "status": "success",
  "chats": [
    {"chatId": "...", "query": "...", "answer": "完整 Markdown 回答", "status": "..."}
  ],
  "researchType": "search"
}
```

### 4.4 其他功能模块 API

#### 草稿 (Drafting)
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/getDraftSessionList` | GET | 获取草稿列表 |
| `/api/createDraftSession` | POST | 创建草稿（需要 scenario, position, industry, contractType, governingLaw, language） |

#### 审查 (Review)
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/listFiles` | POST | 列出文件（`{"type": "review"}`） |

#### 翻译 (Translate)
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/getTranslateSessionList` | GET | 获取翻译列表 |
| `/api/createTranslateSession` | POST | 创建翻译（需要 sourceLanguage, targetLanguage, fileUrl） |

#### 工作流 (Workflows)
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/getSessionList/workflow` | GET | 获取工作流列表 |

---

## 5. Python 客户端使用说明

### 5.1 文件结构

```
demo/
├── alta_lex_client.py    # 客户端核心代码（AltaLexClient 类 + CLI）
└── API Analysis spec.md  # 本文档
```

### 5.2 依赖

```
pip install requests
```

（仅依赖 `requests` 库，无其他第三方依赖）

### 5.3 CLI 使用

```bash
# 登录并列出所有会话
python3 ~/workspace/demo/alta_lex_client.py -u *** -p '***' --list-sessions

# 查看指定会话的历史
python3 ~/workspace/demo/alta_lex_client.py -u *** -p '***' --session-history <SESSION_ID>

# 发起法律分析查询（SSE 流式输出）
python3 ~/workspace/demo/alta_lex_client.py -u *** -p '***' \
    -q "What are the requirements for a valid contract?" \
    --practice-area "Contract Law" \
    --jurisdiction "Hong Kong"

# 启用 Legal Research Pro 模式
python3 ~/workspace/demo/alta_lex_client.py -u *** -p '***' \
    -q "..." --pro
```

### 5.4 作为 Python 模块调用

```python
from alta_lex_client import AltaLexClient

client = AltaLexClient()

# 登录
client.login("username", "password")

# 验证会话
if client.is_authenticated():
    print("Token 有效")

# 获取 JWT Token（可保存供其他系统使用）
jwt_token = client.get_auth_token()

# 便捷方法：一步完成分析
session_id, full_text = client.legal_analysis(
    query="What is contract law?",
    practice_area="Contract Law",
    jurisdiction="Hong Kong",
)

# 流式接收（逐 chunk 处理）
session_id = client.create_analysis_session("query")
for event in client.legal_analysis_sse(session_id=session_id, query="query"):
    print(event.message, end="", flush=True)
    if event.is_finished:
        break

# 查看历史
sessions = client.get_analysis_session_list()
history = client.get_analysis_session_history(session_id)

# 登出
client.logout()
```

### 5.5 异常处理

```python
from alta_lex_client import (
    AltaLexClient, AuthenticationError, SessionExpiredError, APIError
)

client = AltaLexClient()
try:
    client.login("user", "pass")
except AuthenticationError:
    print("用户名或密码错误")
except SessionExpiredError:
    print("会话已过期，需重新登录")
except APIError as e:
    print(f"API 错误: {e}")
```

### 5.6 集成到 Skill 框架

`AltaLexClient` 类设计为可独立使用的模块：

1. **无状态依赖**: 仅依赖 `requests.Session` 管理 Cookie
2. **错误分层**: `AltaLexError` → `AuthenticationError` / `SessionExpiredError` / `APIError`
3. **SSE 流式**: `legal_analysis_sse()` 返回 Generator，适合流式处理
4. **便捷封装**: `legal_analysis()` 一步完成创建会话 + 收集完整响应
5. **Token 导出**: `get_auth_token()` 可提取 JWT 供其他系统使用

---

## 6. 已验证的功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 登录 (login) | ✅ 已验证 | JWT Token 自动保存到 Cookie |
| 获取用户信息 | ✅ 已验证 | 返回 uid, credit, expiry_date 等 |
| 列出会话 | ✅ 已验证 | 返回所有历史会话列表 |
| 查看会话历史 | ✅ 已验证 | 返回完整 Q&A 历史 |
| 创建分析会话 | ✅ 已验证 | 返回新的 sessionId |
| SSE 流式分析 | ✅ 已验证 | 接收 `data: {"message", "is_finished"}` 格式 |
| 登出 | ✅ 已验证 | 清除服务端会话 |

---

## 7. 注意事项与限制

1. **分析耗时**: 法律分析通常需要 5-8 分钟，SSE 连接需保持长时间打开
2. **Token 有效期**: JWT 约 3 小时过期，长期使用需定期重新登录
3. **积分消耗**: 每次分析消耗积分（credit），需监控余额
4. **无公开 API 文档**: `/docs` 页面需登录且内容为空，所有 API 信息通过逆向工程获取
5. **SSE 心跳**: 在分析处理期间，服务端发送 `: heartbeat N` 注释保持连接
