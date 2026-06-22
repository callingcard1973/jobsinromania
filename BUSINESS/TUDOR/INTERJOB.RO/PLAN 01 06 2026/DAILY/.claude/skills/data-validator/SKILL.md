---
name: daily-data-validator
description: Validate ANOFM job counts, EURES CSV integrity, sector distribution, translation API before daily roundup publishing. Abort if counts are zero or data malformed.
---

# Daily Data Validator Skill

## When to Use
Run this BEFORE publishing any daily roundup article. Ensures data quality and catches infrastructure issues (DB down, EURES scraper failed, translation API unavailable) before wasting time generating content.

## Validation Steps

### 1. ANOFM Database Query
```bash
psql -h localhost -U tudor -d interjob_master -c "
SELECT COUNT(*) as total_jobs FROM ij_jobs 
WHERE source='anofm' AND status='active';"
```
- **Expected:** > 2000 jobs (production baseline ~5,000)
- **Warn if:** 1,500-2,000 (low but acceptable)
- **FAIL if:** < 1,000 (anomaly, likely data issue)
- **FAIL if:** 0 (DB down or scraper crashed)

### 2. Sector Distribution (Top 7)
```bash
psql -h localhost -U tudor -d interjob_master -c "
SELECT sector, COUNT(*) as cnt 
FROM ij_jobs WHERE source='anofm' AND status='active'
GROUP BY sector ORDER BY cnt DESC LIMIT 7;"
```
- Extract sector names and job counts
- Check: no sector > 90% of total (anomaly detection)
- Validate: all sectors have string values (null → 'altul')

### 3. EURES CSV Validation
For each CSV in `/opt/ACTIVE/SCRAPER_DATA/csv/EURES/{country}_{country}_contacts_50.csv`:

```bash
# Check file exists and is readable
ls -l /opt/ACTIVE/SCRAPER_DATA/csv/EURES/Norway/Norway_contacts_50.csv

# Check column headers
head -1 /opt/ACTIVE/SCRAPER_DATA/csv/EURES/Norway/Norway_contacts_50.csv | grep -E "job_title|fingerprint"

# Count rows (should be > 50)
wc -l /opt/ACTIVE/SCRAPER_DATA/csv/EURES/Norway/Norway_contacts_50.csv

# Check UTF-8 encoding
file -b /opt/ACTIVE/SCRAPER_DATA/csv/EURES/Norway/Norway_contacts_50.csv
```
- **FAIL if:** file missing (country folder exists but .csv doesn't)
- **FAIL if:** missing `job_title` or `fingerprint` column
- **WARN if:** < 50 rows (scraper may have underperformed)
- **WARN if:** not UTF-8 encoded (will cause translation errors later)

### 4. EURES Deduplication Check (Python)
```python
import csv
from collections import defaultdict

seen = set()
eures_total = 0
by_country = defaultdict(int)

for country in ["Norway", "Denmark", "Sweden", "Finland", "Germany", "Netherlands", "France"]:
    path = f"/opt/ACTIVE/SCRAPER_DATA/csv/EURES/{country}/{country}_contacts_50.csv"
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            fprint = row.get("fingerprint") or row.get("job_id")
            if fprint and fprint in seen:
                continue
            if fprint:
                seen.add(fprint)
            eures_total += 1
            by_country[country] += 1

print(f"EURES total unique: {eures_total}")
for country, cnt in sorted(by_country.items()):
    print(f"  {country}: {cnt}")
```
- **WARN if:** EURES total = 0 (but don't fail — can publish RO-only)
- **Validate:** dedup works correctly (no duplicates in combined set)

### 5. Translation API Sanity Check
```python
from deep_translator import GoogleTranslator

try:
    test = GoogleTranslator(source="auto", target="ro")
    result = test.translate("test job title")
    if not result or len(result) < 3:
        print("WARN: Translation returned empty or malformed")
    else:
        print("OK: Translation API reachable and working")
except Exception as e:
    print(f"WARN: Translation API unreachable: {e}")
```
- **WARN if:** API unreachable (content generator will handle retries)
- **OK if:** test translation works

### 6. CSV File Age Check
```bash
find /opt/ACTIVE/SCRAPER_DATA/csv/EURES -name "*.csv" -mtime +7 -print
```
- **WARN if:** any CSV > 7 days old (may indicate scraper failure)
- **WARN if:** no CSVs updated in last 24h (usual pattern is daily updates)

## Output Format

### Success (all checks pass)
```
✅ ANOFM: 5,795 active jobs
   ├─ constructii: 1,240
   ├─ it: 850
   ├─ vanzari: 620
   └─ ... (7 total)

✅ EURES: 4,320 unique jobs
   ├─ Norway: 892
   ├─ Denmark: 634
   └─ ... (7 countries)

✅ Translation API: Ready
✅ All CSV files: Valid UTF-8, updated today

📊 Ready to publish!
```

### Warnings (proceed with caution)
```
⚠️  EURES Denmark CSV is 8 days old
⚠️  ANOFM job count: 1,850 (below normal ~5K)
    → Proceed but flag for manual review

✅ All HARD checks passed
📊 Ready to publish (monitor for anomalies)
```

### Failure (ABORT)
```
❌ ANOFM query returned 0 jobs
   Reason: Database may be down or scraper failed
   Action: Check ij_jobs table and ANOFM source status
   Command: SELECT COUNT(*), source FROM ij_jobs GROUP BY source;

   ABORT: Skipping roundup for today
```

## Return Data to Orchestrator

```json
{
  "status": "valid" | "valid_with_warnings" | "invalid",
  "anofm_total": 5795,
  "anofm_by_sector": {
    "constructii": [
      {"title": "Electrician", "city": "Bucharest", "salary_min": 3000, "salary_currency": "RON"},
      ...
    ]
  },
  "anofm_count_sector": {
    "constructii": 1240,
    "it": 850,
    ...
  },
  "eures_total": 4320,
  "eures_by_country": {
    "Norway": [
      ("Senior Developer", "Oslo"),
      ("Nurse", "Bergen"),
      ...
    ]
  },
  "warnings": [
    "EURES Denmark CSV is 8 days old"
  ],
  "error": null,
  "validation_timestamp": "2026-06-23T09:00:00Z"
}
```

Or on failure:

```json
{
  "status": "invalid",
  "error": "ANOFM query returned 0 jobs — database may be down",
  "reason": "HARD_FAIL_ZERO_JOBS",
  "action": "ABORT: Check DB connectivity and ij_jobs table",
  "validation_timestamp": "2026-06-23T09:00:00Z"
}
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "psql: could not translate host name" | DB host incorrect | Check `localhost` vs IP; verify raspibig DB running |
| "role 'tudor' does not exist" | DB user wrong or password expired | Re-check .pgpass file; verify `tudor` user in DB |
| "ERROR: relation 'ij_jobs' does not exist" | DB or table name wrong | Verify table exists: `psql ... -c "\dt ij_jobs"` |
| "EURES/Norway CSV not found" | Scraper failed or path wrong | Check `/opt/ACTIVE/SCRAPER_DATA/` exists; verify EURES scraper ran |
| "ImportError: No module named 'deep_translator'" | Python dependency missing | Install: `pip install deep-translator` on raspibig |

## Success Criteria

✅ ANOFM count > 0  
✅ At least 1 EURES country CSV exists and is valid  
✅ No data type errors (all counts are integers, all titles are strings)  
✅ Translation API responds  
✅ All sector fields populated (null → 'altul')
