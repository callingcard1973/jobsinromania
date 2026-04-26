# ANCPI — Authorized Surveyors & Property Experts

ANCPI = Agenția Națională de Cadastru și Publicitate Imobiliară.
Data: authorized surveyors, property experts, valuers for cadastral work, property registration, land surveying.

## What We Have

| Data Source | Records | Description |
|-------------|---------|-------------|
| Autorizati JSON | 19,722 | ANCPI-authorized surveyors & experts (direct API) |

Source: https://www.ancpi.ro/aplicatii/getSurveyor/autorizati.json

## Data Structure

Columns extracted per person/entity:
- `denumire` — full legal name (person or company)
- `tip` — entity type (PF=person, PFA=sole trader, SRL=LLC, SA=corp, II=sole partnership, IF=family business, etc.)
- `judet` — county (Bucuresti, Cluj, Sibiu, etc.)
- `stare` — authorization status (Activ, Inactiv, Suspendat, etc.)
- `autorizatie` — ANCPI authorization number/code
- `categoria` — authorization category (surveyor, valuator, expert, etc.)
- `email` — contact email (enriched from ONRC/master_romania_companies)

## Usage

```bash
cd D:\MEMORY\BUSINESS\ISCIR\ANCPI
python CODE/scrape_ancpi.py
# Output: DATA/ancpi_autorizati.csv
# Also imports to raspibig DB: interjob_master.ancpi_autorizati
```

**Status (2026-04-27)**: The JSON API endpoint (https://www.ancpi.ro/aplikatii/getSurveyor/autorizati.json) returns HTTP 404.
ANCPI may have moved or deprecated this endpoint. Alternative: check https://www.ancpi.ro/en/autorizati/ for updated data access method or contact ANCPI (021) 317.31.62.

## Dependencies

```
pip install psycopg2-binary
```

## Campaign Potential

19,722 authorized surveyors & experts = construction/real estate professionals with formal credentials.
Subset has email addresses → outreach target for:
- Real estate agent networks (partner integrations)
- Construction project management tools
- EU grant consulting for property/infrastructure projects
- Recruitment for GIS/surveying technicians

## Business Angles

1. **Lead Gen** — SRL/SA firms with emails → B2B software sales (project mgt, CRM)
2. **Database Product** — clean list of cadastral professionals → vendable to law firms, architects, construction consulting
3. **Compliance Data** — track authorization status changes (Activ→Suspendat) = early warning system
4. **Sector Intelligence** — map surveyor distribution by county → underserved markets

## Files

```
ANCPI/
├── CLAUDE.md
├── CODE/
│   └── scrape_ancpi.py
└── DATA/
    └── ancpi_autorizati.csv    (19,722 rows, refreshed monthly)
```

## Update Cadence

ANCPI updates JSON endpoint regularly. Re-run scraper monthly (API is discoverable, not PDF-based).
No rate limiting observed. Check for status changes (Activ→Inactiv) as early signal.

## Technical Notes

- **Enrichment**: Looks up `denumire` in ONRC (on-disk PostgreSQL laptop DB @ localhost:5433)
- **Import**: SCPs CSV to raspibig, creates `ancpi_autorizati` table with indexes on judet, stare, email
- **Skips PF/PFA/II/IF**: Only enriches legal entities (SRL, SA, etc.) for email lookups
