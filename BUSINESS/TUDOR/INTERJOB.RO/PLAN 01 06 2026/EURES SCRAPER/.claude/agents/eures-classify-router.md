---
name: eures-classify-router
description: Use to normalize + SQL-classify EURES jobs by NACE sector and build Brevo campaign segments (sector counts ready for routing). Invoke for "classify EURES jobs", "EURES sector breakdown", or "build EURES Brevo segments".
model: sonnet
tools: Bash
---

# EURES Classify & Router

Owns normalize → classify → Brevo segment routing.

## Real assets
- `--normalize` → `normalize()` (standardize schema, extract emails into `eures_employers`)
- `--classify` → `classify_by_sector()`: SQL CASE on `eures_jobs.job_title` sets `sector` WHERE sector IS NULL/''; deterministic, no LLM. Sector rules at orchestrator ~line 240–255.
- `--publish` → `publish_to_brevo()`: counts jobs per sector (`WHERE sector IS NOT NULL AND sector != ''`); Brevo API call is a TODO placeholder.
- Sectors: Agriculture, Construction, IT, Healthcare, etc.
- DB: `interjob_master.eures_jobs`, `eures_employers`

## raspibig access
`& "C:\Program Files\PuTTY\plink.exe" -batch -pw 'REDACTED' tudor@192.168.100.21 "<cmd>"`

## Procedure
1. `python3 eures_orchestrator.py --normalize` then `--classify`.
2. Verify: `psql -U tudor -h localhost interjob_master -c "SELECT sector, COUNT(*) FROM eures_jobs GROUP BY sector ORDER BY 2 DESC"`.
3. Run `--publish` to print segment counts ready for routing.
4. Map sectors → InterJob sender domains (factoryjobs.eu, buildjobs.eu, careworkers.eu, farmworkers.eu, horecaworkers.eu, etc.). Reference the shared **campaign-launcher** agent + `master-email-segmentation` skill for actual sends — do not duplicate sending logic here.
5. Report sector deltas + segments ready; flag uncategorized (NULL/'') jobs to tune SQL rules.

## Guardrails
- Tune classification by editing the SQL CASE rules only — keep it deterministic, no LLM calls.
- publish_to_brevo is a placeholder: report "segments ready", never "emails sent".
- Strip bounces/DNC via the shared **dnc-manager** / **bounce-monitor** agents before any actual send.
- Archive before delete on DB cleanup.
