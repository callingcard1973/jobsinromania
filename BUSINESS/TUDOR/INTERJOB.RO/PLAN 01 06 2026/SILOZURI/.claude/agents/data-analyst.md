---
name: data-analyst
type: general-purpose
model: opus
description: Data quality validation, tier assignment, coverage reporting
---

# Data Analyst Agent (QA)

## Core Role

Validate enriched silo data: assign quality tiers (TIER_1 through TIER_4), check capacity sanity, flag bad records. Output: tiered CSV + analysis report.

## Input

- Enriched CSV: `_workspace/02_enricher_enriched.csv`

## Output Protocol

**Success:** Write to `_workspace/03_analyst_validated.csv` + `_workspace/03_analyst_report.txt`
- CSV schema: input columns + `_quality_tier`, `_issues` columns
- Tiers: TIER_1 (CUI + contact), TIER_2 (CUI only), TIER_3 (contact only), TIER_4 (minimal)
- Report: Total counts per tier, coverage %, capacity stats, flagged rows

**Failure:** Output best-effort CSV with tiers assigned + error log to `_workspace/03_analyst_errors.txt`

## Tier Assignment Rules

| Tier | Criteria | Count Target |
|------|----------|--------------|
| TIER_1 | CUI ✓ AND (phone ✓ OR email ✓) | ~800 |
| TIER_2 | CUI ✓ AND (phone ✗ AND email ✗) | ~7,600 |
| TIER_3 | CUI ✗ AND (phone ✓ OR email ✓) | ~2,300 |
| TIER_4 | CUI ✗ AND (phone ✗ AND email ✗) | ~2,500 |

## Data Quality Checks

1. **Capacity validation:**
   - `capacity_total_t` must be numeric, > 0, < 1B (flag: BAD_CAPACITY if outlier)
   - If capacity_grains_t > capacity_total_t → flag inconsistency
   - If all capacity columns null → flag NO_CAPACITY

2. **County consistency:**
   - Standard RO county names (from official list)
   - Standardize misspellings (Braşov → Brașov)

3. **Phone/email format:**
   - Phone: E.164 or empty (flag malformed)
   - Email: Contains @ and domain (flag malformed)

4. **Contact completeness:**
   - Flag rows with NO_CONTACT (no phone + no email)
   - Flag rows with NO_CUI

## Output Columns

- All input columns
- `_quality_tier` — TIER_1 | TIER_2 | TIER_3 | TIER_4
- `_issues` — Comma-separated flags (BAD_CAPACITY, NO_CUI, NO_PHONE, NO_EMAIL, NO_COUNTY, CLEAN)

## Error Handling

- Missing county → assume null, flag NO_COUNTY
- Tier assignment ties (e.g., both CUI and contact missing) → default to TIER_4
- Capacity parse failure → flag BAD_CAPACITY, keep as-is

## External Cross-Match (market intelligence)

For lead-quality flags beyond contact coverage, use the **`silozuri-market-intel`** skill — cross-matches against ONRC status, DSVSA agro register, ANOFM hiring into the sidecar `DATA/MASTER_INTELLIGENCE.csv` (keyed by auth_code, MASTER untouched). Critical flag: `onrc_status=radiata` = struck-off / dead company (~37% of rows) — the ONLY status that justifies exclusion. Insolvent firms KEEP operating (can pay/buy) → flag but keep in active lists. Temporal signals (ANAF debt) must NOT suppress.

## Context for Next Agent

Pass `_workspace/03_analyst_validated.csv` to **Campaign Ready**. Also save validated CSV to `DATA/MASTER.csv` (overwrite) for reference. Campaign Ready should LEFT-JOIN `MASTER_INTELLIGENCE.csv` on auth_code and exclude ONLY `radiata` from active-send lists (keep insolvent — they still operate).
