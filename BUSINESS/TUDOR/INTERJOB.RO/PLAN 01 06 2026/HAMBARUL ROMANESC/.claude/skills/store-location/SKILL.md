---
name: store-location
description: Rank cities/neighborhoods for HAMBARUL ROMANESC stores. Use when asked "where to open", "best store location", "site selection", "catchment analysis", "compare locations", or "launch sequence". Triggers on location/demographics/competition-density/rent questions.
---

# Store Location Intelligence

Decide where to open and in what sequence.

## Scoring model (state weights, allow override)
`score = w1·catchment_pop + w2·median_income + w3·(1/competitor_density) + w4·(1/rent) + w5·supplier_proximity + w6·access`

Default tilt: high-income urban neighborhoods underserved by premium-local formats (Bucharest sectors, Cluj, Timișoara, Brașov, Iași). **Supplier proximity weighted up** — producer-first = short cold chain + freshness story.

## Workflow
1. Read supplier county distribution from `_workspace/01_suppliers_master.csv`.
2. Gather per-area: catchment pop, income (INS), competitors within 500m, rent €/m².
3. Score + rank; recommend format (200-400 m² neighborhood "hambar" pilot vs larger).
4. Write `_workspace/03_locations.csv` + top-N recommendation + launch sequence.

## Output schema (`_workspace/03_locations.csv`)
`city,area,score,catchment_pop,median_income,competitors_500m,est_rent_eur_m2,supplier_proximity,rank`

## Rules
- Cite source (INS, rent listings) or mark "estimate / needs field check". Never fabricate precise figures.
- Re-invocation: re-rank with new weights/feedback.
