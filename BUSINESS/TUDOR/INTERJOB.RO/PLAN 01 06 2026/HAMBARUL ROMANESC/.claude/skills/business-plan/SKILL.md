---
name: business-plan
description: Assemble the full HAMBARUL ROMANESC business plan in Romanian AND English with financials. Use when asked for "business plan", "plan de afaceri", "financial model", "P&L/projections", "break-even", "investor deck", or "funding ask". Triggers on synthesis of all sections into a bilingual plan. Also triggers on "update the plan", "regenerate financials".
---

# Business Plan (bilingual synthesizer)

Integrate all agent outputs into an investor-ready plan in **both Romanian and English**.

## Bilingual, parallel
Produce two professionally-written documents (not machine-translated stubs):
- `PLAN_DE_AFACERI_RO.md`
- `BUSINESS_PLAN_EN.md`

## Structure (both languages)
1. Executive summary 2. Company & vision (Romanian-producer-first) 3. Market study 4. Competition & positioning 5. Products & sourcing 6. Operations, logistics & ERP 7. Locations & rollout 8. Marketing & brand 9. Compliance 10. Financial plan 11. Funding ask 12. Risks & mitigation 13. Roadmap.

## Financials (explicit, traceable)
- Capex: store fit-out, cold chain, ERP/POS.
- Revenue model: stores × catchment × basket × frequency.
- Gross margin from `_workspace/02_catalog.csv`; opex; break-even; 3-year P&L.
- Assumptions in a table; mark estimates. Never present a fabricated precise number as fact.
- Write `_workspace/07_financials.csv` (P&L model).

## Workflow
Read all `_workspace/00..06_*` artifacts → write the two root plan files + financials CSV. Missing input → state the assumption used, continue (don't block the whole plan).

## Rules
- Decision-framework discipline: every major recommendation answers problem/beneficiary/revenue/cost; rank by ROI.
- Re-invocation: regenerate only changed sections, preserve user-edited prose, apply feedback.
