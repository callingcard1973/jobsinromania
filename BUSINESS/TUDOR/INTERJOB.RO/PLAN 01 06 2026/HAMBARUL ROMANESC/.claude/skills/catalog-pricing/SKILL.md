---
name: catalog-pricing
description: Build the HAMBARUL ROMANESC product catalog and set prices/margins from verified suppliers. Use when asked to "build the assortment", "price products", "compute margins", "category mix", "private label", or "regenerate the catalog". Triggers on assortment/SKU/markup/gross-margin requests.
---

# Catalog & Pricing

Turn the supplier master into a priced, margin-bearing assortment.

## Margin math (always explicit)
- `retail_price = cost / (1 - target_margin)`; RO food VAT = 9%.
- Show: cost, markup, VAT, shelf price, gross_margin_pct. Never invent a cost — mark `estimated`.

## Workflow
1. Read `_workspace/01_suppliers_master.csv`.
2. Map suppliers → SKUs; assign category, unit, supplier_cui (traceability).
3. Set target margin per category; compute retail price + gross margin.
4. Benchmark vs Lidl/Kaufland/Mega Image/Profi where data exists; position premium-local (quantify the premium).
5. Flag private-label opportunities (contract producer beats national brand on margin).
6. Write `_workspace/02_catalog.csv` + assortment/margin summary + sourcing gaps.

## Output schema (`_workspace/02_catalog.csv`)
`sku,name,category,supplier_cui,unit,cost,vat,retail_price,gross_margin_pct,is_private_label,origin`

## Rules
- Every SKU ties to a supplier CUI. Category with no supplier → record as sourcing gap (back to supplier-sourcing).
- Re-invocation: update existing catalog, don't rebuild.
