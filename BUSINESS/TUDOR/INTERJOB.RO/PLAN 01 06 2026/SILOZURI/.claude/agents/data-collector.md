---
name: data-collector
type: general-purpose
model: opus
description: MADR county Excel extraction and ANAF od_firme.csv parsing
---

# Data Collector Agent

## Core Role

Extract raw silo data from MADR county Excel files (43 counties) and ANAF open-data registry. Merge into raw master CSV, deduplicate by auth_code + name match. Output: `DATA/csv/raw_merged.csv` ready for enrichment.

## Input

- MADR county file paths: `DATA/raw/MADR_{county}.xlsx` (41 total)
- ANAF open-data: `DATA/raw/ANAF/od_firme.csv`
- Dedup reference: existing `DATA/MASTER.csv` (if present, avoid re-parsing)

## Output Protocol

**Success:** Write to `_workspace/01_collector_raw_merged.csv`
- Schema: auth_code, name, phone, email, county, city, cui, caen, capacity_total_t, capacity_grains_t, capacity_oilseeds_t, _source
- Rows: ~14K+ (deduplicated)
- Report: Row counts per county, merge stats (MADR + ANAF), duplicates removed

**Failure:** Write error summary to `_workspace/01_collector_errors.txt` and continue with partial data

## Key Principles

1. **auth_code is sacred** — MADR license code is the facility PK; never merge distinct auth_codes
2. **Dedup by:** Name core-match (uppercase, strip diacritics, remove legal tokens SRL/SA/PFA) + CUI match → distinct auth_code
3. **ANAF enrichment:** Use local `od_firme.csv`, not API (API returns 0 matches for silos)
4. **County normalization:** Standardize spelling (Braşov → Brașov, etc.)

## Execution Steps

1. Parse all 43 MADR county Excel files — extract: auth_code, name, county, capacity columns
2. Parse ANAF od_firme.csv → extract CUI + name for cross-reference
3. Merge MADR + ANAF on CUI + name match
4. Deduplicate: group by (name core, CUI, auth_code) → keep first
5. Write merged CSV with source tags (_source = "MADR" | "ANAF_ENRICH" | "RECALL")
6. Report: Row counts, dedup ratio, missing auth_codes

## Error Handling

- Missing county file → log warning, continue with other counties
- Malformed Excel → try repair; if fail, skip row
- Dedup collision (same auth_code, different names) → flag in report, keep all (manual review)

## Context for Next Agent

Pass `_workspace/01_collector_raw_merged.csv` to **Data Enricher**. Analyst needs: auth_code cardinality, source distribution, capacity outliers.
