# MEDICINA_MUNCII — Occupational Medicine Clinics Scraper

MEDICINA_MUNCII = Authorized occupational medicine (medicina muncii) clinics and companies providing health & safety monitoring services in Romania.

## What We Have

Data: ~16K authorized occupational health clinics (CAEN 8622 — Other professional, scientific and technical activities).
Source: ONRC (Registrul Comertului) companies with CAEN code 8622 + Ministry of Health (DSP) authorizations.

## Data Structure

Columns extracted per clinic:
- `cui` — fiscal code (CUI) — unique identifier for company
- `name` — company name (Romanian: denumire)
- `address` — full address (Romanian: adresa)
- `city` — city/municipality (Romanian: localitate)
- `county` — county code (Romanian: judet)
- `phone` — phone number
- `email` — contact email
- `website` — company website (if available)

## Primary Source

**ONRC Database (Registrul Comertului)** — Romanian Trade Register
- Companies with CAEN code **8622** (Occupational health/safety services)
- ~16K registered clinics and providers
- Includes contact info: CUI, name, address, phone, email, website

**Ministry of Health (Ministerul Sănătății)** — Occupational Medicine Authorization
- Each clinic must have DSP (county health department) authorization
- Authorization tracking: https://ms.ro/ (check Medical Inspectorate listings per county)
- Individual DSP websites: 42 DSP branches (one per county)

## Update Cadence

ONRC updates companies continuously (registrations, name changes, dissolutions).
Ministry of Health updates authorizations as clinics apply/expire.

**Re-scrape monthly** from ONRC. Check updated company count vs cached to detect changes.

## Scraping Strategy

1. **Option A (Current):** Export CAEN 8622 companies from laptop ONRC DB
   - Source: `companies_clean` table on laptop (postgres://127.0.0.1:5433)
   - Query: `SELECT * FROM companies_clean WHERE caen_main = '8622' AND country = 'RO'`
   - Output: CSV with cui, name, address, city, county, phone, email, website

2. **Option B (Future):** Direct ONRC API or DSP portal scraping
   - Check: https://www.onrc.ro/
   - Individual DSP sites: https://ms.ro/ → Inspectoratele de Sanatate Publica
   - Note: Some DSP sites have searchable registries, others publish PDFs

3. **Enrichment:** Cross-reference with `companies_clean` for emails and metadata

## Usage

```bash
cd D:\MEMORY\BUSINESS\IDEAS\ISCIR\MEDICINA_MUNCII
python CODE/scrape_medicina_muncii.py
# Output: DATA/medicina_muncii_raw.csv (CUI, name, address, city, county, phone, email, website)
```

To import to raspibig:
```bash
scp DATA/medicina_muncii_raw.csv tudor@192.168.100.21:/tmp/
ssh tudor@192.168.100.21 'python3 /tmp/import_medicina_db.py'
```

## Dependencies

```
pip install pandas psycopg2-binary requests
```

## Campaign Potential

16K occupational health clinics + companies = SMEs with mandatory employee health compliance.
Many have email addresses → outreach targets for:
- Job postings (occupational health doctors, nurses, technicians)
- Safety training services (EU WorkSafe regulations)
- Equipment procurement (medical diagnostic devices)
- PNRR grants (workplace digitization, occupational safety upgrades)

## Files

```
MEDICINA_MUNCII/
├── CLAUDE.md
├── CODE/
│   ├── scrape_medicina_muncii.py       (new — refresh data from ONRC)
│   └── import_medicina_db.py           (existing — import to raspibig)
└── DATA/
    ├── medicina_muncii_raw.csv         (extracted output, ~16K rows)
    └── medicina_muncii_raw.csv.bak     (previous version, archive)
```

## Contact

- Ministry of Health: https://ms.ro/
- ONRC (Trade Register): https://www.onrc.ro/
- DSP (County Health Dept) emails: <county>@ms.ro pattern
