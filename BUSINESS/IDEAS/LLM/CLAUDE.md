# LLM Email Response Assistant

## Goal

Local LLM on **raspibig** (24/7) and **laptop** (optional) that:
1. Classifies incoming emails from 30+ accounts (sklearn + LLM fallback)
2. Drafts responses for inquiry/application/campaign_reply emails
3. Pushes drafts to Gmail for human review → approve and send from Gmail

## Architecture

```
email_collector (every 15 min, 34 IMAP accounts)
  → raw_emails.jsonl (75,849 collected)
  → email_classifier (sklearn 97.2% + Qwen3-8B fallback, port 5080)
    → email_labels (PostgreSQL)
      → Auto: spam/bounce/newsletter → archive
      → email_responder.py (Qwen3-8B drafts for inquiry/application/campaign_reply)
        → email_drafts (PostgreSQL, status: pending→in_gmail→sent)
          → gmail_drafter.py (IMAP APPEND to Gmail Drafts)
            → YOU review in Gmail → Send or Delete
```

## Machines

| Machine | LLM | Model | Role |
|---------|-----|-------|------|
| raspibig (192.168.100.21) | LM Studio headless | Qwen3-8B Q4_K_M (5 GB) | Production 24/7 |
| Laptop (192.168.100.25) | LM Studio GUI | DeepSeek-R1 8B / Qwen3-14B | Optional speed boost |

Responder tries laptop first, falls back to raspibig. Laptop never required.

## Files (this directory)

| File | What |
|------|------|
| `email_responder.py` | LLM draft generator (OpenAI API → LM Studio) |
| `gmail_drafter.py` | Push drafts to Gmail via IMAP APPEND |
| `response_templates.py` | Multilingual templates RO/EN/FR + LLM system prompts |
| `import_labels_to_pg.py` | SQLite labels.db → PostgreSQL email_labels |
| `train_classifier.py` | sklearn trainer (local copy, patched for Windows) |
| `config.json` | All settings (LLM endpoints, DB, review rules) |
| `deploy.sh` | One-command deploy to raspibig |
| `email-responder.service` | systemd unit for responder daemon |
| `gmail-drafter.service` | systemd unit for Gmail draft pusher |

## Database (raspibig, interjob_master)

| Table | What |
|-------|------|
| `email_labels` | 10,043 classified emails (imported from labels.db) |
| `email_drafts` | LLM-generated response drafts + status tracking |

## Training Results (2026-03-13)

| Metric | Before (2,545) | After (10,043) |
|--------|---------------|----------------|
| Intent accuracy | 94.5% | **97.2%** |
| Priority accuracy | 98.0% | **98.3%** |
| Folder accuracy | 95.9% | **96.9%** |
| Low confidence | 4.4% | **2.5%** |
| Model size | 2.1 MB | 3.3 MB |

## TODO

- [x] Inspect raspibig + laptop for existing systems
- [x] Research web/GitHub for approaches
- [x] Download Qwen3-8B on raspibig (confirmed in `lms ls`)
- [x] Fix email-collector timeout (600→900s)
- [x] Rule-labeled 70,859 emails (DB: 3,299→10,043)
- [x] Retrained sklearn: 97.2% intent accuracy
- [x] Built email_responder.py (LLM draft generator)
- [x] Built gmail_drafter.py (Gmail draft via IMAP)
- [x] Built response_templates.py (RO/EN/FR)
- [x] Built import_labels_to_pg.py
- [x] Built deploy.sh + systemd services
- [ ] Deploy to raspibig (`bash deploy.sh`)
- [ ] Set Gmail app password for draft pushing
- [ ] Load Qwen3-8B as default on raspibig (`lms load qwen3-8b`)
- [ ] Test end-to-end: email → classify → draft → Gmail
