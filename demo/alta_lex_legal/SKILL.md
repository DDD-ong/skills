---
name: alta_lex_legal
version: 2.4.0
description: "Full-featured legal AI assistant via Alta Lex platform (法律AI助手). Covers 11 modules: contract drafting (合同起草), contract review (合同审查), contract comparison (合同比对), legal research (法律研究/法规查询), IPO support (IPO合规审查), negotiation playbook (谈判策略), document translation (文件翻译), due diligence (尽职调查), legal compliance (合规审查), desensitization (数据脱敏), and tabular analysis (表格分析). Use when: (1) user wants to draft, review, compare, or translate contracts or legal documents (起草、审查、比对、翻译合同或法律文件); (2) user asks ANY legal question, seeks legal advice, wants legal research, regulation lookup, or case analysis (任何法律咨询、法律问题、法规查询、案例分析); (3) user wants to draft or prepare legal documents like petitions, legal opinions, memos, letters, agreements (起草起诉状、答辩状、法律意见书、备忘录、律师函、协议书); (4) user needs IPO compliance checks, negotiation strategies, due diligence, compliance review, data desensitization, or document data extraction; (5) user mentions keywords like: law, legal, attorney, lawyer, statute, regulation, contract, agreement, clause, liability, litigation, arbitration, court, judgment, verdict, appeal, plaintiff, defendant, counsel, jurisdiction, tort, damages, injunction, indemnity, warranty, intellectual property, employment law, corporate law, criminal law, family law, tax law, environmental law, maritime law, international law, constitutional law, administrative law, bankruptcy, merger, acquisition, antitrust, data privacy, GDPR, PIPL, NDA, SPA, MOU, JV, 法律, 法规, 合同, 协议, 条款, 责任, 诉讼, 仲裁, 律师, 合规, 知识产权, 劳动法, 公司法, 侵权, 赔偿, 法院, 判决, 起诉, 辩护, 立法, 司法, 行政法, 刑法, 民法, 婚姻法, 继承法, 税法, 环境法, 国际法, 商法, 证券法, 保险法, 担保, 抵押, 质押, 股权, 债权, 尽职调查, 法律意见, 法律咨询, 法律文书, 律师函, 起诉状, 答辩状, 代理词, 调解, 和解, 执行, 强制执行, 保全, 管辖, 上诉, 再审, 终审. NOT for: non-legal questions, simple factual lookups unrelated to law."
metadata: { "openclaw": { "emoji": "⚖️", "requires": { "bins": ["python3"], "env": ["ALTA_LEX_USERNAME", "ALTA_LEX_PASSWORD"] }, "os": ["darwin", "linux"] } }
---

## Important: How to Use This Skill

**DO NOT read or modify any source code files.** This skill is used exclusively through CLI commands.

### Workflow (Async Two-Step Mode)

1. **Start task**: Run the CLI `start` command (WITHOUT `--wait`) — returns immediately with `session_id` and optional `chat_id`
2. **Report to user**: Immediately tell the user the task has started, include the session_id for reference
3. **Poll for results**: Run `cron_poll.py` with `--loop` in background to automatically poll until complete
4. **Return results**: When status becomes `complete`, parse the JSON output and return the `content` field to the user

This async mode avoids blocking. The user gets instant feedback while the task runs in background.

### Error Handling

- If a command returns `{"status": "error", ...}`, report the error message to the user
- **Never** try to read source files to diagnose issues

### Result Size

- Results can be very long (10,000+ characters)
- Summarize key findings for the user instead of returning raw content
- If the user wants full details, offer to break it into sections

# Alta Lex Legal AI — Unified Skill (11 Modules)

Full legal AI assistant covering contract management, legal research, compliance, and document processing. Uses async two-step workflow: **start command returns immediately**, then `cron_poll.py` polls in background until results are ready.

## Architecture

```
User (Discord/Web) → OpenClaw Agent
  Step 1: python3 {baseDir}/scripts/alta_lex.py ... MODULE start [params]  (returns session_id immediately)
  → Report to user: "Task started, session_id: sess_xxx"
  Step 2: python3 {baseDir}/scripts/cron_poll.py ... MODULE --session-id sess_xxx --loop --interval 30  (background:true)
  → Background polling until status becomes "complete"
  → {"status":"complete", "content":"...", "session_id":"..."}
  → deliver content to user
```

The async workflow: `start` command returns instantly with a session identifier, then `cron_poll.py` handles polling in the background. When the task completes, the final JSON with full results is delivered.

## Credentials

Environment variables injected via `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "alta_lex_legal": {
        "enabled": true,
        "env": {
          "ALTA_LEX_USERNAME": "<username>",
          "ALTA_LEX_PASSWORD": "<password>",
          "ALTA_LEX_SESSION_ID": "<optional: direct token, bypasses login>"
        }
      }
    }
  }
}
```

Authentication priority: `ALTA_LEX_SESSION_ID` (if set) > `ALTA_LEX_USERNAME` + `ALTA_LEX_PASSWORD`.

## File Structure

All modules are implemented under the `scripts/` subdirectory. **You do NOT need to read or reference any of these files.** All interaction is done via CLI commands only.

```
scripts/
├── alta_lex.py          # Main CLI entry point
├── cron_poll.py         # Polling utility for async results
├── core/
│   ├── client.py        # HTTP client, authentication, session cache
│   └── sse.py           # SSE stream handler
├── modules/             # 11 legal AI modules
│   ├── legal_research.py
│   ├── contract_draft.py
│   ├── contract_review.py
│   ├── contract_compare.py
│   ├── ipo_support.py
│   ├── negotiation.py
│   ├── translation.py
│   ├── due_diligence.py
│   ├── compliance.py
│   ├── desensitization.py
│   └── tabular.py
└── utils/
    └── output.py
```

> **Important**: Always use the full path `python3 {baseDir}/scripts/alta_lex.py` when running CLI commands.

## Intent Detection

| User Intent (keywords) | Module | Action |
|---|---|---|
| Draft/write/create a contract | draft | `draft start` |
| Review/audit contract for risks | review | `review start` |
| Compare two contract versions | compare | `compare start` |
| Legal question/research/regulation | research | `research start` |
| IPO/listing/prospectus/HKEX check | ipo | `ipo start` |
| Negotiation strategy/playbook | negotiation | `negotiation start` |
| Translate legal document (file) | translation | `translation start` |
| Translate short text snippet | translation | `translation quick` |
| Due diligence/DD/investment check | duediligence | `duediligence checklist` then `start` |
| Compliance/regulatory review | compliance | `compliance start` |
| Desensitize/redact/anonymize doc | desensitize | `desensitize start` |
| Extract tables/data from documents | tabular | `tabular checklist` then `start` |

## Universal Workflow

**All modules follow this pattern:**

### Step 1: Detect Intent
Match user message to a module using the Intent Detection table above.

### Step 2: Gather Parameters
Ask the user for required parameters listed in the Module Reference below. Use defaults when the user doesn't specify.

### Step 3: Start Task (Async)
```bash
python3 {baseDir}/scripts/alta_lex.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  MODULE start [params...]
```
Returns immediately: `{"status":"started", "session_id":"sess_xxx", "chat_id":"chat_xxx", "module":"MODULE"}`

Capture the `session_id` (and `chat_id` if present) from the response for polling.

### Step 4: Poll for Results (Background)
```bash
python3 {baseDir}/scripts/cron_poll.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  MODULE --session-id "sess_xxx" \
  --loop --interval 30 --max-attempts 30
```
Run with `background:true`. Outputs JSON on each poll cycle. When `status` becomes `complete`, the `content` field has the full result.

> **Polling parameter variations by module:**
> - `review`: use `--filename "$FILENAME"` instead of `--session-id`
> - `compliance`, `duediligence`, `tabular`: use both `--session-id "sess_xxx"` and `--chat-id "chat_xxx"`
> - All other modules: use `--session-id "sess_xxx"` only

### Step 5: Check Active Tasks (Optional)
```bash
python3 {baseDir}/scripts/alta_lex.py tasks list
```
Returns all active tasks with their status, module, session_id, chat_id, and other metadata.

### Step 6: Notify User & Auto-Delivery
Send: "I'm processing your request using Alta Lex AI. This typically takes ~X minutes. I'll notify you when it's ready."
(Refer to the Expected Duration table below.)

When the background polling finishes and `status` is `complete`, deliver `content` verbatim to the user.
When `status` is `error`, deliver the error message to the user.

**Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim.**

## Expected Duration

| Module | Expected Duration |
|---|---|
| draft | ~1 min |
| review | ~2 min |
| compare | ~1 min |
| research | ~5-8 min |
| ipo | ~1 min |
| negotiation | ~1 min |
| translation | ~1 min |
| duediligence | ~3 min |
| compliance | ~10 min |
| desensitize | ~30s |
| tabular | ~5 min |

## Polling with cron_poll.py

`cron_poll.py` is the standard tool for retrieving async task results. It supports two modes:

### Single Query Mode (One-shot)
Check the current status of a task once:
```bash
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  MODULE --session-id "sess_xxx"
```

### Loop Mode (Background Polling — Recommended)
Automatically poll until the task completes or max attempts are reached:
```bash
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  MODULE --session-id "sess_xxx" \
  --loop --interval 30 --max-attempts 30
```
Run with `background:true`. The script outputs JSON on every poll cycle.

### Default Polling Intervals by Module

| Module | Default Interval |
|---|---|
| draft | 30s |
| compare | 30s |
| research | 30s |
| ipo | 30s |
| negotiation | 30s |
| translation | 30s |
| review | 30s |
| duediligence | 60s |
| compliance | 90s |
| desensitize | 20s |
| tabular | 60s |

If `--interval` is omitted, `cron_poll.py` uses the module's default interval. Use `--max-attempts` to prevent infinite polling.

### Full cron_poll.py Options
```
python3 {baseDir}/scripts/cron_poll.py -u USER -p PASS MODULE \
  [--session-id SID] [--chat-id CID] [--filename FN] \
  [--loop] [--interval SECS] [--max-attempts N] \
  [--auth-session-id AID] [--base-url URL]
```

## Module Reference

### Contract Draft (`draft`)
**Trigger**: User wants to draft/write/create a contract
**Required params**: `--industry`, `--position`, `--scenario`, `--contract-type`, `--governing-law`
**Optional**: `--language` (default: Chinese), `--template-url`, `--request`
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  draft start --industry "$INDUSTRY" --position "$POSITION" --scenario "$SCENARIO" \
  --contract-type "$TYPE" --governing-law "$LAW"

# Step 2: Poll in background
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  draft --session-id "$SESSION_ID" --loop --interval 30 --max-attempts 30
```

### Contract Review (`review`)
**Trigger**: User wants to review/audit a contract file for risks
**Required params**: `--file-url`, `--review-type` (1=Summary, 2=Edit), `--industry`, `--position`, `--scenario`, `--contract-type`
**Optional**: `--governing-law`, `--language`, `--request`
**Commands**:
```bash
# Step 1: Start (returns immediately with extra.filename)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  review start --file-url "$URL" --review-type "1" --industry "$IND" \
  --position "$POS" --scenario "$SCE" --contract-type "$TYPE"

# Step 2: Poll in background (use --filename, not --session-id)
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  review --filename "$FILENAME" --loop --interval 30 --max-attempts 30
```
**Note**: Review type "1"=Summary (text analysis), "2"=Edit (tracked changes). Default to "1".

### Contract Compare (`compare`)
**Trigger**: User wants to compare two contract versions
**Required params**: `--original-url`, `--revised-url`
**Optional**: `--industry`, `--position`, `--contract-type`, `--language`, `--governing-law`, `--title`, `--request`
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  compare start --original-url "$URL1" --revised-url "$URL2"

# Step 2: Poll in background
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  compare --session-id "$SESSION_ID" --loop --interval 30 --max-attempts 30
```

### Legal Research (`research`)
**Trigger**: User asks a legal question, wants regulation/case research
**Required params**: `-q` (query)
**Optional**: `--research-type` (quick/search, default: search), `--file-urls` (comma-separated, max 5)
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  research start -q "Legal question here" --research-type "search"

# Step 2: Poll in background
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  research --session-id "$SESSION_ID" --loop --interval 30 --max-attempts 30
```
**Follow-up**: `research followup --session-id "$SID" -q "Follow-up question"` (max 10 rounds in search mode)

### IPO Support (`ipo`)
**Trigger**: User needs IPO/listing compliance checks (HKEX focused)
**Optional params**: `--title`, `--connected-person`, `--transact-class`, `--transaction-class`, `--involves-guarantees`, `--shareholder-approval`, `--circular-requirements`, `--other-facts`, `--file-url`
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  ipo start --title "IPO Check" --connected-person "Director"

# Step 2: Poll in background
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  ipo --session-id "$SESSION_ID" --loop --interval 30 --max-attempts 30
```

### Negotiation Playbook (`negotiation`)
**Trigger**: User wants negotiation strategies for a contract
**Required params**: `--industry`, `--position`, `--scenario`, `--contract-type`
**Optional**: `--language`, `--title`, `--request`, `--file-url`
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  negotiation start --industry "$IND" --position "$POS" \
  --scenario "$SCE" --contract-type "$TYPE"

# Step 2: Poll in background
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  negotiation --session-id "$SESSION_ID" --loop --interval 30 --max-attempts 30
```

### Document Translation (`translation`)
**Trigger**: User wants to translate a legal document or text
**For files** — Required: `--file-url`. Optional: `--source-lang`, `--target-lang`, `--contract-type`, `--governing-law`
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  translation start --file-url "$URL" --source-lang English --target-lang Chinese

# Step 2: Poll in background
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  translation --session-id "$SESSION_ID" --loop --interval 30 --max-attempts 30
```

**For short text** — Required: `-q` (text). Optional: `--source-lang`, `--target-lang`
**Quick**: `python3 {baseDir}/scripts/alta_lex.py translation quick -q "Text to translate" --source-lang English --target-lang Chinese`
(Returns immediately, no polling needed)

### Due Diligence (`duediligence`)
**Trigger**: User needs due diligence / investment checks
**Two-step workflow**:
1. Generate checklist: `python3 {baseDir}/scripts/alta_lex.py duediligence checklist --document-type "$DOCTYPE" --position "$POS" --industry "$IND"`
2. Start analysis (returns immediately with session_id and chat_id):
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  duediligence start --file-url "$URL" --session-id "$SID" --checklist "$CHECKLIST"
```
3. Poll in background (requires both --session-id and --chat-id):
```bash
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  duediligence --session-id "$SESSION_ID" --chat-id "$CHAT_ID" \
  --loop --interval 60 --max-attempts 30
```
**Note**: Step 1 returns checklist in `content`. Feed it to step 2 via `--checklist`.

### Legal Compliance (`compliance`)
**Trigger**: User needs regulatory compliance review
**Required**: `--file-urls` (comma-separated), `--jurisdiction`, `--domains` (comma-separated)
**Domains**: DATA_PRIVACY, CYBERSECURITY, FINANCIAL_REGULATION, ANTITRUST, INTELLECTUAL_PROPERTY, LABOR_LAW, ENVIRONMENTAL, CONSUMER_PROTECTION
**Optional**: `--title`, `--output-language`, `--entity-type`, `--data-scope`, `--business-regions`
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id and chat_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  compliance start --file-urls "$URL1,$URL2" --jurisdiction "PRC" \
  --domains "DATA_PRIVACY,CYBERSECURITY"

# Step 2: Poll in background (requires both --session-id and --chat-id)
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  compliance --session-id "$SESSION_ID" --chat-id "$CHAT_ID" \
  --loop --interval 90 --max-attempts 30
```
**Export**: `python3 {baseDir}/scripts/alta_lex.py compliance export --session-id "$SID"` (returns Excel download URL)
**Note**: Check returns `progress` field with percentage and phase info during processing.

### Desensitization (`desensitize`)
**Trigger**: User wants to redact/anonymize sensitive info in a document
**Required**: `--file-url`
**Optional**: `--title`, `--entity-types` (comma-separated: PERSON,ORGANIZATION,EMAIL,PHONE,ID_NUMBER,ADDRESS,BANK_CARD,DATE)
**Commands**:
```bash
# Step 1: Start (returns immediately with session_id)
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  desensitize start --file-url "$URL" --entity-types "PERSON,ORGANIZATION,EMAIL"

# Step 2: Poll in background
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  desensitize --session-id "$SESSION_ID" --loop --interval 20 --max-attempts 30
```
**Note**: Result `content` is the desensitized file download URL.

### Tabular Analysis (`tabular`)
**Trigger**: User wants to extract structured data/tables from documents
**Two-step workflow**:
1. Generate checklist: `python3 {baseDir}/scripts/alta_lex.py tabular checklist --document-type "$DOCTYPE" --position "$POS" --industry "$IND"`
2. Start analysis (returns immediately with session_id and chat_id):
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  tabular start --file-urls "$URL1,$URL2" --checklist '$JSON_CHECKLIST'
```
3. Poll in background (requires both --session-id and --chat-id):
```bash
python3 {baseDir}/scripts/cron_poll.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  tabular --session-id "$SESSION_ID" --chat-id "$CHAT_ID" \
  --loop --interval 60 --max-attempts 30
```

## Tasks Management

List all active tasks to monitor their status:

```bash
python3 {baseDir}/scripts/alta_lex.py tasks list
```

Returns a JSON array of active tasks, each containing:
- `module`: the module name
- `session_id`: task session identifier
- `chat_id`: chat identifier (if applicable)
- `status`: current status (started, running, complete, error)
- `created_at`: task creation timestamp

Use this to check on background tasks or recover session identifiers.

## Formatting Rules

**Discord**: Markdown natively supported. No conversion needed.

**WhatsApp**:
- Replace `## Title` with **bold** text
- Replace tables with bullet lists
- Keep responses under 4000 chars; split if longer
- Use `*bold*` for emphasis

## Error Handling

| Error | Recovery |
|---|---|
| `A01001` Session expired | Client auto-retries login. If still fails, ask user to check credentials. |
| `A04006` Credit insufficient | Tell user to contact admin for credit recharge. |
| `B00001` System error | Retry once. If persists, tell user to try later. |
| Authentication failure | Verify credentials in `~/.openclaw/openclaw.json`. |

## Security & Privacy

- Credentials are injected via environment variables, never hardcoded or logged.
- All data is transmitted over HTTPS to the Alta Lex API server (default: `test.alta-lex.ai`, overridable via `ALTA_LEX_BASE_URL` env).
- No local state files are written; session state is managed server-side.
- By using this skill, legal queries and documents are sent to the Alta Lex AI platform for processing.

## External Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| /api/login | POST | Authentication |
| /api/createDraftSession | POST | Contract draft session |
| /api/commonGenerateSse | GET | SSE generation (draft, compare, ipo, negotiation) |
| /api/common_review | POST | Submit contract review |
| /api/getReviewAnswer | POST | Poll review result |
| /api/createContractCompare | POST | Contract compare session |
| /api/createAnalysisSession | POST | Legal research session |
| /api/legalAnalysisSse | POST | SSE legal analysis |
| /api/createIpoCheckListSession | POST | IPO check session |
| /api/createNegotiationPlaybook | POST | Negotiation session |
| /api/createTranslateSession | POST | Translation session |
| /api/textTranslate | POST | SSE translation |
| /api/genaralTranslate | POST | Quick translate |
| /api/generateDueDiligenceChecklist | POST | DD checklist |
| /api/checkDueDiligenceFile | POST | DD single file check |
| /api/analyzeDocuments | POST | DD batch analysis |
| /api/legal_compliance/startComplianceAnalysis | POST | Start compliance |
| /api/legal_compliance/getComplianceTaskResult | GET | Poll compliance |
| /api/runDesensitize | POST | Start desensitization |
| /api/getWorkflowDetail/desensitize | GET | Poll desensitization |
| /api/startTabularAnalysis | POST | Start tabular analysis |
| /api/getTabularTaskResult | GET | Poll tabular result |
