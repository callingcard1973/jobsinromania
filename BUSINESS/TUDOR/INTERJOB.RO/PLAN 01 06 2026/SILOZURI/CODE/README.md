# SILOZURI Data Pipeline Scripts

Reusable Python scripts for extracting, parsing, and enriching Romanian agricultural storage facility data from MADR sources.

## Scripts

### 1. extract_silos_madr.py
**Purpose:** Download all 43 county MADR Excel files and parse into master CSV.

**Usage:**
```bash
python extract_silos_madr.py
```

**Input:** 43 Excel files from MADR (downloaded via curl User-Agent bypass)
**Output:** `silos_master.csv` (457 facilities)

**Key features:**
- Curl + User-Agent to bypass WAF
- openpyxl for Excel parsing
- Handles multi-row facility records
- Phone normalization to E.164 format (+40...)

### 2. parse_madr.py
**Purpose:** Parse individual or batch Excel files with flexible column name detection.

**Usage:**
```bash
cd DATA/
python ../parse_madr.py
```

**Input:** *.xlsx files in DATA/ directory
**Output:** CSV with extracted facility data

**Key features:**
- Auto-detects column headers (denumire, name, phone, telefon, etc.)
- Cleans company names
- Dedupes by email+phone

### 3. enrich_silos.py
**Purpose:** Enrich facilities with ANAF company registry data (CUI, status, activity).

**Usage:**
```bash
python enrich_silos.py
```

**Input:** `silos_master.csv`
**Output:** `silos_enriched.csv` (adds cui, company_status, anaf_activity, anaf_address)

**Note:** ANAF API currently returning 0 matches; requires alternative approach (web scraping or local ANAF data).

### 4. final_interjob_match.py
**Purpose:** Cross-reference facilities against InterJob database on raspibig (ij_companies, fw_companies, etc.).

**Usage:**
```bash
python final_interjob_match.py
```

**Input:** `silos_enriched.csv`
**Output:** `silos_final.csv` (adds in_interjob YES/NO flag)

**Note:** Requires SSH access to raspibig (192.168.100.21, user tudor, password REDACTED).

## Data Files

- **SILOS_CONSOLIDATED_MASTER.csv** — 455 facilities (combined authorized + licensed), deduplicated, with contact info and enrichment
- **silos_licensed_operators.csv** — 15 major MADR-licensed operators (reference)

## Contact Info Coverage

- **Phone:** 408/455 (90%)
- **Email:** 11/455 (2%)
- **Both:** 11/455 (2%)

## Next Steps

1. **Email campaign:** Use phone/email for Brevo cold outreach
2. **Web enrichment:** Extract websites, social media for top 50 operators
3. **Financial data:** Append revenue/employee size from BPI/ONRC
4. **Geographic:** Add lat/lon, distance to major markets
5. **Capacity analysis:** Correlate capacity with regional production

## Technical Notes

- **Rate limiting:** 0.1-0.3s delay between API/ANAF requests
- **Phone normalization:** RO +40 prefix, remove formatting chars
- **Dedup key:** (lower(email), phone) to avoid phantom entries
- **Archive strategy:** Move intermediate files to ARCHIVE/ after consolidation
