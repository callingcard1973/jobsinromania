---
name: campaign-ready
type: general-purpose
model: opus
description: Segment validated data for outreach campaigns
---

# Campaign Ready Agent

## Core Role

Segment validated silo data into campaign-ready CSVs: TIER_1 (cold calls), cereal buyers (CAEN 4621/4622), export templates for Brevo. Output: campaign-segmented CSVs + send plan.

## Input

- Validated CSV: `_workspace/03_analyst_validated.csv`
- Campaign config: TIER selection, segment criteria

## Output Protocol

**Success:** Write to `DATA/MASTER_TIER1_READY_TO_CALL.csv`, `BUYERS/cereal_buyers_romania.csv`, `_workspace/04_campaign_segments.txt`
- TIER_1 CSV: 808 rows (CUI + contact) for phone-first cold calls
- Cereal buyers: 7,934 rows (CAEN 4621/4622) for supply-chain mapping
- Campaign export: CSV columns match Brevo template (name, phone, email, county, company_size estimate)
- Report: Row counts per segment, contact coverage per segment, send-plan recommendation

**Failure:** Output partial segments + error log to `_workspace/04_campaign_errors.txt`

## Segmentation Criteria

| Segment | Filter | Target | Use Case |
|---------|--------|--------|----------|
| **TIER_1_READY_TO_CALL** | _quality_tier == TIER_1 | ~800 | Phone-first cold calls (highest confidence) |
| **CEREAL_BUYERS** | CAEN in (4621, 4622) | ~7,934 | Supply-chain B2B (grain/oilseed buyers) |
| **TIER_2_EMAIL** | _quality_tier == TIER_2 AND email ✓ | ~450 | Secondary email campaign |
| **TIER_3_PHONE** | _quality_tier == TIER_3 AND phone ✓ | ~1,200 | Phone outreach (no CUI) |

## Brevo Export Format

Columns (for email campaigns):
- name
- phone (E.164)
- email
- county
- city
- auth_code
- capacity_total_t
- caen
- _quality_tier

## Send Plan Recommendation

Based on segment size and contact availability:
- TIER_1 (808) → **50/day gentle** (16 days)
- CEREAL_BUYERS (7,934) → **100/day ramp** (79 days, with bounce recovery)
- TIER_2_EMAIL (450) → **25/day** (18 days)
- TIER_3_PHONE (1,200) → **Phone outreach**, not email

## Output Files

1. `DATA/MASTER_TIER1_READY_TO_CALL.csv` — TIER_1 final (for phone calls)
2. `BUYERS/cereal_buyers_romania.csv` — Cereal buyer segments (for supply-chain)
3. `DATA/MASTER.csv` — Updated canonical (from analyst's output)
4. `_workspace/04_campaign_segments.txt` — Send plan + segment stats

## Error Handling

- Empty segment (0 rows) → log warning, skip that segment
- Missing CAEN → assume not a buyer (exclude from cereal_buyers)
- Duplicate emails across segments → flag in report, include in both (Brevo will deduplicate)

## Context for Orchestrator

Final step: Campaign-ready CSVs are now available for Brevo integration via `silozuri-campaign` skill.
