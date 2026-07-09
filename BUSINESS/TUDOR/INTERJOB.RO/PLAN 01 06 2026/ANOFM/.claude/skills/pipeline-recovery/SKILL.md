---
name: pipeline-recovery
description: Diagnose, analyze, and recover multi-phase data pipelines (scrape→transform→ingest→send) from partial failures. Detects which phase failed, recovers idempotently (dedup prevents data loss), validates data integrity, and resumes without human intervention. SSH-based on-demand via plink. Used when pipeline fails mid-cycle, diagnosing where it broke, recovering corrupted data, verifying end-to-end integrity, or resuming after infrastructure failure.
---

# Skill: pipeline-recovery

**Domain:** Multi-phase pipeline orchestration, error recovery  
**Target:** Data pipelines (CSV→DB→email, scrape→transform→publish, etc.)  
**Input:** Pipeline name, error message, phase information  
**Output:** Root cause analysis, recovery steps, integrity verification results

---

## When to Use

- **Pipeline fails mid-cycle:** "Ingest failed. Continue from there or start over?"
- **Data corruption suspected:** "Did the failure corrupt the database?"
- **Partial delivery:** "Some emails sent before crash. Resume without duplicates?"
- **Unknown failure point:** "Where exactly did the pipeline break?"
- **Recovery verification:** "Is the system safe to resume?"
- **Post-incident audit:** "What happened during the outage?"

---

## How It Works

### Step 1: Identify Failure Point

**Determine which phase failed:**

```bash
# Check last execution log
tail -50 /opt/ACTIVE/INFRA/LOGS/pipeline.log | grep -i "error\|failed\|exception"

# Check phase markers
# Pipelines leave breadcrumbs: Phase 1 started, Phase 2 complete, Phase 3 failed

# Examples:
# 2026-06-23 09:00:00 [SCRAPER] Starting...
# 2026-06-23 09:08:45 [SCRAPER] Complete - 11,869 rows
# 2026-06-23 09:09:00 [INGEST] Starting...
# 2026-06-23 09:09:15 [INGEST] ERROR: Transaction timeout
#   ^ FAILURE POINT = Phase 3 (Ingest)
```

**Output: Failure summary**
```json
{
  "failed_phase": 3,
  "phase_name": "Ingest",
  "error": "Transaction timeout",
  "timestamp": "2026-06-23T09:09:15Z",
  "status": "PARTIAL - Scraper OK, Ingest FAILED, Campaign SKIPPED"
}
```

### Step 2: Check Data State at Failure Point

**For each phase, check what data was committed:**

**Phase 1 (Scraper) — Check CSV output:**
```bash
ls -lh /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_*.csv | tail -3
# If CSV exists and recent: Phase 1 ✅ COMPLETE

wc -l /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_latest.csv
# If 0 rows: Scraper partial or failed
```

**Phase 2/3 (Validation) — Check report:**
```bash
test -f /opt/ACTIVE/ANOFM/_workspace/scraper_validation_report.json
# If exists: Validation ran and saved result

cat /opt/ACTIVE/ANOFM/_workspace/scraper_validation_report.json | grep recommendation
# Shows: PASS or HOLD or FAIL
```

**Phase 4 (Ingest) — Check database:**
```bash
export PGHOST=localhost
psql anofm_db -c "SELECT COUNT(*) FROM ij_jobs WHERE updated_at >= '2026-06-23';"
# Compare to expected row count from CSV

# Check for incomplete transaction
psql anofm_db -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state='active';"
# If > 0: Transaction may be in progress (lock issue)
```

**Phase 5 (Campaign) — Check sent list:**
```bash
wc -l /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv
# If increased from yesterday: Emails were sent before failure

grep "$(date +%Y-%m-%d)" /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv | wc -l
# Count sent today
```

**Phase 6 (Health) — Check report:**
```bash
cat /opt/ACTIVE/ANOFM/_workspace/pipeline_health_report.json | grep health_score
# Last known health state
```

### Step 3: Assess Data Integrity

**For failed phase, determine if data is corrupted:**

| Phase | Integrity Check | Safe to Retry? |
|-------|-----------------|---|
| **Scraper** | CSV exists, row count reasonable? | ✅ YES (dedup by job_id) |
| **Validation** | Report file valid JSON? | ✅ YES (read-only) |
| **Ingest** | All new rows present? Check dedup? | ⚠️ TEST (see below) |
| **Campaign** | Duplicates in sent.csv? | ✅ YES (dedup by email) |
| **Health** | Report file valid JSON? | ✅ YES (read-only) |

**Test ingest safety (most critical):**
```bash
export PGHOST=localhost

# Before recovery
BEFORE=$(psql anofm_db -tc "SELECT COUNT(*) FROM ij_jobs WHERE source='anofm';")
echo "Row count before: $BEFORE"

# Check for duplicate content_hashes (indicates failed ingest was retried)
psql anofm_db -c "SELECT content_hash, COUNT(*) as cnt FROM ij_jobs GROUP BY content_hash HAVING cnt > 1 LIMIT 5;"
# If results show duplicates with same hash: Ingest ran twice (need rollback)

# If no duplicates: Safe to retry ingest (dedup will handle)
```

### Step 4: Choose Recovery Strategy

**Three strategies based on failure point:**

#### Strategy A: Restart from Failure Point (Recommended)

**Use when:** Last phase before failure was complete and committed

**Example:** Ingest failed, but scraper and validation both passed

**Steps:**
```bash
# 1. Verify previous phase clean
tail -10 /opt/ACTIVE/ANOFM/_workspace/scraper_validation_report.json | grep PASS

# 2. Manually run failed phase
cd /opt/ACTIVE/INTERJOB && python3 ingest_anofm.py
# Add --dry-run first to test

# 3. Verify success
export PGHOST=localhost && psql anofm_db -c "SELECT COUNT(*) FROM ij_jobs;"

# 4. Continue pipeline
# Run campaign, health check, etc.
```

**Advantages:** Fast, minimal re-work, proven safe with dedup

#### Strategy B: Rollback + Restart (If Corruption Suspected)

**Use when:** Data corruption detected or dedup failed

**Example:** Database has duplicate entries or transaction left lock

**Steps:**
```bash
# 1. Backup corrupted state
pg_dump anofm_db > /tmp/anofm_db.corrupted_backup.sql

# 2. Identify point to rollback to
# If failure recent (< 1 day): revert to previous day's backup
psql anofm_db < /opt/ACTIVE/BACKUPS/anofm_db_2026-06-22.sql

# 3. Remove partial files
mv /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_*.csv /tmp/failed_csvs/

# 4. Re-run full pipeline
# Scraper will re-produce CSV, ingest will load cleanly
```

**Advantages:** Guarantees clean state, removes all corruption

**Disadvantages:** Time consuming, loses partial work

#### Strategy C: Skip Failed Phase (If Not Critical)

**Use when:** Phase is optional or can be skipped this cycle

**Example:** Health check failed, but campaign and ingest succeeded

**Steps:**
```bash
# Skip health check, continue to next cycle
# Or run health check manually later

# Mark phase as skipped in logs
echo "2026-06-23 09:20:00 [HEALTH] Skipped - will retry next cycle" >> /opt/ACTIVE/INFRA/LOGS/pipeline.log

# Resume normal operation
```

**Advantages:** Minimal downtime, non-blocking

---

### Step 5: Execute Recovery

**Generic recovery workflow:**

```bash
#!/bin/bash
# Recovery script

PIPELINE="anofm"
FAILED_PHASE="ingest"

echo "[RECOVERY] Starting $PIPELINE recovery from $FAILED_PHASE"

# 1. Verify previous phase
echo "[1] Verifying previous phase..."
if [ ! -f /opt/ACTIVE/ANOFM/_workspace/scraper_validation_report.json ]; then
  echo "ERROR: Scraper validation missing. Cannot proceed."
  exit 1
fi

# 2. Test database connection
echo "[2] Testing database..."
export PGHOST=localhost
psql anofm_db -c "SELECT 1;" > /dev/null || { echo "ERROR: DB unreachable"; exit 1; }

# 3. Dry-run failed phase
echo "[3] Dry-running failed phase..."
cd /opt/ACTIVE/INTERJOB && python3 ingest_anofm.py --dry-run --limit 10
if [ $? -ne 0 ]; then
  echo "ERROR: Phase still failing. Needs investigation."
  exit 1
fi

# 4. Execute failed phase
echo "[4] Executing failed phase..."
python3 ingest_anofm.py
if [ $? -ne 0 ]; then
  echo "ERROR: Phase execution failed. Rolling back..."
  # Rollback steps here
  exit 1
fi

# 5. Verify integrity
echo "[5] Verifying data integrity..."
ROW_COUNT=$(psql anofm_db -tc "SELECT COUNT(*) FROM ij_jobs WHERE source='anofm';")
if [ "$ROW_COUNT" -lt 16000 ]; then
  echo "WARNING: Row count low ($ROW_COUNT). Check for data loss."
fi

# 6. Continue pipeline
echo "[6] Resuming pipeline..."
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI && python3 campaign_anofm_angajatori.py --limit 150

echo "[RECOVERY] Complete - Pipeline resumed"
```

### Step 6: Verify End-to-End Integrity

**After recovery, verify whole pipeline:**

```bash
# 1. Check all outputs exist
ls -lh /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_latest.csv  # ✅ Must exist
test -f /opt/ACTIVE/ANOFM/_workspace/ingest_report.json && echo "✓ Ingest report"
test -f /opt/ACTIVE/ANOFM/_workspace/campaign_report.json && echo "✓ Campaign report"
test -f /opt/ACTIVE/ANOFM/_workspace/pipeline_health_report.json && echo "✓ Health report"

# 2. Check database consistency
export PGHOST=localhost
psql anofm_db << 'EOF'
SELECT 
  COUNT(*) as total_rows,
  COUNT(DISTINCT content_hash) as unique_rows,
  COUNT(DISTINCT source_job_id) as unique_jobs
FROM ij_jobs WHERE source='anofm';
EOF
# All three counts should be similar (few duplicates if any)

# 3. Check no corrupted records
psql anofm_db -c "SELECT COUNT(*) FROM ij_jobs WHERE company IS NULL OR job_title IS NULL;"
# Should be 0 (no nulls in required fields)

# 4. Check sent list consistency
SENT_COUNT=$(wc -l < /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv)
DNC_SIZE=$(wc -l < /opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt)
echo "Emails sent: $SENT_COUNT, DNC size: $DNC_SIZE"
# Ratio should be reasonable (DNC < 20% of sent)
```

---

## Recovery Scenarios

### Scenario 1: Scraper Timeout

**Error:**
```
[SCRAPER] Timeout after 900 seconds. Process killed.
CSV incomplete: 4,500 rows (expected 11,000)
```

**Recovery:**
```bash
# 1. Check CSV state
ls -lh /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_*.csv | tail -1
# If size is small: Partial CSV, will cause ingest errors

# 2. Move partial CSV
mv /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_*.csv /tmp/failed_scrapes/

# 3. Re-run scraper
cd /opt/ACTIVE/INTERJOB && python3 anofm_scraper.py

# 4. Resume pipeline
python3 ingest_anofm.py  # Will load new CSV
```

### Scenario 2: Ingest Transaction Deadlock

**Error:**
```
[INGEST] FATAL: deadlock detected in transaction
Transaction rolled back. 0 rows inserted.
```

**Recovery:**
```bash
# 1. Check for locks
export PGHOST=localhost
psql anofm_db -c "SELECT pid, usename, query FROM pg_stat_activity WHERE state='active';"

# 2. Kill blocking query (if safe)
psql anofm_db -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%ij_jobs%' AND pid != pg_backend_pid();"

# 3. Retry ingest
python3 ingest_anofm.py

# 4. If still fails: Restart PostgreSQL
sudo systemctl restart postgresql
# Wait 10 sec, retry
```

### Scenario 3: Campaign Partial Send (100 of 150 sent, then crashed)

**Error:**
```
[CAMPAIGN] Brevo API 500 error after 100 emails
Campaign interrupted at email #101
```

**Recovery:**
```bash
# 1. Check sent.csv
tail -20 /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv
# Shows: 100 emails with today's date

# 2. Resume campaign (dedup will skip sent)
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI && python3 campaign_anofm_angajatori.py --limit 150
# Will send remaining 50 (sent.csv prevents duplicates)

# 3. Verify
tail -10 /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv
# Should show 50 new lines added
```

---

## Idempotency Guarantee

**ANOFM is designed for safe re-runs:**

| Phase | Dedup Key | Safe to Retry? | Notes |
|-------|-----------|---|---|
| Scraper | job_id | ✅ YES | Scraper itself dedupes by job_id |
| Validation | (read-only) | ✅ YES | No state change |
| Ingest | content_hash (MD5) | ✅ YES | ON CONFLICT DO NOTHING prevents duplicates |
| Campaign | email + date | ✅ YES | sent.csv tracks sent addresses |
| Health | (read-only) | ✅ YES | No state change |

**This means:** You can retry any phase multiple times with zero risk of duplicate data.

---

## Monitoring for Early Recovery

**Detect issues before they cause full failures:**

```bash
# In health check, monitor these signals:
# 1. Phase execution time spike (> 2× normal)
if [ $(grep "INGEST.*took" /opt/ACTIVE/INFRA/LOGS/pipeline.log | tail -1 | awk '{print $NF}') -gt 60 ]; then
  echo "ALERT: Ingest slow. May be approaching timeout."
fi

# 2. Database lock count high
LOCKS=$(psql anofm_db -tc "SELECT COUNT(*) FROM pg_locks;")
if [ "$LOCKS" -gt 100 ]; then
  echo "ALERT: $LOCKS locks detected. Risk of deadlock."
fi

# 3. Disk space low
DISK_USAGE=$(df /opt | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
  echo "ALERT: Disk $DISK_USAGE% full. Cleanup needed."
fi
```

---

## Integration with ANOFM Harness

**Health Checker agent runs recovery detection:**
- Monitors last execution logs
- Checks all phase outputs exist
- Tests database for locks
- Alerts if recovery needed

**Orchestrator can trigger recovery:**
```
"ANOFM failed. Recover from ingest phase."
→ Runs recovery workflow
→ Re-executes ingest
→ Resumes campaign
→ Generates report
```
