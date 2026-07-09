---
name: supplier-sourcing
description: Build/extend the HAMBARUL ROMANESC supplier master of verified Romanian producers. Use when asked to "find producers", "source suppliers", "build supplier list", "verify Romanian origin", "extend the supplier database", or reuse VIA-PROFI/silozuri/MADR/wholesale producer assets. Also triggers on "add suppliers", "re-run sourcing", "supplier gaps".
---

# Supplier Sourcing

Build the supplier master that powers a Romanian-producer-first supermarket.

## Why Romanian-origin verification matters
The brand promise is "produs românesc, de la producător". A reseller/importer in the list breaks that promise and exposes the chain to false-advertising risk. So every supplier must be checked: is the CUI a producer (cultivation/manufacturing NACE), not a wholesale/import NACE? Does the origin claim hold?

## Workflow
1. **Reuse first.** Pull from existing assets before any new scrape:
   - VIA-PROFI 781 producers (email/phone/products, county+category)
   - Silozuri grain/cereals (TIER_1 808 ready-to-contact)
   - Wholesale buyer/seller leads, MADR producer/land data
   Locate via `D:\MEMORY\SCRAPERS\REGISTRY.md` and `D:\MEMORY\SCRAPER_LOCATIONS.md`.
2. **Dedup** by CUI, then normalized name+county.
3. **Verify origin** — NACE/CAEN code class, ANAF CUI, product-origin claim. Mark `origin_verified`.
4. **Score fit (0-100)** = weighted(category coverage, capacity, contactability, certification, price, delivery radius).
5. Write `_workspace/01_suppliers_master.csv` + a coverage summary (category × county, gaps).

## Output schema (`_workspace/01_suppliers_master.csv`)
`cui,name,county,category,products,email,phone,capacity,certifications,origin_verified,fit_score,source`

## Rules
- Lead hygiene: never drop a supplier on a temporal signal (ANAF debt). Record as-of, informational.
- Conflicting data → keep both, tag source. One retry on a failed source, then continue and note the gap.
- Re-invocation: read existing master, enrich/extend — do not rebuild from scratch.
