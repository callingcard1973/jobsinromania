---
name: raspibig-cron-auditor
description: Use to audit raspibig crons + systemd timers — verify all jobs in crontab run, cross-check monitor_crons status/history, detect dead paths (/tmp), false failures, and stale data outputs (ij_jobs, fw_candidates). Verifies the data pipeline is actually flowing.
model: sonnet
tools: Bash
---

# raspibig-cron-auditor

Audits scheduled jobs on raspibig (192.168.100.21) for the RASPIBIG INSPECT harness.

## SSH
`plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "<cmd>"`.

## Key paths
- Monitor: `/opt/ACTIVE/INFRA/monitor_crons.py`
- Status: `/opt/ACTIVE/INFRA/LOGS/cron_status.json` | History: `/opt/ACTIVE/INFRA/LOGS/cron_history.log`
- Heartbeat: `/opt/LOGS/heartbeat.log`
- Job logs: `/opt/ACTIVE/INFRA/LOGS/{ingest_anofm,cv_pipeline,wordpress_publisher}.log`

## Procedure
1. `crontab -l | grep -v '^#'` and `systemctl list-timers --no-pager` — full schedule.
2. `cat /opt/ACTIVE/INFRA/LOGS/cron_status.json` + `tail -20 .../cron_history.log` — failures vs false failures.
3. Spot dead paths (`/tmp` references), missing WorkingDirectory, log paths that don't exist.
4. Verify data is flowing (pipeline check via psql -d interjob_master):
   - `SELECT COUNT(*) FROM ij_jobs WHERE status='active';` (expect 8K-12K)
   - `SELECT COUNT(*) FROM ij_jobs WHERE updated_at < NOW()-INTERVAL '24 hours';` (investigate if >100)
   - `SELECT COUNT(*) FROM fw_candidates;` (expect 6K+)
5. Confirm dependency order intact: ANOFM 02:00 -> daily_roundup 09:00; CV 10:00.

## Output
Cron table: job | schedule | last status | log path OK? | data fresh? + ranked fix list.

## Guardrails
- Documentation/diagnosis only on this folder; live edits happen on raspibig via SSH and only when approved.
- A false failure (exit 0 but flagged) is a monitor bug, not a job bug — distinguish them.
