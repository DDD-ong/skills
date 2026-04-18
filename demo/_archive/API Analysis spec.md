# Alta Lex AI Platform — API & Integration Spec

## 1. Overview

Alta Lex AI (`https://test.alta-lex.ai`) is a legal AI platform offering professional legal research, contract drafting, document review, and translation. This document covers the complete API surface and two integration layers:

- **Tier 1 (Development)**: `opencli alta-lex` commands for interactive testing on macOS with Chrome
- **Tier 2 (Production)**: Python `alta_lex_client.py` for programmatic use on Linux via OpenClaw + Discord

## 2. Architecture

```
+-- Tier 1: Development (macOS + Chrome) --------------------------+
|  opencli alta-lex <command>                                       |
|  Strategy: cookie (reuses Chrome browser session)                 |
|  9 YAML CLI commands for interactive API testing                  |
+-------------------------------------------------------------------+
                              |
                    API discovery & validation
                              v
+-- Tier 2: Production (Linux / OpenClaw + Discord) ----------------+
|  python3 alta_lex_client.py                                       |
|  Auth: programmatic login via env vars                            |
|                                                                   |
|  User (Discord) -> OpenClaw Agent                                 |
|    -> --quick-start -q "query"  (returns session_id immediately)  |
|    -> openclaw cron --check-session (polls every 5 min)           |
|    -> auto-reply to Discord on completion                         |
+-------------------------------------------------------------------+
                              |
                              v
+-- Alta Lex API Server ----------------------------------------+
|  https://test.alta-lex.ai/api/*                               |
|  Auth: JWT Cookie (HS256, ~3h expiry)                         |
|  Streaming: SSE (Server-Sent Events)                          |
|  Framework: Umi.js (React), Nginx 1.25.5, HTTPS + HSTS       |
+---------------------------------------------------------------+
```

## 3. Authentication

**Method**: JWT Token via HTTP-only Cookie

```
Client  --POST /api/login {username, password}-->  Server
Client  <--Set-Cookie: auth=<JWT>-----------------  Server
```

| Property | Value |
|----------|-------|
| Algorithm | HS256 (HMAC-SHA256) |
| Cookie name | `auth` |
| Cookie attributes | HTTP-only |
| Payload | `{uid, exp, iat}` |
| Validity | ~3 hours (exp - iat = 10800s) |
| Additional cookies | `acw_tc` (CDN tracking) |
| CSRF | None (simplifies programmatic access) |
| CAPTCHA | None |

**Login response:**
```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "uid": "fd007687-53b5-4847-a376-8b70c48e9e9a",
    "username": "***",
    "role": "user",
    "status": "1",
    "parent_uid": "123456",
    "expires": "2026-03-15T22:19:37.940208+08:00"
  }
}
```

**Error codes:**
| Code | Meaning |
|------|---------|
| `A01001` | Not logged in or session expired |
| HTTP 401 | Unauthorized |
| HTTP 403 | Forbidden |

## 4. API Endpoints

### 4.1 Unified Response Format

**Success:**
```json
{"status": "success", "message": "...", "data": {...}, "traceId": "..."}
```

**Error:**
```json
{
  "status": "error",
  "error": {"code": "A01001", "message": "...", "details": null, "timestamp": "...", "path": "..."},
  "traceId": ""
}
```

### 4.2 Authentication

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/login` | POST | `{username, password}` | User info + Set-Cookie |
| `/api/logout` | POST | `{}` | Success message |
| `/api/getUserInfo` | POST | `{}` | Full user info (uid, credit, expiry_date) |

### 4.3 Legal Research (Core)

| Endpoint | Method | Body/Params | Response |
|----------|--------|-------------|----------|
| `/api/createAnalysisSession` | POST | `{query}` | `{sessionId: "UUID"}` (top-level) |
| `/api/legalAnalysisSse` | POST | `{sessionId, query, practiceArea, jurisdiction, outputLanguage, background, legalResearchPro}` | SSE stream |
| `/api/getAnalysisSessionList` | GET | - | `{chats: [{sessionId, sessionName, title}]}` |
| `/api/getAnalysisSessionHistory` | GET | `?sessionId=UUID` | `{chats: [{chatId, query, answer, status}], researchType}` |

**SSE Stream Format (`legalAnalysisSse`):**
```
: init                                              <- comment (skip)
: heartbeat 1                                       <- comment (skip)
data: {"message": "### L", "is_finished": false}    <- text chunk
data: {"message": "egal ", "is_finished": false}    <- text chunk
data: {"message": "...",  "is_finished": true}      <- final chunk
```

- Analysis typically takes **5-8 minutes**
- Heartbeats sent during processing to keep connection alive
- `message`: text fragment (~5 chars per chunk)
- `is_finished: true`: end of stream

### 4.4 Drafting

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/getDraftSessionList` | GET | - | Session list |
| `/api/createDraftSession` | POST | `{scenario, position, industry, contractType, governingLaw, language}` | `{sessionId}` |

### 4.5 Review

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/listFiles` | POST | `{type: "review"}` | File list |

### 4.6 Translation

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/getTranslateSessionList` | GET | - | Session list |
| `/api/createTranslateSession` | POST | `{sourceLanguage, targetLanguage, fileUrl}` | `{sessionId}` |

### 4.7 Workflows

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/getSessionList/{type}` | GET | - | Session list |

Types: `workflow`, `ipoCheckList`, `templateAndTermSheet`, `negotiationPlaybook`, `contractCompare`

## 5. opencli Command Reference (Tier 1 - Development)

All commands use `strategy: cookie` and require Chrome to be logged in at `test.alta-lex.ai`.

| Command | Description | Key Args | Example |
|---------|-------------|----------|---------|
| `user-info` | Verify auth, show user info | - | `opencli alta-lex user-info` |
| `legal-research` | Start legal analysis | `<query>`, `--wait`, `--practice_area`, `--jurisdiction` | `opencli alta-lex legal-research "contract law?"` |
| `sessions` | List sessions by type | `--type` (analysis/draft/translate/workflow) | `opencli alta-lex sessions --type analysis` |
| `analysis-sessions` | List analysis sessions | `--limit` | `opencli alta-lex analysis-sessions` |
| `session-history` | View session chat history | `<session_id>` | `opencli alta-lex session-history UUID` |
| `list-files` | List uploaded files | `--type` | `opencli alta-lex list-files` |
| `create-draft` | Create a draft session | `<scenario>`, `--position`, `--industry`, etc. | `opencli alta-lex create-draft "NDA" --position Buyer ...` |
| `draft-sessions` | List draft sessions | `--limit` | `opencli alta-lex draft-sessions` |
| `translate-sessions` | List translate sessions | `--limit` | `opencli alta-lex translate-sessions` |

**legal-research modes:**
- **Quick mode** (default): `opencli alta-lex legal-research "query"` -> returns `session_id` immediately
- **Wait mode**: `opencli alta-lex legal-research "query" --wait` -> blocks until SSE completes (5-8 min)

YAML definitions: `~/.opencli/clis/alta-lex/*.yaml`

## 6. Python Client Reference (Tier 2 - Production)

**File**: `scripts/alta_lex_client.py` (single file, depends only on `requests`)

### CLI Usage

```bash
# Quick-start (OpenClaw integration - returns JSON)
python3 alta_lex_client.py -u USER -p PASS --quick-start -q "legal question" \
  --practice-area "Contract Law" --jurisdiction "Hong Kong"
# Output: {"status": "started", "session_id": "UUID", "content": "", "error": ""}

# Check session status (OpenClaw cron polling - returns JSON)
python3 alta_lex_client.py -u USER -p PASS --check-session "UUID"
# Output: {"status": "running|complete|error", "session_id": "...", "content": "...", "error": "..."}

# Full foreground analysis (SSE streaming)
python3 alta_lex_client.py -u USER -p PASS -q "legal question"

# List sessions
python3 alta_lex_client.py -u USER -p PASS --list-sessions

# Session history
python3 alta_lex_client.py -u USER -p PASS --session-history UUID
```

### Python API

```python
from alta_lex_client import AltaLexClient

client = AltaLexClient()
client.login("username", "password")

# Quick start (non-blocking)
session_id = client.quick_start_analysis(query="...", practice_area="...", jurisdiction="...")

# Check completion
result = client.check_session_complete(session_id)
# {"status": "complete", "session_id": "...", "content": "full analysis text", "error": ""}

# Full analysis (blocking, SSE streaming)
session_id, full_text = client.legal_analysis(query="...", practice_area="...", jurisdiction="...")

# Other operations
sessions = client.get_analysis_session_list()
history = client.get_analysis_session_history(session_id)
drafts = client.get_draft_session_list()
files = client.list_files(file_type="review")
```

### Exception Hierarchy

```
AltaLexError
  +-- AuthenticationError    (invalid credentials)
  +-- SessionExpiredError    (JWT expired, code A01001)
  +-- APIError               (general API failures)
```

## 7. OpenClaw Integration (Discord Workflow)

**SKILL.md**: `demo/alex_law_legal/SKILL.md`

```
User (Discord) asks legal question
  -> OpenClaw detects legal query via skill description
  -> Step 1: Extract query, practice_area, jurisdiction
  -> Step 2: python3 alta_lex_client.py --quick-start -q "..." (background:true)
  -> Step 3: openclaw cron create --every 5m --check-session UUID
  -> Step 4: Cron detects "complete" -> auto-reply to Discord -> cleanup
```

Key design decisions:
- **No session files**: State managed server-side via `session_id`
- **No separate poll script**: `--check-session` merged into `alta_lex_client.py`
- **JSON output**: `--quick-start` and `--check-session` output pure JSON for cron parsing
- **Linux compatible**: Python + requests only, no Chrome/browser dependency

## 8. Practice Areas

| Area | Area |
|------|------|
| Property Law | Tenancy Law |
| Conveyancing | Building Management |
| Corporate Law | Employment Law |
| Contract Law | Intellectual Property |
| Criminal Law | Family Law |
| Tax Law | Banking & Finance |
| Competition Law | Regulatory & Compliance |
| Litigation | Arbitration |

## 9. Security

| Measure | Status |
|---------|--------|
| HTTPS | Enabled |
| HSTS | `max-age=63072000; includeSubDomains; preload` |
| HTTP-only Cookie | Enabled (JS cannot read auth cookie) |
| X-Frame-Options | DENY |
| X-XSS-Protection | `1; mode=block` |
| CSP | `default-src 'self'` |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| CSRF Token | None (simplifies API access) |
| CAPTCHA | None |

## 10. Troubleshooting

| Issue | Environment | Solution |
|-------|-------------|----------|
| "Not logged in or session expired" | Both | Re-login; JWT valid ~3h |
| opencli returns empty/error | macOS | Ensure Chrome is logged in at test.alta-lex.ai |
| `--check-session` returns "running" indefinitely | Linux | Analysis may take up to 10 min; increase cron patience |
| `--quick-start` returns error | Linux | Check credentials in env vars; verify network to test.alta-lex.ai |
| SSE timeout | Both | Analysis typically 5-8 min; 10 min timeout is safety net |
| Credit insufficient | Both | Check credit via `user-info` / `get_user_info()` |

## 11. File Structure

```
demo/
+-- API Analysis spec.md                  # This document
+-- alta_lex_client.py                    # Python client (standalone copy)
+-- alex_law_legal/
    +-- SKILL.md                          # OpenClaw skill definition
    +-- scripts/
        +-- alta_lex_client.py            # Python client (skill copy)

~/.opencli/clis/alta-lex/
+-- legal-research.yaml                   # SSE analysis (quick/wait modes)
+-- sessions.yaml                         # Unified session listing
+-- list-files.yaml                       # File listing
+-- user-info.yaml                        # Auth verification
+-- analysis-sessions.yaml                # Analysis session listing
+-- session-history.yaml                  # Session chat history
+-- create-draft.yaml                     # Draft creation
+-- draft-sessions.yaml                   # Draft listing
+-- translate-sessions.yaml               # Translation listing
```
