---
name: alta_lex_legal
version: 2.0.0
description: "Full-featured legal AI assistant via Alta Lex platform. Covers 11 modules: contract drafting, contract review, contract comparison, legal research, IPO support, negotiation playbook, document translation, due diligence, legal compliance, desensitization, and tabular analysis. Use when: (1) user wants to draft, review, compare, or translate contracts; (2) user asks legal questions or requests legal research; (3) user needs IPO compliance checks, negotiation strategies, due diligence, compliance review, data desensitization, or document data extraction. NOT for: non-legal questions, simple factual lookups unrelated to law."
metadata: { "openclaw": { "emoji": "⚖️", "requires": { "bins": ["python3"], "env": ["ALTA_LEX_USERNAME", "ALTA_LEX_PASSWORD"] }, "os": ["darwin", "linux"] } }
---

# Alta Lex Legal AI — Unified Skill (11 Modules)

Full legal AI assistant covering contract management, legal research, compliance, and document processing. Results are generated asynchronously via SSE or background tasks.

## Architecture

```
User (Discord/WhatsApp) → OpenClaw Agent
  → python3 {baseDir}/scripts/alta_lex.py ... MODULE start [params]
  → {"status": "started", "session_id": "UUID", ...}
  → openclaw cron (every Xm: MODULE check --session-id UUID)
  → status: "complete" → auto-reply to user → cleanup
```

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
          "ALTA_LEX_PASSWORD": "<password>"
        }
      }
    }
  }
}
```

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

### Step 3: Execute Start Command
```bash
python3 {baseDir}/scripts/alta_lex.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  MODULE ACTION [--param value ...]
```
Run with `background:true`. Parse the JSON output to extract `session_id`, `chat_id`, or `filename`.

### Step 4: Notify User
Send: "I'm processing your request using Alta Lex AI. This typically takes ~X minutes. I'll notify you when it's ready."

### Step 5: Register Cron
```bash
openclaw cron create \
  --name "alta-lex-MODULE-SESSION_ID_SHORT" \
  --every INTERVAL \
  --command "python3 {baseDir}/scripts/alta_lex.py -u \"$ALTA_LEX_USERNAME\" -p \"$ALTA_LEX_PASSWORD\" MODULE check --session-id \"SESSION_ID\" [--chat-id \"CHAT_ID\"] [--filename \"FILENAME\"]" \
  --on-complete "reply" \
  --on-error "reply" \
  --auto-cleanup
```

### Step 6: Auto-Delivery (via Cron)
- `status: "running"` → wait for next poll
- `status: "complete"` → deliver `content` verbatim to user, cleanup cron
- `status: "error"` → deliver error message, cleanup cron

**Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim.**

## Cron Intervals

| Module | Duration | Interval |
|---|---|---|
| draft | ~1 min | 30s |
| review | ~2 min | 30s |
| compare | ~1 min | 30s |
| research | ~5-8 min | 2m |
| ipo | ~1 min | 30s |
| negotiation | ~1 min | 30s |
| translation | ~1 min | 30s |
| duediligence | ~3 min | 1m |
| compliance | ~10 min | 2m |
| desensitize | ~30s | 20s |
| tabular | ~5 min | 1m |

## Module Reference

### Contract Draft (`draft`)
**Trigger**: User wants to draft/write/create a contract
**Required params**: `--industry`, `--position`, `--scenario`, `--contract-type`, `--governing-law`
**Optional**: `--language` (default: Chinese), `--template-url`, `--request`
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  draft start --industry "$INDUSTRY" --position "$POSITION" --scenario "$SCENARIO" \
  --contract-type "$TYPE" --governing-law "$LAW"
```
**Check**: `draft check --session-id "$SID"`

### Contract Review (`review`)
**Trigger**: User wants to review/audit a contract file for risks
**Required params**: `--file-url`, `--review-type` (1=Summary, 2=Edit), `--industry`, `--position`, `--scenario`, `--contract-type`
**Optional**: `--governing-law`, `--language`, `--request`
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  review start --file-url "$URL" --review-type "1" --industry "$IND" \
  --position "$POS" --scenario "$SCE" --contract-type "$TYPE"
```
**Check**: `review check --filename "$FILENAME"` (filename from start output `extra.filename`)
**Note**: Review type "1"=Summary (text analysis), "2"=Edit (tracked changes). Default to "1".

### Contract Compare (`compare`)
**Trigger**: User wants to compare two contract versions
**Required params**: `--original-url`, `--revised-url`
**Optional**: `--industry`, `--position`, `--contract-type`, `--language`, `--governing-law`, `--title`, `--request`
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  compare start --original-url "$URL1" --revised-url "$URL2"
```
**Check**: `compare check --session-id "$SID"`

### Legal Research (`research`)
**Trigger**: User asks a legal question, wants regulation/case research
**Required params**: `-q` (query)
**Optional**: `--research-type` (quick/search, default: search), `--file-urls` (comma-separated, max 5)
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  research start -q "Legal question here" --research-type "search"
```
**Check**: `research check --session-id "$SID"`
**Follow-up**: `research followup --session-id "$SID" -q "Follow-up question"` (max 10 rounds in search mode)

### IPO Support (`ipo`)
**Trigger**: User needs IPO/listing compliance checks (HKEX focused)
**Optional params**: `--title`, `--connected-person`, `--transact-class`, `--transaction-class`, `--involves-guarantees`, `--shareholder-approval`, `--circular-requirements`, `--other-facts`, `--file-url`
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  ipo start --title "IPO Check" --connected-person "Director"
```
**Check**: `ipo check --session-id "$SID"`

### Negotiation Playbook (`negotiation`)
**Trigger**: User wants negotiation strategies for a contract
**Required params**: `--industry`, `--position`, `--scenario`, `--contract-type`
**Optional**: `--language`, `--title`, `--request`, `--file-url`
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  negotiation start --industry "$IND" --position "$POS" \
  --scenario "$SCE" --contract-type "$TYPE"
```
**Check**: `negotiation check --session-id "$SID"`

### Document Translation (`translation`)
**Trigger**: User wants to translate a legal document or text
**For files** — Required: `--file-url`. Optional: `--source-lang`, `--target-lang`, `--contract-type`, `--governing-law`
**Start**: `translation start --file-url "$URL" --source-lang English --target-lang Chinese`
**Check**: `translation check --session-id "$SID"`

**For short text** — Required: `-q` (text). Optional: `--source-lang`, `--target-lang`
**Quick**: `translation quick -q "Text to translate" --source-lang English --target-lang Chinese`
(Returns immediately, no cron needed)

### Due Diligence (`duediligence`)
**Trigger**: User needs due diligence / investment checks
**Two-step workflow**:
1. Generate checklist: `duediligence checklist --document-type "$DOCTYPE" --position "$POS" --industry "$IND"`
2. Submit files: `duediligence start --file-url "$URL" --session-id "$SID" --checklist "$CHECKLIST"`
**Check**: `duediligence check --session-id "$SID" --chat-id "$CID"`
**Note**: Step 1 returns checklist in `content`. Feed it to step 2 via `--checklist`.

### Legal Compliance (`compliance`)
**Trigger**: User needs regulatory compliance review
**Required**: `--file-urls` (comma-separated), `--jurisdiction`, `--domains` (comma-separated)
**Domains**: DATA_PRIVACY, CYBERSECURITY, FINANCIAL_REGULATION, ANTITRUST, INTELLECTUAL_PROPERTY, LABOR_LAW, ENVIRONMENTAL, CONSUMER_PROTECTION
**Optional**: `--title`, `--output-language`, `--entity-type`, `--data-scope`, `--business-regions`
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  compliance start --file-urls "$URL1,$URL2" --jurisdiction "PRC" \
  --domains "DATA_PRIVACY,CYBERSECURITY"
```
**Check**: `compliance check --session-id "$SID" --chat-id "$CID"`
**Export**: `compliance export --session-id "$SID"` (returns Excel download URL)
**Note**: Check returns `progress` field with percentage and phase info during processing.

### Desensitization (`desensitize`)
**Trigger**: User wants to redact/anonymize sensitive info in a document
**Required**: `--file-url`
**Optional**: `--title`, `--entity-types` (comma-separated: PERSON,ORGANIZATION,EMAIL,PHONE,ID_NUMBER,ADDRESS,BANK_CARD,DATE)
**Start**:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  desensitize start --file-url "$URL" --entity-types "PERSON,ORGANIZATION,EMAIL"
```
**Check**: `desensitize check --session-id "$SID"`
**Note**: Result `content` is the desensitized file download URL.

### Tabular Analysis (`tabular`)
**Trigger**: User wants to extract structured data/tables from documents
**Two-step workflow**:
1. Generate checklist: `tabular checklist --document-type "$DOCTYPE" --position "$POS" --industry "$IND"`
2. Start analysis: `tabular start --file-urls "$URL1,$URL2" --checklist '$JSON_CHECKLIST'`
**Check**: `tabular check --session-id "$SID" --chat-id "$CID"`

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

## Fallback — Manual Polling

If `openclaw cron` is unavailable, poll manually:
```bash
python3 {baseDir}/scripts/alta_lex.py -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  MODULE check --session-id "$SID" [--chat-id "$CID"] [--filename "$FN"]
```
Repeat at the interval specified in the Cron Intervals table until `status` is `complete` or `error`.

## Security & Privacy

- Credentials are injected via environment variables, never hardcoded or logged.
- All data is transmitted over HTTPS to `api.alta-lex.ai`.
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
