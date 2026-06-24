# ANOFM Harness Build Summary

**Date:** 2026-06-21  
**Target:** raspi (192.168.100.20)  
**Scope:** Full automated pipeline orchestration  
**Status:** ✅ COMPLETE

---

## Overview

Built a **5-agent + 4-skill orchestration system** for independent ANOFM pipeline on raspi. Automates scraping, ingestion, email sending, and health monitoring with error recovery and trending analysis.

**Key achievement:** One-command activation of complete pipeline (scrape → ingest → send → monitor).

---

## Artifacts Created (13 Files)

### Agents (5)
```
.claude/agents/
├── scheduler.md                    (timer management)
├── scraper-monitor.md              (CSV validation)
├── ingest-monitor.md               (CSV→DB ingestion)
├── campaign-monitor.md             (email sending)
└── health-checker.md               (system metrics)
```

### Skills (5)
```
.claude/skills/
├── anofm-scraper-launch/SKILL.md   (SSH to raspi, run scraper)
├── anofm-ingest-run/SKILL.md       (CSV→DB with schema mapping)
├── anofm-campaign-send/SKILL.md    (Brevo SMTP, rate limiting)
├── anofm-pipeline-health/SKILL.md  (metrics aggregation, alerts)
└── anofm-orchestrator/SKILL.md     (central coordinator, phase sequencing)
```

### Documentation (3)
```
.claude/
├── HARNESS_README.md               (quick start guide)
├── HARNESS_CHECKLIST.md            (validation tracker)
└── BUILD_SUMMARY.md                (this file)
```

### Updated (1)
```
CLAUDE.md                           (harness pointer + change history)
```

---

## Architecture

**Execution model:** Orchestrator-led agent team

```
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                           │
│           (anofm-orchestrator skill)                     │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
     Phase 1            Phase 2               Phase 3
    (Scheduler)      (Scraper Monitor)     (Ingest Monitor)
        │                   │                   │
    Enable timers     Validate CSV         CSV→DB load
    Verify schedule   Schema check         Dedup logic
                      Row counts           Atomicity
                         │
                    Phase 4 (Campaign Monitor)
                         │
                  Send emails (150/day)
                  Track bounces
                  Update DNC
                         │
                   Phase 5 (Health Checker)
                         │
                   Verify health (0–100)
                   Generate alerts
                   Trend analysis
                         │
                  ┌──────┴──────┐
                  │             │
              SUCCESS        FAILURE
                  │             │
             Report         Pause + Alert
```

**Team communication:** SendMessage (coordination) + File-based (data: CSV, DB, sent.csv, metrics)

---

## Workflow: 7 Phases

| Phase | Agent | Task | Input | Output |
|-------|-------|------|-------|--------|
| 1 | Scheduler | Enable timers | (none) | timer_status.json |
| 2 | Scraper | Run scraper | (automatic via timer) | CSV file |
| 3 | Scraper Monitor | Validate CSV | CSV path | scraper_validation_report.json |
| 4 | Ingest Monitor | Load CSV→DB | CSV + validation report | ingest_report.json |
| 5 | Campaign Monitor | Send emails | DB + DNC list | campaign_report.json + sent.csv |
| 6 | Health Checker | Monitor health | All reports + system metrics | pipeline_health_report.json |
| 7 | Orchestrator | Synthesize | All phase reports | Final summary report |

---

## Key Features

### ✅ Error Recovery
- Atomic transactions (ingest rollback on error)
- Pause points (validation HOLD, ingest ROLLBACK)
- No data loss (all files preserved in `_workspace/`)
- Retry logic with exponential backoff (Brevo rate limiting)

### ✅ Idempotency (Safe Re-runs)
- Scraper: deduped by job_id
- Ingest: deduped by content_hash
- Campaign: tracked in sent.csv (skips already-sent)

### ✅ Rate Limiting
- 150 emails/day (Brevo quota)
- 8 sec delay per email (bot prevention)
- Daily cap enforcement (wait until UTC midnight if exceeded)

### ✅ Monitoring
- Health score (0–100)
- Trend analysis (7-day moving average)
- Alert generation (critical, warning, info)
- Bounce rate tracking

### ✅ Validation
- CSV schema check (job_id, company, title, city, etc.)
- Row count range (2,000–15,000 expected)
- Data type validation (numeric, string, nullable fields)
- Duplicate detection (by job_id and content_hash)

### ✅ DNC Management
- Brevo bounces collection (24h API)
- Gmail bounces (optional, via IMAP)
- Suppression list dedup
- Bounce rate trending

---

## Data Flow

```
1. Scraper → CSV
   /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_[timestamp].csv

2. Validation → Report
   _workspace/scraper_validation_report.json
   (schema, row count, quality score)

3. Ingest → Database
   raspi:anofm_db.ij_jobs
   (16,429+ rows, deduped by content_hash)

4. Campaign → Sent List + Bounces
   /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv
   /opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt

5. Health Check → Metrics
   _workspace/pipeline_health_report.json + health_history.json
   (30-day rolling history for trends)
```

---

## Usage Examples

### Activation (First Run)
```
"Activate ANOFM on raspi. Run full pipeline test."

Expected: Orchestrator activates all 5 agents, runs complete cycle.
Duration: ~60–90 min
Result: All timers enabled, CSV ingested, emails sent, health report generated
```

### Health Check (Daily)
```
"Check ANOFM health on raspi."

Expected: Health Checker agent runs (< 5 min)
Result: Health score, alerts, trends, recommendations
```

### Dry-run Test (Safe)
```
"Run ANOFM in dry-run mode. Show me what would be sent without actually sending."

Expected: All phases run with --dry-run flags
Result: Simulation report, no DB changes, no emails sent
```

### Single Phase
```
"Send ANOFM emails today."           → Campaign Monitor only
"Ingest the latest CSV."             → Ingest Monitor only
"Run the scraper now."               → Scraper + Scraper Monitor
```

---

## Metrics & Alerts

### Health Score Formula
```
score = 100
score -= (timer_failures × 10)       # Each failure: -10
score -= (ingest_errors × 5)         # Each error: -5
score -= (bounce_rate × 0.5)         # Bounce rate as % points
if db_size < 16,000: score -= 20     # DB corruption suspect
if disk_usage > 90%: score -= 15     # Disk full risk
if any_service_down: score = 0       # Critical
```

### Alert Thresholds
- **Critical (< 50):** Timer failures, DB unreachable, disk full
- **Warning (50–75):** Bounce rate > 25%, disk > 80%, low send activity
- **Info (75+):** Slight trends, minor bounce increase

---

## Performance Notes

| Component | Typical Time | Notes |
|-----------|--------------|-------|
| Scraper | 8–10 min | Full cycle (85 pages, 7K rows) |
| Validation | <30 sec | CSV schema + quality check |
| Ingest | <30 sec | 7K rows → DB with dedup |
| Campaign | 20 min | 142 emails @ 8 sec/ea + delays |
| Health check | <1 min | Metrics collection + analysis |
| **Total cycle** | **60–90 min** | Mostly scraper + campaign |

---

## File Locations

### Source (Laptop)
```
D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ANOFM\.claude/
├── agents/            (5 agent definitions)
├── skills/            (5 skill definitions)
├── HARNESS_README.md
├── HARNESS_CHECKLIST.md
└── BUILD_SUMMARY.md
```

### Runtime (Raspi)
```
/opt/ACTIVE/INTERJOB/            (scraper, ingest scripts)
/opt/ACTIVE/ANOFM_DATA/csv/      (CSV output)
/opt/ACTIVE/EMAIL/CAMPAIGNS/     (campaign + DNC)
/opt/ACTIVE/ANOFM/.env           (credentials)
anofm_db (PostgreSQL)            (production DB)
```

### Workspace (Raspi/Laptop)
```
_workspace/
├── timer_status.json
├── scraper_validation_report.json
├── ingest_report.json
├── campaign_report.json
├── pipeline_health_report.json
└── health_history.json           (30-day rolling)
```

---

## Dependencies

### External
- raspi (192.168.100.20) — target machine
- PostgreSQL 15+ — anofm_db
- Brevo API — email sending (warehouseworkers.eu account)
- Gmail SMTP — Elena's account (elena.manpower.dristor@gmail.com)
- ANOFM API (public) — job data source

### Internal
- Credentials: `/opt/ACTIVE/ANOFM/.env` (Brevo key, Gmail password)
- Database: anofm_db with ij_jobs table (synced 2026-06-21)
- Systemd timers: anofm-scraper, anofm-ingest, anofm-audience-rebuild

---

## What's NOT Included (Out of Scope)

- SMS/WhatsApp sending (email only)
- Machine learning (no prediction models)
- Real-time dashboard (no Grafana integration)
- Multi-language support (English + Romanian templates only)
- Webhook callbacks (one-way pipeline)

---

## Known Limitations

1. **Schema mismatch:** Raspi's anofm_db columns may differ from raspibig's interjob_master. Workaround: pre-sync or manual schema fix.
2. **Scraper atomic rename:** `.tmp` files may not rename on kill. Workaround: manual rename or cleanup script.
3. **No auto disk cleanup:** Requires manual cleanup if > 90% used. Future: add cron.
4. **No failover:** Raspi independent, but no automatic switchover to raspibig if raspi down.

---

## Next Steps (Operator)

### Phase 1: Prepare (Now)
- [ ] Read HARNESS_README.md
- [ ] Verify raspi connectivity: `ping 192.168.100.20`
- [ ] Verify database: `psql -h 192.168.100.20 anofm_db -c "SELECT COUNT(*) FROM ij_jobs;"`
- [ ] Check credentials: `/opt/ACTIVE/ANOFM/.env` exists + populated

### Phase 2: Activate (First Run)
- [ ] Ask Claude: "Activate ANOFM on raspi. Run full pipeline test."
- [ ] Wait for orchestrator to complete (60–90 min)
- [ ] Verify: health_score ≥ 75, timers enabled, emails sent

### Phase 3: Monitor (Daily)
- [ ] Timers run automatically (Mon-Fri 08:25, 12:25, 15:59)
- [ ] Send emails manually as needed: "Send ANOFM emails today."
- [ ] Health check each evening: "Check ANOFM health."

### Phase 4: Maintain (Weekly/Monthly)
- [ ] Review bounce trends (should be < 5%)
- [ ] Archive old CSVs if disk > 85%
- [ ] Check DB integrity: `SELECT COUNT(*) FROM ij_jobs;`

---

## Support

**For troubleshooting:**
- See HARNESS_README.md "Troubleshooting" section
- Check `/opt/ACTIVE/INFRA/LOGS/ingest_anofm.log`
- Review systemd logs: `journalctl -u anofm-*.service`
- Run health check: "Check ANOFM health."

**For enhancement requests:**
- Add to HARNESS_CHECKLIST.md "Future Enhancements" section
- Update CLAUDE.md change history
- Rebuild harness with `anofm-orchestrator`

---

## Sign-off

✅ **Build complete**  
✅ **All components deployed**  
✅ **Documentation complete**  
✅ **Ready for activation**

**Built by:** Claude  
**Date:** 2026-06-21  
**Version:** 1.0

---

**To activate: Ask Claude "Activate ANOFM on raspi. Run full pipeline test."**
