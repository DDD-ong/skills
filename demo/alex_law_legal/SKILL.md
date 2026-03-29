---
name: alex_law_legal
description: "Professional legal research, analysis, and drafting via Alta Lex AI platform. Use when: (1) user asks any legal question or requests legal analysis, (2) user asks about laws, regulations, ordinances, legal rights, obligations, or legal procedures in any practice area, (3) user requests drafting, reviewing, or preparing legal documents such as agreements, contracts, letters, memoranda, or other legal instruments, (4) user explicitly requests Alta Lex legal analysis. NOT for: non-legal questions, simple factual lookups unrelated to law."
metadata: { "openclaw": { "emoji": "⚖️", "requires": { "bins": ["python3"], "env": ["ALTA_LEX_USERNAME", "ALTA_LEX_PASSWORD"] }, "os": ["darwin", "linux"] } }
---

# Alta Lex Legal Research Skill

Query the Alta Lex AI platform for professional legal analysis across all practice areas. Results are streamed via SSE and typically take around 5 minutes to complete.

## Architecture

```
User (WhatsApp) → OpenClaw → python3 alta_lex_poll.py run → Alta Lex API (SSE)
                                       ↓
                               session file (JSON)
                                       ↓
                     OpenClaw polls every 5 mins → reply to user
```

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

### Step 2: Start Background Analysis

Generate a unique session file path and run the analysis script in background mode:

```bash
SESSION_FILE="/tmp/alta-lex-$(date +%s)-$RANDOM.json"

python3 {baseDir}/scripts/alta_lex_poll.py run \
  --username "$ALTA_LEX_USERNAME" \
  --password "$ALTA_LEX_PASSWORD" \
  --query "The legal question here" \
  --session-file "$SESSION_FILE" \
  --practice-area "$practice_area" \
  --jurisdiction "$jurisdiction" \
  --output-language "$language"
```

Run this command with `background:true` so it executes in the background. Do NOT append `&` — OpenClaw handles backgrounding via the `background:true` flag.

**Important**: Immediately after starting, send the user a message:
> "I'm consulting Alta Lex AI for a professional legal analysis of your question. This typically takes around 5 minutes. I'll keep you updated on the progress."

### Step 3: Schedule Polling via OpenClaw Cron

Use `openclaw cron` to schedule periodic polling, ensuring results are reliably returned even if the current conversation context is lost.

Register a cron job immediately after starting the background analysis:

```
openclaw cron --every 5m --command "python3 {baseDir}/scripts/alta_lex_poll.py poll --session-file \"$SESSION_FILE\"" --until-status complete --on-complete "reply" --on-error "reply"
```

This tells OpenClaw to:
1. Execute the poll command every **5 minutes**
2. Automatically terminate the cron job execution if the following boolean expression evaluates to true:
IF (finished_at IS NOT NULL) OR (error IS NOT NULL) THEN STOP
3. Trigger a reply to the user with the result upon completion

**If `openclaw cron` is not available**, fall back to manual polling — run the poll command yourself every 5 minutes:

```bash
python3 {baseDir}/scripts/alta_lex_poll.py poll --session-file "$SESSION_FILE"
```

The poll command returns JSON with these fields:
- `status`: `"running"` | `"complete"` | `"error"`
- `content`: accumulated analysis text so far
- `error`: error message if status is `"error"`

### Step 4: Send Progress Updates

While `status` is `"running"`:
- On each poll (every 5 mins), send the user a brief update:
  > "Still analyzing... Alta Lex is working on your legal research."
- Do NOT send the partial `content` to the user — wait for completion.

**Note**: When using `openclaw cron`, the cron mechanism handles the polling loop automatically. You only need to handle the final result delivery (Step 5) or error handling (Step 6) when the cron triggers the reply callback.

### Step 5: Deliver Final Result

When `status` is `"complete"`:
1. Read the full `content` from the poll output.
2. **Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim.**
3. Format the legal analysis for the user (the content is Markdown).
4. For **WhatsApp**: convert Markdown to WhatsApp-friendly format (see WhatsApp Formatting Rules below).
5. Send the complete analysis to the user.
6. Clean up: `rm "$SESSION_FILE"`

### Step 6: Handle Errors

When `status` is `"error"`:
1. Read the `error` field from the poll output.
2. If authentication failed → verify credentials in `~/.openclaw/openclaw.json`.
3. If session expired → the script auto-retries re-login once; if it still fails, inform the user.
4. Send user a polite error message:
   > "I encountered an issue while consulting Alta Lex. Please try again later or rephrase your question."

## Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--practice-area` | `"Property Law"` | Legal practice area |
| `--jurisdiction` | `"Hong Kong"` | Legal jurisdiction |
| `--output-language` | `"English"` | Response language |
| `--background` | `""` | Additional context for the query |
| `--pro` | off | Enable advanced research mode (uses more credits) |

Common practice areas: `"Property Law"`, `"Tenancy Law"`, `"Conveyancing"`, `"Building Management"`, `"Corporate Law"`, `"Employment Law"`, `"Contract Law"`, `"Intellectual Property"`, `"Criminal Law"`, `"Family Law"`, `"Tax Law"`, `"Banking & Finance"`, `"Competition Law"`, `"Regulatory & Compliance"`, `"Litigation"`, `"Arbitration"`.

Adjust `--practice-area` and `--jurisdiction` based on the user's question context.

## WhatsApp Formatting Rules

When delivering results via WhatsApp:
- Replace Markdown headers (`## Title`) with **bold** text
- Replace Markdown tables with bullet lists
- Keep responses under 4000 characters; if longer, split into multiple messages
- Use `*bold*` for emphasis (WhatsApp format)
- Preserve numbered lists and bullet points as-is

## Example Interaction

**User (WhatsApp):** "I want to know what are my rights as a tenant if my landlord wants to increase the rent significantly in Hong Kong?"

**Agent actions:**
1. **Identify**: Property/tenancy law question; set `$practice_area = "Tenancy Law"` (auto-detected), `$jurisdiction = "Hong Kong"`, `$language = "English"`
2. **Start background analysis** with query: "What are the legal rights of a tenant when a landlord wants to significantly increase rent in Hong Kong? What protections does the Landlord and Tenant (Consolidation) Ordinance provide?"
3. **Notify user**: "Consulting Alta Lex AI for professional analysis..."
4. **Poll** every 5 minutes until status is `"complete"` or `"error"`
5. **On completion**: Format and deliver the legal analysis verbatim
6. **Clean up** session file

## Direct CLI Usage (for testing)

```bash
# Run analysis directly (foreground, via alta_lex_client.py)
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  -q "What are the tenant rights regarding rent increase in Hong Kong?" \
  --practice-area "Property Law" \
  --jurisdiction "Hong Kong"

# Run with polling (background mode, via alta_lex_poll.py)
SESSION_FILE="/tmp/alta-lex-test.json"
python3 {baseDir}/scripts/alta_lex_poll.py run \
  --username "$ALTA_LEX_USERNAME" --password "$ALTA_LEX_PASSWORD" \
  --query "tenant rights for rent increase" \
  --session-file "$SESSION_FILE" &

# Check status
python3 {baseDir}/scripts/alta_lex_poll.py poll --session-file "$SESSION_FILE"
```

## Notes

- Analysis typically takes around 5 minutes; do not kill the background process prematurely
- JWT token is valid for ~3 hours; the script handles automatic re-login on expiry
- Each analysis consumes credits on the Alta Lex platform
- The session file is atomically written (write to `.tmp` then `os.replace`) to prevent corruption during concurrent polling
- **Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim. Not translate anyting.**

## External Endpoints

| Endpoint | Method | Data Sent | Purpose |
|----------|--------|-----------|---------|
| https://test.alta-lex.ai/api/login | POST | username, password | Authentication |
| https://test.alta-lex.ai/api/createAnalysisSession | POST | query, parameters | Session creation |
| https://test.alta-lex.ai/api/legalAnalysisSse | POST | query, practice area, jurisdiction | SSE streaming analysis |

## Security & Privacy

- **Credentials:** `ALTA_LEX_USERNAME` and `ALTA_LEX_PASSWORD` are required and injected via environment variables configured in `~/.openclaw/openclaw.json`. They are never hardcoded or logged.
- **Data transmission:** Legal queries and analysis results are sent to `test.alta-lex.ai` (third-party Alta Lex AI service) over HTTPS.
- **Token lifecycle:** JWT authentication tokens are managed automatically via `requests.Session` cookies (approx. 3-hour expiry, auto-refreshed on 401).
- **Local storage:** Temporary session state files are stored in `/tmp/alta_lex_session_*.json` and cleaned up after analysis completion.

## Trust Statement

By using this skill, your legal queries and conversation context will be sent to the Alta Lex AI platform for analysis. Only install this skill if you trust Alta Lex as a legal research provider. You must provide valid Alta Lex credentials via environment variables. This skill does not store or forward your credentials beyond the Alta Lex authentication endpoint.

## Model Invocation Note

This skill is designed to be autonomously invoked by the agent when it detects legal questions in conversation. If you prefer manual-only invocation, set `disable-model-invocation: true` in the skill's frontmatter or OpenClaw configuration.