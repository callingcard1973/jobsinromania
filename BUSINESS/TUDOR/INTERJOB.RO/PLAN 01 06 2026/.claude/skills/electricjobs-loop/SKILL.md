---
name: electricjobs-loop
description: "Run the ELECTRICJOBS.EU two-sided operating loop — source electrical contracts from ij_jobs+EURES, rebuild bilingual catalog, publish job posts to electricjobs.eu/wp, generate country x specialization SEO pages, run electrician-attraction outreach, capture+match applications, and report. Use when asked to 'run electricjobs cycle', 'publish electrical contracts', 'attract electricians', 'electricjobs status', or working in the ELECTRICJOBS.EU folder."
---

# electricjobs-loop Skill

**Purpose:** Operate electricjobs.eu as a two-sided marketplace — grow electrician supply
and electrical-contract demand together, daily. Reuses existing InterJob harnesses.

**Domain:** electricjobs.eu on A2 (`loaiidil`), docroot `~/electricjobs.eu/` + `/wp`.
ISCO 741 (electricians). See `ELECTRICJOBS.EU/CLAUDE.md` for full spec.

## The loop (8 steps, mostly reused engines)

| # | Step | UTC | Engine | Output |
|---|------|-----|--------|--------|
| 1 | Pull electrical jobs from `ij_jobs`+EURES, dedup vs posted | 00:30 | pipeline-orchestrator | electrical jobs JSON |
| 2 | Rebuild bilingual catalog (PDF+HTML, public variant) | 01:00 | interjob-catalog | electricjobs_catalog.pdf/html |
| 3 | Publish individual job posts | 11:00 | wp-job-publisher | one WP post per contract |
| 4 | Generate/refresh SEO pages (country x specialization) -> A2 | 11:30 | SEO + cpanel-deployer | /electrician-jobs-<country>/ |
| 5 | Attract electricians (outreach to global lists + diaspora) | 06:00 | campaign-launcher + Brevo | sends within daily cap |
| 6 | Capture applications (apply.html?ref=) + classify replies | 30-min | reply-classifier + CV pipeline | new electricians in DB |
| 7 | Match electricians <-> contracts (country/spec/cert) | 12:00 | matcher (manual->rules) | shortlist per contract |
| 8 | Bounce/DNC + daily report | 07:00 | bounce-monitor + dnc-manager + report-generator | clean lists + digest |

**Loop invariant:** every new contract triggers targeted electrician outreach; every new
electrician is matched against open contracts. Supply and demand grow together.

## Electrical filter (step 1)

```sql
sector ILIKE '%electric%'
 OR title ILIKE '%ELECTRIC%' OR title ILIKE '%ELECTRICIAN%'
 OR title ILIKE '%TABLOU%' OR title ILIKE '%INSTALATOR ELECTR%'
 OR title ILIKE '%PV%' OR title ILIKE '%FOTOVOLTAIC%'
```
from `ij_jobs` on raspibig `interjob_master` (raspi feeds raspibig — see ABOUT RASPI).

## Rules

- ASCII pure everywhere (subject+body+jobs.json+PDF); fold diacritics with NFKD on send.
- Real data only from `ij_jobs`+EURES — never fabricate jobs.
- Public catalog variant only on the site (no employer phone/email exposed).
- A2/WP via cPanel API or HTTPS REST only — NEVER SSH/FTP to A2.
- Never git commit/push without explicit instruction. No secrets in repo files.
- Sender = electricjobs.eu Brevo domain (onboarded via brevo-sender-onboarding).

## Status check

- Jobs available: count electrical rows in `ij_jobs`.
- Catalog freshness: mtime of electricjobs_catalog.pdf.
- Outreach: today's sends vs cap; bounces; DNC size.
- wp-json health: if 404 -> WP Admin > Permalinks > Save (flush rewrite).

## Gaps to build (incremental)

1. Steps 1-3 wiring (data->catalog->publish) — fastest, reuses everything.
2. electricjobs.eu sender domain + step 5 attraction campaign.
3. Country x specialization SEO batch (step 4).
4. Matcher (step 7): manual shortlist -> rules -> automation.
