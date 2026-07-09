# ANMDM — Medical Device Distributors & Importers

ANMDM = Agenția Națională a Medicamentului și a Dispozitivelor Medicale (NAMMDR).
Data: authorized distributors, importers, and representatives of medical devices in Romania.

## What We Have

| Registry | URL | Records | Description |
|----------|-----|---------|-------------|
| F1/F2 Medical Devices | dispozitive.anm.ro/f1f2-display | ~8,000+ | Class I-III device distributors & authorized reps |
| MDR Devices | dispozitive.anm.ro/f1mdr-display | ~4,000+ | Modern MDR regulation devices & operators |

Source: https://dispozitive.anm.ro/

## Data Structure

Columns extracted per company:
- `denumire` — full legal name (distributor/importer/authorized representative)
- `tip` — device category (F1, F2, MDR, IVDR, etc.)
- `localitate` — city
- `judet` — county
- `cui` — fiscal code (CUI, when available from enrichment)
- `email` — contact email (enriched from ONRC database)
- `sursa` — data source (anmdm)

## Usage

```bash
cd D:\MEMORY\BUSINESS\ISCIR\ANMDM
python CODE/scrape_anmdm.py
# Output: /opt/scrapers/anmdm_medical.csv
# Also imports to laptop DB: interjob_master.anmdm_medical
```

## Dependencies

```
pip install requests beautifulsoup4 psycopg2-binary
```

## Scraping Strategy

- Paginated search by letter (A-Z) on dispozitive.anm.ro
- Extract "Reprezentant autorizat" column from F1/F2 and MDR tables
- Dedup by `denumire` (lowercase)
- Enrich with CUI → email from ONRC mapping
- Store to PostgreSQL with unique constraint on `denumire`

## Campaign Potential

8,000+ medical device distributors = regulated healthcare/pharma professionals with compliance requirements.
Email-enriched subset targets:
- EU grant consulting (PNRR Component 11: healthcare digitalization)
- B2B software (inventory mgt, regulatory tracking, supplier management)
- Recruitment (supply chain managers, regulatory affairs, sales reps)
- Market research for pharma/medical device manufacturers

## Business Angles

1. **Lead Gen** — distributors with emails → B2B SaaS sales (compliance, inventory)
2. **Database Product** — official list of authorized importers → vendable to manufacturers, consultants
3. **Regulatory Intelligence** — track status changes, new authorizations = early market signal
4. **Sector Mapping** — distributor concentration by county → franchise/expansion opportunities

## Files

```
ANMDM/
├── CLAUDE.md
├── CODE/
│   └── scrape_anmdm.py
└── DATA/
    └── anmdm_medical.csv    (8,000+ rows, updated monthly)
```

## Update Cadence

ANMDM database updates regularly as new distributors are authorized or existing ones change status.
Re-run scraper monthly. Scraper automatically handles pagination and letter-based search.
No explicit rate limiting; SLEEP = 0.5s between requests.

## Technical Notes

- **Source**: Web scraping only (no official API); registry is public HTML table
- **Enrichment**: Optional CUI→email mapping from tmp_cui_email.csv (requires pre-loaded ONRC data)
- **Dedup**: Handles duplicate company names via UNIQUE constraint on `denumire`
- **Import**: Creates or updates `anmdm_medical` table with standard fields
- **Regex**: Extracts max pagination page number from links for comprehensive crawl
