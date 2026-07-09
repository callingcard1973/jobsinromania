---
name: seo-county-pages
description: Use when asked to "build county pages", "regenerate SEO pages", "deploy interjob county jobs", "refresh /jobs/ pages", "publish county job pages", or when working in the INTERJOB.RO SEO folder. Generates the 42 Romanian county static job pages from ij_jobs and deploys them to interjob.ro/jobs/ via the cPanel API.
---

# SEO County Pages Harness

Trigger skill for the InterJob county-level SEO page pipeline.

## When to use
- "build/regenerate/refresh county pages", "deploy /jobs/ pages", single-county refresh, or weekly SEO health check.

## What it does
Coordinates the SEO agents:
- **seo-county-orchestrator** — runs the full cycle and reports.
- **seo-page-builder** — `--dry-run` build + HTML/schema validation.
- **seo-cpanel-publisher** — deploy to A2 via cPanel API.
- **seo-page-analytics** — verify live URLs + track trends.

## Usage steps
1. Invoke **seo-county-orchestrator**. It pre-flights `ij_jobs` data on raspibig, then chains builder → publisher → analytics.
2. For a preview only: ask **seo-page-builder** for a dry run.
3. For one county: pass `--county <Name>` through builder/publisher.
4. For verification only: invoke **seo-page-analytics**.

## Key facts
- Script: `/opt/ACTIVE/INTERJOB/seo/build_county_pages.py` (mirror in this folder).
- Data: `interjob_master.ij_jobs` (source='anofm', status='active'), min 5 jobs/county.
- Output: `https://interjob.ro/jobs/{slug}/index.html` + `/jobs/index.html`.
- Deploy: cPanel UAPI `Fileman/save_file_content` (user `loaiidil`). A2 = cPanel API ONLY, never SSH/FTP.
- raspibig runs the Python: `plink -batch -pw '<pw>' tudor@192.168.100.21 "..."`.
- Log: `/opt/ACTIVE/INFRA/LOGS/county_pages.log`. Recommended cron: daily 07:00 UTC (after ANOFM ingest 02:00 + report 06:00).

## Guardrails
- Never deploy on 0/anomalously-low job counts.
- Read-only on the DB. Quote all paths.
