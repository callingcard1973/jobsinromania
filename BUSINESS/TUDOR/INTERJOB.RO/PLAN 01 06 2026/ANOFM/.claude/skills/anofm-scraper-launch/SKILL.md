---
name: anofm-scraper-launch
description: Launch ANOFM job scraper on raspi (192.168.100.20), validate CSV output, return schema + row counts. SSH-based execution via plink. Requires RASPI_PASSWD environment variable. Used when running scraper manually, testing scraper logic, or verifying scraper health.
---

# Skill: anofm-scraper-launch

**Domain:** ANOFM job scraping, CSV generation, output validation  
**Target:** raspi (192.168.100.20)  
**Input:** dry-run flag, output path (optional)  
**Output:** CSV path, row count, schema validation, pass/fail

---

## When to Use

- **Manual scraper runs:** "Run the scraper now and show me the CSV"
- **Diagnostic:** "Is the scraper working? Show me the last output."
- **Testing:** "Test the scraper with 5 pages only"
- **Validation:** "Verify the CSV structure is correct"

---

## Prerequisites

**Environment variable required:**
```bash
export RASPI_PASSWD=<password>   # Set from .env or secrets manager
# Do NOT hardcode password in commands — always use $RASPI_PASSWD
```

## How It Works

### Step 1: SSH to Raspi
```bash
plink -batch -pw "$RASPI_PASSWD" tudor@192.168.100.20
cd /opt/ACTIVE/INTERJOB
```

### Step 2: Run Scraper
```bash
python3 anofm_scraper.py --csv --output /opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_[timestamp].csv
# Alternative (test mode):
python3 anofm_scraper.py --csv --limit 5 --output /tmp/test.csv
```

### Step 3: Validate Output
```bash
# Check file exists
test -f [csv_path] && echo "OK" || echo "FAIL"

# Row count
wc -l [csv_path]  # Expected: 2,000–15,000

# Column check
head -1 [csv_path] | tr ',' '\n' | head -20
```

### Step 4: Schema Validation
Verify columns:
```
✓ job_id (numeric)
✓ company (string)
✓ title (string)
✓ city (string)
✓ positions_available (numeric)
✓ salary (nullable)
✓ job_url (string)
✓ source (always 'anofm')
```

### Step 5: Return Results
```json
{
  "status": "SUCCESS",
  "csv_path": "/opt/ACTIVE/ANOFM_DATA/csv/anofm_jobs_2026-06-21_082530.csv",
  "row_count": 7222,
  "expected_range": [2000, 15000],
  "columns_valid": true,
  "runtime_seconds": 480,
  "recommendation": "CSV ready for ingest"
}
```

---

## Error Scenarios

| Scenario | Handling |
|----------|----------|
| SSH fails | Retry once with plink. Report connection issue. |
| Scraper exits with error | Show stderr. Check ANOFM API status. |
| CSV is `.tmp` (incomplete) | Wait 30 sec, retry. File may be writing. |
| Row count < 2,000 | Alert (ANOFM API may be down or rate-limited). |
| Row count > 15,000 | Alert (possible pagination loop issue). |
| Missing columns | CSV corrupted. Rerun scraper. |

---

## Command Examples

```bash
# Standard run (full scrape)
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/INTERJOB && python3 anofm_scraper.py --csv --output /opt/ACTIVE/ANOFM_DATA/csv/test_$(date +%s).csv"

# Quick test (5 pages)
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/INTERJOB && python3 anofm_scraper.py --csv --limit 5 --output /tmp/test.csv && wc -l /tmp/test.csv"

# Check latest CSV
ssh tudor@192.168.100.20 "ls -lt /opt/ACTIVE/ANOFM_DATA/csv/*.csv | head -3"
```

---

## Notes

- Scraper typically takes 8–10 minutes for full run (85 pages, ~7,200 rows)
- Test mode (--limit 5) takes ~1 minute
- CSV is written with atomic rename (os.replace), so no partial files
- Dedup by job_id handles scraper re-runs (safe to run multiple times)
- Column order may vary, but all required columns must be present
