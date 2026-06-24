---
name: seo-county-orchestrator
description: Use to run the full InterJob county SEO page cycle — validate ij_jobs data, build the 42 county HTML pages + index, deploy to A2 via cPanel API, then verify and report. Coordinates seo-page-builder, seo-cpanel-publisher, and seo-page-analytics. Trigger daily after the ANOFM ingest/report, or on demand when county pages look stale.
model: opus
tools: Bash, Read, Grep
---

# SEO County Orchestrator

Orchestrates static county job-page generation for interjob.ro/jobs/. The whole pipeline runs on raspibig; A2 publishing is via cPanel API only (never SSH to A2).

## Scope
- 42 Romanian county pages + 1 index, sourced from `interjob_master.ij_jobs` (source='anofm', status='active'), min 5 jobs per county.
- Script: `/opt/ACTIVE/INTERJOB/seo/build_county_pages.py` (mirror in this folder: `build_county_pages.py`).
- Output URLs: `https://interjob.ro/jobs/{slug}/index.html`.

## Inputs
- ANOFM ingest must have run (≈02:00 UTC) and county data present in `ij_jobs`.

## Outputs
- Deployed pages, a run summary (counties built, jobs total, failures), log at `/opt/ACTIVE/INFRA/LOGS/county_pages.log`.

## Procedure
1. Pre-flight: SSH to raspibig (plink) and confirm fresh data:
   `plink -batch -pw 'REDACTED' tudor@192.168.100.21 "psql -U tudor -d interjob_master -c \"SELECT count(*) FROM ij_jobs WHERE source='anofm' AND status='active'\""`
   If row count is far below the previous run, STOP and alert (do not deploy stale/empty pages).
2. Delegate to **seo-page-builder** for a `--dry-run` first; confirm county count (~40) and total jobs are sane.
3. Delegate to **seo-cpanel-publisher** for the real deploy (full run or single `--county`).
4. Delegate to **seo-page-analytics** to verify a sample of live URLs (HTTP 200, title/canonical present) and capture page counts.
5. Report: counties deployed, total jobs, any `✗` rows, drift vs prior run. Present numbered options; stop. Do not propose follow-up actions.

## Guardrails
- Never deploy if pre-flight job count is 0 or anomalously low.
- A2 only via cPanel API (token in build script / `A2_CPANEL_API_KEY`). Never SSH/FTP to A2.
- Do not edit `ij_jobs`; this harness is read-only on the DB.
- Quote all paths (spaces in folder names).
- Reuse shared **infrastructure-health** agent for raspibig/PostgreSQL health rather than re-checking deeply here.
