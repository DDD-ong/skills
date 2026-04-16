# Alta Lex Legal AI — OpenClaw Skill

Full-featured legal AI assistant integrated with OpenClaw, covering 11 functional modules via the Alta Lex platform.

## Modules

| Module | Description |
|--------|-------------|
| Contract Draft | AI-powered contract generation from templates and parameters |
| Contract Review | Intelligent contract risk analysis (Summary/Edit modes) |
| Contract Compare | Multi-version contract diff analysis |
| Legal Research | Legal regulation search and deep analysis (Quick/Search modes) |
| IPO Support | HKEX IPO compliance checklist generation |
| Negotiation Playbook | Data-driven negotiation strategy generation |
| Document Translation | Multi-language legal document translation |
| Due Diligence | Systematic due diligence analysis with checklist |
| Legal Compliance | 3-step regulatory compliance review workflow |
| Desensitization | Sensitive information identification and redaction |
| Tabular Analysis | Structured data extraction from documents |

## Installation

```bash
npx alta-lex-legal
```

## Configuration

Add to `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "alta_lex_legal": {
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

## Requirements

- Python 3.8+
- `pip install requests`
- OpenClaw framework installed

## Usage

Once installed and configured, simply ask your OpenClaw agent legal questions through Discord, WhatsApp, or any connected chat platform. The agent automatically detects the intent and routes to the appropriate module.

## CLI (Direct)

```bash
# Contract draft
python3 scripts/alta_lex.py -u USER -p PASS draft start \
  --industry Technology --position Buyer --scenario "Software Licensing" \
  --contract-type "License Agreement" --governing-law PRC

# Legal research
python3 scripts/alta_lex.py -u USER -p PASS research start \
  -q "What are tenant rights for rent increases in Hong Kong?"

# Quick translate
python3 scripts/alta_lex.py -u USER -p PASS translation quick \
  -q "This Agreement shall be governed by PRC law." \
  --source-lang English --target-lang Chinese

# Check status
python3 scripts/alta_lex.py -u USER -p PASS draft check --session-id "sess_xxx"
```

## License

MIT
