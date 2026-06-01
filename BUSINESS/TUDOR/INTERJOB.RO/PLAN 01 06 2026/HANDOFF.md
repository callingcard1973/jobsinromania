# HANDOFF — InterJob Engine

**Status:** 2026-06-01 Session 3 Final | **Mode:** Upgrade & extend (70-80% exists)

---

## 0. CRITICAL: 70-80% of System Already Exists

This is NOT greenfield. Key infrastructure on raspibig:
- PostgreSQL interjob_master (434 tables, 9,087 ANOFM jobs)
- Production ingest/build/deploy pipeline (working daily)
- 14 live domains generating HTML weekly
- farmworkers.eu CV pipeline (221 applicants)

See `/opt/ACTIVE/INTERJOB/` and `/opt/ACTIVE/FARMWORKERS/` on raspibig.

---

## 10. PICK-UP STATE — CURRENT (2026-06-01 SESSION 3)

### ✅ WHAT'S DONE

**3 WP Sites Live & Authenticated:**
- buildjobs.eu/wp/ (DB: loaiidil_wp500)
- meatworkers.eu/wp/ (DB: loaiidil_wp351)
- factoryjobs.eu/wp/ (DB: loaiidil_a2wp496)

**Credentials Saved** → `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env`
```
WP_BUILDJOBS_EU_USER=apaminerala / PASS=T39_8GZY0Snp2eZx
WP_MEATWORKERS_EU_USER=apaminerala / PASS=11oEbWmL-47s3MwD
WP_FACTORYJOBS_EU_USER=apaminerala / PASS=jVyCZWFOl9WytL1c
```

**Code Updated:**
- wordpress_publisher.py: Added 3 WP_JOB_SITES entries
- install_wp_pilot.py: Ready for 10 remaining sites

### ⏸ BLOCKERS

1. **WP Core Files** — Not uploaded to A2 (need wget + cPanel Fileman)
2. **Category Creation Test** — Publisher reported failure on dry-run

### 📋 NEXT STEPS (In Order)

1. Download WP core → `wget https://wordpress.org/latest.zip` (once on raspibig)
2. Install 10 remaining sites (farmworkers, horecaworkers, warehouseworkers, careworkers, electricjobs, mechanicjobs, internaltransfers, expatsinromania, horecaworkers2026, nepalezi)
3. Add 10 sites to wp_sites.env with credentials
4. Expand wordpress_publisher.py WP_JOB_SITES dict (10 new entries)
5. Add cron jobs for daily publishing (7 templates, see detailed plan)
6. Test publisher on all 13 sites (dry-run → live)

**Est. Time:** 2-3 hours (file upload bottleneck)

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

**Last Updated:** 2026-06-01 17:00 UTC | **Next Review:** When 10 remaining WP sites installed
