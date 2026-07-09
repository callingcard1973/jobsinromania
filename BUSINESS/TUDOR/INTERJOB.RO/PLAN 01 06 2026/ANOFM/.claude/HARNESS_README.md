# ANOFM Harness — Quick Start

**Built:** 2026-06-21  
**Target:** raspi (192.168.100.20)  
**Mode:** Agent team orchestration  

---

## Directory Structure

```
.claude/
├── agents/
│   ├── scheduler.md                      # Manage systemd timers
│   ├── scraper-monitor.md                # Validate CSV output
│   ├── ingest-monitor.md                 # Load CSV → DB
│   ├── campaign-monitor.md               # Send emails, track bounces
│   └── health-checker.md                 # System health metrics
├── skills/
│   ├── anofm-scraper-launch/SKILL.md     # SSH to raspi, run scraper
│   ├── anofm-ingest-run/SKILL.md         # CSV→DB ingestion
│   ├── anofm-campaign-send/SKILL.md      # Brevo SMTP, rate limiting
│   ├── anofm-pipeline-health/SKILL.md    # System metrics, alerts
│   └── anofm-orchestrator/SKILL.md       # Central coordinator
└── HARNESS_README.md                      # This file
```

---

## How to Use

### Option 1: Full Pipeline (Recommended First Run)

Ask Claude:
```
"Activate ANOFM on raspi. Run complete cycle: scrape → ingest → send → monitor."
```

The orchestrator will:
1. **Scheduler** — Enable 3 systemd timers (scraper, ingest, audience-rebuild)
2. **Scraper** — Run scraper, produce CSV
3. **Scraper Monitor** — Validate CSV (schema, row counts)
4. **Ingest Monitor** — Load CSV into anofm_db
5. **Campaign Monitor** — Send emails (up to 150/day)
6. **Health Checker** — Verify all systems healthy
7. **Report** — Show complete summary

**Expected duration:** 60–90 minutes

---

### Option 2: Health Check (Daily Monitor)

Ask Claude:
```
"Check ANOFM health on raspi. Show me status of all systems."
```

The **Health Checker** agent will:
- Check if all timers are enabled
- Verify database row count (should be ~16,429)
- Check disk usage
- Review recent logs for errors
- Calculate bounce rate trend
- Generate health score (0–100)

**Expected duration:** <5 minutes

---

### Option 3: Dry-Run Test (Safe Testing)

Ask Claude:
```
"Run ANOFM in dry-run mode. Show me what would be sent without actually sending."
```

All agents run with `--dry-run` flags:
- Scraper: No CSV written
- Ingest: No DB changes
- Campaign: Show candidates, no emails sent

**Expected duration:** 30 minutes

---

### Option 4: Manual Single-Phase

**Run scraper only:**
```
"Launch ANOFM scraper on raspi. Validate the CSV output."
```
→ Scheduler + Scraper Monitor agents

**Ingest only:**
```
"Ingest the latest ANOFM CSV into the database."
```
→ Ingest Monitor agent

**Send emails:**
```
"Send today's ANOFM campaign emails (up to 150)."
```
→ Campaign Monitor agent

---

## Key Concepts

### Idempotency
All tasks are **safe to re-run**:
- Scraper: deduped by job_id
- Ingest: deduped by content_hash
- Campaign: tracked in sent.csv (skips already-sent)

Resume after failure with zero duplication risk.

### Rate Limiting
- **Campaign:** 150 emails/day (Brevo quota)
- **Email delay:** 8 seconds (prevents bot flagging)
- **Bounce collection:** 1× per 24 hours

### Shared Workspace
All intermediate files stored in `_workspace/`:
```
_workspace/
├── timer_status.json
├── scraper_validation_report.json
├── ingest_report.json
├── campaign_report.json
├── pipeline_health_report.json
└── health_history.json  (30-day rolling history)
```

These files enable error recovery, trending, and auditing.

---

## Typical Daily Flow

1. **08:25 Mon-Fri** — Scraper timer triggers automatically
   - Runs scraper (8–10 min)
   - Produces CSV

2. **09:00 Mon-Fri** — Ingest timer triggers automatically
   - Loads CSV → anofm_db
   - Deduplicates by content_hash

3. **09:10 Mon-Fri** — Audience rebuild timer
   - Regenerates campaign candidate list
   - Filters by business email, excludes DNC

4. **Manual send** (when needed, within 150/day cap):
   - Ask: "Send ANOFM emails today."
   - Campaign Monitor runs, sends up to 150
   - Tracks bounces + DNC updates

5. **Evening health check** (optional):
   - Ask: "Check ANOFM health."
   - Health Checker generates daily report

---

## Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Health score | 50–75 | < 50 |
| Bounce rate | > 15% | > 25% |
| Disk usage | > 80% | > 95% |
| DB row count | < 15,000 | < 14,000 |
| Timer failures | Any | Multiple |

---

## Troubleshooting

### "Scraper failed to run"
Check:
- `systemctl status anofm-scraper.timer` (enabled?)
- `sudo journalctl -u anofm-scraper.service -n 20` (logs)
- ANOFM API status (may be rate-limited or down)

### "Ingest row count mismatch"
Check:
- CSV schema matches DB columns (common: schema drift between raspibig ↔ raspi)
- DNC list size (did many rows get skipped?)
- Ingest logs: `/opt/ACTIVE/INFRA/LOGS/ingest_anofm.log`

### "Campaign send rate is low"
Check:
- Daily cap exceeded? `wc -l /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv`
- DNC list size growing (more bounces)? `wc -l /opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt`
- Brevo API 429 (rate-limited)? Check logs for backoff events.

### "Bounce rate spike"
Check:
- Did we send to a bad list segment?
- Email domain reputation? (Brevo dashboard)
- Audience quality (consider list refresh)

---

## Agents Overview

### Scheduler
- **Role:** Oversee systemd timers
- **Tasks:** Enable, disable, check status, monitor schedule
- **Output:** timer_status.json

### Scraper Monitor
- **Role:** Validate CSV data quality
- **Tasks:** Check schema, row count, dedups, data types
- **Output:** scraper_validation_report.json

### Ingest Monitor
- **Role:** Load CSV into database
- **Tasks:** Column mapping, dedup by content_hash, atomicity, error recovery
- **Output:** ingest_report.json

### Campaign Monitor
- **Role:** Send emails, manage bounces
- **Tasks:** Load DNC/sent lists, query DB, send with Brevo, collect bounces, update DNC
- **Output:** campaign_report.json + updated sent.csv + updated dnc_bounces.txt

### Health Checker
- **Role:** Monitor overall pipeline health
- **Tasks:** Collect metrics (timers, DB, disk, logs, campaign), trend analysis, alert generation
- **Output:** pipeline_health_report.json + health_history.json

---

## Orchestrator

**Central coordinator** that activates agent team and manages flow:
1. Create workspace (`_workspace/`)
2. Activate Scheduler → Scraper Monitor → Ingest Monitor → Campaign Monitor → Health Checker
3. Assign tasks in sequence (wait for each phase to complete)
4. Handle errors (pause, report, wait for user decision)
5. Synthesize final report

**Command:** Use skill `anofm-orchestrator` to trigger.

---

## Files Reference

| File | Purpose | Access |
|------|---------|--------|
| agents/*.md | Agent role + workflow | Read (reference) |
| skills/*/SKILL.md | Skill logic + examples | Read (reference) |
| HARNESS_README.md | This quick start | Read |
| CLAUDE.md | Project context + harness pointers | Updated 2026-06-21 |
| /opt/ACTIVE/INTERJOB/ (raspi) | Production scripts | SSH access |
| /opt/ACTIVE/ANOFM_DATA/ (raspi) | CSV storage | SSH access |
| anofm_db (raspi:5432) | Production database | psql access |

---

## Next Steps (Activation)

1. **First activation** (execute once):
   ```
   "Activate ANOFM on raspi. Run full pipeline test."
   ```
   → Orchestrator enables timers + runs complete cycle

2. **Verify success:**
   - Check health report (health_score ≥ 75)
   - Verify `sent.csv` has entries (emails sent)
   - Check `/opt/ACTIVE/ANOFM_DATA/csv/` for latest CSV

3. **Daily operation** (automated):
   - Timers run on schedule (Mon-Fri 08:25, 12:25, 15:59)
   - Manual send when needed: "Send ANOFM emails today."
   - Health check every evening: "Check ANOFM health."

4. **Monthly audit:**
   - Review bounce trends
   - Archive old CSVs (if disk > 85%)
   - Check DB integrity

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-21 | 1.0 | Harness deployed (5 agents + 4 skills + orchestrator) |

---

**Questions?** Ask Claude: "Explain [component] of ANOFM harness."
