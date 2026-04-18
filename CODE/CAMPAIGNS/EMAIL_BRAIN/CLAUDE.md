# EMAIL_BRAIN — Automated Email Intelligence System

Processes all incoming emails: classifies, routes workers, creates solonet orders, tracks responses, manages CV vault. Runs on raspibig, zero tokens.

## Status: LIVE — 41 bot commands, 19 inboxes, 10 crons

## Crons (10 automation scripts)

| Cron | Script | What |
|------|--------|------|
| */5 min | response_tracker.py | Scan 19 inboxes, classify, route workers, create solonet drafts |
| */10 min | email_processor.py | sklearn (95.7%) + Ollama draft reply → Telegram /approve_ |
| */10 min | gmail_label_actions.py | SOLONET/APPLICANTS/LATER/DNC/IMPORTANT Gmail labels |
| */10 min | trash_to_dnc.py | Deleted emails → master_dnc 3 months (skips INTERESTED + workers) |
| */15 min | bot_watchdog.py | Autoheal 10 checks + solonet follow-ups |
| 03:00 | bounce_cleaner.py | Brevo/Gmail bounces → master_dnc + clean CSVs |
| 03:30 | backup_master_dnc.sh | CSV backup of DNC table |
| 07:00 | morning_digest.py | Daily summary + follow-up reminders + auto-DNC unsubscribes |
| 14:00 | auto_followup.py | Check due follow-ups → Telegram /followup_send_ or /skip_ |

## DNC Architecture — ONE master

```
master_dnc (PostgreSQL, 7,859 emails, indexed)
  ← bounce_cleaner (daily)
  ← trash_to_dnc (deleted emails, 3 months, skips INTERESTED + workers)
  ← gmail_label_actions (DNC/UNSUBSCRIBE labels, permanent)
  ← morning_digest (auto-DNC unsubscribes)
  ← email_executor (manual via /approve_)
  → send_db.py checks on EVERY send (primary: PostgreSQL, fallback: CSV backup)
  → backup daily 03:30 to /opt/ACTIVE/INFRA/BACKUPS/master_dnc.csv
```

## Gmail Labels = Commands

| Label | Action |
|-------|--------|
| SOLONET | Auto-creates enriched solonet order draft (company/city/phone from DB) |
| APPLICANTS | Auto-adds to applicant DB + cv_vault |
| LATER | Follow-up reminder in 7 days |
| DNC | Permanent block everywhere |
| IMPORTANT | Telegram alert |
| (delete) | DNC 3 months (skips INTERESTED leads + workers) |

## Telegram Alerts (silenced noise — only these)

| Alert | When |
|-------|------|
| 🟢 NEW EMPLOYER LEAD | INTERESTED response detected |
| 🏢 SOLONET DRAFT | Order created (Gmail label or .ro employer) |
| 📋 MORNING DIGEST | Daily 07:00 summary |
| 📅 FOLLOW-UP DUE | Due items at 14:00 |
| 🔴 SERVICE FAILURE | Autoheal failed |
| ⭐ IMPORTANT | Gmail label |

Silenced: workers, bounces, DNC, NOT_INTERESTED, applicants.

## ML Model

- **sklearn**: 95.7% intent accuracy, 0.6ms/email, 10,349 training pairs
- **Classes**: application, auto_reply, bounce, business_reply, campaign_reply, inquiry, newsletter, official, other, spam, transactional
- **Location**: `/opt/ACTIVE/EMAIL/ORDERS/models/email_classifier.pkl` (3.8MB)
- **Training**: `/opt/ACTIVE/EMAIL/PROCESSORS/data/training_data/`
- **Retrain**: `cd /opt/ACTIVE/EMAIL/PROCESSORS/classify && python3 train_classifier.py`

## Solonet Pipeline

- DB: `interjob_master.solonet_orders` (5 active drafts)
- Enrichment: auto-lookup company in 208M DB → city, phone, campaign source
- Email: TO solonet.vacancy@gmail.com, BCC manpower.dristor
- Tracking: `solonet_conversations` table (via adrian.craciunescu@buildjobs.eu inbox)
- Follow-up: 3 days auto-reminder if no response

## CV Vault

- **Local**: `I:\DOCUMENTS\INTERJOB SOLUTIONS EUROPE\2026\CV_VAULT\` (116 unique, 352 collected)
- **DB**: `interjob_master.cv_vault` (58 indexed for bot matching)
- **Auto-ingest**: worker_router adds new applications
- **Bot**: `/match <skill>`, `/cv_stats`
- **Script**: `cv_vault.py build|match|pack|dedup|stats`

## Inboxes (19 — all working)

| Type | Count | Accounts |
|------|-------|----------|
| Gmail | 4 | manpower.dristor, manpowersearch, elena, lucian |
| Zoho | 3 | seicarescu, transport.work, workers.europe |
| A2 | 12 | buildjobs, careworkers, interjob, factoryjobs, warehouseworkers, mivromania, expatsinromania, horecaworkers2026, electricjobs, meatworkers, agroevolution, cifn + adrian.craciunescu (solonet tracker) |

## Bot Commands (41 on @raspibig_controller_bot)

**System**: `/q` `/health` `/svc` `/restart` `/logs` `/errors` `/disk` `/mem` `/top` `/topmem` `/temp` `/uptime` `/ping` `/net` `/ssl` `/cron` `/ollama` `/nanoclaw` `/backup` `/wake` `/kill`
**Campaigns**: `/campaigns` `/norway` `/bounce` `/bounce_clean` `/send` `/stop_campaign` `/blockers`
**Email**: `/process` `/approve_eXXX` `/skip_eXXX` `/queue` `/responses` `/leads`
**Workers**: `/workers` `/match` `/cv_stats`
**Solonet**: `/solonet` `/send_solonet_X` `/skip_solonet_X` `/solonet_history` `/solonet_placed_X` `/solonet_responded_X`
**Follow-up**: `/followup_send_X` `/followup_skip_X`
**Autoheal**: `/watchdog` `/heal`

## Related

- `D:\MEMORY\JOBFAIRS\` — NORWAY_VIRGIL campaign
- `D:\MEMORY\EMAIL\` — Legacy order collector
- `D:\MEMORY\CV\` — CV scanner (older)
- `D:\MEMORY\AUTOREPLY\` — Account sorting
