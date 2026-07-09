# Scrapers Tentacle

## Scope
D:\MEMORY\DATA\ scraped sets + raspibig /opt/ACTIVE/SCRAPERS/

## Active scrapers on raspibig
- EURES: 129K jobs, 2,404 employers, max 2 workers (swap limit)
- ANOFM: 8,037+ contacts synced daily
- Norway daily (buildjobs.eu/no/)
- NanoClaw governor: 9 scrapers, Ollama diagnosis on failure

## Key data locations (symlinked to HDD /mnt/hdd/OPT_MIGRATION/)
- SCRAPERS/EUROPE/EUROPE/ROMANIA/ → HDD
- SCRAPERS/ROMANIA/MADR/ → HDD (821MB PDFs)
- SCRAPER_DATA/csv/EURES/ → HDD (2.3GB)
- OPENDATA/DATA/ → HDD (28GB)

## Rules
- Max 2 concurrent scrapers on raspibig (RAM limit)
- Playwright scraping: run locally on laptop, not raspibig
- Never run scrapers during campaign peak hours (09:00-17:00 EET)

## EU Funding Scrapers

All scripts live on **raspi** (192.168.100.20) at `/opt/ACTIVE/EU_FUNDING/`. Data is saved to PostgreSQL on raspibig (interjob_master). No cron entries — all were run manually in March 2026.

### SCRAPER_beneficiar.fonduri-ue (status: completed one-shot, not recurring)

Source: `https://beneficiar.fonduri-ue.ro:8080` — MIPE private EU beneficiary procurement data.

Scripts:
- `SCRAPER_beneficiar.fonduri-ue/CODE/beneficiar_fonduri_ue_scraper.py` — synchronous single-worker scraper, original version
- `SCRAPER_beneficiar.fonduri-ue/CODE/parallel_scraper.py` — multi-process parallel version
- `SCRAPER_beneficiar.fonduri-ue/CODE/async_scraper.py` — async aiohttp+Tor version, final production scraper (CONCURRENT=5, RATE_LIMIT=2 req/s)
- `DATA/async_scraper.py` — duplicate/staging copy of async_scraper.py kept in DATA/

DB tables populated:
- `beneficiari_privati` — ~48,000 procurement announcements (company, CUI, phone, email, county, budget, contract type)
- `proiecte` — ~16,000 EU projects with SMIS codes

Data files (on raspi):
- `SCRAPER_beneficiar.fonduri-ue/DATA/beneficiari_privati.csv` (132KB)
- `SCRAPER_beneficiar.fonduri-ue/DATA/proiecte.csv` (40KB)
- `SCRAPER_beneficiar.fonduri-ue/DATA/beneficiar_fonduri_ue.csv` (44KB)

Last run: 2026-03-17 (async.log 88KB, proiecte_raspi.log 49KB). Not in cron.

### PNRR (status: partial, abandoned mid-run)

Source: public PNRR project portal (Selenium/Firefox-based).

Scripts:
- `PNRR/scrape_distributed.py` — distributed scraper, raspibig goes backwards from last page, raspi goes forwards from page 1; saves to raspibig DB
- `PNRR/pnrr_worker.py` — Selenium worker server that can run standalone or respond to HTTP API calls (port 5055)
- `PNRR/run_forwards.sh` — launcher: `python3 scrape_distributed.py --mode forwards --stop-at 10000 --db-host 192.168.100.21`

State (`distributed_state.json`): forwards reached page 1000/~20000 (10,000 of 19,999 records scraped) as of 2026-03-17. Backwards run on raspibig status unknown. Not in cron. Likely needs resume.
