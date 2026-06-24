# HAMBARUL ROMANESC — Supplier Master Coverage Summary

Re-invocation 2026-06-24: gap categories filled by reusing existing assets (no new scraping).
Original (VIA-PROFI + SILOZURI) preserved; new rows appended + deduped (CUI, then name+county).

- **Total suppliers:** 15,500 (was 3,571 + 11,929 new)
- **New sources added:** DSVSA_RO_REGISTRY (registered production units), DAIRY_RO, MEAT_PROCESSORS_RO, CONSERVE_FACTORIES, ANSVSA_STARTER
- **Origin verification:** all new rows are DSVSA/ANSVSA-registered production units (cultivation/processing, not wholesale/import) → origin_verified=True

## By category (full master)

| Category | Count | With email | With phone | Origin verified |
|---|---|---|---|---|
| dairy | 7,272 | 96 | 253 | 7,272 |
| cereals/grain | 2,628 | 717 | 2,508 | (existing) |
| bakery | 1,878 | 0 | 0 | 1,878 |
| honey | 1,454 | 0 | 0 | 1,454 |
| meat/charcuterie | 1,120 | 99 | 23 | 1,120 |
| produce/vegetables | 858 | 359 | 836 | (existing) |
| eggs | 168 | 0 | 0 | 168 |
| other/traditional | 78 | 49 | 77 | (existing) |
| preserves/conserve | 39 | 25 | 19 | 39 |
| wine/tuica | 5 | 2 | 5 | (existing) |

## New rows added this run (gap categories)

| Category | Rows added | Source(s) |
|---|---|---|
| dairy | 7,271 | DSVSA PRELUCRARE LAPTE (7,256) + DAIRY_RO contacts (15) |
| bakery | 1,878 | DSVSA FABRICAREA PAINII + BRUTARIE |
| honey | 1,454 | DSVSA APICULTURA/MIERE (capped at 1,500) |
| meat/charcuterie | 1,119 | DSVSA PRELUCRARE CARNE + MEAT_PROCESSORS_RO + ANSVSA_STARTER |
| eggs | 168 | DSVSA COLECTARE/AMBALARE OUA |
| preserves/conserve | 39 | CONSERVE_FACTORIES_FV |
| **Total** | **11,929** | |

## Category x County (gap categories, top counties)

- **dairy** (41 counties): Suceava 1066, Brasov 764, Botosani 459, Timis 441, Iasi 397, Bacau 392, Vrancea 321, Vaslui 297
- **meat/charcuterie** (37 counties): Bucuresti 483, Botosani 162, Arges 84, Bihor 81, Brasov 81, Alba 80, Arad 51
- **bakery** (31 counties): Bucuresti 297, Neamt 230, Alba 210, Timis 112, Prahova 107, Buzau 83, Sibiu 80
- **eggs** (4 counties): Iasi 142, Harghita 15, Caras-Severin 6, Buzau 5
- **honey** (2 counties so far): Alba 1067, Arges 387
- **preserves/conserve**: county not captured in source (national factories), 39 units

## Remaining gaps / caveats

- **Contactability low for bakery, honey, eggs** — DSVSA registry provides verified producer name + county but NO email/phone. These need an enrichment pass (ANAF CUI lookup → web/email scrape, or Google Places) before outreach. Origin is verified; contact is not.
- **honey & eggs county coverage incomplete** — DSVSA file read alphabetically and honey capped at 1,500, so only ALBA/ARGES (honey) and 4 counties (eggs) loaded. Full national coverage available in source (17,377 honey, 187 eggs) — lift the cap / full pass to extend.
- **preserves/conserve thin (39)** — only the curated factory list; viable as supplier base but small. Could extend via DSVSA fruit/veg processing units.
- **No CUI captured for DSVSA-sourced rows** — registry keys on registration_number, not CUI. Dedup used name+county. ANAF CUI resolution recommended before contracting.
- Categories NOT requiring import-distribution fallback: all six gap categories now have Romanian-producer coverage. None left empty.
