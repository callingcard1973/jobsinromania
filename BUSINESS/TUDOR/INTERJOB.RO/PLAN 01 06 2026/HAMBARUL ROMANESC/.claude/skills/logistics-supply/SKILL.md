---
name: logistics-supply
description: Supply chain, cold chain, and ERP/POS/inventory system design for HAMBARUL ROMANESC. Use when asked about "distribution model", "cold chain", "warehousing", "inventory/replenishment", "which ERP", "POS system", "retail software", or "e-Factura/SAF-T". Triggers on logistics/operations/systems-stack questions.
---

# Logistics, Supply Chain & Systems

How product moves producer → shelf, and the software that runs it.

## Distribution (producer-first = short chain)
Choose & justify: direct-store-delivery vs central cross-dock hub vs hybrid. Quantify cost/freshness/complexity. Many small fragmented suppliers favor a cross-dock hub near supplier clusters.

## Cold chain
Temperature zones for dairy/meat/produce; transport + store cold storage. Flag perishable SKUs from `_workspace/02_catalog.csv`.

## ERP/POS selection — present 2-3 options with fit/cost/RO localization
- Enterprise: SAP Business One, MS Dynamics 365 BC.
- RO SME-friendly: Senior ERP, SmartBill, FGO, Saga — ANAF e-Factura ready.
- POS: retail POS with RO fiscal (casa de marcat) integration + inventory/replenishment.
- Note ANAF obligations: e-Factura (RO e-Invoice), SAF-T D406.
Recommend by store count/budget.

## Workflow
Read catalog + `_workspace/03_locations.csv` + supplier geography → write `_workspace/05_logistics.md` (distribution model, cold-chain plan, ERP/POS comparison table + recommendation, inventory policy, est. operating cost).

## Rules
- Cost unknown → benchmark estimate, flag. Re-invocation: update, apply feedback.
