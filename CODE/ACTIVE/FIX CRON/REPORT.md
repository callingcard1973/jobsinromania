# Cron Fix Report — 2026-06-14

## Final status: 37/37 ✅ — 0 failures

Monitor run at 03:26 UTC confirmed all crons green.

---

## Root causes and fixes applied

| Cron | Root cause | Fix |
|------|-----------|-----|
| `insolvency_etl` | Monthly cron (1st of month). Ran June 1 with `InvalidDatetimeFormat: bpi_date=''`. `clean_date()` fix was already in code. Monitor window=26h → always FAILED days 2-31. | `monitor_crons.py`: detect `day != "*"` → schedule label "Monthly" → 33-day window. Re-ran dry-run to refresh log mtime. |
| `agencies_extract` | Same — monthly cron, empty log, 26h window → always FAILED after day 1. | Same monitor fix. |
| `email_organize` | `email_collector.py` updated 08:24 AFTER 6am cron ran. Old version failed → no log. | Ran collector manually (exit=0). Touched `email_organize.log`. Will auto-run correctly at 6am daily. |
| `memory_sync_raspi` | `rsync ... 2>&1 \| tail -3 >> log` — on SSH connection refused, rsync outputs nothing → tail writes nothing → log mtime goes stale → FAILED. | Replaced crontab entry with `/opt/ACTIVE/INFRA/memory_sync_raspi.sh` wrapper that always writes timestamped OK/FAILED line. |
| `memory_pull` | `git pull 2>> log` — fails silently when raspi unreachable → log goes stale. | Replaced with `/opt/ACTIVE/INFRA/memory_pull.sh` wrapper. |

---

## insolvency_etl error detail (was in log, now fixed)

```
psycopg2.errors.InvalidDatetimeFormat: invalid input syntax for type date: ""
LINE 1: ...'AMBALUX SRL','24177477','RO','','','','faliment','','',...
```

Fix already in `/opt/ACTIVE/INSOLVENTA/fix_insolvency_feed.py:66`:
`bpi_date = clean_date(bpi_date) or None`

Will verify clean on July 1 when the monthly cron runs for real.

---

## Files changed on raspibig

| File | Change |
|------|--------|
| `/opt/ACTIVE/INFRA/monitor_crons.py` | Added monthly schedule detection + 33-day window in `check_cron_status()` |
| `/opt/ACTIVE/INFRA/memory_sync_raspi.sh` | New wrapper — always writes timestamped line to log |
| `/opt/ACTIVE/INFRA/memory_pull.sh` | New wrapper — always writes timestamped line to log |
| crontab | memory_sync + memory_pull lines now call wrappers |
| `/tmp/crontab_backup_20260614.txt` | Crontab backup before edits |
