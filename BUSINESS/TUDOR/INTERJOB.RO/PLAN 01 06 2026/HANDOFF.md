# HANDOFF — InterJob Engine

**Status:** 2026-06-01 Session 4 Final | **Mode:** Upgrade & extend (70-80% exists)

---

## 0. CRITICAL: 70-80% of System Already Exists

This is NOT greenfield. Key infrastructure on raspibig:
- PostgreSQL interjob_master (434 tables, 9,087 ANOFM jobs)
- Production ingest/build/deploy pipeline (working daily)
- 14 live domains generating HTML weekly
- farmworkers.eu CV pipeline (221 applicants)

See `/opt/ACTIVE/INTERJOB/` and `/opt/ACTIVE/FARMWORKERS/` on raspibig.

---

## 10. PICK-UP STATE — CURRENT (2026-06-01 SESSION 4)

### ✅ WHAT'S DONE

**WordPress at /wp/ (3 sites live):**
- buildjobs.eu/wp/ (DB: loaiidil_wp500) ✅
- meatworkers.eu/wp/ (DB: loaiidil_wp351) ✅
- factoryjobs.eu/wp/ (DB: loaiidil_a2wp496) ✅
- Credentials in `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env`
- wordpress_publisher.py updated with 3 WP_JOB_SITES entries

**JobsInRomania Daily Pipeline (✅ LIVE & PRODUCTION READY):**
- ✅ GitHub repo: https://github.com/callingcard1973/jobsinromania/
- ✅ Live site: https://callingcard1973.github.io/jobsinromania/index.html
- ✅ Scripts on raspibig: `/opt/ACTIVE/JOBSINROMANIA/`
  - `generate_romania_jobs.py` — extracts ANOFM Romania jobs from ij_jobs (1,533 jobs)
  - `build_romania_pages.py` — generates single searchable index.html (color: #e65100)
  - `deploy_github.py` — auto-commits + pushes to GitHub via SSH
  - `daily_build.sh` — orchestrates all 3 with logging
- ✅ Daily cron: `0 2 * * * bash /opt/ACTIVE/JOBSINROMANIA/daily_build.sh` (2 AM UTC)
- ✅ Pipeline tested: extracts → builds → deploys (all 3 steps pass)
- ✅ GitHub Pages enabled (source: main branch /docs/)
- ✅ Client-side search works (filter by title, city, sector)

### ⏸ BLOCKERS (WordPress)

1. **10 remaining WP sites need installation** (farmworkers, horecaworkers, etc.)
2. **WP Core files** not uploaded to A2 (bottleneck: file upload via cPanel Fileman)

### 📋 NEXT STEPS

**WordPress Installation (10 remaining sites, 2-3 hours):**
1. Download WP core: `wget https://wordpress.org/latest.zip` (once on raspibig)
2. Install on: farmworkers, horecaworkers, warehouseworkers, careworkers, electricjobs, mechanicjobs, internaltransfers, expatsinromania, horecaworkers2026, nepalezi
3. Update wp_sites.env + wordpress_publisher.py with 10 new entries
4. Test publisher dry-run → live on all 13 sites
5. Add cron jobs for daily publishing per site

### 📂 CRITICAL FILES

- `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env` — all credentials
- `/opt/ACTIVE/EVENT_PUBLISHER/wordpress_publisher.py` — multi-site publisher
- `/opt/ACTIVE/INTERJOB/deploy/install_wp_pilot.py` — WP installer script
- `D:\MEMORY\...\PLAN 01 06 2026\synchronous-wishing-flurry.md` — detailed plan (site colors, DB names, etc.)

### ✅ SUCCESS CRITERIA

All 13 WP sites respond 200 OK to REST API `/wp-json/wp/v2/posts` + publisher can POST test jobs without error.

---

## Database Inventory

**ANOFM (ij_jobs):** 9,087 jobs (agricultura 83, constructii 1,386, horeca 432, IT 1,199, logistica 378, productie 570, sanatate 218, transport 452, vanzari 1,143, altul 3,226)

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
