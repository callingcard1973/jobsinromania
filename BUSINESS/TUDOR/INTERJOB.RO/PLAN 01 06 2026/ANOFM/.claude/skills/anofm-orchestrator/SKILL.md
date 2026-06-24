---
name: anofm-orchestrator
description: Orchestrate complete ANOFM pipeline on raspi — activate timers (scheduler), validate scraper output (scraper-monitor), ingest CSV to DB (ingest-monitor), send emails (campaign-monitor), verify health (health-checker). Execution: agent team with dependency-based tasking. Use when initializing pipeline, running full cycle (scrape→ingest→send), recovering from failure, or auditing complete system state.
---

# Skill: anofm-orchestrator

**Execution mode:** Agent team (5 specialists)  
**Phases:** Activate → Scrape → Validate → Ingest → Campaign → Monitor → Report  
**Duration:** ~60–90 min (scraper 8–10 min, ingest <1 min, campaign 20 min, monitor <1 min)

---

## When to Use

- **Initial activation:** "Set up ANOFM on raspi — activate all timers and run once"
- **Full cycle:** "Run scrape→ingest→send→check in sequence"
- **Recovery:** "Resume pipeline after interruption (with dedup safety)"
- **Diagnostic:** "Show me complete system state (all metrics, logs, alerts)"
- **Dry-run:** "Test the entire pipeline without sending emails"

---

## Architecture

**5-member team:**
1. **Scheduler** — Manage systemd timers, enable/disable, monitor schedule
2. **Scraper Monitor** — Validate CSV output, schema, row counts
3. **Ingest Monitor** — Load CSV → DB with error recovery
4. **Campaign Monitor** — Send emails, track bounces, update DNC
5. **Health Checker** — Verify overall pipeline health, generate alerts

**Data flow:**
```
Scheduler (verify timers enabled)
    ↓
Scraper Monitor (validate CSV)
    ↓ (_workspace/scraper_validation_report.json)
Ingest Monitor (CSV → DB)
    ↓ (_workspace/ingest_report.json)
Campaign Monitor (send emails)
    ↓ (_workspace/campaign_report.json)
Health Checker (aggregate metrics)
    ↓ (_workspace/pipeline_health_report.json)
ORCHESTRATOR (synthesize final report)
```

**Shared files** (`_workspace/`):
- `timer_status.json` — Scheduler output
- `scraper_validation_report.json` — Scraper Monitor output
- `ingest_report.json` — Ingest Monitor output
- `campaign_report.json` — Campaign Monitor output
- `pipeline_health_report.json` — Health Checker output
- `health_history.json` — Historical metrics (30-day rolling)

---

## Phase-by-Phase Workflow

### Phase 0: Context Check (Orchestrator)
Determine execution mode:
- **Initial activation:** No `_workspace/` directory. Run full pipeline (all phases).
- **Resume:** `_workspace/` exists, user requested "continue". Skip completed phases (check timestamps).
- **Partial re-run:** User specifies "re-run ingest only". Skip scheduler + scraper, start at ingest.
- **Dry-run:** User specified `--dry-run`. All agent tasks execute with dry-run flags (no DB changes, no emails sent).

Action: Create `_workspace/` if missing. Load previous reports if available.

### Phase 1: Activate Timers (Scheduler)
**Task:** Enable ANOFM timers on raspi.

**Input:** `activation_mode` (enable | check | disable)

**Output:** `_workspace/timer_status.json`
```json
{
  "timers": {
    "anofm-scraper.timer": { "enabled": true, "next_run": "2026-06-21T18:25:00Z" },
    "anofm-ingest.timer": { "enabled": true, "next_run": "2026-06-21T18:30:00Z" },
    "anofm-audience-rebuild.timer": { "enabled": true, "next_run": "2026-06-21T18:40:00Z" }
  },
  "status": "ACTIVATED"
}
```

**Success criteria:** All timers enabled. Orchestrator stores timestamp.

---

### Phase 2: Run Scraper (Implicit)
**Note:** Orchestrator does NOT run scraper directly. Instead, waits for scheduler to report that scraper timer is enabled. Typical flow:
1. Scheduler enables scraper.timer
2. Scraper runs automatically at next scheduled time (Mon-Fri 08:25, 12:25, 15:59)
3. Orchestrator can force immediate run: `systemctl start anofm-scraper.service` (one-off)

For **immediate execution:** Orchestrator sends message to scheduler: "Start scraper now and wait 10 min".
Scheduler executes: `ssh tudor@192.168.100.20 "sudo systemctl start anofm-scraper.service && sleep 600 && ls -lt /opt/ACTIVE/ANOFM_DATA/csv/*.csv | head -1"`

---

### Phase 3: Validate Scraper Output (Scraper Monitor)
**Task:** Verify latest CSV is valid (schema, row count, dedup).

**Input:** Latest CSV path (auto-detected from `/opt/ACTIVE/ANOFM_DATA/csv/`)

**Output:** `_workspace/scraper_validation_report.json`
```json
{
  "csv_path": "/opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_2026-06-21_082530.csv",
  "row_count": 7222,
  "schema_valid": true,
  "data_quality_score": 98,
  "recommendation": "PASS"
}
```

**Decision tree:**
- If PASS → proceed to Phase 4
- If HOLD → pause. Report to orchestrator. Wait for user decision.

---

### Phase 4: Ingest to Database (Ingest Monitor)
**Task:** Load CSV → anofm_db.ij_jobs with schema mapping + dedup.

**Input:** CSV path from Phase 3 + scraper validation report

**Output:** `_workspace/ingest_report.json`
```json
{
  "rows_inserted": 6999,
  "rows_updated": 200,
  "rows_skipped": 23,
  "transaction_status": "COMMITTED",
  "db_row_count_after": 16429,
  "recommendation": "PASS"
}
```

**Decision tree:**
- If COMMITTED + > 95% success → proceed to Phase 5
- If ROLLED_BACK or < 95% → pause. Investigate schema issue. Report to orchestrator.

---

### Phase 5: Send Campaign Emails (Campaign Monitor)
**Task:** Execute ANOFM_ANGAJATORI campaign (with 150/day cap).

**Input:** Database ready (from Phase 4) + dry-run flag (if specified)

**Output:** `_workspace/campaign_report.json`
```json
{
  "emails_sent": 142,
  "bounce_rate": 3.2,
  "dnc_updated": true,
  "status": "COMPLETE"
}
```

**Decision tree:**
- If live mode: send emails, update DNC, append to sent.csv
- If dry-run mode: show candidate emails, do NOT send, do NOT update lists
- Either way → proceed to Phase 6

---

### Phase 6: Health Check (Health Checker)
**Task:** Verify overall pipeline health, generate alerts, recommend actions.

**Input:** All previous reports + live system metrics

**Output:** `_workspace/pipeline_health_report.json`
```json
{
  "health_score": 85,
  "status": "HEALTHY",
  "alerts": ["Bounce rate trending up. Monitor next 3 days."],
  "recommendations": ["Continue current schedule."]
}
```

---

### Phase 7: Final Report (Orchestrator)
**Task:** Synthesize all agent reports into executive summary.

**Output:** Final report to user
```
=== ANOFM PIPELINE ORCHESTRATION COMPLETE ===

Execution Mode: FULL CYCLE (scrape → ingest → send → monitor)
Runtime: 65 minutes
Status: SUCCESS ✓

[Phase Breakdown]
1. Timers: ACTIVATED (3/3 enabled)
2. Scraper: 7,222 rows ✓
3. Validation: PASS ✓ (schema valid, quality 98%)
4. Ingest: 6,999 inserted, 200 updated ✓ (99.5% success)
5. Campaign: 142 emails sent ✓ (bounce rate 3.2%)
6. Health: Score 85/100 (HEALTHY) ✓

[Alerts]
- Bounce rate trending up (2.1% → 3.2%). Monitor next 3 days.

[Recommendations]
- Continue current schedule.
- Schedule disk cleanup if usage exceeds 85%.

Next scheduled run: 2026-06-21T12:25:00Z (scraper timer)
```

---

## Error Handling Strategy

### Recovery Logic
| Phase | Error | Recovery |
|-------|-------|----------|
| 1 (Timers) | Timer fails to enable | Report + pause. User can manually restart. |
| 2 (Scraper) | Timeout (> 15 min) | Report timeout. Assume scraper hung. Kill + restart. |
| 3 (Validate) | Schema invalid | Report schema error. Halt pipeline. User investigates. |
| 4 (Ingest) | ROLLBACK | Report transaction failure. Skip campaign. Investigate DB. |
| 5 (Campaign) | Brevo 429 (rate limit) | Backoff 60 sec, retry. Continue if succeeds. |
| 5 (Campaign) | Email parse error | Log + skip row. Continue loop. Report failure count. |
| 6 (Health) | Metrics unavailable | Skip metric. Report warning. Continue. |

### Automatic Pause Points
- Scraper validation HOLD → pause before ingest
- Ingest ROLLBACK → pause before campaign
- Health score < 50 → alert user before next scheduled cycle

### Rollback Strategy
- **Ingest fails:** Mark CSV as "ingest_failed" (rename `.csv` → `.failed`). Do NOT delete.
- **Campaign partial send:** Sent emails logged in sent.csv. Resume will skip sent addresses (idempotent).
- **No data loss:** All files preserved in `_workspace/` and system logs.

---

## Dry-run Mode

```
Usage: "Run ANOFM pipeline in dry-run mode"

Execution:
1. Scheduler: check timers (no changes)
2. Scraper Monitor: validate CSV (read-only)
3. Ingest Monitor: simulate ingest (no DB changes)
4. Campaign Monitor: show candidates (no emails sent)
5. Health Checker: full diagnostics (read-only)
6. Orchestrator: final report (show what would happen)

Output: Full simulation report + metrics, no side effects
```

---

## Re-run Safety (Idempotency)

**Scraper → Ingest → Campaign chain is idempotent:**
- Scraper: deduped by job_id (safe to re-run)
- Ingest: deduped by content_hash (safe to re-run)
- Campaign: tracked in sent.csv (safe to resume)

**Example scenario:** Ingest fails due to network. Pipeline pauses. User fixes issue + re-runs.
```
1. Scheduler: check timers (no-op, already enabled)
2. Scraper: CSV exists from previous run (skip re-scrape)
3. Validate: re-validate same CSV (pass again)
4. Ingest: retry with same CSV (dedup prevents double-insert)
5. Campaign: resume from sent.csv line count (skip already-sent)
6. Health: re-check all metrics
```
Result: Safe retry with zero duplication risk.

---

## Task Dependencies

```
[Scheduler] ─→ Timers enabled
    ↓
[Scraper Monitor] ─→ CSV validated
    ↓
[Ingest Monitor] ─→ DB ingested
    ↓
[Campaign Monitor] ─→ Emails sent
    ↓
[Health Checker] ─→ Metrics aggregated
    ↓
[Orchestrator] ─→ Final report
```

**Dependency enforcement:** Orchestrator pauses if any phase fails. Each agent waits for task assignment before proceeding. No parallel steps (sequential pipeline).

---

## Team Communication Protocol

**Orchestrator → Agents:**
- TaskCreate: assign phase task + input parameters
- SendMessage: "Proceed to phase X" (coordination)

**Agents → Orchestrator:**
- SendMessage: "Phase complete. Results: [summary]"
- File-based: write output JSON to `_workspace/`

**Agent ↔ Agent:**
- File-based: read previous phase output (via `_workspace/`)
- SendMessage: "Validation complete. Clear to ingest."

---

## Success Criteria

- [ ] All 5 agents activated ✓
- [ ] Phase 1 (Timers): enabled ✓
- [ ] Phase 3 (Validate): PASS ✓
- [ ] Phase 4 (Ingest): COMMITTED ✓
- [ ] Phase 5 (Campaign): emails sent ✓
- [ ] Phase 6 (Health): score ≥ 75 ✓
- [ ] All reports written to `_workspace/` ✓
- [ ] Final orchestrator report generated ✓

---

## Sample Execution Times

```
Scheduler (timer check): 10 sec
Scraper (full cycle): 480 sec (8 min)
[Wait for scraper to complete]
Scraper Monitor (validate CSV): 5 sec
Ingest Monitor (CSV → DB): 30 sec
Campaign Monitor (142 emails @ 8 sec/ea): 1200 sec (20 min)
Health Checker (metrics): 10 sec
Orchestrator (synthesis): 5 sec

Total: ~60–90 min (mostly scraper + campaign delays)
```

---

## Notes

- **First activation:** Timers disabled on raspi. Orchestrator enables them. Subsequent cycles run on schedule (no manual action needed).
- **Monitoring:** After activation, systemd timers run autonomously. Health checker runs every 30 min (optional, not blocking).
- **Metrics:** All reports stored in `_workspace/` for auditing + trending analysis.
- **Alert integration:** Critical alerts (health score < 50) can integrate with Telegram/Slack (future enhancement).
