# Inspection Results — Email LLM Systems (2026-03-13)

## Already Running on raspibig (ACTIVE services)

| Service | Status | What |
|---------|--------|------|
| email-classifier.service | **ACTIVE** | sklearn + LLM fallback, port 5080 |
| llm-email-processor.service | **ACTIVE** | LLM email processing |
| interjob-reply-classifier.service | **ACTIVE** | Reply classification (local LLM) |
| gmail-applicant-sorter.service | **ACTIVE** | Auto-moves applications to folder |
| email-collector.service | **FAILED** | IMAP collector (needs fix) |

## Key Files on raspibig

### Production classifier (`/opt/ACTIVE/EMAIL/`)
- `email_classifier.py` — sklearn TF-IDF + LLM fallback (port 5080)
- `email_collector.py` — IMAP from 34 accounts every 15 min
- `train_classifier.py` — Retraining script
- `models/email_classifier.pkl` — 2.1 MB trained model
- `training_data/raw_emails.jsonl` — 2,545+ labeled emails
- `SMART_EMAIL_PROCESSOR_FIXED.py` — LLM response drafting (litellm)

### Reply classifier (`/opt/ACTIVE/INFRA/SKILLS/`)
- `reply_classifier.py` — Uses LM Studio (laptop or local), 6 categories
- `email_organizer.py`, `email_spam_checker.py`, `email_reply_summarizer.py`
- `email_content_scorer.py`, `email_sorter.py`, `email_validator.py`

### LLM layer (`/opt/ACTIVE/LLM/AI/`)
- `email_fetcher.py` — IMAP fetch for Gmail accounts
- `train_local_llm.py` — Local model training
- `smart_router.py` — LLM request routing
- `llm_tools.py` — LLM utilities

## Key Files on Laptop

### Email sorting (`D:\MEMORY\CLAUDE\AUTOREPLY\`)
- `email_sorter.py` (41.5 KB) — 30 accounts, sorts to AUTOREPLY/APPLICATIONS
- `SMART_EMAIL_PROCESSOR_FIXED.py` — LLM response generator
- `ENHANCED_KNOWLEDGE_BASE_MANAGER.py` — Company context for responses

### Email triage (`D:\MEMORY\CLAUDE\EMAIL_ASSISTANT\`)
- `enhanced_email_triage_direct.py` — IMAP + LM Studio triage
- `enhanced_dashboard.py` — Web dashboard
- `picoclaw_api_server.py` — API server

### Email processing (`D:\MEMORY\Z.AI\EMAIL PROCESSING\`)
- Full pipeline: classifier, collector, trainer, labeler
- `CLAUDE.md` — 152-line architecture doc

### IMAP helper (`D:\MEMORY\CLAUDE\OLLAMA\shared\imap_helper.py`)
- Reusable IMAP module for all 28 domains

## Current Classification (sklearn model, 94.5% accuracy)

11 intents: bounce (53.5%), other (35.2%), newsletter (6.5%), auto_reply (2.6%),
application (1.3%), campaign_reply (0.5%), spam, inquiry, unsubscribe

Folders: APPLICATIONS_RECEIVED, AUTOREPLY, INBOX, SPAM

## LM Studio on raspibig (ALREADY INSTALLED)

- Server: ON, port 1234
- Loaded: `lfm2.5-1.2b-instruct` (1.25 GB) — too small for drafting
- Available: EXAONE 1.2B, Granite micro 3B, Qwen2.5-Coder 1.5B, spam-classifier-3b-v1
- Custom fine-tuned: LoRA on Qwen2.5-0.5B-Instruct (adapter 34 MB, 3 checkpoints)
- NLLB-200 translation model (594 MB)
- RAG index at `/opt/ACTIVE/LLM/AI/rag_index/`
- Disk: 31 GB free (87% used)

## Training Data (much more than initially thought)

- 75,849 raw emails (89 MB) — collected from 34 accounts
- 3,299 labeled in labels.db (not 2,545 as training_pairs.jsonl suggests)
- ~72,550 UNLABELED — rule_labeler.py can auto-label obvious ones
- Label distribution: bounce 1539, other 1397, newsletter 230, auto_reply 72, application 35

## What's Missing (gap = this project)

1. **Model too small** — lfm2.5-1.2b loaded, need Qwen3-8B (downloading)
2. **Response drafting not in production** — SMART_EMAIL_PROCESSOR exists but not integrated
3. **No human review UI** — drafts generated but no approve/reject flow
4. **email-collector.service timeout** — fixed (600→900s), expatsinromania@gmail.com bad creds
5. **72K unlabeled emails** — run rule_labeler + retrain for better accuracy
6. **No multilingual response templates** — classification works, responses don't

## RAM on raspibig

Total: 15 GB, Used: 7.4 GB, Available: 8.5 GB
(Enough for Qwen3-8B Q4_K_M at ~5 GB via LM Studio headless)
