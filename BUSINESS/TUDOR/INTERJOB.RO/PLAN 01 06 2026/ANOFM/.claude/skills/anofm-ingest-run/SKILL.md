---
name: anofm-ingest-run
description: Ingest validated ANOFM CSV into raspi:5432/anofm_db.ij_jobs with schema mapping, dedup, and rollback on error. Handles column mapping (CSV → DB), MD5 dedup, atomicity, and error recovery. Used when loading scraped jobs into database, testing ingest pipeline, or recovering from partial ingests.
---

# Skill: anofm-ingest-run

**Domain:** CSV→PostgreSQL ingestion, schema mapping, dedup  
**Target:** raspi (192.168.100.20:5432/anofm_db)  
**Input:** CSV file path, optional dry-run mode  
**Output:** rows inserted/updated/skipped, dedup key, transaction status, ingest report

---

## When to Use

- **After scraper:** "Ingest the latest CSV into the database"
- **Recovery:** "Re-ingest this specific CSV (with dedup protection)"
- **Testing:** "Test ingest logic without committing (dry-run)"
- **Debugging:** "Why did ingest fail? What columns don't match?"

---

## How It Works

### Step 1: Pre-flight Validation
```bash
ssh tudor@192.168.100.20

# Check CSV exists
test -r /opt/ACTIVE/ANOFM_DATA/csv/[latest_csv]

# Check DB reachable
psql anofm_db -c "SELECT 1;"

# Check target table exists
psql anofm_db -c "\d ij_jobs"
```

### Step 2: Column Mapping
```
CSV columns → DB columns:
job_id → source_job_id
company → company
title → job_title
city → location
positions_available → positions_available
salary → salary (nullable)
job_url → job_url
source → source (always 'anofm')
posted_date → posted_date (nullable)
[all fields] → content_hash (MD5 for dedup)
```

### Step 3: Dedup Strategy
**Primary key:** MD5 hash of [job_id, company, title, city, salary, job_url]
```sql
INSERT INTO ij_jobs (source_job_id, company, job_title, location, ..., content_hash, uploaded_at)
VALUES (?, ?, ?, ?, ..., ?, NOW())
ON CONFLICT (content_hash) DO NOTHING;
```

### Step 4: Ingest Loop (Transactional)
```python
BEGIN;

for row in csv.DictReader(f):
    # Map columns
    mapped = {
        'source_job_id': row['job_id'],
        'company': row['company'],
        'job_title': row['title'],
        'location': row['city'],
        'positions_available': int(row['positions_available']),
        'salary': float(row['salary']) if row['salary'] else None,
        'job_url': row['job_url'],
        'source': 'anofm',
        'content_hash': md5(json.dumps(row)).hexdigest(),
    }
    
    # Execute insert
    cursor.execute(INSERT_STMT, mapped)

COMMIT;  # If no errors
```

### Step 5: Post-ingest Validation
```bash
psql anofm_db -c "SELECT COUNT(*) FROM ij_jobs WHERE source='anofm' AND uploaded_at >= '[start_time]';"

# Sample check (first 5 rows inserted)
psql anofm_db -c "SELECT company, job_title, location FROM ij_jobs WHERE source='anofm' ORDER BY uploaded_at DESC LIMIT 5;"
```

### Step 6: Generate Report
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
  "runtime_seconds": 25,
  "recommendation": "PASS to campaign"
}
```

---

## Error Scenarios

| Scenario | Handling |
|----------|----------|
| CSV not found | FAIL. Check latest CSV path. |
| DB unreachable | FAIL. Check PostgreSQL service on raspi. |
| Column mismatch | FAIL. Show expected vs actual columns. Requires schema fix. |
| Duplicate key violations | LOG & SKIP (expected). Continue ingest. |
| Data type error (e.g., positions_available is 'abc') | LOG & SKIP row. Show sample errors. |
| Transaction timeout | ROLLBACK. Report infrastructure issue. |
| > 5% rows skipped due to errors | FAIL. Investigate error pattern. |

---

## Dry-run Mode

```bash
# Read CSV, perform mapping, show what WOULD be inserted
# Do NOT execute INSERT/UPDATE/DELETE
# Do NOT modify database

python3 /opt/ACTIVE/INTERJOB/ingest_anofm.py \
  --csv /opt/ACTIVE/ANOFM_DATA/csv/[latest].csv \
  --dry-run \
  --limit 10  # Show first 10 rows
```

Output (dry-run):
```
Would insert: 10 rows
Would update: 0 rows
Would skip: 0 rows
Schema mapping:
  CSV job_id → DB source_job_id ✓
  CSV company → DB company ✓
  CSV title → DB job_title ✓
  ...
```

---

## Command Examples

```bash
# Full ingest (live)
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/INTERJOB && python3 ingest_anofm.py"

# Dry-run (no DB changes)
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/INTERJOB && python3 ingest_anofm.py --dry-run"

# Specific CSV
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/INTERJOB && python3 ingest_anofm.py --csv /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_2026-06-21_082530.csv"

# Check results
ssh tudor@192.168.100.20 "psql anofm_db -c \"SELECT COUNT(*) FROM ij_jobs WHERE source='anofm';\""
```

---

## Known Issues & Workarounds

**Schema mismatch (raspi vs raspibig):**
- Raspi's anofm_db column names differ from raspibig's interjob_master
- Workaround: Use pre-synced data (already done: 16,429 rows) OR fix column mappings in ingest script
- If ingest fails due to schema: skip timer, rely on manual pre-sync

**Dedup strategy:**
- Uses MD5 hash of full row to prevent duplicate sends
- If job is re-posted (same company, different positions), treats as new row
- If job is updated (same job_id, higher positions), update positions only

---

## Performance Notes

- Typical run: 7,222 rows ingested in <30 sec
- Bottleneck: network latency (SSH) or DB disk I/O
- If > 5 min: check DB indexes or consider batch processing
