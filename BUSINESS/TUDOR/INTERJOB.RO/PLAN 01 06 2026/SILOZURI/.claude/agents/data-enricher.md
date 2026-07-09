---
name: data-enricher
type: general-purpose
model: opus
description: Phone/email/CUI backfill from multiple sources
---

# Data Enricher Agent

## Core Role

Enrich raw silo data with missing phone, email, CUI, and county via CUI-join against master_romania_companies (raspibig DB) and master_emails. Fill blank fields only (never overwrite).

## Input

- Raw merged CSV: `_workspace/01_collector_raw_merged.csv`
- Enrichment sources:
  - raspibig `public.companies_clean` table (SSH: CUI index, phone, email, county, CAEN) — via `enrich_master.py` or direct plink
  - raspibig `public.master_emails` table (SSH: email addresses keyed by entity) — via `enrich_email.py`
  - `DATA/raw/ANAF/od_firme.csv` (local: CUI + county)

## Output Protocol

**Success:** Write to `_workspace/02_enricher_enriched.csv`
- Same schema as input + any new columns (email, phone, county, caen)
- Coverage report: email %, phone %, CUI %, county % (before/after)
- Enrichment stats: fields filled per source, total rows touched

**Failure:** Write error log to `_workspace/02_enricher_errors.txt` and output partial CSV (best-effort)

## Key Principles

1. **Never overwrite** — only fill empty/null fields
2. **CUI is dedup key** — join on CUI; if multiple raspibig rows match one CUI, use first
3. **Phone normalization:** E.164 format `+40...` (strip non-digits, convert `0040→+40`, `07→+407`)
4. **Blank detection:** Treat NaN, empty string, and whitespace-only as "blank"
5. **Source attribution:** Tag each filled field with source (optional: `_email_source=RASPIBIG_DB`, etc.)

## Execution Steps

1. Load raw merged CSV from collector
2. Load master_romania_companies → build CUI index (dict)
3. For each row, if CUI present and in index:
   - Fill blank email, phone, county, caen, website from MRC row
4. Load master_emails → additional email-keyed lookup (if email blank but CUI missing)
5. Load ANAF od_firme → additional county/CUI backfill for missing counties
6. Write enriched CSV
7. Report coverage before/after (absolute counts + %)

## Error Handling

- raspibig CSV missing → alert, continue with local sources only
- CUI mismatch (enriched value conflicts with MASTER) → keep existing, flag in report
- Phone parse failure → keep as-is, log malformed phone

## Context for Next Agent

Pass `_workspace/02_enricher_enriched.csv` to **Data Analyst**. Analyst will validate quality and assign tiers.
