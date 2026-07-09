---
name: madr-offer-crawl
description: Crawl the MADR agricultural-land sale-offers feed (Legea 17/2014 extravilan) — oferte.html, arhiva.html, and sequential offer IDs — collecting detail URL, county, slug, date, and Anexa PDF link per offer. Use when discovering new land-sale offers, refreshing the MADR offer list, or backfilling the archive.
---

# madr-offer-crawl

Enumerate the MADR land-sale offers at `madr.ro/terenuri-agricole/`. Driver: `scrape_madr_offers.py` (list stage).

## Structure (verified)
- `oferte.html` = latest ~5; `arhiva.html` = paginated full history (`?start=N*20`).
- Offer URLs: `/terenuri-agricole/{judet}/{id}-{slug}.html` with **sequential numeric IDs**.
- Offers valid 45 days; IDs never reused → ID is the durable dedup key, and `--since-id` gives clean incremental crawls.

## Procedure
1. Walk archive pages (or iterate IDs above last-seen max).
2. Per offer: capture `id, judet, slug, detail_url` (county+locality are in the URL — free, no PDF needed) and follow to the detail page to grab the **Anexa PDF href** + publication date.
3. Write `_workspace/01_crawler_offers.json`.

## Why ID-based, not scrape-the-list-only
Pagination on gov sites breaks; sequential IDs don't. Backfilling the whole history (the land-liquidity time series) is just iterating IDs downward — robust against layout churn.

## Politeness
Real User-Agent, ~1.5s delay, per-offer try/except. One dead page never aborts the crawl. This is a public gov feed — stay gentle.

## Failure modes
- 0 results on a page → archive end, stop (not an error).
- No PDF link on an offer → keep the URL row, flag `no_pdf`; extraction skips it.
