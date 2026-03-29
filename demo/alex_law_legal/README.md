# Alex Law Legal ⚖️

An OpenClaw skill for professional legal research and analysis via the Alta Lex AI platform.

This skill provides expert legal research and analysis across all practice areas, powered by the Alta Lex AI platform.

---

## Installation

```bash
npm install -g github:DDD-ong/alex-law-legal
alex-law-legal
```

The first command downloads the package. The second command deploys the skill files to `~/.openclaw/skills/alex_law_legal/`.

---

## Configuration

Add the following to your `~/.openclaw/openclaw.json`:

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

Restart your OpenClaw session after updating the configuration.

---

## Usage

Once configured, the skill is automatically invoked when you ask legal questions:

**Example questions:**

- "What are my rights as a tenant if my landlord wants to increase the rent significantly in Hong Kong?"
- "Explain the stamp duty requirements for property purchase in Hong Kong"
- "What are the key legal considerations for a cross-border M&A transaction?"
- "How does GDPR affect data processing for companies operating in the EU?"
- "What are the employer's obligations when terminating an employee in Hong Kong?"

Analysis typically takes around 5 minutes. The skill will poll for results and notify you when complete.

---

## Parameters

The following parameters can be configured per query:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `practice_area` | `Auto-detect` | Legal practice area — auto-detected from query (e.g., Property Law, Corporate Law, Employment Law, Contract Law) |
| `jurisdiction` | `"Hong Kong"` | Legal jurisdiction for the analysis |
| `output_language` | `"English"` | Language for the response |
| `pro` | off | Enable advanced research mode (uses more credits) |

---

## Requirements

- OpenClaw installed
- Python 3
- Valid Alta Lex AI credentials

---

## License

MIT
