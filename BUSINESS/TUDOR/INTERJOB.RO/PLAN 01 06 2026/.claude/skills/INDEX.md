# INTERJOB.RO Harness — Skills Index

**Deployed:** 2026-06-23  
**Version:** 1.0 (Master Harness)  
**Scope:** 4 orchestration skills + 6 reused campaign skills + 4 reused roundup skills

---

## New Skills (This Harness)

| Skill | Purpose | Trigger |
|-------|---------|---------|
| pipeline-orchestrator | Orchestrate daily data pipeline (jobs, enrichment, catalogs) | "Run pipeline", "regenerate catalogs", "check data sources" |
| infrastructure-health | Monitor raspibig, PostgreSQL, crons, system health | "Check health", "system status", "cron jobs", "disk usage" |
| report-generator | Generate daily digest + weekly stakeholder reports | "Daily report", "weekly report", "blockers", "revenue analysis" |
| interjob-master-orchestrator | Central coordinator for all marketplace operations | "Start daily ops", "full workflow", "orchestrate marketplace" |

---

## Reused Skills (Email Campaigns Harness)

Located: `EMAIL CAMPAIGNS/.claude/skills/`

| Skill | Purpose |
|-------|---------|
| campaign-launcher | Launch campaigns within daily rate limits |
| send-optimizer | Analyze delivery patterns, recommend rate changes |
| bounce-monitor | Process bounce emails, suppress hard bounces |
| reply-classifier | Classify email replies, suppress opt-outs |
| dnc-manager | Maintain suppression list, prevent duplicates |
| analytics | Compute KPIs, generate analytics JSON |

---

## Reused Skills (Daily Roundup Harness)

Located: `DAILY/.claude/skills/`

| Skill | Purpose |
|-------|---------|
| data-validator | Validate job/article sources |
| content-creator | Generate social post content |
| publisher | Publish to WordPress/social platforms |
| monitor | Track daily roundup health |

---

## Skill Dependencies

```
interjob-master-orchestrator (main orchestrator)
  ├── pipeline-orchestrator (data pipeline)
  ├── campaign-launcher (campaign execution)
  │   ├── send-optimizer (optimization)
  │   ├── bounce-monitor (monitoring)
  │   │   └── dnc-manager (suppression)
  │   ├── reply-classifier (replies)
  │   │   └── dnc-manager (opt-out suppression)
  │   └── analytics (KPIs)
  ├── infrastructure-health (system monitoring)
  ├── report-generator (aggregation + reporting)
  └── daily-roundup-orchestrator (social posts)
```

---

## Skill Execution Order

**Phase 1 (Daily 00:30 UTC):**
```
pipeline-orchestrator
  → validates ANOFM/EURES APIs
  → enriches PostgreSQL
  → generates catalogs
  → outputs pipeline_state.json
```

**Phase 2 (Daily 06:00 UTC):**
```
campaign-launcher + report-generator (parallel)
  campaign-launcher:
    → reads state.json
    → spawns campaign scripts
    → updates daily counts
  report-generator:
    → reads pipeline_state.json
    → queries analytics
    → generates digest email
```

**Phase 3 (Daily 09:00 UTC):**
```
daily-roundup-orchestrator
  → collects jobs/articles
  → generates posts
  → publishes to platforms
```

**Phase 4 (Every 30 min, continuous):**
```
infrastructure-health
  → system metrics
  → alerts on thresholds
  → logs status

send-optimizer
  → analyzes delivery
  → recommends changes

bounce-monitor → dnc-manager
  → suppress hard bounces

reply-classifier → dnc-manager
  → suppress opt-outs
```

**Phase 5 (Monday 07:00 UTC):**
```
report-generator (deep analysis)
  → aggregates 7-30 day data
  → computes trends
  → generates PDF report
  → sends to stakeholders
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json` | Campaign definitions, enabled status, daily caps |
| `/opt/ACTIVE/EMAIL/CAMPAIGNS/state.json` | Daily send counts, timestamps (atomically updated) |
| `pipeline_state.json` | Data source status, row counts, last_run times |
| `health_status.json` | System metrics (CPU, memory, disk, connections) |
| `latest_blockers.json` | Identified issues requiring action |

---

## Alert Channels

- **Email:** fruitnature4@gmail.com
- **Telegram:** @expatsinromania_news (-1003830000766)
- **Dashboard:** Port 8096 (unified stats)

---

## Control Commands

**View active processes:**
```bash
ps aux | grep -E 'campaign_|pipeline|roundup|health' | grep -v grep
```

**Check campaign state:**
```bash
cat /opt/ACTIVE/EMAIL/CAMPAIGNS/state.json | jq .
```

**Tail logs:**
```bash
tail -f /opt/ACTIVE/INFRA/LOGS/orchestrator_$(date +%Y%m%d).log
```

**SSH to raspibig:**
```bash
ssh tudor@192.168.100.21
```

**Restart orchestrator:**
```bash
systemctl restart campaign-orchestrator
```
