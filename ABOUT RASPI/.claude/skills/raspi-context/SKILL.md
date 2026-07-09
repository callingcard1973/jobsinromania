---
name: raspi-context
description: 'Load raspi (192.168.100.20) operating context before any work on the scraper node — the FULL ANOFM pipeline runs here (scraper → ingest anofm_db.ij_jobs → campaign cron 0 9 * * 1-5 @150/day → daily-report timer 04:00), plus EU wholesale scrapers, skills sync target, and system /usr/bin/python3 (no venv). Use when SSHing to raspi, running/debugging the ANOFM scraper/ingest/campaign/report, the EU market scrapers, or whenever a task names raspi or 192.168.100.20. NOT raspibig — ANOFM lives here.'
---

# raspi-context

Serves `ABOUT RASPI/CLAUDE.md`. Read it before acting on the scraper node.

## Apply
1. **SSH:** IP `192.168.100.20` (not raspibig). Key-based or password from memory `raspibig-ssh-password` (same pw) — never inline in a synced file.
2. **ANOFM lives HERE (not raspibig):** scraper → `/opt/ACTIVE/ANOFM_DATA/csv/`; ingest → `anofm_db.ij_jobs`; campaign `campaign_anofm_angajatori.py` cron `0 9 * * 1-5` (150/day); daily report `anofm-daily-report.timer` 04:00 (reads `anofm_db`); `push_csv_to_raspibig.sh` feeds raspibig's `ij_jobs`. See memory `anofm-host-map`.
3. **Python:** system `/usr/bin/python3`, **no venv**. PostgreSQL listens **localhost only** (run DB checks over SSH on the host).
4. **Also:** EU wholesale market scrapers (cron, `/opt/ACTIVE/INFRA/SKILLS`). Skills sync target `/opt/ACTIVE/INFRA/SKILLS` (symlinks).
5. **Git:** never auto-commit/push.

## When to invoke
Any task naming raspi / 192.168.100.20, ANOFM pipeline, or EU wholesale scrapers.
