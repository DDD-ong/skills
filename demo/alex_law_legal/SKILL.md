---
name: alex_law_legal
description: "Professional legal research and analysis via Alta Lex AI platform. Use when: (1) user asks about property law, real estate law, housing law, tenancy, lease, landlord-tenant disputes, building management, property transactions, conveyancing, or stamp duty, (2) user asks a legal question about buying/selling/renting property or housing regulations, (3) user explicitly requests Alta Lex legal analysis, (4) user asks about the property ordinances, building codes, or land law. NOT for: general legal questions unrelated to property/housing, simple factual lookups, non-legal questions about real estate prices or market trends."
metadata: { "openclaw": { "emoji": "⚖️", "requires": { "bins": ["python3"], "env": ["ALTA_LEX_USERNAME", "ALTA_LEX_PASSWORD"] }, "os": ["darwin", "linux"] } }
---

# Alta Lex Legal Research Skill

Query the Alta Lex AI platform for professional property/housing legal analysis. Results are streamed via SSE and typically take 5 minutes to complete.

## Architecture

```
User (WhatsApp) → OpenClaw → python3 alta_lex_poll.py → Alta Lex API (SSE)
                                  ↓
                          session file (JSON)
                                  ↓
                    OpenClaw polls every 8mins → reply to user
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
      "alta-lex-legal": {
        "enabled": true,
        "env": {
          "ALTA_LEX_USERNAME": "your_username",
          "ALTA_LEX_PASSWORD": "your_password"
        }
      }
    }
  }
}
```

## Workflow — Step by Step

### Step 1: Identify the Legal Question

Extract the core property/housing legal question from the user's message. Rephrase into a clear legal query in English if the user wrote in another language. Include relevant context (jurisdiction, property type, specific scenario).

**Important**:
It needs to the client to import the key information. you need to ask the key inofmration
- What is the practice-area? And set the the answer into $practice_area. The answer is like "Property Law"
- What is the juridiction? And set the answer into $jurisdiction and the answer is like "Hong Kong"
- What is the output-language" And set the answer into $language? The default is "English"


### Step 2: Start Background Analysis

Run the analysis script in background mode. Generate a unique session file path:

```bash
SESSION_FILE="/tmp/alta-lex-$(date +%s)-$RANDOM.json"

python3 {baseDir}/scripts/alta_lex_poll.py run \
  --username "$ALTA_LEX_USERNAME" \
  --password "$ALTA_LEX_PASSWORD" \
  --query "The legal question here" \
  --session-file "$SESSION_FILE" \
  --practice-area "$practice_area" \
  --jurisdiction "$jurisdiction" \
  --output-language "$language" &
```

Run this command with `background:true` so it executes in the background.

**Important**: Immediately after starting, send the user a message:
> "I'm consulting Alta Lex AI for a professional legal analysis of your question. This typically takes 5 minutes. I'll keep you updated on the progress."

### Step 3: Poll for Results (5-minute intervals)

Poll the session file every 5 minutes to check progress:

```bash
python3 {baseDir}/scripts/alta_lex_poll.py poll --session-file "$SESSION_FILE"
```

The poll command returns JSON with these fields:
- `status`: `"running"` | `"complete"` | `"error"`
- `content`: accumulated analysis text so far
- `error`: error message if status is `"error"`

### Step 4: Send Progress Updates

While `status` is `"running"`:
- Every poll (5 mins), must send the user a brief update:
  > "Still analyzing... Alta Lex is working on your legal research."
- Do NOT send the partial content to the user — wait for completion.

### Step 5: Deliver Final Result

When `status` is `"complete"`:
1. Read the full `content` from the session file
2. Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim.
3. Format the legal analysis for the user (the content is Markdown)
4. For **WhatsApp**: Convert markdown to WhatsApp-friendly format (no tables, use bold/bullets)
5. Send the complete analysis to the user
6. Clean up: `rm "$SESSION_FILE"`

### Step 6: Handle Errors

When `status` is `"error"`:
1. Read the `error` field
2. If authentication failed → check credentials in config
3. If session expired → the script auto-retries once; if still failing, inform the user
4. Send user a polite error message:
  > "I encountered an issue while consulting Alta Lex. Please try again later or rephrase your question."

## Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--practice-area` | `"Property Law"` | Legal practice area |
| `--jurisdiction` | `"Hong Kong"` | Legal jurisdiction |
| `--output-language` | `"English"` | Response language |
| `--background` | `""` | Additional context |
| `--pro` | off | Enable advanced research mode |

Adjust `--practice-area` and `--jurisdiction` based on the user's question context. Common practice areas for property: `"Property Law"`, `"Tenancy Law"`, `"Conveyancing"`, `"Building Management"`.

## WhatsApp Formatting Rules

When delivering results via WhatsApp:
- Replace markdown headers (`## Title`) with **bold** text
- Replace markdown tables with bullet lists
- Keep responses under 4000 characters; if longer, split into multiple messages
- Use `*bold*` for emphasis (WhatsApp format)
- Preserve numbered lists and bullet points as-is

## Example Interaction

**User (WhatsApp):** "I want to know what are my rights as a tenant if my landlord wants to increase the rent significantly in Hong Kong?"

**Agent actions:**
1. Identify: Property/tenancy law question, jurisdiction = Hong Kong
2. Start background analysis with query: "What are the legal rights of a tenant when a landlord wants to significantly increase rent in Hong Kong? What protections does the Landlord and Tenant (Consolidation) Ordinance provide?"
3. Notify user: "Consulting Alta Lex AI for professional analysis..."
4. Poll every 5 minutes
5. On completion: Format and deliver the legal analysis
6. Clean up session file

## Direct CLI Usage (for testing)

```bash
# Run analysis directly (foreground)
python3 {baseDir}/scripts/alta_lex_client.py \
  -u "$ALTA_LEX_USERNAME" -p "$ALTA_LEX_PASSWORD" \
  -q "What are the tenant rights regarding rent increase in Hong Kong?" \
  --practice-area "Property Law" \
  --jurisdiction "Hong Kong"

# Run with polling (background mode)
SESSION_FILE="/tmp/alta-lex-test.json"
python3 {baseDir}/scripts/alta_lex_poll.py run \
  --username "$ALTA_LEX_USERNAME" --password "$ALTA_LEX_PASSWORD" \
  --query "tenant rights for rent increase" \
  --session-file "$SESSION_FILE" &

# Check status
python3 {baseDir}/scripts/alta_lex_poll.py poll --session-file "$SESSION_FILE"
```

## Notes

- Analysis takes 5 minutes; do not kill the process prematurely
- JWT token is valid for ~3 hours; the script handles automatic re-login on expiry
- Each analysis consumes credits on the Alta Lex platform
- The session file is atomically written (tmp + rename) to prevent corruption during polling
- Output must use ONLY the original data returned by Alta Lex. Do NOT modify, rephrase, or alter any content. Present verbatim.