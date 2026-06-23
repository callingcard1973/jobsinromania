---
name: data-collector
description: Extract silo records from MADR county Excel files (43 counties) and ANAF od_firme.csv. Parse, deduplicate, merge into raw master CSV. Use when the user says "parse MADR", "extract silos", "rebuild raw data from sources", "merge MADR+ANAF", or when silozuri orchestrator initiates collection phase. Handles all Excel parsing quirks, county name normalization, and auth_code deduplication.
---

# Data Collector Skill

Parse MADR county files + ANAF open-data → deduplicated raw master CSV.

## When to Use

- User: "Parse MADR data", "Extract all silos from Excel", "Rebuild from sources"
- Orchestrator: Initiates collection phase before enrichment
- Scenario: New MADR files added, need to re-parse and merge

## Files to Work With

**Source files (read-only):**
- `DATA/raw/MADR_{COUNTY}.xlsx` (41 files, one per county)
- `DATA/raw/ANAF/od_firme.csv` (ANAF open-data registry)

**Output:**
- `_workspace/01_collector_raw_merged.csv` (deduplicated merged raw)

**Reference (if exists):**
- `DATA/MASTER.csv` (to detect existing schema)

## Parsing Rules

### MADR Excel Files

1. **Sheet name:** Usually "Silozuri" or "Data" (try common variants; if fails, list available sheets)
2. **Columns to extract:** Auth code (MADR license ID), name, county, capacity columns
3. **County normalization:** Standardize RO diacritics (Braşov → Brașov, Suceava → Suceava)
4. **Blank handling:** Skip rows where auth_code is empty

### ANAF od_firme.csv (Optional)

1. **If exists:** Load `DATA/raw/ANAF/od_firme.csv`
   - Filter: CAEN in (0161, 0162, 01610, 01620, 01630, 01640, 0164) — agricultural production
   - Link to MADR: CUI + name match → enrich with MADR data
2. **If missing:** Skip ANAF step (not fatal; enricher will backfill CUI via raspibig DB)

### Deduplication

**Dedup key:** (name core-match) + (CUI match) + distinct auth_code

**Name core-match algorithm:**
1. Strip accents (ş→s, ț→t, etc.)
2. Uppercase
3. Remove legal suffixes (SRL, SA, PFA, ONG, IFN, etc.)
4. Tokenize by space/punctuation
5. Compare token sets (order-independent)

**Keep-first rule:** If multiple auth_codes have identical name/CUI, keep first occurrence, flag collision in report

## Output Schema

```csv
auth_code,name,phone,email,county,city,cui,caen,capacity_total_t,capacity_grains_t,capacity_oilseeds_t,_source
```

**_source values:** MADR, ANAF_ENRICH, RECALL (reference dedup)

## Execution Steps

```bash
cd "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\SILOZURI"

# Read all county Excel files
for file in DATA/raw/MADR_*.xlsx:
  - Extract sheet "Silozuri" or first sheet
  - Get: auth_code, name, county, capacity_total_t, capacity_grains_t, capacity_oilseeds_t
  - Normalize county name
  - Append to working df

# Enrich with ANAF
- Load DATA/raw/ANAF/od_firme.csv
- Filter: CAEN in agricultural codes
- Join on CUI + name match
- Fill: CUI, CAEN for non-matched MADR records

# Deduplicate
- Sort by: auth_code, name
- Group by (name_core, CUI)
- Keep first per group
- Flag collisions

# Write output
- Save to _workspace/01_collector_raw_merged.csv
- Report: Row counts per county, merge stats, collisions
```

## Error Handling

- **Excel file missing:** Log warning, continue (some counties may not have files)
- **Sheet not found:** List available sheets, try "Data" fallback
- **Malformed cell:** Log row number, skip cell, continue
- **Dedup collision (same auth_code, different names):** Flag in report, keep both rows (manual review)

## Output Report

Log to console and `_workspace/01_collector_raw_merged.log`:

```
Total rows parsed: 14,000
Rows per county: [county breakdown]
MADR raw: 14,000
ANAF cross-references: 2,500 (with CUI match)
Dedup collisions flagged: 5
Final deduplicated: 13,287
```

## Next Agent

Pass CSV to **Data Enricher** for phone/email/CUI backfill.
