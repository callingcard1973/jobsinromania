# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Produs Montan — Aggregation & Distribution

Build a database of Romanian "Produs Montan" certified producers from produsmontan.ro,
aggregate via **Gospodarii de Altadata** cooperative (CUI 51957925), sell to hypermarkets and export.

## Architecture

```
CODE/
├── produs_montan_parse.py    ← Core parser: RNPM Excel → producers dict (no DB dependency)
├── create_produs_montan_db.py ← Import parsed data → PostgreSQL (produs_montan_producers + _products)
├── generate_catalog.py       ← PostgreSQL → static HTML catalog (9 sector pages + index + judete)
├── deploy_catalog.py         ← Upload catalog/ to agroevolution.com via cPanel API
├── campaign_cos_legume.py    ← Email campaign template (preview only, send via raspibig)
├── publish_2026_post.py      ← WordPress post publisher
├── SCRAPER/
│   ├── scrape_produsmontan.py ← Live scraper: paginated listing + detail pages, resumable
│   └── scrape_state.json      ← Scraper resume state
└── SCRAPER AGRICULTURA ECOLOGICA/
    └── CODE/                  ← Organic agriculture registry scraper (separate dataset)

DATA/                          ← Source CSVs and Excel files (NEVER delete originals)
catalog/                       ← Generated HTML output (deployed to agroevolution.com/catalog/)
```

## Key Commands

```bash
# Parse RNPM Excel (dry run — no DB needed)
python CODE/create_produs_montan_db.py --dry-run

# Import to PostgreSQL on raspibig (DROPS and recreates tables)
python CODE/create_produs_montan_db.py

# Import specific Excel file
python CODE/create_produs_montan_db.py DATA/RNPM-02.03.2026.xlsx

# Generate HTML catalog from DB
python CODE/generate_catalog.py

# Deploy catalog to agroevolution.com
python CODE/deploy_catalog.py

# Scrape fresh data from produsmontan.ro (resumable, 2.5s delay)
cd CODE/SCRAPER && python scrape_produsmontan.py

# Preview email campaign stats
python CODE/campaign_cos_legume.py --preview
```

## Database Schema (PostgreSQL on raspibig)

DB: `interjob_master` | Host: `192.168.100.21` | User: `tudor` | Pass: `tudor`

```sql
-- produs_montan_producers (1,507 rows)
-- Columns: id, name, county, year_registered, addr_punct_lucru, addr_sediu,
--   siruta, decision, contact_raw, email, phone, emails[], phones[],
--   website_url, obs, is_traditional, has_qr, products[], categories[],
--   rnpm_numbers[], product_count, source, created_at

-- produs_montan_products (4,686 rows)
-- Columns: id, producer_id (FK), product_name, category, agrip_sector,
--   processing, rnpm_number, created_at
```

## Data Pipeline

1. **Source**: RNPM Excel (`DATA/RNPM-02.03.2026.xlsx`) — official registry export
2. **Parse**: `produs_montan_parse.py` reads Excel, normalizes 12 diacritics category variants → 8 ASCII categories, extracts emails/phones from contact field, classifies products into AGRIP sectors
3. **Enrich**: Cross-references 3 CSVs from `DATA/` (680 URLs, 666 emails, 651 phones)
4. **Import**: `create_produs_montan_db.py` inserts into PostgreSQL with per-product AGRIP classification
5. **Catalog**: `generate_catalog.py` queries DB, generates static HTML with search, county filter, WhatsApp CTA
6. **Deploy**: `deploy_catalog.py` uploads via cPanel Fileman API to `agroevolution.com/catalog/`

## AGRIP Product Classification

`produs_montan_parse.py:classify_product()` maps products to sectors + processing state:
- **Sectors**: DAIRY, HONEY, MEAT, FISH, FRESH_FV, PROCESSED_FV, BAKERY, HERBS, CEREALS, OTHER
- **Processing**: FRESH, MATURED, PROCESSED, NON_PERISHABLE
- Classification uses regex patterns on Romanian product names

## 8 Normalized Categories (from RNPM)

LAPTE SI PRODUSE DIN LAPTE (1,345) | PRODUSE VEGETALE (2,495) | PRODUSE APICOLE (611) |
CARNE SI PRODUSE DIN CARNE (179) | PESTE SI PRODUSE DIN PESTE (34) | OUA (17) |
PAINE, PRODUSE DE PANIFICATIE SI PATISERIE (4) | LEGUME-FRUCTE (1)

## Scraper Details (CODE/SCRAPER/)

- Iterates paginated listings on produsmontan.ro, fetches detail pages for new producers only
- Known producers get products added without re-fetching (saves requests)
- State persisted to `scrape_state.json` after each page — resume with `python scrape_produsmontan.py`
- Rate limit: 2.5s between requests, UA: `RNPM-Scraper/1.0`
- Output: `rnpm_producers_YYYY-MM-DD.csv`

## Deployment

- **Catalog live at**: https://agroevolution.com/catalog/
- **cPanel**: host `nl1-cl8-ats1.a2hosting.com:2083`, user `loaiidil`, token in `deploy_catalog.py`
- **WordPress**: agroevolution.com (2026 post at `/exprimam-interes-in-productie-2026/`)

## Cooperative & Contacts

- **Cooperative**: Gospodarii de Altadata (CUI 51957925)
- **Email**: cumparlegume@agroevolution.com
- **WhatsApp**: +33 7 51 17 13 56
- **Data source**: https://produsmontan.ro/ (RNPM — Registrul National al Produselor Montane)

## Business Context

- **Jan 2024 campaign** to 666 producers got 201+ replies (30%+ rate) — producers eager to sell
- **AGRIP EU grant**: Deadline 23 Apr 2026, EUR 205M budget. OIPA as lead applicant (cooperative too young)
- **Target buyers**: Kaufland "Din Romania", Lidl "Romaneste", Carrefour, Mega Image, diaspora shops
- **Revenue**: domestic wholesale, EU export, Moldova trade, AGRIP grants
- Detailed strategy and ideas: `BUSINESS_IDEAS.txt`, `REVENUE_PLAN.txt`, `SEGMENTATION_PROPOSAL.md`

## Existing Data Files

| File | Records | Content |
|------|---------|---------|
| `DATA/RNPM-02.03.2026.xlsx` | Full | Latest RNPM export (current import source) |
| `DATA/RNPM 10.07.2023.xlsx` | Full | Previous RNPM export (baseline) |
| `DATA/PRODUS MONTAN PRODUCATORI.csv` | 680 | Email + produsmontan.ro URL per producer |
| `DATA/rnpm_producers_1331.csv` | 1,331 | Enriched producer list with categories |
| `DATA/DATE EXTRASE/rnpm email.csv` | 666 | Extracted emails |
| `DATA/DATE EXTRASE/contact rnpm doar telefon - Sheet1.csv` | 651 | Phone numbers |

## Rules

- Follow parent `D:\MEMORY\CLAUDE.md` conventions (Unix style, max 250 lines, LF only)
- All scraper output must include source URL and scrape timestamp
- Deduplicate by CUI first, then by email
- Never delete original CSVs — they are the baseline from OIPA 2023
- `produs_montan_parse.py` must stay DB-free (pure parsing module)
