# BOOK PUBLISHER

## What
Data → KDP-ready PDF → publish on Amazon + Lulu + Draft2Digital + Bookvault.
Print-on-demand: they print, they ship, you collect royalties.

## Files
- `book_publisher.py` — main: data → interior.pdf + cover.pdf
- `templates/catalog_interior.html` — Jinja2 interior (title page, TOC, sections, back matter)
- `templates/cover.html` — Jinja2 cover (dark blue + gold)
- `register_publishers.py` — Playwright Edge: auto-register at 4 platforms
- `PUBLISHING_GUIDE.md` — full KDP guide, costs, royalties, step-by-step
- `.env` — publisher account credentials
- `output/` — generated PDFs

## Usage
```bash
python book_publisher.py \
  --data path/to/data.json \
  --title "Book Title" \
  --subtitle "Subtitle" \
  --trim 8.5x11 \
  --group-by sector \
  --output ./output
```

## Accounts (apaminerala@yahoo.com)
- Amazon KDP: kdp.amazon.com (use Amazon login)
- Lulu: lulu.com
- Draft2Digital: draft2digital.com
- Bookvault: bookvault.app
- Password: in .env

## First Book Generated (2026-04-15)
- "European Factory Employers Directory 2026"
- 2,809 companies, 124 sectors
- Interior: 1.3MB PDF | Cover: 62KB PDF
- Also in Downloads/

## Profit: $13.59/book at $29.99 price (KDP 8.5x11 B&W 200pg)

## Related IDEAS
- IDEA-136: Amazon KDP Print Catalogs (12 book concepts)
- IDEA-137: Book Publisher Skill (this tool)
- IDEA-138: Black Card Books 40 Steps (Gerry Robert marketing)
