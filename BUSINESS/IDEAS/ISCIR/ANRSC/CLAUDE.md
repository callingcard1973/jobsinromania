# ANRSC — Licensed Utility Operators

ANRSC = Agenția Națională pentru Reglementarea și Supravegherea Serviciilor Sociale
(National Authority for Social Services Regulation & Oversight)

Actually scrapes licensed **utility operators** (water, sanitation, lighting, transport):
Data: authorized service providers with contact information and license details.

## What We Scrape

| Service Type | PDF Source | Companies |
|--------------|------------|-----------|
| Apă (Water) | evidenta-licente-apa-*.pdf | ~200-250 |
| Salubrizare (Sanitation) | evidenta-licente-sal-*.pdf | ~150-200 |
| Iluminat (Lighting) | evidenta-licente-il-*.pdf | ~100-150 |
| Transport Local | evidenta-autorizatiilor-*.pdf | ~150-200 |
| **Total unique** | — | ~600-700 operators |

Source: https://www.anrsc.ro (WordPress site, PDFs in `/wp-content/uploads/`)

## Data Structure

Columns extracted per operator:
- `cui` — fiscal code (extracted from `cod_operator` column, e.g., BC27278646 → CUI=27278646)
- `denumire` — full legal name of operator
- `judet` — county (inferred from CUI prefix: BC=Bacau, BV=Brasov, etc.)
- `tip_serviciu` — service type: `apa`, `salubrizare`, `iluminat`, `transport`
- `nr_licenta` — license/authorization number from register
- `email` — enriched from laptop ONRC database (master_romania_companies)
- `sursa` — always "anrsc"

## Usage

```bash
cd D:\MEMORY\BUSINESS\IDEAS\ISCIR\ANRSC
python CODE/scrape_anrsc.py
# Output: DATA/anrsc_operatori.csv
# Also imports to raspibig:interjob_master.anrsc_operatori
```

## Dependencies

```
pip install pdfplumber psycopg2
```

## Strategy

1. **PDF download** (cached in DATA/)
   - 4 official ANRSC PDF registers (updated monthly)
   - Check if file exists locally; skip if cached

2. **Table extraction via pdfplumber**
   - Each PDF contains structured table rows
   - Row format: [index, cod_operator, denumire, contact?, nr_licenta, ...]

3. **CUI extraction from code**
   - Regex: `^([A-Z]{1,2})(\d+)$` (prefix = county, digits = CUI)
   - Prefix map: BC→Bacau, BV→Brasov, B→Bucuresti, etc.

4. **Email enrichment**
   - Query `interjob_master.master_romania_companies` on laptop (:5433)
   - Match by CUI; extract email if available

5. **Deduplication**
   - Key: (CUI, tip_serviciu) — same operator across multiple services counted once per service
   - Remove rows with empty CUI or malformed code

## Campaign Potential

Utility operators = regulated SMEs + municipal authorities with:
- HR needs: water technicians, sanitation supervisors, electrical maintenance
- Supply chain: equipment, chemicals, spare parts for utilities
- Infrastructure: EU PNRR funding for water/sanitation upgrades, smart metering
- Training: certifications for water & sanitation professionals

Target: ~600 operators × email enrichment (assume 40-60% valid emails) = 240-360 prospects

## Files

```
ANRSC/
├── CLAUDE.md
├── CODE/
│   └── scrape_anrsc.py
└── DATA/
    ├── anrsc_apa.pdf         (cached)
    ├── anrsc_salubrizare.pdf (cached)
    ├── anrsc_iluminat.pdf    (cached)
    ├── anrsc_transport.pdf   (cached)
    └── anrsc_operatori.csv   (final output)
```

## Update Cadence

ANRSC updates PDF registers quarterly (March, June, September, December).
Re-run scraper every 3 months or after confirmation of new PDF version.
Check: https://www.anrsc.ro (look for "Evidenta licente" links in footer or pages)

## Database Table

```sql
CREATE TABLE IF NOT EXISTS anrsc_operatori (
    id SERIAL PRIMARY KEY,
    cui TEXT,
    denumire TEXT NOT NULL,
    judet TEXT,
    tip_serviciu TEXT,
    nr_licenta TEXT,
    email TEXT,
    sursa TEXT DEFAULT 'anrsc',
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX(judet), INDEX(cui), INDEX(email)
);
```

## Notes

- PDF URLs contain dates; update PDFS list if links change
- CUI extraction from prefix depends on 2-letter + digits format; non-matching rows skipped
- Email enrichment requires laptop PostgreSQL (:5433) with `master_romania_companies` table
- All CSV and DB import assumes laptop + raspibig SSH access (scp + psql)
- Service type classification: `apa`, `salubrizare`, `iluminat`, `transport` (fixed by PDF source)
