# Tentacle: eures-scraper

## Machine
raspibig — tudor@192.168.100.21 (SSH key, never hostname)

## What It Does
Scrapes EURES EU job portal → deduplicates employers → classifies by sector (SQL) → feeds:
1. interjob_master DB
2. TikTok pipeline (norway flow → RO diaspora videos)
3. Brevo campaign segments

## Key Facts
- 129K jobs scraped, 2,404 unique employers deduped
- Resume logic: tracks last scraped job ID, skips duplicates
- Max 2 concurrent scrapers on raspibig — HARD LIMIT

## Scripts Location (raspibig)
/opt/ACTIVE/EURES/

## DB Tables (interjob_master, raspibig localhost:5432)
- eures_jobs — raw job posts
- eures_employers — deduped employer list
- tiktok_posts — 79 rows from first TikTok batch

## Cron — DISABLED (was 03:00 UTC)
Re-add after verifying resume logic works:
```bash
ssh tudor@192.168.100.21 'crontab -e'
# 0 3 * * * python3 /opt/ACTIVE/EURES/eures_scraper.py >> /opt/ACTIVE/EURES/eures.log 2>&1
```

## Log
/opt/ACTIVE/EURES/eures.log

## Rules
- Always resume — never full re-scrape
- Max 2 concurrent workers
- Playwright: laptop only, not raspibig
- After scrape: run sector SQL classifier, then feed TikTok norway pipeline
