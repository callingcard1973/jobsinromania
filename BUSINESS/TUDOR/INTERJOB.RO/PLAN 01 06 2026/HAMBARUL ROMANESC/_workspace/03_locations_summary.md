# 03 — Store Location Ranking: HAMBARUL ROMANESC

**Date:** 2026-06-24 · **Agent:** store-location · **Inputs:** `01_suppliers_master.csv` (15,721 suppliers / 61 counties), `00_market_study.md`
**Source honesty:** Demographic/income/rent figures are **estimates** triangulated from INS metro data + Romanian rent listings (Imobiliare.ro / Storia) order-of-magnitude. Mark **needs field check** before lease signing. Supplier-proximity is the one **hard** variable — counted directly from the supplier master.

---

## 1. Scoring model & weights

`score = 0.20·catchment_pop + 0.18·median_income + 0.15·(1/competitor_density) + 0.12·(1/rent) + 0.25·supplier_proximity + 0.10·access`

| Weight | Variable | Rationale |
|--------|----------|-----------|
| **0.25** | **supplier_proximity** | Highest weight — producer-first chain lives or dies on short cold chain + a credible "from the next county" freshness story. Keyed off in-county + adjacent-county supplier counts. |
| 0.20 | catchment_pop | Footfall base; premium format needs density. |
| 0.18 | median_income | Premium-origin basket; targets top-income urban. |
| 0.15 | 1/competitor_density (within ~500m of premium-local formats) | White space = few BIO/farmers'-market/origin boutiques nearby. Majors (Lidl/Kaufland) are NOT direct competitors — different price tier. |
| 0.12 | 1/rent €/m² | Margin protection; Cluj/Sector1 rents bite. |
| 0.10 | access (parking, transit, loading dock for daily produce) | Producer deliveries need a dock; shoppers need parking. |

All weights overridable on re-invocation.

## 2. Supplier geography (hard data from master)

In-county supplier counts (normalized): **Brașov 919 · București 817 · Iași 647 · Timiș 645 · Cluj only 93.**
National supplier mass sits in **Alba (1,685), Suceava (1,174), Brașov, Argeș, Botoșani** — Transylvania + Moldova.

> **Key finding:** Cluj-Napoca, despite top provincial income, is **supplier-poor in-county (93)** — its cold chain leans on Alba/Mureș/Bihor (1–2h haul). Brașov is the standout: highest in-county supplier base AND a top-5 income metro. This reorders the naive "Bucharest/Cluj first" instinct.

## 3. Ranking (see `03_locations.csv`)

| Rank | City / Area | Score | Why |
|------|-------------|-------|-----|
| 1 | **Brașov — Centru / Astra-Răcădău** | 8.7 | Best supplier proximity (919 + adjacent Sibiu/Covasna/Argeș), high income, lower rent than BUC/Cluj, tourism halo. Flagship freshness story. |
| 2 | **București — Sector 1** (Floreasca/Dorobanți/Aviației) | 8.5 | Highest income + largest single-metro spend; supplier base solid (817). Rent high. |
| 3 | **București — Sector 4** (Tineretului) | 7.9 | Dense, high catchment, cheaper rent than S1, underserved by origin formats. |
| 4 | **Iași — Copou/Centru** | 7.6 | Strong Moldova supplier cluster (647 + Botoșani/Vaslui), cheapest rent, less premium competition. |
| 5 | **Timișoara — Cetate/Circumvalațiunii** | 7.4 | West anchor, good supplier base (645 + Arad), high income. |
| 6 | București — Sector 2 | 7.1 | Backfill once metro proven. |
| 7 | **Cluj-Napoca — Andrei Mureșanu** | 6.8 | High income but **supplier-poor + expensive rent** → defer; serve later via Transylvania hub from Brașov/Alba. |

## 4. Pilot format

**200–400 m² neighborhood "hambar"** for all pilots — NOT a large format.
- Premium-origin = lower footfall, higher basket → big-box risks idle floor + spoilage on perishables.
- Small format suits daily producer drops, tight cold chain, neighbourhood loyalty, and lower capex/breakeven (de-risks the model).
- Target **~300 m²** sales floor + dock for daily deliveries. Scale to a single larger "market hall" flagship (600–800 m²) only after 3+ stores validate demand.

## 5. Launch sequence (first 3–5 stores)

1. **Store 1 — Brașov (Centru/Astra)** — flagship; shortest cold chain, best origin narrative, validates concept at lowest supplier risk.
2. **Store 2 — București Sector 1 (Floreasca/Dorobanți)** — prove premium-metro economics + top income.
3. **Store 3 — București Sector 4 (Tineretului)** — second BUC node → shared logistics hub, density.
4. **Store 4 — Iași (Copou)** — open Moldova; cheap rent, strong local supplier cluster, low competition.
5. **Store 5 — Timișoara (Cetate)** — west anchor; completes the metro spread.

**Cluj deferred to phase 2** — open only once a Transylvania supply hub (Brașov/Alba) can backfill its weak in-county base, or on a strong local-supplier recruitment push.

## 6. Handoffs
- → **business-plan**: 5 stores, ~300 m² pilot format, BUC two-store cluster for shared hub → feed capex/revenue model.
- → **logistics-supply**: two distribution clusters — **Transylvania (Brașov/Alba hub)** + **Moldova (Iași)** + BUC consolidation; west (Timiș/Arad) served locally.

## 7. Flagged for field check
Per-area rents, exact 500m competitor counts, catchment radii, and Sector-level income all **need ground verification** before lease. Only supplier counts are hard.
