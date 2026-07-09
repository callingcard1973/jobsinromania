---
name: bpp-loop
description: "Run the BPPLTD.CO.UK two-sided deficit marketplace loop — source ALL 7 ANOFM deficit-occupation jobs (Bucatar/Electrician/Mecanic/Sofer/Sudor/Tamplar/Zidar) from ij_jobs+anofm_scrapes+EURES, rebuild bilingual catalog, publish job posts to bppltd.co.uk/wp, generate country x occupation SEO pages, run worker-attraction outreach, capture+match applications, and report. Use when asked to 'run bpp cycle', 'publish deficit jobs', 'attract deficit workers', 'bpp status', or working in the BPPLTD.CO.UK folder. The aggregate/catch-all counterpart to electricjobs-loop."
---

# bpp-loop Skill

**Purpose:** Operate bppltd.co.uk as a two-sided deficit marketplace — grow worker
supply and employer demand together, daily, across ALL 7 ANOFM deficit occupations.
The aggregate domain complementing the occupation-specific sites. Reuses existing
InterJob harnesses (mirror of `electricjobs-loop`, generalized).

**Domain:** bppltd.co.uk on A2 (`loaiidil`), `~/bppltd.co.uk/` + `/wp`. Also the ANOFM
catch-all Brevo sender (`office@bppltd.co.uk`). See `BPPLTD.CO.UK/CLAUDE.md`.

## Deficit occupations (the 7, official ANOFM)
Bucatar (751101), Electrician (741301), Mecanic utilaje (721201),
Sofer (832203), Sudor (722106), Tamplar (752201), Zidar (711201).

## The loop (8 steps, mostly reused engines)

| # | Step | UTC | Engine | Output |
|---|------|-----|--------|--------|
| 1 | Pull deficit jobs from `anofm_scrapes`+`ij_jobs`+EURES, dedup vs posted | 00:30 | pipeline-orchestrator | deficit jobs JSON (all 7 occ) |
| 2 | Rebuild bilingual catalog (PDF+HTML, public variant) | 01:00 | interjob-catalog | bpp_catalog.pdf/html |
| 3 | Publish individual job posts to bppltd.co.uk/wp | 11:00 | **wp-job-publisher** (`wordpress_publisher.py`, raspibig — REUSE, don't reinvent; add bppltd.co.uk to WP_JOB_SITES + WP_BPPLTD_CO_UK_USER/PASS in wp_sites.env) | one WP post per job, dedup via wp_job_posts |
| 4 | Generate/refresh SEO pages (country x occupation) -> A2 | 11:30 | SEO + cpanel-deployer | /<occupation>-jobs-<country>/ |
| 5 | Attract workers (outreach to global/diaspora lists, all 7 trades) | 06:00 | campaign-launcher + Brevo (office@bppltd.co.uk) | sends within daily cap |
| 6 | Capture applications (apply.html?ref=) + classify replies | 30-min | reply-classifier + CV pipeline | new workers in DB |
| 7 | Match workers <-> jobs (occupation/country/cert) | 12:00 | matcher (manual->rules) | shortlist per job |
| 8 | Bounce/DNC + daily report | 07:00 | bounce-monitor + dnc-manager + report-generator | clean lists + digest |

**Loop invariant:** every new deficit job triggers targeted worker outreach for that
occupation; every new worker is matched against open jobs in their trade. Supply and
demand grow together across all 7 occupations.

## Deficit filter (step 1)

Job-title match (diacritic-stripped, lowercased) against the 7 occupation keywords:
`bucatar, electrician, mecanic, sofer, sudor, tamplar, zidar, dulgher`. Source:
`anofm_scrapes.scrape_jobs` (43k+ postings, raspi) + `ij_jobs` + EURES. Real data only.

## Rules

- ASCII pure everywhere (subject+body+jobs.json+PDF); fold diacritics with NFKD on send.
- Real data only from `anofm_scrapes`/`ij_jobs`/EURES — never fabricate jobs.
- Public catalog variant on the site (no employer phone/email exposed).
- A2/WP via cPanel API or HTTPS REST only — NEVER SSH/FTP to A2.
- All ANOFM-adjacent runs on raspi .20 (see anofm-host-map). Outreach via the ANOFM
  orchestrator's BPP catch-all sender (do NOT create a parallel sender).
- Never git commit/push without explicit instruction. No secrets in repo files.

## Status check

- Jobs available: deficit rows in `anofm_scrapes.scrape_jobs` per occupation.
- Catalog freshness: mtime of bpp_catalog.pdf.
- Outreach: today's office@bppltd.co.uk sends vs cap; bounces; DNC size.
- wp-json health: if 404 -> WP Admin > Permalinks > Save (flush rewrite).

## Gaps to build (incremental, same order as electricjobs)

1. Steps 1-3 wiring (data->catalog->publish to bppltd.co.uk/wp) — fastest, reuses everything.
2. Step 5 worker-attraction campaign on office@bppltd.co.uk (already the ANOFM catch-all sender).
3. Country x occupation SEO batch (step 4) — 7 occupations x N countries.
4. Matcher (step 7): manual shortlist -> rules -> automation.

## Test scenarios

- Normal: "run bpp cycle" -> steps 1-3 produce a fresh catalog + WP posts for deficit jobs.
- Error: WP REST 404 -> report "flush permalinks", skip publish, continue catalog.
