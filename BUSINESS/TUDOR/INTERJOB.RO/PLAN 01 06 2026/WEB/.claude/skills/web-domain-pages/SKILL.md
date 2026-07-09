---
name: web-domain-pages
description: Generate bilingual (EN/RO) sector + county SEO landing pages for the 9–10 InterJob job domains (meatworkers, warehouseworkers, careworkers, mechanicjobs, electricjobs, buildjobs, horecaworkers, internaltransfers, farmworkers) from a single domain config, then deploy them to A2. Use when asked to "generate domain pages", "build sector pages", "regenerate the SEO pages", "replicate FactoryJobs to other domains", "add a county page", or "rebuild all domains". Zero-cost organic-traffic engine — trigger on any multi-domain page-generation request. Used by the page-builder agent.
---

# web-domain-pages

Batch-generate the InterJob domain landing pages and hand them to the deployer. Reuses `generate_all_domains.py` (per-sector EN/RO pages) and `REPLICATE_DOMAINS.py` (clones the FactoryJobs structure to a new domain). One config drives 9–10 domains × their ISCO sectors × {EN, RO} — currently ~26 sector pages, expandable with county pages.

## Source of truth
The `DOMAINS` dict in `generate_all_domains.py` / `REPLICATE_DOMAINS.py`: per domain → sectors (ISCO code → EN/RO names + descriptions + job count), brand colors. Edit the config to add a domain, sector, or county — never hand-edit generated HTML; it gets overwritten on the next run.

## Procedure
1. Confirm/extend the `DOMAINS` config for the target scope (one domain, all, or +county pages).
2. Run the generator → pages land under `WEB/{DOMAIN}/PAGES/sector_{code}[_ro].html`.
3. Lint each page before deploy: valid HTML, `<title>` + meta description present, lang attribute set, no dead internal links, no leaked contact data on public pages.
4. Hand the file list to the deployer (web-publish skill / deployer agent) for cPanel upload.

## Why config-driven, not per-domain scripts
9 domains drifting independently is how you end up with 9 inconsistent templates. A single config + generator keeps branding, ISCO mapping, and bilingual parity uniform, and makes "add a county page to all domains" a one-line change instead of 9 edits.

## SEO intent
Each sector/county page targets a long-tail query ("welders jobs Europe", "ingrijitori batrani Germania"). Bilingual EN/RO doubles the surface. County expansion (42 RO counties) is the highest-volume untapped page set — generate from the same config.

## Failure modes
- Missing sector in config → page silently absent. The generator must report generated/expected counts per domain; a gap means a config hole, fix it there.
- Diacritics in RO pages are fine (HTML, not email) — do NOT ASCII-fold these.
