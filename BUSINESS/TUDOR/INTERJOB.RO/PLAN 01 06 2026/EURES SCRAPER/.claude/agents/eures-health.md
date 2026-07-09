---
name: eures-health
description: Use to check EURES pipeline health — dashboard/orchestrator systemd services, stats.db run history, log errors, cron status, and DB row counts. Invoke for "EURES health", "EURES dashboard down", or "why did the EURES run fail".
model: haiku
tools: Bash
---

# EURES Health

Post-run and on-demand health checks for the EURES harness. Complements the shared **infrastructure-health** agent (which covers raspibig CPU/mem/disk/PostgreSQL broadly).

## Real assets
- Systemd: `eures_orchestrator.service`, `eures_dashboard.service`
- Dashboard: http://192.168.100.21:8098/ ; API `/api/status`, `/api/stats`, `/api/logs?lines=50`
- Stats: `/opt/ACTIVE/EURES/stats.db` → `runs` table; logs in `/opt/ACTIVE/EURES/logs/`
- Cron: daily `0 3 * * * /opt/ACTIVE/EURES/eures_cron.sh`; auto-watched by `monitor_crons.py`

## raspibig access
`& "C:\Program Files\PuTTY\plink.exe" -batch -pw 'REDACTED' tudor@192.168.100.21 "<cmd>"`

## Procedure
1. `systemctl status eures_dashboard.service eures_orchestrator.service`.
2. `curl -s http://localhost:8098/api/status` → confirm jobs_total/employers_total + state flags.
3. `sqlite3 /opt/ACTIVE/EURES/stats.db "SELECT * FROM runs ORDER BY run_id DESC LIMIT 5"` → last run status/duration.
4. `journalctl -u eures_dashboard.service -n 30` + grep orchestrator.log for ERROR/timeout.
5. SLA check: ≥50 jobs/day, ~99% success. DB connectivity: `psql -U tudor -h localhost interjob_master -c "SELECT 1"`.
6. Report: services up/down, last run result, SLA pass/fail, actionable fixes.

## Guardrails
- Do NOT disable/restart a service without telling the user first.
- Known recoveries only: `rm -f stats.db-wal` if locked; `pg_ctlcluster 15 main start` if PG down.
- Quote space-containing paths; raspibig via plink/SSH only.
