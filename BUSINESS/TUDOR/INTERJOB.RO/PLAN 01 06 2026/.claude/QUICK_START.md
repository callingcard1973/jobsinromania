# INTERJOB.RO Harness — Quick Start

**Harness deployed:** 2026-06-23

---

## What is this?

Fully automated marketplace operation for INTERJOB.RO — runs daily:
1. **00:30 UTC** — Refresh job data (ANOFM, EURES, lands)
2. **06:00 UTC** — Send emails (11 campaigns, 440/day), send daily digest
3. **09:00 UTC** — Generate social posts
4. **Every 30 min** — Monitor infrastructure, optimize delivery
5. **Monday 07:00 UTC** — Weekly report

---

## How to use

### Normal operation
```
"Run daily ops" or "start pipeline"
→ interjob-master-orchestrator skill triggers
→ all phases run automatically
```

### Check status
```
"Check infrastructure health"
→ infrastructure-health checks CPU/disk/crons
→ alerts if any threshold crossed

"Campaign status"
→ Shows sends/bounces/replies per campaign
→ Recommends optimizations
```

### Generate reports
```
"Daily report"
→ Sends digest email immediately

"Weekly report"
→ Deep analysis + PDF + stakeholder email
```

### Debug issues
```
"What's failing?"
→ report-generator lists all blockers
→ Shows severity + recommended action

"Pipeline status"
→ Shows which data sources are available
→ Row counts vs yesterday
```

---

## Key skills (triggers)

| Use case | Trigger |
|----------|---------|
| Run everything | `interjob-master-orchestrator` |
| Data pipeline | `pipeline-orchestrator` |
| Email campaigns | `campaign-launcher` |
| Infrastructure | `infrastructure-health` |
| Reports | `report-generator` |
| Email analytics | `analytics` |

---

## Team members

- **pipeline-orchestrator** — Data pipelines
- **campaign-launcher** — Email sending
- **send-optimizer** — Delivery analysis
- **bounce-monitor** — Bounce suppression
- **reply-classifier** — Response classification
- **dnc-manager** — Suppression list
- **analytics** — KPI computation
- **infrastructure-health** — System monitoring
- **report-generator** — Reporting
- **daily-roundup** — Social posts (reused)

---

## Where to find things

| Item | Location |
|------|----------|
| Agent definitions | `.claude/agents/` |
| Skills definitions | `.claude/skills/` |
| Campaign config | `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json` |
| Campaign logs | `/opt/ACTIVE/EMAIL/CAMPAIGNS/{CAMPAIGN}/logs/` |
| Daily logs | `/opt/ACTIVE/INFRA/LOGS/` |
| Dashboard | Port 8096 (raspibig) |
| Alerts | Email + Telegram |

---

## Common commands

**Check all running processes:**
```bash
ps aux | grep -E 'campaign|pipeline|roundup' | grep -v grep
```

**View campaign state:**
```bash
ssh tudor@192.168.100.21 "cat /opt/ACTIVE/EMAIL/CAMPAIGNS/state.json" | jq .
```

**Check system health:**
```bash
ssh tudor@192.168.100.21 "free -h && df -h /opt"
```

**View latest logs:**
```bash
ssh tudor@192.168.100.21 "tail -50 /opt/ACTIVE/INFRA/LOGS/orchestrator_$(date +%Y%m%d).log"
```

---

## Next steps

1. ✅ Harness deployed
2. ⏳ Run first daily cycle: `interjob-master-orchestrator`
3. ⏳ Monitor for 24h, check alerts
4. ⏳ Review daily digest + dashboard
5. ⏳ Optimize campaign rates based on send-optimizer recommendations
