---
name: wp-job-publisher
description: 'Use when publishing individual EURES/ANOFM jobs as one-post-per-job to the InterJob WordPress sites (interjob.ro, buildjobs.eu, meatworkers.eu, factoryjobs.eu, warehouseworkers.eu, careworkers.eu, mechanicjobs.eu, internaltransfers.eu, horecaworkers2026.eu, nepalezi.com). Triggers — "publish jobs to WordPress", "run the WP publisher", "post jobs to all sites", "wp publish status", "retry failed wp posts", or working in the WP PUBLISHER folder. Distinct from DAILY ROUNDUP (one summary article/day).'
---

# WP Job Publisher

Orchestrates the WP PUBLISHER harness: dedup-safe, multi-site individual job posting with REST health checks and retry.

## Agents
- **wp-publish-orchestrator** — runs the full cycle, delegates to the others.
- **wp-rest-health-checker** — verifies `/wp-json/` per site before posting.
- **wp-dedup-tracker** — audits the `wp_job_posts` ledger.
- **wp-publish-retry** — re-attempts failed/orphan posts with backoff.

## Engine facts
- Script: `/opt/ACTIVE/EVENT_PUBLISHER/wordpress_publisher.py` (raspibig).
- Dedup: `wp_job_posts` UNIQUE(job_id, site) in interjob_master.
- Translation: deep_translator (ANOFM RO→EN, EURES EN→RO).
- Categories: "Jobs in Romania" (EN/ANOFM), "Joburi in Europa" (RO/EURES).
- Cron: 11:00 EURES/ro + 13:00 ANOFM/en on interjob.ro.
- Creds: `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env`.

## Usage
1. Health: run wp-rest-health-checker → get publishable sites (skip REST-404).
2. Status: run wp-dedup-tracker (or `wordpress_publisher.py --status`).
3. Dry-run new sites: `--site <site> --limit 5 --dry-run`.
4. Publish: cron commands, or `--all-sites --limit N` / `--site <site> --source <anofm|eures|all> --lang <ro|en|auto>`.
5. Retry: run wp-publish-retry for any `WP error`/`exception` lines.

## Rules
- WordPress/A2 only via HTTPS REST API — never SSH/FTP to A2. raspibig via plink.
- Always dry-run a never-published site first.
- Never bypass dedup; archive before deleting ledger rows.
- 4 sites need a permalink flush (WP Admin → Settings → Permalinks → Save) before REST works.
- Quote all paths (spaces in folder names). Present results, then stop.
