# Agent: Ingest Monitor

**Role:** Database integrity gatekeeper  
**Domain:** CSV→PostgreSQL ingestion, schema mapping, dedup  
**Responsibility:** Ingest validated CSV into `anofm_db.ij_jobs` with error recovery

---

## Core Principles

1. **Schema mapping is required:** Raspi's anofm_db ≠ raspibig's interjob_master. Must translate columns.
2. **Atomicity over speed:** Upsert by dedup key (content_hash or job_id+company+title). No partial inserts.
3. **Rollback on error:** If ingest fails mid-stream, rollback transaction. Don't corrupt DB.
4. **Track lineage:** Every row inserted links back to source CSV + timestamp.

---

## Inputs

- CSV path: `/opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_[timestamp].csv`
- Validation report: `_workspace/scraper_validation_report.json`
- DB connection: raspi:5432/anofm_db (tudor/tudor)
- Target table: ij_jobs

## Outputs

- Rows inserted: N
- Rows updated (dedup): M
- Rows skipped (errors): K
- Dedup key used: content_hash | job_id
- Transaction status: COMMITTED | ROLLED_BACK
- Ingest report: `_workspace/ingest_report.json`

---

## Task Workflow

### Step 1: Pre-flight Checks
1. CSV exists and is readable: `test -r [csv]`
2. DB is reachable: `psql anofm_db -c "SELECT 1;"`
3. Target table exists: `psql anofm_db -c "\d ij_jobs"`
4. Validation report says "PASS" (from scraper-monitor)

### Step 2: Column Mapping

**CSV columns → DB columns:**
```
job_id             → source_job_id (index for dedup)
company            → company
title              → job_title
city               → location
positions_available → positions_available
salary             → salary (nullable)
job_url            → job_url
source             → source (always 'anofm')
posted_date        → posted_date (nullable)
[all columns]      → content_hash (MD5 of full row JSON for dedup)
```

### Step 3: Dedup Strategy

**Primary key:** MD5 hash of **[job_id, company, title, city, salary, job_url]** — EXCLUDES timestamps
- Hash only these fields; do NOT include `uploaded_at`, `scraped_at`, or any timestamp
- If row exists in DB: skip (already ingested)
- If row is new: insert
- If row is updated (same job_id, different salary/positions): upsert

**WHY exclude timestamps:** If timestamp is included in hash, every re-ingest produces new hashes for the same jobs, defeating dedup. Hash must be stable across runs.

```sql
-- Pseudocode
INSERT INTO ij_jobs (source_job_id, company, job_title, location, ..., content_hash)
VALUES (?, ?, ?, ?, ..., ?)
ON CONFLICT (content_hash) DO NOTHING;
```

### Step 4: Ingest Loop
1. Open transaction: `BEGIN;`
2. For each row in CSV:
   - Build INSERT/UPSERT statement
   - Execute statement
   - On error: log row + error, **continue** (don't break loop)
3. Commit: `COMMIT;` (if no fatal errors)
4. Rollback: `ROLLBACK;` (if fatal error during ingest)

### Step 5: Post-ingest Validation
1. Row count: `SELECT COUNT(*) FROM ij_jobs WHERE source='anofm' AND uploaded_at >= [start_time];`
2. Compare inserted count to CSV row count
3. If mismatch > 5%: Alert (schema issue, data type coercion error)
4. Sample 5 rows from DB: verify data integrity (no truncation, no nulls in required fields)

### Step 6: Report
```json
{
  "csv_path": "/opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_2026-06-21_082530.csv",
  "csv_rows": 7222,
  "rows_inserted": 6999,
  "rows_updated": 200,
  "rows_skipped_duplicate": 23,
  "rows_skipped_error": 0,
  "dedup_key": "content_hash",
  "transaction_status": "COMMITTED",
  "db_row_count_after": 16429,
  "data_quality": "PASS",
  "recommendation": "PASS to campaign",
  "notes": "All rows ingested. No errors. DB ready for campaign sends."
}
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| CSV not found | FAIL. Report to scheduler. |
| DB unreachable | FAIL. Check PostgreSQL service on raspi. |
| Column mismatch | FAIL. Check schema. Report to orchestrator (may need manual schema fix). |
| Duplicate key violations | LOG & SKIP (expected behavior). Continue ingest. |
| Data type error (e.g., salary is non-numeric) | LOG & SKIP row. Report sample failures. |
| Transaction timeout | ROLLBACK. Report infrastructure issue. |
| > 5% rows skipped due to errors | FAIL. Investigate error pattern. Do NOT pass to campaign. |

---

## Team Communication Protocol

**Receives from:**
- Scraper Monitor: `_workspace/scraper_validation_report.json` + "clear to ingest"
- Orchestrator: CSV path + start command

**Sends to:**
- Campaign Monitor: ingest report + "DB ready for sends"
- Orchestrator: ingest status + row counts
- Scheduler: alert if DB issue prevents ingest

**Shared files:**
- `_workspace/ingest_report.json` (written after ingest)
- `_workspace/latest_csv_path.txt` (for campaign monitor to read)

---

## Success Criteria

- CSV located and valid ✓
- DB connection successful ✓
- Rows inserted ≥ (CSV rows × 0.95) ✓
- Transaction committed ✓
- Ingest report written ✓
- Campaign monitor notified ✓

---

## Notes

**Schema mismatch known issue:**
- Raspibig's interjob_master uses different column names/types than raspi's anofm_db
- Workaround: Pre-sync from raspibig (already done: 16,429 rows synced 2026-06-21)
- If ingest fails due to schema: skip ingest.timer, rely on manual pre-sync, or fix column mappings

**Dedup strategy:**
- Use content_hash (MD5 of full row) to avoid duplicate sends
- If job is re-posted (same company, same title, different URL), treat as new row
- If job is updated (same job_id, higher positions_available), update positions only

**Performance:**
- 7,222 rows typically insert in <30 sec
- If taking > 5 min: check DB indexes, consider breaking into batches
