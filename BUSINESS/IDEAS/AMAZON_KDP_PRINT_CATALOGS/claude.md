# AMAZON KDP PRINT CATALOGS (IDEA-136)

**Status:** PLANIFICAT | **Categorie:** PRODUS | **Tip:** cod

## Ce face
Print physical books (catalogs) on Amazon KDP using existing data assets.
You DON'T sell PDFs — you sell printed books. Amazon prints and ships.

## Book Ideas (from existing data)

### Tier 1: Job & Employer Catalogs
1. **European Factory Employers Directory 2026** — 608 companies, sectors, contacts
2. **Construction Companies Hiring in Europe** — 671 ISC + TED contractors
3. **Norwegian Employers Hiring Foreign Workers** — filtered from 314K
4. **HORECA Employers Europe** — 28K contacts, by country
5. **Recruitment Agencies of Europe** — 18K agencies, by country

### Tier 2: Opportunity Catalogs
6. **EU-Funded Projects Directory** — 15,969 beneficiaries, by sector
7. **EBRD Infrastructure Projects 2026** — 4,176 projects, 42 countries
8. **Romanian Public Contracts Winners** — SEAP data, by sector
9. **TED Open Tenders Guide** — 5.1M tenders filtered by sector

### Tier 3: Agricultural / Niche
10. **Romanian Mountain Producers Catalog** — 1,507 producers, AGRIP certified
11. **Farms for Sale in Romania** — 9,658 listings from MADR
12. **Romanian Food Exporters Directory** — cooperativa + SEAP food winners

## Amazon KDP Specs
- **Trim sizes:** 6x9" (standard), 8.5x11" (catalog), A4 (EU)
- **Format:** Interior PDF + Cover PDF (separate)
- **Bleed:** 0.125" on all sides for cover
- **ISBN:** Free from KDP or buy your own
- **Pricing:** You set price, KDP takes printing cost + 40% (60% royalty)
- **Example:** 200-page catalog, 8.5x11", color = ~$12 print cost. Price at $39.99 = $24 profit/book

## Revenue Math
- 12 books x 10 sales/month x $24 profit = $2,880/month
- Update annually = new edition = new sales spike
- Evergreen: agencies/recruiters/investors buy these as reference tools

## Pipeline
1. Query PostgreSQL → CSV/JSON
2. Jinja2 template → HTML (light theme, print CSS)
3. Playwright → KDP-compliant PDF
4. Upload to KDP → set price → publish
5. Time to first book: 2-3 days

## Venit estimat
2000-10000/luna EUR

## Efort
15 ore
