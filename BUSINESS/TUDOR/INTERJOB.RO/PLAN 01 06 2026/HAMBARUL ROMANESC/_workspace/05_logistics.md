# 05 - HAMBARUL ROMANESC: Logistics, Cold Chain & Systems Stack

**Date:** 2026-06-24 - logistics-supply agent
**Pilot:** 1 store, Bucuresti Sector 1 (~300 m2); store #2 = Sector 4, shares a city hub. Scale path = 3 Bucuresti stores.
**Inputs:** 02_catalog.csv (156 SKUs), 03_locations.csv, 01_suppliers_summary.md (15,500 suppliers), 08_import_distribution.md.

> Cost discipline: every figure below is a benchmark estimate, flagged (est). No supplier/vendor quote is audited yet. Verify before the business plan locks capex/opex.

---

## 1. Distribution model

### The structural problem
15,500 producer-first suppliers, deliberately fragmented and far from Bucuresti. Supplier geography (01_suppliers_summary) concentrates in Moldova/Transylvania - dairy: Suceava 1,066, Brasov 764, Botosani 459; meat: Bucuresti only 483 of 1,120. Bucuresti in-county depth is high (817) but the premium origin SKUs (mountain dairy, sheep cheese, honey) come from 300-450 km away. Each producer is a small farm/workshop with tiny drop sizes. Direct-store-delivery (DSD) by every producer to a 300 m2 shop = dozens of micro-deliveries/week, jamming the receiving dock and killing buyer time.

### Three models - trade-offs

| Model | Cost | Freshness | Complexity | Verdict (1->3 stores) |
|---|---|---|---|---|
| Pure DSD (each producer delivers) | Low fixed, high per-drop; uneconomic for distant micro-producers | Best for local metro suppliers; poor for distant (no producer drives 400 km for one crate) | Very high - 50+ vendors x receiving windows | Keep ONLY for metro-local daily-fresh |
| Central cross-dock hub | Hub lease + handling; heavy for 1 store | Good if same-day turn; extra cold touchpoint | Medium - single receiving point, underused at 1 store | Premature at 1 store; right at 3+ |
| Hybrid (recommended) | Moderate - 3PL consolidation for distant, DSD for local, no owned hub yet | Best blend: distant consolidated cold weekly; local daily-fresh DSD | Medium - managed, not owned | CHOSEN |

### Recommended: HYBRID, evolving into a shared city hub at store #2

Phase 1 (1 store, Sector 1):
- Metro-local DSD for daily-fresh short-haul: bakery (15), produce (22), eggs (6), Bucuresti-county dairy. Inside ~50 km - cheapest and freshest.
- Consolidated milk-run / 3PL groupage for distant clusters (Suceava, Brasov, Botosani dairy + meat). Chilled groupage carrier (FAN Frigo / Cargus / regional 3PL) (est) or one weekly consolidated run per cluster. One producer per cluster = collection point. Avoids 30 separate long-haul micro-deliveries.
- Shelf-stable long-tail (honey 12, preserves 18, cereals 16, wine/tuica 10, other 15 = 71 SKUs): no cold chain, low velocity, least-frequent delivery, batch by region.
- Din lume import shelf (per 08): cash & carry (Metro/Selgros) buy-to-shelf, plus Macromex for fish cold chain. Zero owned inventory risk.

Phase 2 (store #2, Sector 4 - shared city hub):
- Open a small shared cross-dock (~150-250 m2, 3-zone) serving both Bucuresti stores. Distant consolidation lands once; hub fans out daily to both stores by one chilled van. Cross-dock becomes economic - fixed cost amortizes over 2-3 stores. Hub doubles as private-label (36 SKUs) staging + e-Factura receiving point.

Why hybrid wins: at 1 store a hub is dead weight; pure DSD cannot move distant micro-producers economically. Hybrid pays only for consolidation where distance demands it, keeps local fresh on DSD, and upgrades cleanly into a shared hub at store #2 - no rework.

### Producer consolidation strategy (the fragmentation fix)
1. Cluster by county - 1 anchor producer per cluster (Suceava-dairy, Brasov-dairy, Moldova-meat) as collection drop; others bring crates; one chilled run/week (twice for dairy).
2. Minimum order / minimum-frequency terms so a consolidated run is full enough to be cheap per kg.
3. Brasov is strategically placed (03_locations rank #1, very_high proximity, 919 in-county + Sibiu/Covasna adj) - natural first regional consolidation node at national expansion.
4. Private label (36 SKUs) - contract producers ship to hub in HAMBARUL packaging; shelf-stable so no spoilage exposure on owned stock.

---

## 2. Cold-chain plan

70 chilled/fresh SKUs + 15 daily-fresh bakery drive the design. From 02_catalog: dairy 22, meat/charcuterie 20, produce/vegetables 22, eggs 6.

### Temperature zones (HACCP / RO DSVSA aligned (est) - confirm with DSVSA on fit-out)

| Zone | Target temp | SKUs | Transport | In-store storage |
|---|---|---|---|---|
| Chilled dairy/deli | 0-4 C | dairy 22 (cheese, milk, yogurt, butter, smantana) | Refrigerated van / chilled groupage; logger per pallet | Walk-in cold room + open chilled multideck |
| Chilled meat/charcuterie | 0-4 C (fresh meat 0-2 C) | meat/charcuterie 20 | Refrigerated, physically separated from dairy/produce | Separate meat cold room + serve-over counter |
| Frozen (import fish only) | <= -18 C | fish/seafood (din lume, Macromex) | Macromex frozen chain - do NOT improvise | Chest/upright freezer |
| Produce - cool/chilled | 8-12 C (most veg); 0-4 C leafy | produce/vegetables 22 | Short-haul DSD, ventilated crates; chilled for leafy | Refrigerated produce island + cool back-of-house |
| Eggs | ambient <= 20 C, no temp shock | eggs 6 | Ambient, protected | Ambient shelf, rotated |
| Bakery | ambient | bakery 15 | Daily DSD | Ambient display, daily bake/sell |
| Dry / shelf-stable | ambient, dry | honey, preserves, cereals, wine, other (71) | Standard | Ambient shelving |

### Transport rules
- Distant dairy + meat = unbroken cold chain: reefer + temperature data-logger per consignment; reject on breach. The #1 food-safety and brand risk - a spoiled artisan cheese batch is both a health and a traceability-promise failure.
- Dairy and meat never share a transport compartment with produce (contamination + odor transfer onto premium cheese).
- Last-mile (hub->store, Phase 2): one chilled van, AM run, loggers retained for DSVSA audit.

### In-store cold storage (300 m2 fit-out) (est)
- 1 dairy/deli walk-in cold room (0-4 C); 1 separate meat cold room (0-4 C) + serve-over counter; open chilled multideck cabinets; 1 freezer (import fish); refrigerated produce island.
- Capex cold-chain fit-out estimate: EUR 25,000-45,000 (est) at 300 m2. Flag - needs an HVAC/refrigeration quote.

---

## 3. ERP / POS selection

### ANAF obligations (mandatory day 1)
- e-Factura (RO e-Invoice): mandatory B2B + B2C - supplier invoices and retail receipts flow via ANAF SPV; stack MUST generate/receive UBL XML.
- SAF-T (D406): small taxpayers entered the regime from Jan 2025; HAMBARUL files D406. ERP must produce it.
- e-TVA pre-filled VAT reconciliation. Fiscal POS: every till = ANAF-fiscalized casa de marcat electronica (AMEF journal); POS software must drive a certified fiscal printer/ECR.

### Comparison

| Option | Type | RO localization | e-Factura / SAF-T | Fit 1-3 stores | Cost (est) |
|---|---|---|---|---|---|
| SAP Business One | Enterprise ERP | RO loc via partner | Yes (partner) | Overkill; heavy impl | EUR 15-40k impl + 80-120/user/mo (est) - too costly for pilot |
| MS Dynamics 365 BC | Enterprise ERP | RO loc via partner | Yes | Overkill at pilot | EUR 10-30k impl + ~60-90/user/mo (est) - defer to scale |
| Senior ERP | RO mid-market ERP | Native RO, retail + WMS | Native e-Factura + SAF-T | Upper bound at 3+ stores + own hub | mid 4-5 figures impl (est) - scale option |
| SmartBill / FGO / Saga | RO SME invoicing+acct | Native RO | Native e-Factura + D406 | Right-sized 1-3 stores | SmartBill ~EUR 10-40/mo; Saga low/free; FGO low monthly (est) |
| Retail POS (RO fiscal): SmartCash/Magister/NextUp/OblioPOS | Retail POS + inventory + fiscal | Native casa-de-marcat AMEF | Via paired invoicing | Core of the pilot | POS ~EUR 30-80/till/mo + fiscal printer 300-600/till (est) |

### Recommendation (1-3 store launch budget) - LEAN RO-SME stack, not enterprise ERP
1. Retail POS with native RO fiscal + inventory/replenishment (SmartCash/Magister/NextUp class) (est) - tills, casa-de-marcat, stock-on-hand, reorder points, perishable batch/expiry. The operational backbone.
2. RO SME accounting + e-Factura/D406 (SmartBill or Saga) (est) - supplier e-invoices, retail e-Factura, SAF-T D406, VAT; integrate with POS sales journals.
3. Defer SAP B1 / Dynamics / Senior ERP until 3 stores + owned hub create real WMS/multi-entity finance complexity. Upgrading later is cheaper than carrying enterprise license through a 1-store pilot.

Estimated systems opex (1 store): ~EUR 100-250/month software (est) + fiscal hardware EUR 600-1,500 capex (1-2 tills) (est). At 3 stores ~EUR 300-600/mo (est); re-evaluate ERP upgrade then.

---

## 4. Inventory / replenishment policy

Premium-local, fresh-heavy -> high turnover, low standing stock, near-zero spoilage tolerance on the 70 chilled SKUs.

| SKU class | Policy | Reorder logic | Safety stock |
|---|---|---|---|
| Daily-fresh (bakery, leafy produce, fresh Bucuresti dairy) | Order-up-to daily; sell-through same day | Daily DSD, demand-driven | Minimal - under-stock preferred over markdown |
| Chilled dairy/meat (distant) | 2x/week consolidated cold runs; FEFO, batch/expiry in POS | Min-max short cycle; reorder tied to shelf-life days | 1 run buffer only |
| Produce | Buy-to-sell, short cycle; cull daily | Demand-pull | Low |
| Shelf-stable (honey, preserves, cereals, wine, other = 71) | Periodic review, larger lots OK | Min-max weekly/biweekly | Higher OK - no expiry risk, buffers distant gaps |
| Private label (36) | Contract-replenish to hub; shelf-stable | Min-max vs contract lead time | Moderate |
| Din lume import | Cash & carry buy-to-shelf; Macromex fish | Pull, no holding | None (C&C) |

Rules: FEFO mandatory on all chilled; POS enforces batch+expiry per producer CUI (also satisfies the traceability promise). Track shrink/waste % by category as a core KPI - fresh waste is the margin killer. Target spoilage low single-digit % on fresh (est, set after first 90 days actuals).

---

## 5. Estimated operating cost (all (est) - verify)

| Item | Phase 1 (1 store) | At 3 stores | Basis |
|---|---|---|---|
| Distant-cluster chilled consolidation / 3PL groupage | EUR 1,500-3,000/mo (est) | shared via hub | RO chilled groupage |
| Local DSD (carrier share / fuel) | low - supplier-borne or short van | EUR 1,000-2,000/mo (est) | metro short-haul |
| Shared city hub (lease + handling) | - (not yet) | EUR 1,500-3,000/mo (est) 150-250 m2 | RO peri-urban warehouse |
| Cold-chain in-store energy + maintenance | EUR 400-800/mo (est) | x3 | refrigeration running cost |
| Systems (POS + accounting + e-Factura/SAF-T) | EUR 100-250/mo (est) | EUR 300-600/mo (est) | sec.3 |
| Capex - cold-chain fit-out | EUR 25-45k (est) | per new store | sec.2 |
| Capex - fiscal POS hardware | EUR 600-1,500 (est) | per store | sec.3 |

Phase-1 logistics+systems opex rough band: ~EUR 2,000-4,500/month (est) (excludes rent, staff, COGS). Capex one-off: ~EUR 26k-47k (est) cold + POS. -> handed to business-plan.

---

## Handoff
- To business-plan: opex band + capex above (all flagged estimate; need refrigeration + 3PL + POS quotes to firm up).
- Open risks: (1) distant producer cold chain is the #1 brand/food-safety risk - budget loggers + reject protocol; (2) placeholder supplier CUIs must resolve before POS batch-traceability goes live; (3) hub timing tied to store #2 - do not build it early.
