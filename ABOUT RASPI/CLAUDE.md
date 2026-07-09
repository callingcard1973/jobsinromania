# ABOUT RASPI — operating reference (192.168.100.20)

**Reconstructed 2026-06-25 from sourced memory + root CLAUDE.md** (the canonical folder was missing; rebuilt only from sourced material — no fabrication). Single source of truth for *how raspi runs*. Read before touching raspi work. Do NOT duplicate elsewhere.

---

## Role

**Scraper node.** Heavy scraping + the full ANOFM pipeline + a local PostgreSQL, kept off raspibig so raspibig stays responsive. **Zero Telegram bots, zero email — except the ANOFM campaign send (see below).** Source: root CLAUDE.md infra table; `raspi_skills_complete`; `feedback_raspibig_raspi_rules`.

| Machine | IP | Role |
|---------|-----|------|
| raspi | 192.168.100.20 | scraper node + ANOFM pipeline (`/opt/ACTIVE/INFRA/SKILLS`, 640 synced) |
| raspibig | 192.168.100.21 | primary automation hub (campaigns, LLM, DB `interjob_master`) |

SSH from laptop: `plink -batch -pw '<pw in memory raspibig_ssh_password>' tudor@192.168.100.20 "<cmd>"`. raspi→raspibig is keyless ssh (used by push/rsync below). Source: `feedback_raspibig_raspi_rules`; `anofm_offers_50col`.

---

## ANOFM pipeline (FULL — runs HERE on .20, not raspibig)

User correction 2026-06-24, verified live. After consolidation, raspibig does NO ANOFM work. Source: `anofm_host_map`.

**1. Scraper** — `anofm_scraper.py` (in `/opt/ACTIVE/INTERJOB/`); raw CSVs land in `/opt/ACTIVE/ANOFM_DATA/csv/` (`anofm_jobs_latest.csv` + `_archive/anofm_raw_manual_*.csv`). Cron-driven (not systemd timers). A `run_parallel_scrapers.sh`-style parallel run feeds the CSV dir. Source: `anofm_host_map`; `anofm_offers_50col`.

**2. Ingest** — `ingest_anofm.py` → local **`anofm_db.ij_jobs`**. Note: `interjob_master` is *raspibig's* DB name; on raspi the local DB is `anofm_db`. Source: `anofm_host_map`.

**3. Campaign** — `campaign_anofm_angajatori.py` in `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/`. Cron `0 9 * * 1-5 … --limit 150 --delay 8` (150/day, Mon–Fri). Reads the 7-col dedup audience (`anofm_angajatori_dedup.csv`). Source: `anofm_host_map`.

**4. Daily report** — `anofm-daily-report.timer` @ 04:00 → `anofm_daily_report.py`, reads `anofm_db.ij_jobs`, sends Telegram. Migrated to raspi 2026-06-24. Test: 13,904 active jobs, Telegram OK. Source: `anofm_host_map`.

**5. Health** — `anofm_pipeline_health.py` cron `0 */6 * * *`. Source: `anofm_host_map`.

**Audience rebuild + DNC:** suppression = DNC + `sent.csv` merged on raspi (445 overlap dedup fixed double-send). `master_dnc.csv` is rsync'd from raspibig `:/opt/ACTIVE/INFRA/BACKUPS/master_dnc.csv` (~7,958 rows; bounce_manager runs only on raspibig). raspi's own `dnc_bounces.txt` is empty. Source: `anofm_host_map`; `anofm_offers_50col`.

**Legacy `anofm` DB** now lives on raspi (`createdb -O tudor anofm` + restore): jobs ~145,586, dnc 4,419, send_log 788, schema `raspi_import`. ~10 on-demand consumer scripts (fb_workers_post, dedup_*, dashboard_senders, campaign_dashboard) are synced skills running against this local `anofm`. raspibig's legacy `anofm` DB was dropped. Source: `anofm_host_map`.

### push_csv_to_raspibig.sh — feeds raspibig's ij_jobs
raspi cron pushes ANOFM CSVs to raspibig so raspibig's `anofm-ingest.timer` can populate its `ij_jobs` replica (for news-roundup + catalog products only). Schedule: rsync at **08:45 / 12:45 / 16:10**, before raspibig ingest at **09:00 / 13:00 / 16:30**. Source: `anofm_host_map`.

### ANOFM 50-column offer list (standby)
`build_offers_50col.py` (in `ANOFM_ANGAJATORI/`) → `DATA/anofm_offers_SENDABLE_50col.csv` (~1,290 employers, full 50-col scrape schema; ANOFM schema is **50 cols, not 52**). Cron `0 17 * * 1-5`. NOT used by the live campaign (which reads the 7-col dedup). Source: `anofm_offers_50col`.

---

## EU wholesale market scrapers

EU wholesale market scrapers run on raspi via cron, from `/opt/ACTIVE/INFRA/SKILLS`. Part of the CumparLegume / EU-markets pipeline (Rungis, Berlin, Madrid, etc.). Source: root CLAUDE.md scraper registry; `feedback_raspibig_raspi_rules` (heavy scraping stays on raspi).

Other long-running scrapers per `raspi_skills_complete` (point-in-time, verify before asserting): `ted_scraper.py`, `seap_ro_scraper.py`, `eures_scraper.py`. Max 2 concurrent scrapers enforced by watchdog. EURES needs Firefox + geckodriver. MADR scraper has a known EPIPE memory issue on large runs.

---

## Skills sync

raspi is a **sync target**, not the master. Master = laptop `D:\MEMORY\CODE\ACTIVE\SKILLS\` (640 .py). raspi target: **`/opt/ACTIVE/INFRA/SKILLS/`** (synced to 640), with symlinks from `/opt/SKILLS` and `/opt/ROMANIA/SKILLS`. Sync on-demand / weekly Sunday 04:00 UTC across laptop ↔ raspibig ↔ raspi. Source: root CLAUDE.md Skills Synchronization; `feedback_raspibig_raspi_rules`.

---

## Runtime / DB

- **Python:** system `/usr/bin/python3` — **no venv** on raspi. Source: `anofm_host_map`.
- **PostgreSQL:** local, port 5432 (NOT 5433). Listens on **localhost only** — services use `PGHOST=localhost`. Local DBs incl. `anofm_db` and the legacy `anofm`. Source: `anofm_host_map`; `feedback_raspibig_raspi_rules`.
- **ProtonVPN WireGuard** required for Zoho-related SMTP traffic (`proton-nl`, auto-start enabled). Source: `raspi_skills_complete`; `feedback_raspibig_raspi_rules`.
- Other services per `raspi_skills_complete` (verify before asserting): Node-RED, Caddy (HTTPS), `bot_watchdog.py` (7-service raspi variant), `nanoclaw.py` ops monitor.

---

## Coding rules (raspi + raspibig)

250-line max/file · shebang `#!/usr/bin/env python3` + one-liner docstring + `main()` + `if __name__`. Async I/O (aiohttp/asyncio; wrap psycopg2 in `asyncio.to_thread`). Comments WHY-only. Error handling at boundaries only. **Archive before delete** (SELECT count → INSERT archive → DELETE). No TODO placeholders. Source: root CLAUDE.md Coding Standards; `feedback_raspibig_raspi_rules`.

**Before writing new code:** SSH and check `/opt/ACTIVE/` first — ~70–80% already exists. Never recreate live DB tables. Never rotate passwords/SSH/tokens unless asked. Never deploy to A2 via SSH. **Git: never commit/push without explicit instruction.** Source: root CLAUDE.md GIT RULES; `feedback_raspibig_raspi_rules`.

---

## Gaps / unknowns (not in sources — verify live before asserting)

- Exact filename `run_parallel_scrapers.sh` and its full cron line — implied by prompt; not literally in memory (`anofm_scraper.py` is the named scraper).
- The exact cron lines for EU wholesale scrapers and `push_csv_to_raspibig.sh`.
- `raspi_skills_complete` is 48 days old; service/scraper list is point-in-time.
- Whether raspi scrapers write to a local `scraper` DB (older note) vs `anofm_db`/`anofm` (newer ANOFM note) — both appear in sources at different dates.

*Related memory: `anofm_host_map`, `anofm_offers_50col_2026_06_24`, `raspi_skills_complete`, `feedback_raspibig_raspi_rules`, `raspibig_ssh_password`.*
