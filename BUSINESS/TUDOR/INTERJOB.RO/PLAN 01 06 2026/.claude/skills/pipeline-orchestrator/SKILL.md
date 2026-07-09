---
name: pipeline-orchestrator
description: "Orchestrate INTERJOB.RO daily data pipeline — validate ANOFM/EURES jobs, MADR lands, enrich company database, regenerate job catalogs (PDF+HTML for 9 domains). Use when running pipeline, regenerating catalogs, validating data sources, checking pipeline health, or debugging missing jobs."
---

# Pipeline Orchestrator Skill

**Purpose:** Automate daily data refresh for INTERJOB.RO marketplace — jobs, candidates, companies, catalogs.

**Scope:** ANOFM daily jobs + EURES listings + MADR land scraping + company enrichment + catalog generation (factoryjobs.eu, buildjobs.eu, meatworkers.eu, warehouseworkers.eu, careworkers.eu, mechanicjobs.eu, electricjobs.eu, horecaworkers.eu, farmworkers.eu)

**Execution:**
1. **Validate data sources** — Check ANOFM/EURES APIs, land scraper status
2. **Run enrichment pipeline** — 56 enrichment steps (on laptop + raspibig parallel)
3. **Generate catalogs** — PDF (ReportLab) + HTML (template) for each domain
4. **Archive old artifacts** — Move previous PDFs to ARCHIVE/
5. **Publish** — Copy to A2 Hosting docroots
6. **Report health** — Pipeline state JSON to dashboard

**Key scripts:**
- ANOFM daily: `raspibig:/opt/ACTIVE/DAILY/jobs_daily_anofm.py`
- Enrichment: `laptop:D:\MEMORY\CODE\ACTIVE\SILOZURI\enrich_pipeline_56_steps.py`
- Catalog gen: `laptop:D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG JOBURI\build_job_catalogs.py`
- Archive: `laptop script to move previous PDFs`

**Constraints:**
- Run serially (no concurrent pipelines — file lock `/opt/ACTIVE/INFRA/LOGS/pipeline.lock`)
- Skip any source if >2 hours behind schedule
- Stop entire pipeline if any enrichment step fails >3 times
- Never delete old data without archiving first

**Outputs:**
- `pipeline_state.json` — {source: {row_count, last_run, status}, generated_at}
- Catalog PDFs — `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG JOBURI\*.pdf`
- Catalog HTML — deployed to A2 Hosting docroots
- Health alerts — email + Telegram on failures
