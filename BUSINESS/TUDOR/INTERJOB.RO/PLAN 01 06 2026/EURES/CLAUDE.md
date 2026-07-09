# EURES — Knowledge Base & Pipeline Reference

**v1.0 | 2026-06-26** — consolidated from a full live audit. Single source of truth for EURES.

> **HOST RULE:** EURES runs **ONLY on raspibig (192.168.100.21)**. Never on raspi (.20 = ANOFM only) or laptop. raspi EURES traces were dead leftovers, removed/archived 2026-06-26. (Reciprocal of the ANOFM host split.)

EURES = the EU public Job Mobility Portal (European Employment Services). We scrape EU vacancies + employer contacts to (a) publish jobs to InterJob domains and (b) build B2B leads (EU employers actively hiring foreign labor).

---

## TL;DR — the corrected reality (read this first)

1. **The scraper WORKS.** A Playwright/Firefox worker scraped 264 jobs / 155 emails (0 errors) on 2026-06-26 01:38, across PL,CZ,SK,HU,RO,BG.
2. **Row counts are massively inflated by duplication.** The real contactable asset is **~5,233 unique EU employer emails**, NOT 182K or 107K. Each employer repeats once per vacancy (big staffing agencies post dozens).
3. **Two real defects:**
   - **DB disconnect** — the live scraper writes to `scraper.contacts_50`; the orchestrator + consumers read `interjob_master.eures_jobs` (=0). Different DB+table → "0 jobs added" every night.
   - **Email extraction is weak** — in `scraper.contacts_50`, 180,192 / 182,766 rows (98.6%) have an EMPTY email. Only ~2,548 rows carry a real email.
4. **Normalize stage has TWO blockers (both found 2026-06-26):**
   - (a) FIXED — `eures_normalizer.py` was missing from `/opt/ACTIVE/EURES/`; copied in (`--help` rc=0).
   - (b) **STILL BROKEN** — `eures_normalizer.py` hardcodes `DB_CONFIG = {'dbname': 'csv_raw'}` (line 17). **`csv_raw` DB exists on raspi (.20), NOT on raspibig (.21).** So `--normalize-all` crashes: `database "csv_raw" does not exist`. The whole pipeline was authored against raspi's DB layout, then EURES landed on raspibig without migrating the `csv_raw` staging DB. **This is why EURES never worked on raspibig.**
5. **classify stage works** (runs, "Classified 0 jobs" — 0 only because `eures_jobs` is empty from the disconnect).
6. **enrich stage WIRED 2026-06-26** — added `enrich()` to `eures_orchestrator.py` (runs fast_enrich + mx_email_guesser + whois_enricher, best-effort/non-fatal, between normalize and classify; `--enrich` CLI). Not yet exercised end-to-end because normalize fails upstream (blocker 4b). Backup: `eures_orchestrator.py.bak_20260626_enrich`.

---

## Data inventory (verified 2026-06-26)

| Table | DB | Rows | Rows w/ real email | **Unique real emails** | Notes |
|-------|-----|------|--------------------|------------------------|-------|
| `contacts_50` | `scraper` | 182,766 | 2,548 | **2,548** | LIVE scraper target. 98.6% empty email. cols: id,fingerprint,company_name,email_1,phone_1,job_title,country,source,scraped_at,employer_type |
| `eures_employers_50plus` | `interjob_master` | 107,445 | 104,263 | **2,538** | Heavy dup (~40 vacancies/employer). Rich cols: address,city,postal,website,org_number,contact_person,email_1/2/3,phone_1/2/3,occupation,sector,salary,source_url |
| `eures_contacts` | `interjob_master` | 2,723 | 2,723 | **2,723** | CLEAN curated table — 100% real unique emails. cols: country,employer,contact_person,email1/2,phone1/2/3,positions_count,job_count,quality_score |
| `eures_jobs` | `interjob_master` | **182,741** | n/a (jobs) | n/a | ✅ POPULATED 2026-06-26 via `eures_ingest_contacts.py`. 100% sector-classified. What catalogs/roundup/classify read. |

**COMBINED unique real emails (emp50plus ∪ eures_contacts) = 5,233.** `eures_contacts` (2,723) is the cleanest subset. contacts_50's 2,548 overlap heavily.

**Country spread (real emails, emp50plus):** Sweden 34k rows, Norway 26k, Finland 13k, Poland 12k, Denmark 4k, Belgium 2.4k — collapsing to the ~2,538 unique.

---

## Where everything lives (raspibig)

**Pipeline harness:** `/opt/ACTIVE/EURES/`
- `eures_orchestrator.py` — production harness. `--run-full` / `--scrape-only` / `--classify` / `--status`. Cron `0 3 * * *` via `eures_cron.sh` → log `/tmp/eures_cron.log`.
- `eures_normalizer.py` — normalize/email-extract (restored 2026-06-26). `--scan --table --extract-emails --normalize-all`.
- `eures_germany_enricher.py`, `eures_agency_finder.py`, `eures_instant_send.py`, `sync_eures_data.py`, `eures_dashboard.py`
- `state.json` — last run state (currently shows stale pre-fix normalize error).

### The REAL scraper (always-on) vs the orchestrator's old fake scrape
- **Real engine:** `run_forever_raspibig.sh` + systemd `eures-expansion.service` (active). Persistent 2-worker loop, **14 EU countries, max_pages 9999, 50/page, LAST_WEEK incremental**, 2h cycles. Writes `scraper.scraped_jobs` (raw, **273k+ and growing**) + `scraper.contacts_50` (extracted contacts, 182k). Args pattern: `eures_scraper.py 1 9999 50 <countries> 1 LAST_WEEK`.
- **Why a `--run-full` "scrape" took only 154s (FIXED 2026-06-26):** the orchestrator's `run_scraper()` called `eures_scraper.py 1` with no args → defaults to 1 country (Belgium), 10 pages, binary-search-skip of already-seen → no-op. It never did real work. Replaced with `check_live_scraper()` (status-only: reports run_forever alive + scraped_jobs count, never gates). `--scrape-only` + `run-full`'s scrape stage now just report status. Real scraping stays on run_forever/eures-expansion. Backup `eures_orchestrator.py.bak_20260626_scrapestage`.
- EURES's "millions" accumulate incrementally via the persistent loop (LAST_WEEK = only new postings per cycle), not in one fast pass.

**Actual scraper (the part that works):** `/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/`
- `eures_scraper.py` (Playwright; invoked `python3 eures_scraper.py <page>`). Worker logs in `OUTPUT/LOGS/<countries>/`.
- Core: `scraper_core.py`, `scraper_config.py`, `browser_manager*.py`, `job_processor.py`, `contact_extractor.py`, `csv_writer.py` (writes to DB `scraper`, table `contacts_50`/`contacts_50`-family, `PG_DATABASE` defaults to `scraper`).
- Enrichers: `fast_enrich_eures.py`, `whois_enricher.py`, `mx_email_guesser.py`, `impressum_crawler.py`, `eures_country_enricher.py`.
- Playwright browsers installed: chromium-1187, firefox-1490 (OK).

---

## The two fixes (open work)

### Fix A — reconnect the pipeline ✅ DONE 2026-06-26 (Option 1)
Root cause was: `eures_normalizer.py` read DB `csv_raw` (raspi-only) and only ever built `normalized_*` tables there — it never wrote `eures_jobs`. So even on raspi the consumers stayed empty.
**Resolution:** new script `eures_ingest_contacts.py` (in this folder + `/opt/ACTIVE/EURES/`) reads `scraper.contacts_50` → upserts distinct vacancies into `interjob_master.eures_jobs` (job_id = md5(company|title|country), ON CONFLICT DO NOTHING). Orchestrator's `normalize()` now calls this ingest instead of the dead normalizer (backup `eures_orchestrator.py.bak_20260626_ingest`).
**Result:** `eures_jobs` 0 → **182,741** vacancies, **100% classified** by sector (Hospitality 4,823 · Sales 2,537 · Manufacturing 2,170 · Transport 1,016 · Construction 502 · Healthcare 283 · Agriculture 213 · Education 123 · …). normalize stage 11s, classify clean.
**Note:** `eures_jobs` is jobs-only (no email col) — for catalogs/roundup. Lead emails stay in `eures_contacts` (2,723) / enrich tables. The old `eures_normalizer.py` (csv_raw) is now unused/dead.

### Fix B — raise email yield (the real value lever)
98.6% of scraped rows have no email. The enrichers exist but aren't in the nightly path: `fast_enrich_eures.py`, `whois_enricher.py`, `mx_email_guesser.py`, `impressum_crawler.py`, `eures_germany_enricher.py`. Wire enrichment into the orchestrator AFTER scrape to lift 2.5k → much higher. This is where the marketplace value is (more EU employers reachable).

---

## Monetization (current, honest)

- Usable NOW: **~2,723 clean EU employer emails** (`eures_contacts`) + up to 5,233 deduped across sources. NOT 182K.
- Use: B2B campaign offering RO/EU workers to EU employers (Sweden/Norway/Finland/Poland skew). Host raspibig, ASCII templates, DNC-dedup. Do NOT auto-launch — Tudor decides.
- See memory [[eures-pipeline-diagnosis-2026-06-26]], [[anofm-host-map]], [[brevo_keys_all]].

---

## Employer Outreach Harness (built 2026-06-26, ALL DISABLED)

ANOFM-style multi-sender campaign to offer RO/EU workers to EU employers from EURES. Files in this folder + `/opt/ACTIVE/EURES/`. Skill `eures-employer-outreach` + agent `eures-outreach-orchestrator`.

- `build_audience.py` → `eures_audience_sendable` (**4,916 sendable**: dnc=7,958 stripped, sent=0). Routes sector→sender (EN+Swedish keywords). Today: warehouse 4,763 (GENERAL/no-sector), care 82, build 30, factory 24, horeca 17.
- `eures_outreach_orchestrator.py` (`--dry-run`) — ramp cap, queue minus send_log, claim `INSERT ON CONFLICT(email)` (DB-unique), `sender.send_brevo`, delay 3-6min. Verified no-op when all disabled.
- `senders.json` — 6 domains, ramp 30→150, **enabled:false ALL**.
- `templates/` — 8 sector + 2 follow-up, ASCII, opt-out footer. `digest.py`. `systemd/` units (written, NOT installed).
- Tables: `eures_send_log UNIQUE(email)` + `eures_audience_sendable` on interjob_master.

**To launch:** pilot Construction→buildjobs.eu, set enabled:true cap 30, dry-run. Tudor decides.
**Open:** 4,763 lack sector→GENERAL (fix: join eures_jobs classified sectors by company); 3 domains IP-allowlisted (A2 fallback); ~5k email ceiling → enrichment.

## Orchestrator-driven (2026-06-28)

EURES_OUTREACH is now registered in `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json` and launched by `campaign-orchestrator.service`, the single entrypoint shared with the other 24 campaigns. No standalone systemd timer.

- Entry: `type=python`, `script=/opt/ACTIVE/EURES/eures_outreach_orchestrator.py`, `daily_limit=150`, `brevo_account=BPPLTD`.
- The orchestrator passes `--limit` / `--delay` / `--daily-cap`; these are accepted but ignored — real caps live in `senders.json` (per-sender ramp 30→150).
- The script self-builds its audience at start (calls `build_audience.py`), so no separate audience step is needed.
- Standalone `eures-outreach.timer` + `eures-audience.timer` are DISABLED (no double-run). `flock /tmp/eures_outreach.lock` guards against overlap.

## Change history

| Date | Change | Detail |
|------|--------|--------|
| 2026-06-26 | Full audit + normalizer fix | Diagnosed DB-disconnect + 98.6% empty-email; restored missing `eures_normalizer.py` to `/opt/ACTIVE/EURES/`; corrected "182K monetizable" → ~2.7–5.2k real. Removed dead EURES from raspi (archived). |
| 2026-06-28 | Orchestrator-driven | Registered EURES_OUTREACH in `campaigns.json` (type=python, BPPLTD, daily_limit 150); launched by `campaign-orchestrator.service` like the other 24 campaigns. Disabled standalone eures-outreach.timer + eures-audience.timer (flock-guarded, no double-run). Script self-builds audience at start. |

## Inspect commands

```bash
# real contactable count
PGHOST=localhost psql -U tudor -d interjob_master -tAc \
 "select count(distinct e) from (select lower(email1) e from eures_contacts where email1~'@'
   union select lower(email_1) from eures_employers_50plus where email_1~'@') x"
# live scraper output freshness
PGHOST=localhost psql -U tudor -d scraper -tAc "select count(*) from contacts_50 where email_1 ~ '@'"
# nightly pipeline status
cat /opt/ACTIVE/EURES/state.json; tail -20 /tmp/eures_cron.log
```
