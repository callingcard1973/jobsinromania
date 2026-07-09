---
name: raspi-romania-inspect
description: 'Inspect raspi (192.168.100.20) — the Romania ops hub (ALL Romania + ALL ANOFM sending runs there, never raspibig/laptop). Read-only health audit — crontab duplicate + malformed-schedule validation, ANOFM pipeline freshness (ij_jobs/send_log/dnc/last-sends), failed systemd units, /tmp pressure. Use when asked to "inspect raspi", "check Romania pipeline", "audit raspi crons", "is ANOFM sending healthy", or before changing anything on .20.'
---

# raspi Romania Inspect

**Host:** raspi `192.168.100.20` (Debian). Romania hub — **all Romania work + all ANOFM email sending happens here**, NOT raspibig .21. (Hard rule, [[anofm-host-map]].)

**Runner:** `RASPI INSPECT/inspect_raspi.py` (laptop, via plink). Read-only. Exit 1 if findings.
```
python "RASPI INSPECT/inspect_raspi.py"          # summary + findings
python "RASPI INSPECT/inspect_raspi.py" --raw    # full per-section dump
```

## What it checks
1. **Crontab integrity** — duplicate active lines (double execution) + malformed schedules. raspi crons historically carry `HH:MM * * * *` lines (invalid minute field → never run). Real cron is `min hour dom mon dow`.
2. **ANOFM pipeline** — `anofm_db.ij_jobs` count, `anofm.send_log` + `anofm.dnc`, last `sent=` lines from orchestrator log.
3. **Failed systemd units** — e.g. `chkrootkit.service` (benign false positive when nightly jobs fill /tmp).
4. **/tmp pressure** — `cv_purge` (10 min) + scrapers churn /tmp.

## Known-good baseline (2026-06-28)
- 28 active cron lines, 0 duplicates (deduped 06-26; backup `/tmp/crontab.bak_20260626`).
- ij_jobs ~17.5k, send_log ~2.6k, dnc ~4.4k. Sends Mon-Fri 09:00 (Factory/Warehouse/Care).
- OPEN: 15 EU-wholesale scrapers use malformed `HH:MM` schedules → not running. EU-only, not Romania.
- chkrootkit.service: mail relay fixed (2026-06-28) — alias `root→manpower.dristor@gmail.com` in `/etc/aliases`. Next run at 00:00 should exit cleanly.
- email-catalog-funnel.service DISABLED (2026-06-28) — stale IMAP credentials for `office@interjob.ro`; no basket requests to process.

## Remediation (only on explicit instruction — Tudor decides, never auto-commit)
- Dedup: `crontab -l > /tmp/crontab.bak_DATE` then reinstall deduped lines.
- Fix malformed schedule: `02:30`→`30 2`, `03:00`→`0 3`, etc.
- Never disable a service silently. Never deploy ANOFM sending off raspi.
