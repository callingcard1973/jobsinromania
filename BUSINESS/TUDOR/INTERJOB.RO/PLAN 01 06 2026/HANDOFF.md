# HANDOFF — InterJob Engine

**Status:** 2026-06-01 Session 4 Final | **Mode:** Upgrade & extend (70-80% exists)

---

## 0. CRITICAL: 70-80% of System Already Exists

This is NOT greenfield. Key infrastructure on raspibig:
- PostgreSQL interjob_master (434 tables, 9,087 jobs)
- Production ingest/build/deploy pipeline (working daily)
- 14 live domains generating HTML weekly
- farmworkers.eu CV pipeline (221 applicants)

See `/opt/ACTIVE/INTERJOB/` and `/opt/ACTIVE/FARMWORKERS/` on raspibig.

---

## 10. PICK-UP STATE — FINAL (2026-06-01 SESSION 4)

### ✅ COMPLETED THIS SESSION

**JobsInRomania Daily Pipeline (✅ LIVE & PRODUCTION):**
- ✅ GitHub repo: https://github.com/callingcard1973/jobsinromania/
- ✅ Live site: https://callingcard1973.github.io/jobsinromania/index.html
- ✅ Deployed to raspibig: `/opt/ACTIVE/JOBSINROMANIA/`
  - `generate_romania_jobs.py` — PostgreSQL ij_jobs → 1,533 Romania jobs
  - `build_romania_pages.py` — single searchable index.html (#e65100 branding)
  - `deploy_github.py` — auto-commit + SSH push to GitHub
  - `daily_build.sh` — orchestrator with logging
- ✅ Cron: `0 2 * * * bash /opt/ACTIVE/JOBSINROMANIA/daily_build.sh` (2 AM UTC)
- ✅ Full pipeline tested end-to-end (extract → build → deploy all pass)
- ✅ GitHub Pages active (/docs folder source)
- ✅ Client-side search (title/city/sector filter)

**WordPress /wp/ Installation (8 confirmed LIVE):**
- ✅ buildjobs.eu/wp/ (REST API 200)
- ✅ meatworkers.eu/wp/ (REST API 200)
- ✅ factoryjobs.eu/wp/ (REST API 200)
- ✅ warehouseworkers.eu/wp/ (REST API 200)
- ✅ careworkers.eu/wp/ (REST API 200)
- ✅ mechanicjobs.eu/wp/ (REST API 200)
- ✅ internaltransfers.eu/wp/ (REST API 200)
- ✅ horecaworkers2026.eu/wp/ (REST API 200)
- ✅ Credentials: `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env`

### ⏸ REMAINING WORK

**WordPress: 5 remaining sites to install:**
- ❌ farmworkers.eu (404 — NOT installed)
- ❌ horecaworkers.eu (404 — NOT installed)
- ❌ electricjobs.eu (404 — NOT installed)
- ❌ expatsinromania.org (404 — NOT installed)
- ❌ nepalezi.com (404 — NOT installed)

**Blockers:**
1. WP Core files (wordpress.org/latest.zip) — need to download once
2. cPanel API setup for the 5 remaining sites

### 📋 NEXT STEPS (5 sites remaining)

1. Download WP core: `wget https://wordpress.org/latest.zip` (once on raspibig)
2. Install on 5 remaining sites via cPanel API (install_wp_pilot.py)
3. Get & save credentials for 5 new sites → wp_sites.env
4. Expand wordpress_publisher.py WP_JOB_SITES dict (5 new entries)
5. Test publisher dry-run on all 13 sites (should all be 200 OK)
6. Add daily cron jobs for each site's publishing schedule

### 📂 CRITICAL FILES

- `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env` — all credentials
- `/opt/ACTIVE/EVENT_PUBLISHER/wordpress_publisher.py` — multi-site publisher
- `/opt/ACTIVE/INTERJOB/deploy/install_wp_pilot.py` — WP installer script
- `D:\MEMORY\...\PLAN 01 06 2026\synchronous-wishing-flurry.md` — detailed plan (site colors, DB names, etc.)

### ✅ SUCCESS CRITERIA

All 13 WP sites respond 200 OK to REST API `/wp-json/wp/v2/posts` + publisher can POST test jobs without error.

---

## Database Inventory

**ij_jobs:** 9,087 jobs (agricultura 83, constructii 1,386, horeca 432, IT 1,199, logistica 378, productie 570, sanatate 218, transport 452, vanzari 1,143, altul 3,226)

**EURES:** job_listings table exists (65 rows)

**fw_jobs:** 5,542 (farmworkers pipeline, separate from ANOFM)

**fw_websites:** 14 domains configured (see publish_html_new.py for SITE_CONFIGS: colors, taglines, titles)

---

## Architecture

**One backend, multiple skins:**
- PostgreSQL: interjob_master (raspibig:5432)
- Static HTML: Generated daily by generate_jobs_pages.py → A2 cPanel
- WordPress: 13 sites at /wp/ → Jetpack Social auto-distribution
- Email: Brevo (1,560→2,560/day capacity)
- Analytics: PostHog (free tier: 1M events/month)

**Domain routing:**
- interjob.ro: WordPress + HTML (2 fluxes: EURES→RO, ANOFM→EN via Polylang)
- buildjobs.eu, farmworkers.eu, etc.: HTML + WordPress at /wp/

---

## Infrastructure (Live)

| Machine | IP | Role |
|---------|-----|------|
| raspibig | 192.168.100.21 | PostgreSQL, scrapers, email, N8N, PostHog, Caddy, FastAPI |
| raspi | 192.168.100.20 | Scraper node, ProtonVPN |
| A2 Hosting | nl1-cl8-ats1.a2hosting.com | 30 domains, cPanel, MySQL, LiteSpeed |

**Key Credentials:**
- cPanel: loaiidil / token: K9ATCMHPKVSKUV2M97447JLY45EH29KQ ✅ (verified working)
- PostgreSQL: tudor/tudor on raspibig:5432
- Apply URL: https://interjob.ro/apply.html
- Email: office@interjob.ro, manpower.dristor@gmail.com

---

**Last Updated:** 2026-06-01 13:06 UTC (Session 4 Final) | **Next:** User to confirm which WP sites already installed, then proceed with remaining sites
