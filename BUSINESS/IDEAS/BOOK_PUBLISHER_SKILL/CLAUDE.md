# BOOK PUBLISHER SKILL (IDEA-137)

**Status:** ACTIV — v1 WORKING | **Categorie:** PRODUS | **Tip:** cod

## What it does
Python program: data (CSV/JSON) → KDP-ready PDF (interior + cover).
Tested: 2,809 factory employers → 1.3MB interior + 62KB cover.

## Usage
```bash
cd D:\MEMORY\IDEAS\INVENTAR\IDEA-137_BOOK_PUBLISHER_SKILL

python book_publisher.py \
  --data "D:/MEMORY/CLAUDE/A2_SITE_DEPLOYER/FACTORYJOBS/DATA/factory_employers_unified.json" \
  --title "European Factory Employers Directory 2026" \
  --subtitle "2,809 Verified Manufacturing Companies Across Europe" \
  --trim 8.5x11 \
  --group-by sector \
  --output ./output
```

## Files
- `book_publisher.py` — main script (data → HTML → PDF)
- `templates/catalog_interior.html` — Jinja2 interior template
- `templates/cover.html` — Jinja2 cover template
- `output/` — generated PDFs

## Tech Stack (all installed on laptop)
- Python 3.12 + Jinja2 + Playwright + Pillow + psycopg2

## KDP Trim Sizes
- 6x9 (standard book)
- 8.5x11 (catalog/directory) ← default
- A4 (EU standard)
- A5 (compact)

## Template: catalog_interior.html
- Title page + copyright + TOC + sections + back matter
- Two-column layout for dense entries
- Print CSS with proper margins (0.875in inside for binding)
- Page breaks per section
- Professional serif font (Georgia)

## Template: cover.html
- Dark blue gradient + gold accents
- Title + subtitle + stats badges + publisher
- Front cover only (KDP generates full wrap from this)

## v1 Done (2026-04-15)
- [x] Jinja2 catalog interior template
- [x] Cover template
- [x] Playwright HTML→PDF rendering
- [x] CSV + JSON data loading
- [x] Group-by any field (sector, country, county)
- [x] Auto TOC from sections
- [x] KDP trim size support
- [x] First book generated: 2,809 employers, 124 sectors

## TODO v2
- [ ] PostgreSQL direct query (--source db --query "SELECT...")
- [ ] Directory template (alphabetical A-Z index)
- [ ] Page numbers in footer
- [ ] Full KDP cover (front + spine + back, calculated from page count)
- [ ] Batch mode (config file → 12 books)
- [ ] Claude skill wrapper (/publish-book)
- [ ] ISBN page formatting
- [ ] Sponsor ad pages (back matter, for IDEA-138 Fund It system)
