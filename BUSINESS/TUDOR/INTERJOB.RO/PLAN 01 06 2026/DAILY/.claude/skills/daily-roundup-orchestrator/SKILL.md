---
name: daily-roundup-orchestrator
description: Orchestrate the complete daily job market roundup workflow — validate data, generate bilingual articles, publish to WordPress, monitor performance. Runs on 09:00 UTC cron on raspibig. Triggers on "daily roundup", "publish roundup", "generate daily article", or "run roundup workflow".
---

# Daily Roundup Orchestrator

## Overview
Coordinates a 4-phase pipeline to publish bilingual (RO+EN) job market articles on interjob.ro:

```
Phase 1: Data Validator → Validate ANOFM/EURES data
        ↓
Phase 2: Content Creator → Generate RO + EN articles
        ↓
Phase 3: Publisher → POST to WordPress + Yoast metadata
        ↓
Phase 4: Monitor → Track performance, generate alerts
        ↓
        Completion Report
```

## Execution Mode
**Subagent-based** (NOT team) — sequential workflow, no real-time negotiation between agents. Each phase completes before next begins.

## Phase 0 — Context Detection (on resume/re-run)

When triggered, first check:

1. **First-time run today?**
   - Check `_workspace/` directory (doesn't exist) → Initial run
   - Check `_workspace/` exists + no _workspace_prev → Continuation from previous failure
   - Check `_workspace_prev/` exists → User triggered re-run, preserve old results

2. **Load previous results (if available)**
   ```bash
   if [ -f "_workspace/01_validator_output.json" ]; then
       # Continuation: load last successful validation
       VALIDATOR_OUTPUT=$(cat _workspace/01_validator_output.json)
   else
       # Fresh run: proceed to Phase 1
   fi
   ```

3. **Decision logic**
   - New user input provided + `_workspace/` exists → Backup to `_workspace_prev/`, proceed with new run
   - No new input + previous run succeeded → Skip to Phase 2 (use cached validation)
   - No new input + previous run failed → Restart from Phase 1 (full retry)

## Phase 1 — Data Validator (60s timeout)

**Agent:** data-validator (subagent_type: "general-purpose", model: "opus")

**Input:**
```json
{
  "db_host": "localhost",
  "db_port": 5432,
  "db_name": "interjob_master",
  "db_user": "tudor",
  "db_pass": "<from_env_or_pgpass>",
  "eures_base": "/opt/ACTIVE/SCRAPER_DATA/csv/EURES",
  "eures_countries": ["Norway", "Denmark", "Sweden", "Finland", "Germany", "Netherlands", "France"],
  "dry_run": false
}
```

**Expected output:**
```json
{
  "status": "valid",
  "anofm_total": 5795,
  "anofm_by_sector": {...},
  "anofm_count_sector": {...},
  "eures_total": 4320,
  "eures_by_country": {...},
  "warnings": []
}
```

**Decision:**
- `status == "valid"` → Continue to Phase 2
- `status == "valid_with_warnings"` → Log warnings, continue to Phase 2
- `status == "invalid"` → **ABORT** (return error report, don't proceed)

**Save output:**
```bash
echo "${VALIDATOR_OUTPUT}" > _workspace/01_validator_output.json
```

## Phase 2 — Content Creator (180s timeout)

**Agent:** content-creator (subagent_type: "general-purpose", model: "opus")

**Input:** Pass entire Phase 1 output + today's date

**Expected output:**
```json
{
  "status": "generated",
  "articles": {
    "ro": {...},
    "en": {...}
  },
  "translations_made": 62,
  "warnings": []
}
```

**Decision:**
- `status == "generated"` → Continue to Phase 3
- `status == "partial"` → Log which article failed, continue to Phase 3 (publish what succeeded)
- Missing RO + EN both null → **ABORT** (return error)

**Save output:**
```bash
echo "${CREATOR_OUTPUT}" > _workspace/02_content_output.json
```

## Phase 3 — Publisher (90s timeout)

**Agent:** publisher (subagent_type: "general-purpose", model: "opus")

**Input:** Phase 2 output + orchestrator config (WP credentials, DB config)

**Config loaded from environment:**
```bash
# Source from official wp_sites.env (used by daily_roundup.py and other pub workflows)
source /opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env

export WP_INTERJOB_USER="${WP_INTERJOB_USER:-apaminerala}"
export WP_INTERJOB_PASS="${WP_INTERJOB_PASS}"
export DB_PASS=$(grep '^tudor:' ~/.pgpass | cut -d: -f3)

# Validate credentials loaded
if [ -z "$WP_INTERJOB_PASS" ]; then
  echo "ERROR: WP_INTERJOB_PASS not found in wp_sites.env"
  exit 1
fi
```

**Expected output:**
```json
{
  "status": "published",
  "results": {
    "ro": {"post_id": 12345, ...},
    "en": {"post_id": 12346, ...}
  },
  "db_log_recorded": true
}
```

**Decision:**
- `status == "published"` → Continue to Phase 4 (both articles live)
- `status == "partial"` → Continue to Phase 4 (at least one article published)
- `status == "failed"` → **Abort monitoring** (return error, but DON'T fail orchestrator—articles failed, not orchestrator)

**Save output:**
```bash
echo "${PUBLISHER_OUTPUT}" > _workspace/03_publisher_output.json
```

## Phase 4 — Monitor (45s timeout, non-blocking)

**Agent:** monitor (subagent_type: "general-purpose", model: "opus")

**Input:** Phase 3 output (post_ids and URLs)

**Expected output:**
```json
{
  "status": "monitored",
  "results": {
    "ro": {...},
    "en": {...}
  },
  "summary": "Both posts live and performing well"
}
```

**Decision:**
- `status == "monitored"` → Proceed to completion
- `status == "monitored_with_alerts"` → Log alerts, proceed (non-blocking)
- Monitor fails completely → Log error but **DON'T abort** (articles already published)

**Save output:**
```bash
echo "${MONITOR_OUTPUT}" > _workspace/04_monitor_output.json
```

## Completion Report

After all phases, synthesize a final report:

```json
{
  "orchestration_status": "success",
  "timestamp": "2026-06-23T09:25:00Z",
  "phases_completed": 4,
  "results": {
    "validation": {
      "status": "valid",
      "anofm_count": 5795,
      "eures_count": 4320,
      "warnings": []
    },
    "content": {
      "status": "generated",
      "ro_title": "Piața muncii...",
      "en_title": "Job Market...",
      "translations": 62
    },
    "publishing": {
      "status": "published",
      "ro_post_id": 12345,
      "en_post_id": 12346,
      "urls": [
        "https://interjob.ro/piata-muncii-2026-06-23/",
        "https://interjob.ro/job-market-2026-06-23/"
      ]
    },
    "monitoring": {
      "status": "monitored",
      "ro_ttfb_ms": 412,
      "en_ttfb_ms": 398,
      "alerts": []
    }
  },
  "summary": "✅ Daily roundup published successfully for 2026-06-23 (RO + EN)",
  "next_run": "2026-06-24T09:00:00Z"
}
```

## Error Handling

| Phase | Error | Action |
|-------|-------|--------|
| Phase 1 (Validator) | ANOFM count = 0 | ABORT: Return error detail, don't proceed |
| Phase 1 | EURES CSV missing | WARN: continue (EN will have reduced data) |
| Phase 2 (Creator) | Translation API fails | Partial: return RO, skip EN; continue to publisher |
| Phase 2 | Both RO + EN null | ABORT: return error |
| Phase 3 (Publisher) | WP auth fails | ABORT: return credential error |
| Phase 3 | WP 500 error | Retry 3x (1s, 2s, 4s backoff) |
| Phase 3 | Already published today | WARN: skip (unless --force=true) |
| Phase 4 (Monitor) | Post returns 404 | CRITICAL alert: log, but DON'T block orchestrator |
| Phase 4 | Monitor timeout | WARN: non-blocking, continue |

## Orchestrator Loop (for scheduled re-runs)

The orchestrator can be triggered manually or via cron:

```bash
# Cron: Daily at 09:00 UTC
0 9 * * * cd /opt/ACTIVE/EVENT_PUBLISHER && \
  python3 -c "from orchestrator import run; run(dry_run=False, force=False)" \
  >> /opt/ACTIVE/INFRA/LOGS/daily_roundup.log 2>&1
```

**Flags:**
- `--dry-run`: Validate + generate content, don't publish (test mode)
- `--force`: Publish even if today's language already exists
- `--lang ro|en|both`: Publish only specified language(s)

## Subsequent Runs (Partial Re-run)

If user says "regenerate the EN article", orchestrator detects:
1. `_workspace/01_validator_output.json` exists → **Skip validation** (reuse)
2. `_workspace/02_content_output.json` exists (but user wants regenerate) → **Re-run Phase 2** only
3. **Re-run Phase 3** (publish updated EN)
4. **Re-run Phase 4** (monitor updated post)

## Data Transmission Between Phases

All data flows as JSON via stdout/return values:

```
Phase 1 → Phase 2:  anofm_total, by_sector, by_country, warnings
Phase 2 → Phase 3:  ro_title, ro_slug, ro_meta, ro_content, en_title, en_slug, en_meta, en_content
Phase 3 → Phase 4:  post_ids, URLs, publish_timestamps
Phase 4 → Report:   metrics, alerts, summary
```

**No shared database state** between phases (each phase is independent). All data stored as JSON files in `_workspace/` for auditability and resume capability.

## Test Scenarios

### Scenario 1: Happy Path (All Green)
```bash
$ python3 orchestrator.py --dry-run
[Phase 1] ✅ ANOFM: 5795 | EURES: 4320
[Phase 2] ✅ RO article generated (8942 chars) | EN article (9156 chars)
[Phase 3] ✅ [DRY RUN] Would publish post_id=12345 (RO) and 12346 (EN)
[Phase 4] ✅ [DRY RUN] Would monitor posts
✅ All phases completed successfully
```

### Scenario 2: ANOFM Down (DB Error)
```bash
$ python3 orchestrator.py
[Phase 1] ❌ ANOFM query returned 0 jobs
          Database may be down. Check ij_jobs table.
❌ ABORT: Validation failed. Daily roundup skipped.
```

### Scenario 3: Already Published (Dedup)
```bash
$ python3 orchestrator.py
[Phase 1] ✅ Data valid
[Phase 2] ✅ Content generated
[Phase 3] ⚠️  Already published today (lang=ro)
          Use --force to override.
          → Continue to EN (fresh publish)
          → Skip RO (already exists)
[Phase 4] ✅ Monitored EN post
✅ Partial completion: EN article published, RO skipped
```

### Scenario 4: Translation Fails Midway
```bash
$ python3 orchestrator.py
[Phase 1] ✅ Data valid
[Phase 2] ⚠️  EURES Denmark translation failed (rate limit)
          Continuing with available data...
          RO article: ✅ generated
          EN article: ⚠️ partial (missing Denmark jobs)
[Phase 3] ✅ [RO] Published post_id=12345
          ✅ [EN] Published post_id=12346 (incomplete)
[Phase 4] ✅ Both posts live, performance normal
⚠️  Partial completion: Both published, EN has missing jobs
```

## Success Criteria

✅ Phase 1: Data validation passes (no HARD_FAIL)  
✅ Phase 2: At least one article generated (RO or EN)  
✅ Phase 3: At least one post published and recorded in wp_roundup_log  
✅ Phase 4: Posts return HTTP 200 and are indexed  
✅ Completion report saved to `_workspace/final_report.json`  
✅ No unhandled exceptions (all errors caught and reported)
