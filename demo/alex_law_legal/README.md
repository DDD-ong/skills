# Alex Law Legal ⚖️

An OpenClaw skill for professional property and housing legal analysis via the Alta Lex AI platform.

This skill provides expert legal research on property law, real estate transactions, tenancy disputes, building management, conveyancing, and stamp duty regulations.

---

## Installation

```bash
npm install -g github:DDD-ong/alex-law-legal
```

The skill is automatically deployed to `~/.openclaw/skills/alex_law_legal/` via the postinstall hook.

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

Once configured, the skill is automatically invoked when you ask property or housing law questions:

**Example questions:**

- "What are my rights as a tenant if my landlord wants to increase the rent significantly in Hong Kong?"
- "Explain the stamp duty requirements for property purchase in Hong Kong"
- "What are the legal obligations of a building management company?"
- "How does the Landlord and Tenant (Consolidation) Ordinance protect tenants?"
- "What are the key steps in the property conveyancing process?"

Analysis typically takes around 5 minutes. The skill will poll for results and notify you when complete.

---

## Parameters

The following parameters can be configured per query:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `practice_area` | `"Property Law"` | Legal practice area (e.g., Property Law, Tenancy Law, Conveyancing, Building Management) |
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
