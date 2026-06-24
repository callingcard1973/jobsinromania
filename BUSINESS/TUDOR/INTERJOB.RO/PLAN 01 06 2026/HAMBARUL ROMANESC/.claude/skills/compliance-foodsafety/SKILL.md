---
name: compliance-foodsafety
description: Food-safety & regulatory compliance checklist for HAMBARUL ROMANESC. Use when asked about "ANSVSA/DSVSA registration", "HACCP", "food labelling", "permits to open a store", "cold chain rules", "supplier certification", or "is this legal". Triggers on compliance/authorization/licensing/labelling questions.
---

# Compliance & Food Safety

Map every permit, certification, and labelling rule; vet supplier food-safety standing.

## Be source-honest
Cite the regulation (ANSVSA order, Reg. EU 1169/2011 labelling, Reg. 852/2004 HACCP) or mark "verify with ANSVSA/lawyer". Never invent article numbers.

## Two layers
- **Retailer:** store ANSVSA registration/authorization, HACCP plan, cold-chain temperature logs, traceability, casa de marcat, ANAF e-Factura/SAF-T.
- **Supplier (per category):** DSVSA registration for animal products (raw milk, meat, eggs, honey), BIO/eco certification if claimed, label compliance. Producer-first raises the bar — small producers have specific DSVSA rules.

## Workflow
1. Read supplier categories (`_workspace/01_suppliers_master.csv`) + store plan.
2. Build a **checklist with status** (required / in-progress / done / blocked) — store-level + per supplier category.
3. List labelling rules + cold-chain requirements; flag risk items.
4. Write `_workspace/04_compliance.md` (+ optional `04_supplier_flags.csv`: cui,category,required_cert,status).

## Rules
- Uncertain regulation → "verify with authority/lawyer", never guess specifics.
- Re-invocation: update statuses, apply feedback.
