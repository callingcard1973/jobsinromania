---
name: hambarul-orchestrator
description: HAMBARUL ROMANESC master orchestrator — launch a Romanian-producer-first supermarket chain end to end. Coordinates 9 agents (market-research, supplier-sourcing, catalog-pricing, store-location, compliance-foodsafety, import-distribution, logistics-supply, brand-marketing, business-plan) into market study + supplier master + catalog + locations + compliance + logistics/ERP + marketing + bilingual business plan. Use when asked to "build the HAMBARUL harness", "plan the supermarket", "create the business plan", "run the full analysis", "update the plan", "re-run sourcing/market study", or any HAMBARUL ROMANESC supermarket task.
---

# HAMBARUL ROMANESC — Master Orchestrator

Launch a Romanian-producer-first supermarket chain. Hybrid execution: parallel fan-out where independent, pipeline where dependent, synthesis at the end.

## Phase 0 — Context check
- `_workspace/` missing → **initial run** (full pipeline).
- `_workspace/` exists + user asks partial change → **partial re-run** (only the named agent(s); pass existing artifacts).
- `_workspace/` exists + new scope/inputs → **new run** (move `_workspace/` → `_workspace_prev/`, start fresh).
Create `_workspace/` if absent.

## Team
8 agents, all `model: "opus"`. Spawn via the Agent tool (or TeamCreate for live coordination). Each has a matching skill the agent reads.

## Phase 1 — Foundation (parallel fan-out)
Run concurrently (no cross-dependency):
- **market-research** → `_workspace/00_market_study.md`
- **supplier-sourcing** → `_workspace/01_suppliers_master.csv`

## Phase 2 — Build (pipeline, depends on Phase 1)
- **catalog-pricing** (needs suppliers + competitor pricing) → `_workspace/02_catalog.csv`
- **store-location** (needs supplier geography) → `_workspace/03_locations.csv`
Run these two in parallel; both depend only on Phase 1.

## Phase 3 — Operations (parallel, depends on Phase 2)
- **compliance-foodsafety** → `_workspace/04_compliance.md`
- **import-distribution** (long-tail/non-local sourcing — importers, distributors, cash & carry) → `_workspace/08_import_distribution.md`. Runs before logistics so its hybrid routes feed the distribution plan.
- **logistics-supply** → `_workspace/05_logistics.md`
- **brand-marketing** → `_workspace/06_brand_marketing.md`

## Phase 4 — Synthesis (single)
- **business-plan** reads all `_workspace/00..06_*` → writes `PLAN_DE_AFACERI_RO.md`, `BUSINESS_PLAN_EN.md` (root), `_workspace/07_financials.csv`.

## Data passing
File-based via `_workspace/{NN}_{agent}_{artifact}`. Final deliverables (the two plans) in project root; intermediate artifacts preserved in `_workspace/` for audit.

## Error handling
- Agent fails → one retry. Re-fails → continue without it; business-plan notes the gap + uses a labelled assumption. Never block the whole plan on one input.
- Conflicting data across sources → keep both with source tag, never delete.
- A sourcing gap (category with no supplier) loops back: catalog-pricing flags it → re-invoke supplier-sourcing for that category.

## Test scenarios
- **Normal:** "build the full HAMBARUL plan" → Phase 1→4 → two bilingual plans + 8 artifacts in `_workspace/`.
- **Partial re-run:** "update the market study and regenerate the plan" → market-research only, then business-plan re-synthesis; other artifacts untouched.
- **Error flow:** supplier source unreachable → sourcing continues with VIA-PROFI/silozuri only, notes gap; plan still produced with assumption flagged.

## After every run
Offer feedback capture; reflect changes into agents/skills + CLAUDE.md change log (harness evolution).
