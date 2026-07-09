---
name: terenuri-orchestrator
description: Orchestrate the MADR agricultural-land sale-offers pipeline — crawl the Legea 17/2014 offers feed, extract Anexa 1B fields with a ZERO-TOKEN local OCR stack (tesseract ron+eng), and load deduped land offers (seller, email, phone, area, price, county) into the land_offers store for AgroEvolution + land-liquidity intelligence. Use when asked to "scrape MADR land offers", "refresh terenuri", "get agricultural land for sale", "run the land-offers pipeline", "backfill the land archive", or when working in the TERENURI folder.
---

# terenuri-orchestrator

Coordinates the 3-agent MADR land-offers harness. **Execution mode: agent team** (pipeline, file handoff via `_workspace/`). All agents `model: opus`. Runs on raspibig (.21) where the OCR stack lives. Driver: `scrape_madr_offers.py`.

## Why this exists (business value)
One public feed → three products: (1) AgroEvolution land inventory + seller leads, (2) land-liquidity-by-county time series (a market-intel data product competitors lack), (3) SEO county-land pages. Each offer's Anexă carries a seller email/phone — direct land-brokerage leads.

## Team
| Stage | Agent | Skill | Output |
|-------|-------|-------|--------|
| 1 | madr-offer-crawler | madr-offer-crawl | `_workspace/01_crawler_offers.json` |
| 2 | anexa-extractor | anexa-extract (zero-token OCR) | `_workspace/02_extractor_offers.json` |
| 3 | land-offer-loader | (dedup + load) | `land_offers.csv` / DB + `_workspace/03_loader_result.json` |

## Phase 0: context check
- `_workspace/` absent → initial run (crawl → extract → load).
- partial ("just re-extract", "re-OCR the needs_review ones", "crawl new only") → run named stage(s); `--since-id` for incremental.
- backfill → crawl deep archive, OCR-heavy, run on raspibig with a generous timeout.

## Phase 1: crawl
madr-offer-crawler. County+locality from URL (free). 0 new offers → report empty, skip downstream.

## Phase 2: extract (ZERO-TOKEN)
anexa-extractor. Digital → pdftotext; scanned (~70%) → tesseract OCR ron+eng; regex / optional local Ollama. NEVER a paid API. <3 fields → needs_review. Email+phone are the lead-gold and survive OCR.

## Phase 3: load
land-offer-loader dedups by id (never reused), upserts, keeps needs_review + expired rows (the historical series IS the data product). Verdict + coverage (digital/ocr split, needs_review %, by-county).

## Error handling
One retry per stage. OCR tool missing → digital-only + flag needs_ocr, report. Never drop needs_review rows — they carry county/email leads.

## Test scenarios
- **Normal**: crawl 20 latest → 6 digital + 14 OCR → 17 with email/phone, 3 needs_review → loaded, verdict OK.
- **Backfill**: iterate IDs 1..737 on raspibig → full archive → land-liquidity series by county×month.
