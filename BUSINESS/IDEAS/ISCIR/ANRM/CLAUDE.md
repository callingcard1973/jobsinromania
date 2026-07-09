# ANRM — Mining Concessions & License Holders

ANRM = Agenția Națională pentru Resurse Minerale (National Agency for Mineral Resources)
Data: companies holding active mining licenses, permits, and concessions for resource extraction.

## What We Scrape

| Source | Data | Companies |
|--------|------|-----------|
| https://www.namr.ro/resurse-de-petrol/ | Oil/gas concessions, petroleum operators | ~500+ |
| https://www.namr.ro/resurse-minerale/ | Mineral extraction licenses, active permits | ~300+ |
| https://www.namr.ro/legea-co2/ | CO2 storage & reporting title holders | ~100+ |
| PDF registers & announcements | Archive pages, public tenders | varies |

Source base: https://www.namr.ro (National Agency website)

## Data Structure

Columns extracted per company:
- `cui` — fiscal code (CUI/NACE)
- `denumire` — full legal company name
- `tip_resursa` — resource type: `petrol`, `minier` (minerals), `co2`
- `nr_licenta` — license/permit number (ANRM reference)
- `localitate` — city/locality
- `judet` — county
- `email` — enriched from ONRC (Romania company DB)
- `sursa` — always "anrm"

## Usage

```bash
cd D:\MEMORY\BUSINESS\IDEAS\ISCIR\ANRM
python CODE/scrape_anrm.py
# Output: DATA/anrm_concesiuni.csv
# Also imports to raspibig:interjob_master.anrm_concesiuni
```

## Dependencies

```
pip install requests beautifulsoup4 psycopg2 urllib3
```

## Strategy

1. **HTML page scraping** (public ANRM website pages)
   - Extract PDF filenames → company names
   - Parse text for company patterns (SC, SRL, SA, OMV, ROMGAZ, PETROM, etc.)
   - Regex patterns for "Titular" company mentions

2. **WordPress sitemap crawl**
   - Fetch `/ro/wp-sitemap-posts-page-1.xml`
   - Filter for pages with: anunt, concurs, titular, licent, acord keywords
   - Parse each page for companies

3. **Email enrichment**
   - Match CUI → email from `/tmp/tmp_cui_email.csv` (optional, pre-populated)

## Campaign Potential

Mining/petroleum operators = capital-intensive industrial SMEs with legal compliance needs:
- Equipment & safety: mining equipment leasing, inspection services
- Personnel: mining engineers, safety supervisors, geologists
- Environmental: compliance reporting, waste management
- Finance: EU grants for green mining transition (Horizon Europe)

## Files

```
ANRM/
├── CLAUDE.md
├── CODE/
│   └── scrape_anrm.py
└── DATA/
    ├── *.pdf           (cached PDFs, re-check monthly)
    └── anrm_concesiuni.csv
```

## Update Cadence

ANRM updates PDF registers and permit announcements continuously (2-4 times/month).
Re-run scraper monthly or on-demand.
Check website for new permit announcements at: https://www.namr.ro/resurse-minerale/concurs-public-de-oferta-arhiva/

## Database Table

```sql
CREATE TABLE IF NOT EXISTS anrm_concesiuni (
    id SERIAL PRIMARY KEY,
    cui TEXT,
    denumire TEXT,
    localitate TEXT,
    judet TEXT,
    tip_resursa TEXT,
    nr_licenta TEXT,
    sursa TEXT DEFAULT 'anrm',
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(denumire, nr_licenta)
);
```

## Notes

- PDF URLs may change; check ANRM website for updated links
- Company names extracted from filenames may need manual cleanup (regex heuristic)
- Email enrichment depends on `tmp_cui_email.csv` availability (curated externally)
- Resource type classification: "petrol", "minier", "co2", "necunoscut" (unknown)
