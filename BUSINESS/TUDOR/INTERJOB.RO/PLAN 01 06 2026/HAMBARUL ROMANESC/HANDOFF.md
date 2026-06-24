# HANDOFF — HAMBARUL ROMANESC

**Romanian-producer-first supermarket chain.** Built + run end-to-end 2026-06-24.
Branch: `hambarul-romanesc-harness` (pushed, origin callingcard1973/jobsinromania).

---

## 1. What this is

A supermarket chain stocked **primarily from verified Romanian producers**, with per-SKU producer traceability as the brand moat ("De la hambarul lor, pe masa ta." / "From their barn to your table."). Pilot store = **București Sector 1**, ~300 m² neighborhood format.

Two things live here:
1. **Deliverables** — the business plan + supporting analysis (the actual output).
2. **A reusable harness** — 9 agents + 9 skills + orchestrator that produced it and can re-run/update it.

---

## 2. Deliverables (project root)

| File | What |
|------|------|
| `PLAN_DE_AFACERI_RO.md` | Full business plan, Romanian (252 lines, 13 sections) |
| `BUSINESS_PLAN_EN.md` | Full business plan, English (252 lines, 13 sections) |
| `CLAUDE.md` | Project + harness pointer (trigger rules, change log) |

### Supporting analysis — `_workspace/`
| File | Content |
|------|---------|
| `00_market_study.md` | TAM ~€40-45bn, SAM €6-8bn, SOM €4-9M Y1→€25-45M Y3; competitor SWOTs; positioning gap |
| `01_suppliers_master.csv` | **15,500** origin-verified RO producers; **2,665 CUI-verified** (+caen, +match_confidence) |
| `01_suppliers_summary.md` / `01_cui_resolution.md` | Coverage by category×county / CUI resolution log (2 passes) |
| `02_catalog.csv` / `02_catalog_summary.md` | 156 SKUs, ~36% blended GM, 36 private-label, premium-local |
| `03_locations.csv` / `03_locations_summary.md` | Site ranking; pilot = București Sector 1, rollout S4→S2 |
| `04_compliance.md` / `04_supplier_flags.csv` | ANSVSA/HACCP/labelling checklist with status; blockers |
| `05_logistics.md` | Hybrid DSD+3PL, cold chain, RO-SME ERP/POS (SmartCash+SmartBill), capex €26-47k |
| `06_brand_marketing.md` | Brand, Producer Tag moat, Sector 1 launch ~€37k/90d |
| `08_import_distribution.md` / `08_distributors.csv` | Non-local long tail; Metro/Selgros/Macromex/Parmafood/Aquila/Orbico routes |
| `07_financials.csv` | 3-yr P&L model, assumptions, break-even |

---

## 3. Headline numbers (all estimates flagged in plan)

- Revenue ~€2.7-3.1M/store/yr · blended GM ~36% · EBITDA €159k→€1.53M (Y1-Y3)
- **Funding ask ~€500k Year 1** (€215k capex + €150k working capital + €135k ramp buffer)
- Break-even ~260 txns/day vs 500 target

---

## 4. The harness (reusable) — `.claude/`

**9 agents (all opus) + matching skills + orchestrator `hambarul-orchestrator`.**
Agents: market-research, supplier-sourcing, catalog-pricing, store-location, compliance-foodsafety, import-distribution, logistics-supply, brand-marketing, business-plan.

**Pipeline:** Phase1 foundation (market+suppliers, parallel) → Phase2 build (catalog+locations) → Phase3 ops (import/compliance/logistics/brand) → Phase4 bilingual plan synthesis. File-based handoff via `_workspace/NN_*`.

**To re-run / update:** invoke `hambarul-orchestrator` skill, or say "update the plan" / "re-run sourcing". Custom agent types register as Agent `subagent_type` only after a session reload — until then run via `general-purpose` + Skill invocation.

---

## 5. OPEN ITEMS / next steps

1. **CUI gate — amber, not closed.** 2,665/15,500 CUI-verified (enough to open; only ~100 contracted producers needed for the pilot). Remaining ~12,835 = PFA/individuals + DSVSA entities needing per-name ANAF webservice lookups (rate-limited, diminishing returns). To push further: ANAF `webservicesp.anaf.ro` getInfo or APIA/PFA lookup.
2. **Catalog placeholders.** 140 of 156 SKUs use `PLACEHOLDER-<CAT>` supplier_cui — re-tie to real CUI-verified suppliers from the master before going live.
3. **Pilot shortlist not built yet.** Pick top ~100 CUI-verified producers (category fit + Bucharest proximity) → ready-to-contract list.
4. **Hard compliance blockers** (go/no-go to open): DSVSA store authorization, casă-de-marcat→ANAF, per-supplier DSVSA numbers for dairy/meat. No BIO marketing without Reg. 2018/848 cert (zero certs in master).
5. **Financials are estimates.** Need real quotes: Sector 1 rent, refrigeration fit-out, 3PL, POS.
6. **Honey/eggs partial coverage** — source has more national rows than loaded; contactability (email/phone) missing for bakery/honey/eggs.

---

## 6. KEY REUSABLE FINDINGS

- **Right table for name→CUI matching:** `D:\MEMORY\DATA\ACTIVE\ROMANIA_DB\master_romania_companies.csv` (2.9M rows, 2.8M numeric-CUI). The jobs DB `interjob_master.companies` is construction/jobs/TED-skewed — a dead end for producers (53/14,749).
- **DSVSA registration_number** is itself a valid food-safety traceability key for animal products; CUI strictly needed only at contracting/invoicing.
- **DSVSA_RO_REGISTRY** (309K rows) maps by activity_type → producers by category — the source that filled dairy/meat/bakery/honey/eggs.
- Distributor profiles (Metro/Selgros/Macromex/Parmafood/Aquila/Orbico) in `08_distributors.csv`.

---

## 7. GIT / branch note

All work on `hambarul-romanesc-harness`: c36002a (harness+plan) + f3967bf (CUI resolution). A **concurrent session** co-edited D:\MEMORY on branch `verify-toolkit-and-harnesses`; the CUI commit first landed there and was cherry-picked over. Watch for branch-switching when multiple sessions share the working tree.

Memory: `hambarul_supermarket_harness_2026_06_24.md`.
