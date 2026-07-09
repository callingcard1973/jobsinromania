# INTERJOB.RO Harness — Agent Definitions Index

**Deployed:** 2026-06-23  
**Version:** 1.0 (Master Harness)  
**Scope:** 9 registered agents (6 reused email + 3 new) + 4 daily-roundup *skills* (not registered as agents)

---

## Reused Agents (Email Campaigns Harness v2.0)

| Agent | File | Role |
|-------|------|------|
| campaign-launcher | EMAIL CAMPAIGNS/.claude/agents/campaign-launcher.md | Execute campaigns within daily caps |
| send-optimizer | EMAIL CAMPAIGNS/.claude/agents/send-optimizer.md | Analyze delivery, recommend rate changes |
| bounce-monitor | EMAIL CAMPAIGNS/.claude/agents/bounce-monitor.md | Suppress hard bounces |
| reply-classifier | EMAIL CAMPAIGNS/.claude/agents/reply-classifier.md | Classify responses, suppress opt-outs |
| dnc-manager | EMAIL CAMPAIGNS/.claude/agents/dnc-manager.md | Maintain suppression list |
| analytics | EMAIL CAMPAIGNS/.claude/agents/analytics.md | Compute KPIs, alert on thresholds |

## Reused Daily Roundup Roles (skills, NOT registered agents)

These live as **skills** under `DAILY/.claude/skills/` and are invoked by the daily-roundup orchestrator — they are not spawnable subagents.

| Skill | Role |
|-------|------|
| data-validator | Validate job/article sources |
| content-creator | Generate social posts |
| publisher | Publish to WordPress/social |
| monitor | Track daily roundup health |

## New Agents (This Harness)

### pipeline-orchestrator.md
- **Role:** Coordinate data pipeline (jobs, enrichment, catalogs)
- **Triggers:** "Run pipeline", "regenerate catalogs", "check data sources"
- **Outputs:** pipeline_state.json, PDF/HTML catalogs, alerts

### infrastructure-health.md
- **Role:** Monitor raspibig + PostgreSQL + crons
- **Triggers:** "Check health", "disk usage", "are crons running?"
- **Outputs:** health_status.json, alerts, daily digest

### report-generator.md
- **Role:** Generate daily + weekly reports
- **Triggers:** "Daily report", "weekly report", "blockers", "revenue analysis"
- **Outputs:** Daily digest email, PDF weekly report, blockers.json

---

## Team Communication Protocol

### Intra-team (direct SendMessage)
- pipeline-orchestrator → report-generator: "Pipeline complete: {source_count} sources, {total_rows} rows"
- infrastructure-health → report-generator: Health JSON for aggregation
- campaign-launcher → send-optimizer: Campaign state for analysis
- bounce-monitor → dnc-manager: Hard bounce list for suppression
- reply-classifier → dnc-manager: Opt-out list for suppression

### Error Escalation
- Any agent failure → escalate to report-generator with details + recommendation
- Critical alert (CPU >85%, disk >95%) → infrastructure-health alerts independently + escalates

### Scheduled Phases
- 00:30 UTC: pipeline-orchestrator Phase
- 06:00 UTC: campaign-launcher + report-generator Phase (parallel)
- 09:00 UTC: daily-roundup Phase
- Every 30 min: infrastructure-health + send-optimizer + bounce-monitor + reply-classifier Phase
- Monday 07:00 UTC: weekly report Phase

---

## Model Assignments

All agents use: `model: "opus-4-8"` (unified for quality consistency)

---

## Agent Dependencies

```
pipeline-orchestrator
  ├── validates ANOFM/EURES APIs
  ├── calls enrichment scripts
  └── generates catalogs

campaign-launcher
  ├── depends on pipeline (job data)
  └── reads state.json (concurrent send tracking)

send-optimizer → bounce-monitor → dnc-manager
  (sequential: optimize → monitor → suppress)

report-generator (depends on all)
  ├── reads pipeline_state.json
  ├── reads health_status.json
  ├── reads campaign state.json
  └── queries PostgreSQL for trends
```
