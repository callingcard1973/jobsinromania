# 02 - HAMBARUL ROMANESC Catalog & Pricing Summary

**Date:** 2026-06-24 - **Author:** catalog-pricing agent - **Input:** 01_suppliers_master.csv (15,721 suppliers, 61 counties) + 00_market_study.md

**Assortment:** 156 SKUs across 10 Romanian categories. Positioning = **premium-local** (benchmark vs Mega Image/Carrefour premium, NOT Lidl/Penny discount). Margin math: `retail = cost / (1 - target_margin)`, RO food VAT = 9%. **All costs are estimated** from RO category benchmarks (no audited supplier cost sheet yet - flagged `(estimated)` in CSV).

## 1. Margin & premium by category

| Category | SKUs | Target GM% | Avg shelf (RON) | Avg premium vs discounter | Supplier depth (master) |
|---|---|---|---|---|---|
| dairy | 22 | 32% | 22.9 | +11.0% | 7272 sup / 96 email / 0 CUI |
| produce/vegetables | 22 | 30% | 9.5 | +2.3% | 858 sup / 359 email / 0 CUI |
| meat/charcuterie | 20 | 30% | 57.9 | +9.9% | 1120 sup / 99 email / 0 CUI |
| preserves/conserve | 18 | 42% | 20.6 | +24.3% | 39 sup / 25 email / 0 CUI |
| cereals/grain | 16 | 33% | 14.1 | +11.3% | 2628 sup / 717 email / 751 CUI |
| bakery | 15 | 35% | 17.3 | +12.8% | 1878 sup / 0 email / 0 CUI |
| other/traditional | 15 | 45% | 20.6 | +32.7% | 78 sup / 49 email / 0 CUI |
| honey | 12 | 45% | 48.0 | +32.7% | 1454 sup / 0 email / 0 CUI |
| wine/tuica | 10 | 45% | 58.2 | +36.0% | 5 sup / 2 email / 0 CUI |
| eggs | 6 | 28% | 19.4 | +4.1% | 168 sup / 0 email / 0 CUI |

**Premium discipline:** highest premiums sit on shelf-stable, story-rich categories (honey +33%, wine/tuica +36%, traditional +33%, preserves +24%) where origin + traceability justify the markup. Fresh categories (produce +2%, eggs +4%, dairy/meat +10-11%) stay close to mainstream to remain credible on the weekly basket. Blended catalog gross margin ~36%.

## 2. Private-label opportunities (HAMBARUL brand)

**36 SKUs flagged** for HAMBARUL private label - shelf-stable, contract-produceable, where a HAMBARUL-branded SKU from a contract producer beats buying a national brand on margin and reinforces the origin promise:

- **honey** (8 SKUs): Miere de salcam, Miere de tei, Miere de mana padure, Miere poliflora, Miere de rapita, Miere de floarea-soarelui (+2 more)
- **preserves/conserve** (15 SKUs): Zacusca de vinete traditionala, Zacusca de ciuperci, Zacusca de fasole, Bulion de rosii de casa, Pasta de tomate concentrata, Gem de prune fara zahar (+9 more)
- **cereals/grain** (10 SKUs): Faina alba tip 000 de Banat, Faina integrala de grau, Malai extra din porumb romanesc, Malai de porumb vechi creata, Faina de secara, Faina de hrisca (+4 more)
- **other/traditional** (3 SKUs): Saramura de branza in ulei, Boia de ardei dulce, Otet de mere natural

Rationale: these categories have long shelf life (no spoilage risk on own-brand inventory), simple contract-manufacturing, and the widest cost-to-national-brand gap. A HAMBARUL miere de salcam / zacusca / magiun / faina line captures the full margin instead of splitting it with a national brand, and every jar carries a producer CUI = the traceability promise.

## 3. Sourcing notes (thin supplier depth - back to supplier-sourcing)

Categories with adequate master depth but **weak contactability** (low email/CUI coverage) - need enrichment before contracts:

| Category | Issue | Action |
|---|---|---|
| wine/tuica | only **5 suppliers** in master, 2 with email - thinnest category vs 10 SKUs planned | URGENT: source 15-20 verified distillers/wineries (Vrancea, Bistrita, Maramures, Dealu Mare) |
| preserves/conserve | **39 suppliers** only, 25 email - thin for 18 SKUs | source 30+ conserve/zacusca workshops; overlaps private-label contract producers |
| eggs | **168 suppliers**, 0 email, 0 CUI | enrich contact data; eggs are a footfall staple |
| honey | 1,454 suppliers but **0 email, 0 CUI** | phone-first outreach; CUI/email enrichment needed for contracts |
| bakery | 1,878 suppliers but **0 email, 0 CUI** | enrich; bakery is daily-fresh, needs metro-local suppliers per store |
| dairy | 7,272 suppliers but **only 96 email, 0 CUI** | largest category, worst CUI coverage - priority enrichment |

Only **cereals/grain** has real CUIs (751) - all 16 cereal SKUs tie to verified supplier CUIs. Every other SKU uses a `PLACEHOLDER-<CAT>` CUI pending supplier-sourcing enrichment. **Traceability is the brand promise - placeholder CUIs MUST be resolved to real CUIs before launch.**

## 4. Import long-tail (gaps -> hand to import-distribution)

These are **non-local / non-Romanian** lines a full grocery basket needs but the origin-pure model cannot source domestically. Out of HAMBARUL catalog scope; route to import-distribution as a clearly-separated 'din lume' shelf so they do NOT dilute the Romanian promise:

- **Citrus & tropical:** lamai, portocale, banane, mango, ananas, avocado, kiwi
- **Coffee, cocoa, tea (non-RO):** cafea boabe/macinata, ciocolata, cacao, ceaiuri exotice
- **Fish & seafood:** somon, ton, creveti, peste oceanic (RO has limited freshwater/Black Sea only)
- **Exotic/dry goods:** orez basmati, paste italiene, masline, ulei de masline, condimente exotice, nuci import (caju, migdale, fistic)
- **Non-food:** detergenti, hartie, cosmetice, hrana animale - if stocked, source via distributors
- **Out-of-season produce:** winter tomatoes/berries when RO season closed - import-distribution decides import vs gap-on-shelf

## 5. Handoffs
- -> **brand-marketing:** hero Romanian-made SKUs = Salam de Sibiu, Miere de salcam, Magiun de Topoloveni, Pastrama, Telemea de oaie, Tuica de Bistrita. SEO/story pages per producer CUI + county.
- -> **logistics-supply:** perishables (dairy, meat, bakery, produce, eggs = ~85 SKUs) need cold-chain + daily metro-local replenishment; shelf-stable (honey, preserves, cereals, wine, traditional = ~71 SKUs) tolerate central warehousing.
- -> **supplier-sourcing:** resolve placeholder CUIs + sourcing gaps in section 3 (wine/tuica + preserves urgent).

*All retail prices derived from estimated costs; refresh once supplier cost sheets are signed. Discounter benchmarks are typical RO shelf prices for comparable generic items (estimate), used only to quantify the premium.*