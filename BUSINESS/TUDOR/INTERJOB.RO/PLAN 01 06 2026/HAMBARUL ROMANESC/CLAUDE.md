# HAMBARUL ROMANESC — Romanian-Producer-First Supermarket

**v1.0 | 2026-06-24** — Launch harness deployed

## Concept
Supermarket chain sourced primarily from **Romanian producers**, with full producer traceability as the brand moat. Hambarul = "the granary/barn".

## Harness: HAMBARUL ROMANESC Launch

**Goal:** Plan and launch a Romanian-producer-first supermarket chain end to end — market study → supplier sourcing → catalog/pricing → locations → compliance → logistics/ERP → brand/marketing → bilingual business plan.

**Trigger:** For any HAMBARUL ROMANESC supermarket task (market study, sourcing, catalog, locations, compliance, logistics, branding, business plan), use the `hambarul-orchestrator` skill. Single factual questions can be answered directly.

**Team (9 agents, all opus):** market-research, supplier-sourcing, catalog-pricing, store-location, compliance-foodsafety, import-distribution, logistics-supply, brand-marketing, business-plan.

**Deliverables:** `PLAN_DE_AFACERI_RO.md` + `BUSINESS_PLAN_EN.md` (root) + 8 artifacts in `_workspace/`.

**Reuses:** VIA-PROFI 781 producers, silozuri (13K), wholesale buyers, MADR — see `D:\MEMORY\SCRAPERS\REGISTRY.md`.

**Change history:**
| Date | Change | Target | Reason |
|------|--------|--------|--------|
| 2026-06-24 | Initial harness — 8 agents + 8 skills + orchestrator | full | New supermarket project |
| 2026-06-24 | Added market-research, business-plan (RO+EN), ERP in logistics | agents + skills | User: include business plan RO/EN, market study, competition, ERP, key players |
| 2026-06-24 | Added import-distribution agent (9th) — importers, distributors, cash & carry, hybrid sourcing for non-local long tail | agents + skills + orchestrator | User: need importers/distributors mapped for goods not sourceable from RO producers |
