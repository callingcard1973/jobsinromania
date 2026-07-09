# ISC — Construction Inspection Companies & Professionals Scraper

ISC = Inspecția de Stat în Construcții (State Construction Inspection Authority).
Authorizes and monitors construction professionals and companies performing technical inspections & management.

## What We Have

Data: ~23,000 authorized construction professionals and companies across three categories.
Source: ISC public portal — downloadable Excel registries.

## Data by Type

| Category | Type | Count | Description |
|----------|------|-------|-------------|
| **Diriginti de santier** | PF (individuals) | ~17,500 | Construction site managers/supervisors — must oversee all Romanian construction projects |
| **RTE** | PF (individuals) | ~4,900 | Responsabili Tehnici cu Executia — Technical execution managers |
| **Laboratoare** | PJ (companies) | ~721 | Authorized testing labs (material testing, soil analysis, structural testing) |
| **TOTAL** | Mixed | **~23,100** | | 

## Data Structure

### Diriginti de Santier
- `name` — full name (PF)
- `nr_autorizatie` — authorization number
- `data_emitere` — date issued
- `domenii` — domains/specialties (construction types)
- `email` — contact email
- `telefon` — phone number

### RTE (Responsabili Tehnici cu Executia)
- `name` — full name (PF)
- `nr_autorizatie` — authorization number
- `data_emitere` — date issued
- `valabilitate` — expiry date
- `domenii` — domains/specialties (HTML-encoded, needs cleaning)
- `email` — contact email
- `telefon` — phone number

### Laboratoare (Legal Entities)
- `cui` — fiscal code (extracted from company name pattern: "COMPANY NAME (12345678)")
- `denomination` — company name
- `nr_autorizatie` — authorization number
- `data_emitere` — date issued
- `valabilitate` — expiry date
- `domenii` — testing specialties
- (email/phone — typically missing, needs enrichment from ONRC)

## Primary Source

**ISC Public Portal:** https://isc.gov.ro/
- Excel export files available (no login required)
- Files updated regularly as authorizations are granted/renewed
- Direct download URLs (verify current state at portal)

## Scraping Strategy

1. **Download Excel files** from ISC portal:
   - `isc_diriginti.xlsx` — all site managers (PF)
   - `isc_rte.xlsx` — all technical managers (PF)
   - `isc_laboratoare.xlsx` — all labs (PJ)

2. **Parse with openpyxl** — extract cell values, skip headers

3. **Clean data:**
   - Extract CUI from lab company names: "COMPANY (12345678)" → CUI=12345678
   - Strip HTML tags from domenii field (RTE list has HTML)
   - Normalize phone/email formats

4. **Enrich PJ (labs) with ONRC emails:**
   - Match by CUI against `companies_clean` table (laptop DB)
   - Fill missing email/phone from ONRC data

5. **Consolidate** all three lists into single CSV + DB table

## Usage

```bash
cd D:\MEMORY\BUSINESS\IDEAS\ISCIR\ISC
python CODE/scrape_isc.py
# Output: DATA/isc_diriginti_raw.csv, DATA/isc_rte_raw.csv, DATA/isc_laboratoare_raw.csv

# Or consolidated:
python CODE/scrape_isc.py --consolidate
# Output: DATA/isc_constructii_all.csv
```

To import to raspibig:
```bash
scp DATA/isc_*.csv tudor@192.168.100.21:/tmp/
ssh tudor@192.168.100.21 'python3 /tmp/import_isc.py'
```

## Dependencies

```
pip install openpyxl requests pandas psycopg2-binary
```

## Campaign Potential

23K construction professionals + companies = high-intent industrial audience.
Outreach targets:
- Job postings (construction engineers, technicians, supervisors)
- Professional training/certification upgrades
- Software: construction management platforms, document management
- EU tender alerts (SICAP construction contracts)
- Equipment leasing (testing equipment for labs)

## Files

```
ISC/
├── CLAUDE.md
├── CODE/
│   ├── scrape_isc.py                   (new — download & parse Excel)
│   └── import_isc.py                   (existing — import to raspibig)
└── DATA/
    ├── isc_diriginti.xlsx              (source, site managers)
    ├── isc_rte.xlsx                    (source, technical managers)
    ├── isc_laboratoare.xlsx            (source, labs)
    ├── isc_diriginti_raw.csv           (extracted output, ~17.5K rows)
    ├── isc_rte_raw.csv                 (extracted output, ~4.9K rows)
    ├── isc_laboratoare_raw.csv         (extracted output, ~721 rows)
    └── isc_constructii_all.csv         (consolidated, ~23K rows)
```

## Update Cadence

ISC updates registries monthly as new authorizations are issued and old ones expire.
Re-scrape monthly. Download fresh Excel files from ISC portal, compare row counts to detect updates.

## Contact

- ISC Portal: https://isc.gov.ro/
- ISC Email: contact form on website
