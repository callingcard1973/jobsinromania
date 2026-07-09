# Web Research — Local LLM Email Classification (2026-03-13)

## Top GitHub Projects

| Repo | Description | Relevance |
|------|-------------|-----------|
| [MailSentinel](https://github.com/copyleftdev/mailsentinel) | Ollama Gmail classifier, YAML profiles, Go | Architecture pattern |
| [AI-Email-Classification](https://github.com/waleedmagdy/AI-Email-Classification-Automation-System) | Python IMAP + LLM classify + draft, Ollama | Closest match |
| [LAMBDA](https://github.com/zycyc/LAMBDA) | Learns YOUR email style, fine-tunes local model | Response quality |
| [Clearmail](https://github.com/andywalters47/clearmail) | LM Studio + IMAP, plain-English rules | Simple starting point |
| [Email-Classifier](https://github.com/shxntanu/email-classifier) | Celery + Ollama Qwen 4B, batch processing | Scale pattern |
| [Aomail](https://github.com/aomail-ai/aomail-app) | Full AI email interface, Gmail/Outlook/IMAP | Feature-complete |

## Recommended Models

### raspibig (16 GB RAM, 8.5 GB available, CPU-only)

| Model | Size Q4 | Why |
|-------|---------|-----|
| **Qwen3-8B** Q4_K_M | ~5 GB | 119 languages (RO/FR/EN), best small model |
| Gemma 3 4B Q4_K_M | ~2.5 GB | Fast on CPU, good classification |
| Phi-4-mini 3.8B Q4_K_M | ~2.3 GB | Strong structured JSON output |

### Laptop (32 GB RAM, LM Studio)

| Model | Size Q4 | Why |
|-------|---------|-----|
| **Qwen3-14B** Q4_K_M | ~9 GB | Better response drafting in 3 languages |
| Phi-4 14B Q4_K_M | ~8.5 GB | Outperforms some 27B models |
| DeepSeek-R1 Qwen3-8B | ~5 GB | Already loaded, good reasoning |

## Architecture Pattern (from research)

```
IMAP (30 accounts) → email_fetcher (raspibig, every 60s)
  → PostgreSQL queue (status: new→classified→responded→done)
  → Classifier (LM Studio Qwen3-8B on raspibig, ~200ms/email)
    → Auto-actions: spam→archive, bounce→DNC, newsletter→folder
    → reply_needed → Draft Generator (LM Studio laptop OR raspibig)
      → PostgreSQL drafts table → Human review (Telegram/Flask)
      → Approve → SMTP send
```

## Key Libraries

| Library | Purpose |
|---------|---------|
| `imapclient` | Better IMAP API than stdlib |
| `beautifulsoup4` | Strip HTML from emails |
| `langdetect` | Fast RO/EN/FR detection |
| `openai` (pip) | LM Studio compatible (OpenAI API) |
| `psycopg2` | PostgreSQL |
| `pydantic` | Validate LLM JSON output |

## Classification Prompt Pattern

```
System: Classify email into ONE category.
Categories: spam, inquiry, application, reply_needed, newsletter, bounce
Respond ONLY with JSON: {"category":"...", "confidence":0.0-1.0, "summary":"..."}

User: From: john@company.de / Subject: Workers for warehouse / Body: ...
```

Works reliably with Qwen3-8B and Phi-4 without fine-tuning.
