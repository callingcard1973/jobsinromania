# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Scrape the full produsmontan.ro registry (RNPM) to build a structured database of all
Romanian "Produs Montan" certified producers, products, and contact info.

## Target Site

- **URL**: https://produsmontan.ro/
- **Authority**: ANZM (Agentia Nationala a Zonei Montane)
- **Content**: Product pages with producer name, CUI, product name, category, county,
  address, phone, email, certification date, decision number, QR code

## Existing Data (baseline for dedup)

- `../PRODUS MONTAN PRODUCATORI.csv` — 680 producers (email + URL), Jul 2023
- `../RNPM 10.07.2023.xlsx` — full RNPM export, Jul 2023
- `../DATE EXTRASE/rnpm email.csv` — 666 extracted emails

## Output Format

CSV with columns: producer_name, cui, product_name, category, county, address,
phone, email, certification_date, decision_number, rnpm_number, url, scraped_at

Save to: `rnpm_fresh_YYYY-MM-DD.csv`

## Technical Rules

- Follow `D:\MEMORY\CLAUDE.md` conventions (Unix style, max 250 lines/file, LF only)
- Python 3.12 (`C:\Users\apami\AppData\Local\Programs\Python\Python312\python.exe`)
- Use `requests` + `BeautifulSoup4` (produsmontan.ro is server-rendered HTML)
- Respect rate limits: minimum 2s delay between requests
- Include source URL and scrape timestamp in every row
- Deduplicate by CUI first, then by email
- Store results in PostgreSQL on raspibig (table: `produs_montan`) after CSV export

## Commands

```bash
# Run scraper
python scrape_produsmontan.py

# Import CSV to PostgreSQL
python import_produs_montan.py

# Compare with old data
python diff_rnpm.py --old ../PRODUS\ MONTAN\ PRODUCATORI.csv --new rnpm_fresh_*.csv
```

## Deploy

After local testing, deploy scraper to raspibig:
```bash
scp scrape_produsmontan.py tudor@192.168.100.21:/opt/ACTIVE/SCRAPERS/ROMANIA/
```
