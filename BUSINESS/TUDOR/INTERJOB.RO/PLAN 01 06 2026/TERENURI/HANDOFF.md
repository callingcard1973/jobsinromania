# TERENURI — MADR Land-Offers Harness — HANDOFF (2026-06-27)

Status: **pipeline LIVE end-to-end** (scrape → OCR → extract → DB). Backfill in progress.

## What this is
Scrapes the MADR agricultural-land sale-offers feed (Legea 17/2014 extravilan,
`madr.ro/terenuri-agricole/`) → extracts Anexa 1B fields (seller, email, phone,
area ha, price, county) with a **zero-token** OCR stack → loads `land_offers`.
Three products: AgroEvolution land inventory + seller leads, land-liquidity-by-county
data product, SEO county-land pages.

## Current state (2026-06-27)
- **DB table** `interjob_master.land_offers` on raspibig (.21), PK = offer id.
  Loaded so far: **122 offers, 47 emails, 25 phones (~45% have a contact lead).**
- **Backfill RUNNING** on the laptop (background task `bpbkp23th`), crawling IDs
  downward (was at id ~603 of max 737). Writes `TERENURI/land_offers_full.csv`
  (gitignored — seller PII). Stream-writes + resumable.
- **Speed is the constraint:** EasyOCR on CPU ≈ 2 min/offer (~70% scanned) → full
  737 archive ≈ 30h single-process.

## Key facts / gotchas
- **raspibig Pi CANNOT OCR** (tesseract >300s/page) → OCR runs on the LAPTOP.
- OCR stack installed user-space (no admin): `pip install --user pymupdf easyocr`.
  EasyOCR text quality is excellent; yield came from fixing brittle regex, not OCR.
- OCR quirks handled in regex: TLD dot→space (`agriterenuri ro`→.ro), `ț`→`j`/`t`
  garble (`prejul`), `Subscrisa,`/`Subsemnatul` seller forms, CUI capture.
- SSH: `plink -batch -pw <pwd> tudor@192.168.100.21` (pwd in CLAUDE.md key conventions).

## Files
- `scrape_madr_offers.py` — crawler+extractor. Resumable (skips ids already in CSV),
  stream-writes. `OCR_BACKEND=easyocr` (laptop) | `tesseract`.
- `load_land_offers.py` — idempotent upsert CSV → `land_offers` (dedup by id).
- `.claude/` — 3 agents (madr-offer-crawler → anexa-extractor → land-offer-loader)
  + 3 skills + `terenuri-orchestrator`.
- Commits: 09cb1a9, abb57b5, 75b130f, 5ec52b4.

## RESUME — how to continue later
```bash
cd "D:/MEMORY/BUSINESS/TUDOR/INTERJOB.RO/PLAN 01 06 2026/TERENURI"
# 1. continue/finish the crawl (skips already-done ids):
OCR_BACKEND=easyocr python scrape_madr_offers.py 40 land_offers_full.csv
# 2. load (idempotent) — scp CSV to raspibig then:
python3 load_land_offers.py /tmp/land_offers_full.csv   # on raspibig
```

## OPEN / next
1. **Faster backfill:** run 3-4 scraper procs over split ID ranges (resume design
   supports it) → ~8h instead of ~30h. (Or just let it run + reload daily.)
2. Build **land-liquidity-by-county report** (PDF/CSV data product) off the table.
3. Generate **SEO county-land pages** ("teren agricol de vanzare {judet}").
4. Decide canonical home: keep on `interjob_master.land_offers`. agroevolution.com
   is no longer Tudor's — publish land pages on a domain he owns.
