---
name: email-classifier-orchestrator
description: Use when operating or debugging the Email Classifier inbox hygiene on raspibig — triggers include "run the email classifier", "move candidates/applications out of the manpowerdristor inbox", "why are applications in the inbox", "classify emails", "check classifier model health", or "run the daily bounce digest". Auto-applies when working in the EMAIL CLASSIFIER folder.
---

# Email Classifier Orchestrator (trigger skill)

Coordinates the Email Classifier harness: IMAP collection → regex+pkl classification → IMAP folder moves → model-health → bounce digest. Goal: keep candidate/application/newsletter/bounce mail out of `manpowerdristor@gmail.com`.

## When to use
- Scheduled or manual run of the classifier (daily 06:00, hourly).
- Applications/candidate mail appearing in the inbox.
- Health check of the pkl model (94.5% acc) or confidence drift.
- Daily bounce digest / DNC processing.

## Agents
- `email-classifier-orchestrator` — supervises the cycle.
- `email-classifier-imap-collector` — multi-account IMAP pull → raw_emails.jsonl.
- `email-classifier-labeler` — rule_labeler.py + inline pkl fallback + IMAP moves.
- `email-classifier-model-health` — pkl load, outcome (inbox=0), drift, bounce digest.
- Reuse: `bounce-monitor`, `dnc-manager` for bounce/DNC flows (enhanced_bounce_processor.py).

## Steps
1. Read state: `tail` `email_organize.log` / `email_collect.log` on raspibig (plink SSH).
2. Daily 06:00: collector (`--days 2`) → labeler (rule_labeler + organize) → model-health verify.
3. Hourly: labeler organizes `manpowerdristor@gmail.com` (inline pkl fallback, conf ≥ 0.65).
4. Daily: `daily_bounce_report.py` digest + `enhanced_bounce_processor.py` → DNC.
5. Always `--dry-run` before first live move; report moves per folder + inbox applications count.

## Hard rules
- raspibig only via plink: `& "C:\Program Files\PuTTY\plink.exe" -batch -pw 'REDACTED' tudor@192.168.100.21 "<cmd>"`.
- Never rebuild the model, change the pkl path, or lower 0.65 threshold.
- Never run full 34-account collect hourly; never restart the inactive services.
- Quote all paths with spaces.
