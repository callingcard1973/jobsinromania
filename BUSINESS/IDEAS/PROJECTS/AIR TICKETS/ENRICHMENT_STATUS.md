# Email Enrichment — Complete Status (2026-04-12)

## THE BIG NUMBER

**72,390,062** rows in `companies` table au website dar NU au email.
Plus milioane in alte tabele. Plus 9.4M in CSV-uri locale.

## SCRAPING RESULTS (today)

| Job | Total | Emails Found | Rate | Status |
|-----|-------|-------------|------|--------|
| Romania agencies | 2,968 | 861 API/B2B, 70 GDS | scraped services | DONE |
| OSM hotels EU | 9,651 | **3,994** | **41%** | DONE |
| France hotels | 21,155 | running | ~40% expected | RUNNING |
| Wikidata hotels | 30,000 | running | ~20% expected (worldwide) | RUNNING |

## DB TABLES — Website Without Email

| Table | Total Rows | Has Website | Has Email | **GAP** |
|-------|-----------|------------|-----------|---------|
| **companies** | 208,499,297 | 72,490,530 | 441,461 | **72,390,062** |
| companies_clean | 40,800,552 | pending | pending | pending |
| master_romania | 8,867,059 | pending | pending | pending |
| ro_companies_onrc | 4,161,028 | pending | pending | pending |
| ted_winners | 1,569,378 | 544,714 | 1,568,812 | **0** (complete!) |
| pl_companies | 1,133,107 | **1,137,849** | NO EMAIL COL | **1,137,849** |
| france_contacts | 529,754 | **529,676** | NO EMAIL COL | **529,676** |
| se_companies | 358,321 | **358,349** | NO EMAIL COL | **358,349** |
| be_companies | 106,315 | **106,288** | NO EMAIL COL | **106,288** |
| fi_companies | 61,454 | **61,454** | NO EMAIL COL | **61,454** |
| at_companies | 17,259 | **17,199** | NO EMAIL COL | **17,199** |
| dk_companies | 12,618 | **12,618** | NO EMAIL COL | **12,618** |
| hu_companies | 10,840 | **10,840** | NO EMAIL COL | **10,840** |
| it_companies | 4,503 | **4,503** | NO EMAIL COL | **4,503** |
| es_companies | 3,727 | **3,727** | NO EMAIL COL | **3,727** |
| is_companies | 198 | **198** | NO EMAIL COL | **198** |
| pt_companies | 157 | **157** | NO EMAIL COL | **157** |
| **SUBTOTAL no-email-col** | | **2,242,858** | | **2,242,858** |
| **GRAND TOTAL** | | **74,632,920** | | **~74.6M** |

**NOTE:** 12 tables above need `ALTER TABLE ADD COLUMN email TEXT` before enrichment pipeline can fill them.

## INTERNAL ENRICHMENT (zero scraping, zero cost)

### 1. enriched_email backfill — 23,562 instant
```sql
UPDATE companies SET email = enriched_email
WHERE (email IS NULL OR email = '' OR email NOT LIKE '%@%')
AND enriched_email IS NOT NULL AND enriched_email LIKE '%@%';
```

### 2. Cross-DB website match — potentially hundreds of thousands
Match website domains across tables, copy email from table that has it.

### 3. Domain extraction — tens of thousands  
Extract domain from known emails, match to websites in other tables.

### 4. Duplicate CUI fill — thousands
Same company (by CUI/VAT) in multiple tables, one has email.

### 5. ANAF CUI lookup — ~4M Romanian companies
Free government API, returns official data.

## AUTOMATED PIPELINE (deployed)

**5 cron jobs nightly on raspibig (staggered 21:00-02:00):**
- 19 DB tables, 5,000 per table per night
- Reports to Node-RED at POST /enrichment-status
- State tracking in `/opt/ACTIVE/FLIGHTS/enrichment/state.json`

At 5,000/table/night × 19 tables = 95,000 websites scraped per night.
At 41% email find rate = ~39,000 new emails per night.
72M gap / 39K per night = ~5 years to complete all.

**To accelerate:** increase batch to 20,000 and workers to 40 = ~156,000 new emails/night = ~1.3 years.

## LOCAL CSV FILES — Website Without Email (3.19M URLs)

537 CSV files, top sources:

| CSV | URLs | What |
|-----|------|------|
| EURES Sweden contacts | 498,080 | Swedish employers |
| EURES Norway contacts | 297,039 | Norwegian employers |
| EURES Finland contacts | 135,791 | Finnish employers |
| EURES Unknown contacts | 104,129 | EU employers unclassified |
| EURES Germany contacts | 89,960 | German employers |
| EURES master_contacts | 50,991 | All EURES employers |
| EURES Poland contacts | 46,249 | Polish employers |
| Norway MASTER | 33,478 | Norwegian companies |
| Denmark companies | 21,432 | Danish companies |
| CORDIS organizations | 21,203 | EU R&D organizations |
| EURES Denmark | 11,993 | Danish employers |
| Agricultura ecologica | 13,521 | Romanian eco farms |
| TED winners 2023 | 9,675 | EU procurement winners |
| Romania firme | 9,297 | Romanian companies |

**EURES total: ~1.2M EU employer websites, zero email — highest value for recruitment.**

## GRAND TOTAL — ALL SOURCES

| Source | Website without email |
|--------|---------------------|
| DB companies table | 72,390,062 |
| DB companies_clean | 5,233,080 |
| DB 12 country tables (no email col, now added) | 2,242,858 |
| DB other tables | 35,299 |
| Local CSVs (537 files) | 3,191,034 |
| **TOTAL** | **~83,092,333** |

At 41% email find rate = **~34 million potential emails.**

## FILES

| File | Location |
|------|----------|
| Enrichment pipeline | `/opt/ACTIVE/FLIGHTS/email_enrichment_pipeline.py` |
| Email scraper | `/opt/ACTIVE/FLIGHTS/scrape_emails_from_websites.py` |
| Agency scraper | `/opt/ACTIVE/FLIGHTS/scrape_agencies.py` |
| OSM results | `/opt/ACTIVE/FLIGHTS/TOURISM_DATA/osm/osm_hotels_enriched.csv` |
| France results | `/opt/ACTIVE/FLIGHTS/TOURISM_DATA/france_hotels_enriched.csv` (running) |
| Wikidata results | `/opt/ACTIVE/FLIGHTS/TOURISM_DATA/wikidata/wikidata_hotels_enriched.csv` (running) |
| Node-RED flow | Tab "Email Enrichment", POST/GET /enrichment-status |
| Cron logs | `/opt/ACTIVE/FLIGHTS/logs/enrichment_cron.log` |
| Skill | `C:\Users\apami\.claude\skills\zero-token-website-scraper.md` |
