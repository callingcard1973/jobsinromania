# CIFN.EU

## What This Is
WordPress site for CIFN (Centrul de Informare despre Fonduri Nerambursabile) — Romanian EU funds information portal. Used to publish articles about EU funding programs and generate leads from public procurement/EU project data.

## Site Details
- **URL**: https://cifn.eu (also cifn.info — WordPress)
- **Hosting**: A2 Hosting, cPanel user `loaiidil`, docroot `~/cifn.eu/`
- **CMS**: WordPress (default theme, no SEO plugin)
- **Sitemap**: https://cifn.eu/wp-sitemap.xml (WordPress built-in)

## Google Indexing Issues (2026-04-07) — FIXED
- **Before**: 40 posts (19 duplicates with `-2`/`-3` slugs), all same day, 6 indexed, 2 flagged "Duplicate without user-selected canonical"
- **Fix applied**: Deleted 19 duplicates, staggered 21 posts across Mar 5 – Apr 3
- **Sitemap**: Clean — 21 unique URLs, no duplicates, dates spread naturally

### Still TODO
1. ~~Install Yoast SEO~~ — DONE (active, meta descriptions + JSON-LD schema on all pages)
2. Resubmit sitemap in Google Search Console (Yoast sitemap: /sitemap_index.xml)
3. Request indexing for key pages
4. Add Open Graph tags (configure in Yoast Social settings)

## Data / Leads
- `cifn_eu_leads.csv` — 332 leads scraped from EU procurement (category, company, project_title, budget, county)
- `cifn_eu_leads_tagged.csv` — 280 leads tagged with program/axa codes (PRNE, PRNV, PRC, etc.)
- `program_axa_mapping.md` — Reference table for Romanian EU program codes
- `constructii.html`, `echipamente.html` — scraped pages

## Scripts
- `extract_company.py` — extract company names from lead data
- `tag_program_axa.py` — tag leads with EU program/axis codes
- `report_program_axa.py` — generate reports by program/axis

## Purpose
Prepare cifn.eu to sell EU funding data and consulting leads to Romanian companies seeking EU grants.
