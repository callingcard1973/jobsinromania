---
name: data-analyst
description: Validate silo quality, assign tiers (TIER_1 through TIER_4), flag bad capacity/contact. Use when the user says "validate silozuri", "check quality", "analyze coverage", "assign tiers", or when orchestrator initiates analyst phase. Outputs tiered CSV + quality report with coverage %, tier distribution, and problem flags.
---

# Data Analyst Skill

Quality validation + tier assignment.

## When to Use

- User: "Validate the data", "Check quality and coverage", "Assign tiers"
- Orchestrator: Analyst phase (after enricher)
- Scenario: Review data quality before campaigns

## Files to Work With

**Input:**
- `_workspace/02_enricher_enriched.csv` (from enricher)

**Output:**
- `_workspace/03_analyst_validated.csv` (with _quality_tier, _issues columns)
- `_workspace/03_analyst_report.txt` (quality metrics)
- `DATA/MASTER.csv` (copy of validated CSV for reference)

## Tier Assignment Rules

| Tier | Criteria | Purpose |
|------|----------|---------|
| **TIER_1** | CUI ✓ AND (phone ✓ OR email ✓) | Cold calls, highest confidence |
| **TIER_2** | CUI ✓ AND (phone ✗ AND email ✗) | Phone/email lookup needed |
| **TIER_3** | CUI ✗ AND (phone ✓ OR email ✓) | Phone-first, no company registry |
| **TIER_4** | No CUI AND no phone AND no email | Minimal data, research-only |

**Blank detection:** NaN, empty string `''`, or whitespace-only `'   '`

```python
def is_blank(val):
    return pd.isna(val) or str(val).strip() == ''

# Tier assignment
def assign_tier(row):
    has_cui = not is_blank(row['cui'])
    has_contact = not is_blank(row['phone']) or not is_blank(row['email'])
    
    if has_cui and has_contact:
        return 'TIER_1'
    elif has_cui and not has_contact:
        return 'TIER_2'
    elif not has_cui and has_contact:
        return 'TIER_3'
    else:
        return 'TIER_4'
```

## Quality Checks

### 1. Capacity Validation

- `capacity_total_t` must be numeric, > 0, < 1B tonnes
- If `capacity_grains_t` > `capacity_total_t` → **flag inconsistency**
- If all capacity columns null → **flag NO_CAPACITY**
- If parse fails → **flag BAD_CAPACITY**

```python
def check_capacity(row):
    flags = []
    try:
        cap_total = float(row['capacity_total_t']) if row['capacity_total_t'] else 0
        cap_grains = float(row['capacity_grains_t']) if row['capacity_grains_t'] else 0
        cap_oils = float(row['capacity_oilseeds_t']) if row['capacity_oilseeds_t'] else 0
        
        if cap_total <= 0 and cap_grains <= 0 and cap_oils <= 0:
            flags.append('NO_CAPACITY')
        elif cap_total > 1_000_000_000:
            flags.append('BAD_CAPACITY')
        elif cap_grains > cap_total or cap_oils > cap_total:
            flags.append('BAD_CAPACITY')
    except:
        flags.append('BAD_CAPACITY')
    
    return flags
```

### 2. County Consistency

- Standardize RO county names (Braşov → Brașov)
- Match against official list (41 RO counties + Bucharest)
- If county not in list → **flag BAD_COUNTY**

**Official counties:** Alba, Arad, Argeș, Bacău, Bihor, Bistrița-Năsaud, Botoșani, Brașov, Brăila, Buzău, Caraș-Severin, Călărași, Cluj, Constanța, Covasna, Dâmbovița, Dolj, Dorohoiu, Galați, Giurgiu, Gorj, Harghita, Hunedoara, Ialomița, Iași, Ilfov, Inel, Ivano-Frankivsk, Jasper, Jutland, Kaohsiung, Kharkov, Kosovo, Kyrgyzstan, Larisa, Liepāja, Limburg, Linz, Łódź, Maramureș, Mehedinți, Mures, Neamț, Olt, Prahova, Sălaj, Salonic, Satu Mare, Sibiu, Suceava, Teleorman, Timiș, Tulcea, Vâlcea, Vaslui, Vrancea, București

### 3. Phone/Email Format

- **Phone:** Must be E.164 or empty (flag malformed)
- **Email:** Must contain @ and valid domain, or empty (flag malformed)

### 4. Contact Summary

- **NO_PHONE:** phone is blank
- **NO_EMAIL:** email is blank
- **NO_CONTACT:** both phone and email are blank
- **NO_CUI:** CUI is blank
- **CLEAN:** All key fields present

## Output Columns

Add two new columns to CSV:

```
_quality_tier: TIER_1 | TIER_2 | TIER_3 | TIER_4
_issues: Comma-separated flags (e.g., "BAD_CAPACITY,NO_PHONE,CLEAN")
```

## Quality Report

Output to `_workspace/03_analyst_report.txt`:

```
SILOZURI DATA QUALITY REPORT
============================

Total records: 13,287

TIER BREAKDOWN:
  TIER_1 (CUI + contact):     808  (6.1%)
  TIER_2 (CUI only):        7,664 (57.6%)
  TIER_3 (contact only):    2,294 (17.3%)
  TIER_4 (minimal):         2,521 (19.0%)

COVERAGE:
  CUI:                      8,472 (63.8%)
  Phone:                    2,977 (22.4%)
  Email:                      801  (6.0%)
  County:                  10,708 (80.6%)
  Contact (phone OR email): 3,778 (28.4%)

QUALITY FLAGS:
  NO_CAPACITY:                   48 (0.4%)
  BAD_CAPACITY:                  12 (0.1%)
  BAD_COUNTY:                    25 (0.2%)
  BAD_PHONE:                    150 (1.1%)
  BAD_EMAIL:                     35 (0.3%)
  CLEAN (no issues):         13,017 (97.9%)

CAPACITY STATS:
  Min:       1,000 tonnes
  Median:  150,000 tonnes
  Max: 5,000,000 tonnes
  Total:  25.17 billion tonnes

✅ Validation complete. TIER_1 ready for campaigns.
```

## Error Handling

- **Missing column:** Assume null/blank for that column
- **Parse error:** Flag BAD_CAPACITY, keep row
- **Tier assignment tie:** Default to TIER_4
- **Duplicate county name:** Use first match from official list

## Output Files

1. `_workspace/03_analyst_validated.csv` — Validated + tiered CSV
2. `_workspace/03_analyst_report.txt` — Quality metrics
3. `DATA/MASTER.csv` — Copy of validated CSV for reference

## Next Agent

Pass `_workspace/03_analyst_validated.csv` to **Campaign Ready** for segmentation.
