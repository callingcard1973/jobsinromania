# PHONE CAMPAIGN

Phone outreach to Romanian employers actively hiring, sourced from ANOFM job portal.
Goal: place workers, generate solonet orders.

## What This Is

- Extract phone numbers from ANOFM daily scrape (raspibig)
- Build anonymous job catalogs (dark-theme HTML → PDF)
- Call employers, pitch worker placement service
- Contact: **Yohan** · **+40 723 068 733**

## Directory Structure

| Dir | What |
|-----|------|
| `CODE/` | Python scripts |
| `DATA/` | Extracted phone/contact CSVs |
| `CATALOGS/YOHAN/` | Yohan's HTML catalogs (print to PDF) |

## Scripts (`CODE/`)

| Script | What |
|--------|------|
| `extract_anofm_phones.py` | Pull phones from all ANOFM CSVs on raspibig → normalized E.164 CSV |
| `generate_catalog.py` | CSV → dark-theme HTML catalog, RO→EN job titles, anonymous |

## Data Pipeline

1. **ANOFM scraper** runs 3×/day on raspibig → `/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/DOCKER/PROGRAMS/`
2. **extract_anofm_phones.py** runs daily at 13:30 (cron raspibig) → `/opt/ACTIVE/PHONE_CAMPAIGN/anofm_phones_YYYYMMDD.csv`
3. SCP latest to `DATA/` on laptop when needed
4. Run `generate_catalog.py` → `CATALOGS/` HTML → open in browser → Print → PDF

## Data Stats (2026-04-16)

- 77 CSV files · 32 days of data
- **8,311 unique companies** from ANOFM
- **8,103 valid Romanian phones** (+40XXXXXXXXX)
- 32 sectors · top: Construction, Production, Restaurants, Retail, Transport

## Grab latest data from raspibig

```bash
scp tudor@192.168.100.21:/opt/ACTIVE/PHONE_CAMPAIGN/anofm_phones_$(date +%Y%m%d).csv "D:/MEMORY/PHONE CAMPAIGN/DATA/"
```

## Rules

- Employer names **never shown** in catalogs (anonymous)
- Job titles translated RO → EN
- Apply always via WhatsApp: +40 723 068 733 (Yohan)
- Data source label: "public labor market data" (never mention ANOFM)
- Catalog output: `CATALOGS/` only
