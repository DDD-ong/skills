---
name: alex_law_legal
description: "Professional legal research and analysis via Alta Lex AI platform. Use when: (1) user asks any legal question or requests legal analysis, (2) user asks about laws, regulations, ordinances, legal rights, obligations, or legal procedures in any practice area, (3) user explicitly requests Alta Lex legal analysis. NOT for: non-legal questions, simple factual lookups unrelated to law."
metadata: { "openclaw": { "emoji": "⚖️", "requires": { "bins": ["python3"], "env": ["ALTA_LEX_USERNAME", "ALTA_LEX_PASSWORD"] }, "os": ["darwin", "linux"] } }
---

# Alta Lex Legal Research Skill

Query the Alta Lex AI platform for professional legal analysis across all practice areas. Results are streamed via SSE and typically take around 5 minutes to complete.

## Architecture

```
User (Discord/WhatsApp) → OpenClaw Agent
  → python3 alta_lex_client.py --quick-start -q "..." → {"session_id": "UUID"}
  → openclaw cron (every 5m: --check-session UUID)
  → status: "complete" → auto-reply to user → cleanup
```

No intermediate session files are needed. The session state is managed server-side by Alta Lex (via `session_id`). The `--check-session` command queries the API directly for completion status.

## Credentials

Credentials are injected via environment variables:
- `ALTA_LEX_USERNAME` — Alta Lex login username
- `ALTA_LEX_PASSWORD` — Alta Lex login password

Configure in `~/.openclaw/openclaw.json`:
```json
{
  "skills": {
    "entries": {
      "alex_law_legal": {
        "enabled": true,
        "env": {
          "ALTA_LEX_USERNAME": "<your_username>",
          "ALTA_LEX_PASSWORD": "<your_password>"
        }
      }
    }
  }
}
```

## Workflow — Step by Step

### Step 1: Identify the Legal Question

Extract the core legal question from the user's message. If the user wrote in another language, rephrase the query into clear English. Include relevant context (jurisdiction, property type, specific scenario).

**Important — Gather required parameters before proceeding:**

You MUST ask the user for the following information and store the answers in variables. If the user does not provide a value, use the default.

| Question | Variable | Example / Default |
|----------|----------|-------------------|
| What is the practice area? | `$practice_area` | Auto-detect from query (default: "General") |
| What is the jurisdiction? | `$jurisdiction` | `"Hong Kong"` (default) |
| What is the preferred output language? | `$language` | `"English"` (default) |

### Step 2: Quick-Start Analysis

Run the analysis in quick-start mode. This creates a session, fires the SSE analysis request, and immediately returns the `session_id`:

```bash
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  --quick-start \
  -q "The legal question here" \
  --practice-area "$practice_area" \
  --jurisdiction "$jurisdiction" \
  --output-language "$language"
```

Run this command with `background:true`. The output is a JSON object:
```json
{"status": "started", "session_id": "UUID", "content": "", "error": ""}
```

Extract the `session_id` from the output for use in Step 3.

**Important**: Immediately after starting, send the user a message:
> "I'm consulting Alta Lex AI for a professional legal analysis of your question. This typically takes around 5 minutes. I'll keep you updated on the progress."

### Step 3: Schedule Auto-Notification via OpenClaw Cron

Register a **temporary cron job** to poll for results and auto-reply upon completion:

```bash
openclaw cron create \
  --name "alta-lex-$SESSION_ID" \
  --every 5m \
  --command "python3 {baseDir}/scripts/alta_lex_client.py -u \"$ALTA_LEX_USERNAME\" -p \"$ALTA_LEX_PASSWORD\" --check-session \"$SESSION_ID\"" \
  --on-complete "reply" \
  --on-error "reply" \
  --auto-cleanup
```

This tells OpenClaw to:
1. Execute the check command every **5 minutes**
2. Parse the JSON output and check the `status` field
3. When `status` is `"running"` — do nothing, wait for the next poll cycle
4. When `status` is `"complete"` — automatically reply to the user with the `content` field, then **stop and remove the cron job**
5. When `status` is `"error"` — automatically reply with a polite error message, then **stop and remove the cron job**

**The check command returns JSON with these fields:**
- `status`: `"running"` | `"complete"` | `"error"`
- `session_id`: the analysis session UUID
- `content`: full analysis text (present when `status` is `"complete"`)
- `error`: error message (present when `status` is `"error"`)

### Step 4: Automatic Result Delivery (via Cron)

When the cron detects `status: "complete"`:
1. The cron reads the full `content` from the check output.
2. **Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim.**
3. The cron triggers a reply to the user with the complete analysis (Markdown format).
4. For **WhatsApp**: convert Markdown to WhatsApp-friendly format (see Formatting Rules below).
5. For **Discord**: Markdown is natively supported.

No manual intervention is required — the cron handles the entire delivery lifecycle automatically.

### Step 5: Automatic Error Handling (via Cron)

When the cron detects `status: "error"`:
1. The cron reads the `error` field from the check output.
2. The cron triggers a reply to the user with a polite error message:
   > "I encountered an issue while consulting Alta Lex. Please try again later or rephrase your question."

If authentication failed -> verify credentials in `~/.openclaw/openclaw.json`.
If session expired -> the client auto-retries login; if it still fails, the error is reported.

### Step 6: Fallback — Manual Polling

If `openclaw cron` is not available, fall back to manual polling:

```bash
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  --check-session "$SESSION_ID"
```

Repeat every 5 minutes until `status` is `"complete"` or `"error"`, then deliver results or error message to the user manually.

## Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--practice-area` | `""` | Legal practice area |
| `--jurisdiction` | `""` | Legal jurisdiction |
| `--output-language` | `"English"` | Response language |
| `--background` | `""` | Additional context for the query |
| `--pro` | off | Enable advanced research mode (uses more credits) |

Common practice areas: `"Property Law"`, `"Tenancy Law"`, `"Conveyancing"`, `"Building Management"`, `"Corporate Law"`, `"Employment Law"`, `"Contract Law"`, `"Intellectual Property"`, `"Criminal Law"`, `"Family Law"`, `"Tax Law"`, `"Banking & Finance"`, `"Competition Law"`, `"Regulatory & Compliance"`, `"Litigation"`, `"Arbitration"`.

Adjust `--practice-area` and `--jurisdiction` based on the user's question context.

## Formatting Rules

**Discord**: Markdown is natively supported. No conversion needed.

**WhatsApp**: When delivering results via WhatsApp:
- Replace Markdown headers (`## Title`) with **bold** text
- Replace Markdown tables with bullet lists
- Keep responses under 4000 characters; if longer, split into multiple messages
- Use `*bold*` for emphasis (WhatsApp format)
- Preserve numbered lists and bullet points as-is

## Example Interaction

**User (Discord):** "I want to know what are my rights as a tenant if my landlord wants to increase the rent significantly in Hong Kong?"

**Agent actions:**
1. **Identify**: Property/tenancy law question; set `$practice_area = "Tenancy Law"` (auto-detected), `$jurisdiction = "Hong Kong"`, `$language = "English"`
2. **Quick-start** analysis with query: "What are the legal rights of a tenant when a landlord wants to significantly increase rent in Hong Kong? What protections does the Landlord and Tenant (Consolidation) Ordinance provide?"
3. **Notify user**: "Consulting Alta Lex AI for professional analysis..."
4. **Register cron** to poll `--check-session` every 5 minutes
5. **On completion**: Deliver the legal analysis verbatim via Discord reply
6. **Cron auto-cleanup**

## Direct CLI Usage (for testing)

```bash
# Quick-start (returns JSON with session_id)
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  --quick-start -q "tenant rights for rent increase" \
  --practice-area "Tenancy Law" --jurisdiction "Hong Kong"

# Check session status (returns JSON)
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  --check-session "SESSION_ID_HERE"

# Full foreground analysis (SSE streaming, 5-8 minutes)
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  -q "What are the tenant rights regarding rent increase in Hong Kong?" \
  --practice-area "Property Law" --jurisdiction "Hong Kong"

# List existing sessions
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" --list-sessions

# View session history
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" --session-history "SESSION_ID"
```

## Notes

- Analysis typically takes around 5 minutes; do not kill the background process prematurely
- JWT token is valid for ~3 hours; the client handles automatic re-login on expiry
- Each analysis consumes credits on the Alta Lex platform
- No temporary session files are needed; state is managed server-side via `session_id`
- **Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim. Do not translate anything.**

## External Endpoints

| Endpoint | Method | Data Sent | Purpose |
|----------|--------|-----------|---------|
| https://test.alta-lex.ai/api/login | POST | username, password | Authentication |
| https://test.alta-lex.ai/api/getUserInfo | POST | (empty) | Verify auth / get credit balance |
| https://test.alta-lex.ai/api/createAnalysisSession | POST | query | Session creation |
| https://test.alta-lex.ai/api/legalAnalysisSse | POST | sessionId, query, practiceArea, jurisdiction, outputLanguage, background, legalResearchPro | SSE streaming analysis |
| https://test.alta-lex.ai/api/getAnalysisSessionHistory | GET | sessionId (query param) | Check results / poll status |

## Security & Privacy

- **Credentials:** `ALTA_LEX_USERNAME` and `ALTA_LEX_PASSWORD` are required and injected via environment variables configured in `~/.openclaw/openclaw.json`. They are never hardcoded or logged.
- **Data transmission:** Legal queries and analysis results are sent to `test.alta-lex.ai` (third-party Alta Lex AI service) over HTTPS.
- **Token lifecycle:** JWT authentication tokens are managed automatically via `requests.Session` cookies (approx. 3-hour expiry, auto-refreshed on 401).
- **No local state files:** Session state is managed server-side. No temporary files are written to disk.

## Trust Statement

By using this skill, your legal queries and conversation context will be sent to the Alta Lex AI platform for analysis. Only install this skill if you trust Alta Lex as a legal research provider. You must provide valid Alta Lex credentials via environment variables. This skill does not store or forward your credentials beyond the Alta Lex authentication endpoint.

## Model Invocation Note

This skill is designed to be autonomously invoked by the agent when it detects legal questions in conversation. If you prefer manual-only invocation, set `disable-model-invocation: true` in the skill's frontmatter or OpenClaw configuration.
