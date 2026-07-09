# Unified DB Usage — Romanian Company Bankruptcy Risk Scanner

## Purpose
Scan public Romanian company data to identify businesses at risk of bankruptcy.
Leads for: recruitment services, banking/financial, existing campaigns.

## Files
- `db_helper.py` — DB connection, safe_query, ANAF API, bilant import
- `company_lookup.py` — Main CLI: query by CUI/name, risk score, formatted output

## Usage
```bash
# Lookup by CUI
python company_lookup.py 12345678

# Search by name
python company_lookup.py "CONSTRUCT"

# JSON output
python company_lookup.py 12345678 --json

# Import bilant data (one-time)
python db_helper.py --import-bilant
```

## Data Sources (all on raspibig)
- `interjob_master.companies` — 770K RO companies
- `interjob_master.faliment` — 222K insolvency records
- `interjob_master.tenders` — SEAP/TED procurement
- `bilant_years` table — Revenue/profit/employees 2023+2024
- ANAF v9 API — Live VAT status, address, phone

## Risk Score (0-100)
0-20 LOW | 21-50 MEDIUM | 51-75 HIGH | 76-100 CRITICAL
