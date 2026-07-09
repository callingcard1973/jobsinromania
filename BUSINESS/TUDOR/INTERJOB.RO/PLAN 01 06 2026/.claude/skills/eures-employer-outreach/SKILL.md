---
name: eures-employer-outreach
description: 'Run the EURES employer cold-email outreach (offer RO/EU workers to EU companies that posted EURES vacancies). ANOFM-style multi-sender, gentle ramp 30->150/day, DB-unique suppression. Runs ONLY on raspibig (.21). Use when asked to launch/resume EURES outreach, enable a sector sender, build the EURES audience, check EURES send status, or work in the EURES folder.'
---

# EURES Employer Outreach

**Host:** raspibig `192.168.100.21` ONLY (EURES lives there; ANOFM-only on raspi .20). Files: `/opt/ACTIVE/EURES/`.

Offer InterJob.ro's RO/EU workers to EU employers who posted EURES vacancies. Modeled on the ANOFM multi-sender design.

## Components
- `build_audience.py` — UNION eures_contacts + eures_employers_50plus → ASCII-fold, dedup, strip `master_dnc` + `eures_send_log`, route sector→sender domain → `eures_audience_sendable`. (~4,916 sendable today.)
- `eures_outreach_orchestrator.py` — per ENABLED sender: ramp cap, build queue minus send_log, render `templates/<sector>.txt`, claim via `INSERT ON CONFLICT(email)` (DB-unique, no double-send), send via shared `sender.send_brevo`, delay 3-6 min. `--dry-run` prints only.
- `senders.json` — 6 job-domains, ramp 30→150, `enabled:false` (ALL OFF by default).
- `digest.py` — per-sender sent/cap/bounce/optout/queue.
- `templates/` — 8 sector .txt (ASCII, Subject line1) + 2 follow-ups. opt-out + List-Unsubscribe footer.
- **Launch path (2026-06-28):** runs via the campaign orchestrator, not a separate timer. `EURES_OUTREACH` is registered in `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json` (type=python, script=`/opt/ACTIVE/EURES/eures_outreach_orchestrator.py`, daily_limit 150, brevo_account BPPLTD) and launched by `campaign-orchestrator.service` like the other 24 campaigns. The orchestrator passes `--limit`/`--delay`/`--daily-cap` (accepted, ignored — caps live in `senders.json`); the script self-builds its audience at start (calls `build_audience.py`). `flock /tmp/eures_outreach.lock` guards overlap.
- `systemd/` — eures-audience.timer + eures-outreach.timer are DISABLED (no double-run; orchestrator is the single entrypoint).

## Suppression / safety
- `eures_send_log UNIQUE(email)` = structural no-double-send across all senders.
- Disjoint partition: sector→exactly one sender domain.
- `master_dnc` (7,958) anti-joined at build. Opt-outs/bounces → master_dnc via reused reply-classifier/bounce-monitor.
- ASCII-only, honest claims (no "verified/certified"). Fold {company}/{job_title} NFKD at send.

## To launch (Tudor decides — never auto-enable/send)
1. Pilot = Construction → buildjobs.eu: set that sender `enabled:true`, cap 30 in senders.json.
2. `PGHOST=localhost python3 build_audience.py` then `--dry-run` the orchestrator to preview.
3. The campaign orchestrator picks it up from `campaigns.json` (no timers to install).

## Open items
- Routing: ~4,763/4,916 lack sector → GENERAL (warehouseworkers.eu). Real sector signal is in `eures_jobs` (429k classified) — join by company to spread across senders. Enrichment Phase 4.
- 3 domains (factoryjobs/horeca/meatworkers) IP-allowlisted on Brevo → A2 SMTP fallback until whitelisted.
- Audience ceiling ~5k emails (429k jobs, only ~5k with email) → enrichment unlocks scale.
