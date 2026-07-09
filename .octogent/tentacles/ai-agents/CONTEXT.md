# ai-agents

LLM-powered automation tools: CV processing, bounce analysis, campaign intelligence.

## Scope

- `CODE/INFRA/AUTOMATE/skills/` — LLM skill scripts (bounce_analyzer_llm.py, cv_*.py, campaign_llm_manager.py, campaign_monitor_llm.py, llm_cli.py, enrich_seap_winners.py)
- `CODE/INFRA/AUTOMATE/` — email_proposer.py and other LLM-driven automation
- Laptop AI workstation: LM Studio at `localhost:1234`, Jan-v3.5-4B (fast) + Qwen3-8B (batch)
- CV generator FastAPI :5050 on raspibig

## Key Decisions

- **LM Studio as OpenAI-compatible endpoint** — all LLM calls use `openai` library pointed at `http://localhost:1234/v1`. No Ollama. No cloud LLMs in automation (cost control).
- **Qwen3-8B params for batch work**: `temp=0.6`, `top_k=20`, `repeat_penalty=1.1` — tuned for factual output, not creativity.
- **Skills are standalone scripts** — each file in `AUTOMATE/skills/` is independently runnable. No shared framework. No imports between skill files.
- **CV pipeline lives on raspibig** — `cv_processor.py`, `cv_scanner.py` run at `/opt/ACTIVE/CV/`. Laptop LM Studio handles inference when raspibig calls back via API.
- **SEAP enrichment uses LLM** — `enrich_seap_winners.py` calls localhost:1234 to classify procurement winners into sectors. Batch mode, not streaming.

## Conventions

- LLM client init pattern used across all skill files:
  ```python
  from openai import OpenAI
  client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
  ```
- Skills max 250 lines. Split on responsibility if larger.
- Batch LLM tasks run on raspibig (192.168.100.21), streaming/interactive tasks run locally.
- Max 2 concurrent scrapers/LLM workers on raspibig.
- SCP to deploy: `scp "D:/MEMORY/CODE/path.py" tudor@192.168.100.21:/opt/ACTIVE/path.py`

## Active LLM Services

| Service | Where | Port | Model |
|---------|-------|------|-------|
| LM Studio | laptop | 1234 | Jan-v3.5-4B / Qwen3-8B |
| CV generator FastAPI | raspibig | 5050 | qwen2.5:1.5b streaming |
| ANOFM phone catalog | laptop | — | local LLM |

## Adding New LLM Skills

1. Create file in `CODE/INFRA/AUTOMATE/skills/`
2. Keep under 250 lines
3. Use `localhost:1234` OpenAI-compat client
4. Test locally before SCP to raspibig
5. Add cron or systemd on raspibig if recurring
