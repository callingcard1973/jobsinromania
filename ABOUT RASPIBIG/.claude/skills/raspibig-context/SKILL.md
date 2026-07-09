---
name: raspibig-context
description: 'Load raspibig (192.168.100.21) operating context before any work on the production hub — services + ports (PostgreSQL :5432 interjob_master, email orchestrator :8096, llama :8082, MARM :8011), /opt/ACTIVE layout, cron/systemd + monitor_crons, nightly backup window (00:00–03:15 UTC, high load), skills-sync target, and the hard "what NOT to do" rules. Use when SSHing to raspibig, deploying/restarting a service there, touching its crons/DB/campaigns, or debugging its load — and whenever a task names raspibig or 192.168.100.21.'
---

# raspibig-context

Serves `ABOUT RASPIBIG/CLAUDE.md`. Read it before acting on the production hub.

## Apply
1. **SSH:** always IP `192.168.100.21` (not hostname); ControlMaster pooling. Password lives in memory `raspibig-ssh-password` / use key-based — never inline a password in a synced file.
2. **Key services:** PostgreSQL 15.17 :5432 (`interjob_master` ~40.8M rows), email orchestrator + dashboard :8096 (11 campaigns), llama-coder :8082, MARM :8011. Restart/disable a service → **tell the user first** (hard rule).
3. **Backup window:** pg_dumpall 00:00–03:15 UTC drives load ~13 — don't schedule heavy work there; campaigns run 06:00 UTC (no overlap).
4. **psql:** use `-h localhost`; NEVER wrap psql in a shell `timeout` (orphans the server query → lock deadlock) — use server-side `statement_timeout`.
5. **Skills sync:** target `/opt/ACTIVE/SKILLS` (640). **Git:** never auto-commit/push.

## When to invoke
Any task naming raspibig / 192.168.100.21, or touching its services, crons, DB, campaigns, or load.
