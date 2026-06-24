---
name: raspibig-deep-inspect
description: Use when asked to "inspect raspibig", "audit raspibig", "deep-inspect infrastructure", "check restart loops / swap storms", "reconcile docs vs live state", or run the periodic RASPIBIG INSPECT audit of 192.168.100.21 (systemd, crons, email campaigns, /opt, /home/tudor). Produces a dated FINDINGS.md with ranked proposals.
---

# raspibig-deep-inspect

Triggers the RASPIBIG INSPECT harness — a four-part deep audit of raspibig (192.168.100.21).

## When to use
- "Inspect / audit raspibig", "deep inspection", "why is swap full / load high".
- "Check restart-looping services", "are crons passing", "are campaigns actually sending".
- "Reconcile docs against live state" / verify a "deployed" or "resolved" claim.

## Steps
1. Invoke `raspibig-inspect-orchestrator`. It confirms reachability
   (`plink -batch -pw 'bucare' tudor@192.168.100.21 "uptime; free -h; df -h /"`).
2. Orchestrator runs the specialists:
   - `raspibig-systemd-auditor` — restart loops (use `--state=activating,failed`), failed units, swap/load.
   - `raspibig-cron-auditor` — crontab + timers + monitor_crons status + data freshness (ij_jobs, fw_candidates).
   - `raspibig-campaign-inspector` — supervisor PID, campaigns.json vs dashboard 8096, send counts, dry_run gaps.
   - `raspibig-doc-reconciler` — live vs `D:\MEMORY` docs; flag false "deployed/resolved" claims + junk Windows-path dirs.
3. Merge findings; rank proposals by impact x effort.
4. Write `RASPIBIG INSPECT\FINDINGS.md` dated today; present numbered proposals.

## Trigger cadence
On demand, plus suggested weekly + after any "I deployed/fixed X on raspibig" claim.

## Guardrails
- Diagnose and report; do NOT execute fixes unprompted (Tudor decides).
- raspibig via plink/SSH only; A2/WordPress via cPanel API. Archive before delete. Never rotate credentials.
