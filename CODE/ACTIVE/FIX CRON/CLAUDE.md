# CLAUDE.md — FIX CRON

**Purpose:** Fix and maintain the 37 crons on raspibig (192.168.100.21). Monitor at `/opt/ACTIVE/INFRA/monitor_crons.py`.

## How to run monitor

```bash
plink -batch -pw REDACTED tudor@192.168.100.21 "python3 /opt/ACTIVE/INFRA/monitor_crons.py --report 2>/dev/null"
```

## Known failure classes

### 1. Monthly crons always show FAILED (days 2-31)
- Crons with `day=1` in crontab (e.g., `0 3 1 * *`) run once a month.
- Old monitor window = 26h → always FAILED after day 1.
- **Fix applied 2026-06-14:** `monitor_crons.py` now detects "Monthly" schedule → 33-day window.
- Affected: `agencies_extract`, `insolvency_etl`

### 2. rsync/git cron log never updates when SSH target is down
- Old pattern: `rsync ... 2>&1 | tail -3 >> log` — if connection refused immediately, rsync outputs nothing → tail writes nothing → log mtime goes stale → monitor flags FAILED.
- **Fix applied 2026-06-14:** wrapper scripts always write a timestamped OK/FAILED line.
- Wrappers: `/opt/ACTIVE/INFRA/memory_sync_raspi.sh`, `/opt/ACTIVE/INFRA/memory_pull.sh`
- Crontab entries now call the wrappers.

### 3. Cron chain fails silently before last log file
- Pattern: `cmd1 >> log1 && cmd2 >> log2 && cmd3 >> log3`
- If cmd1 fails, log3 never gets created → monitor sees missing log → FAILED.
- Monitor checks the LAST script's log in a chain.
- **Fix:** run cmd1 manually to bootstrap the log, then chain runs normally next day.

## Recurring maintenance

- **Monthly crons** (agencies_extract, insolvency_etl): expect FAILED alert on 2nd of month if the 1st-of-month run fails. Check log content, not just monitor status.
- **raspi offline**: memory_sync_raspi + memory_pull will write FAILED lines (not silent). Easy to spot.
- **New cron**: ensure it writes to `/opt/ACTIVE/INFRA/LOGS/{cron_name}.log`. The monitor auto-detects by extracting `script_name.log` from the cron command.

## Files

| File | Purpose |
|------|---------|
| `/opt/ACTIVE/INFRA/monitor_crons.py` | Main monitor — run every 30 min, alerts via Telegram + email |
| `/opt/ACTIVE/INFRA/memory_sync_raspi.sh` | rsync wrapper with guaranteed log write |
| `/opt/ACTIVE/INFRA/memory_pull.sh` | git pull wrapper with guaranteed log write |
| `/opt/ACTIVE/INFRA/LOGS/cron_status.json` | Latest monitor snapshot |
| `/opt/ACTIVE/INFRA/LOGS/cron_history.log` | All monitor runs |
| `/tmp/crontab_backup_20260614.txt` | Crontab backup before today's edits |
