---
name: campaign-ready
description: Segment validated silos into campaign-ready CSVs: TIER_1 (phone calls), cereal buyers (CAEN 4621/4622), tier-filtered exports. Use when the user says "prepare campaigns", "segment for outreach", "export for brevo", "create tier_1 list", or when orchestrator initiates campaign export phase. Outputs Brevo-formatted CSVs + send plan recommendation.
---

# Campaign Ready Skill

Segment validated data for outreach campaigns.

## When to Use

- User: "Prepare campaigns", "Segment by tier", "Export for Brevo"
- Orchestrator: Campaign export phase (final)
- Scenario: Ready to launch cold-email or cold-call campaigns

## Files to Work With

**Input:**
- `_workspace/03_analyst_validated.csv` (from analyst)

**Output:**
- `DATA/MASTER_TIER1_READY_TO_CALL.csv` (TIER_1, 808 rows)
- `BUYERS/cereal_buyers_romania.csv` (CAEN 4621/4622, ~7,934 rows)
- `DATA/MASTER.csv` (Updated canonical)
- `_workspace/04_campaign_segments.txt` (Send plan + stats)

## Segmentation Criteria

### TIER_1: Ready to Call

**Filter:** `_quality_tier == 'TIER_1'`

- **Count:** ~808 rows
- **Criteria:** CUI ✓ AND (phone ✓ OR email ✓)
- **Use case:** Phone-first cold calls (highest confidence)
- **Contact method:** Phone primary, email fallback
- **Expected conversion:** 5-10% (quality leads)

### Cereal Buyers (Supply Chain)

**Filter:** `CAEN in (4621, 4622)` AND (phone ✓ OR email ✓)

- **Count:** ~7,934 rows
- **CAEN codes:** 4621 (grain milling), 4622 (oilseed crushing)
- **Use case:** B2B supply-chain (farmers → buyers)
- **Contact method:** Email + phone
- **Expected conversion:** 3-5% (inquiry leads)

### TIER_2: Email Campaign

**Filter:** `_quality_tier == 'TIER_2'` AND email ✓

- **Count:** ~450 rows
- **Criteria:** CUI ✓, no contact info, but has email from enrichment
- **Use case:** Secondary email campaign
- **Send rate:** 25/day (gentle, ~18 days)

### TIER_3: Phone Outreach

**Filter:** `_quality_tier == 'TIER_3'` AND phone ✓

- **Count:** ~1,200 rows
- **Criteria:** No CUI, but has phone
- **Use case:** Phone research + outreach
- **Contact method:** Phone direct

## Brevo Export Format

**CSV columns for email campaigns:**

```
name,phone,email,county,city,auth_code,capacity_total_t,caen,_quality_tier
"Silo ABC SRL",+40712345678,contact@silo.ro,Bihor,Oradea,MAD12345,250000,1520,TIER_1
...
```

**Important:**
- Phone: E.164 format (required by Brevo)
- Email: Valid email or empty
- All text: UTF-8 encoded, no BOM
- No duplicate emails (Brevo will deduplicate on send)

## Send Plan Recommendation

**Output to `_workspace/04_campaign_segments.txt`:**

```
CAMPAIGN SEND PLAN
==================

TIER_1_READY_TO_CALL (808 rows)
  Contact method: Phone-first (primary), email fallback
  Recommended rate: 50/day gentle (16 days total)
  Rationale: High confidence, but small list
  Expected outcome: 40-80 qualified leads

CEREAL_BUYERS (7,934 rows)
  Contact method: Email + phone
  Recommended rate: 100/day with ramp (79 days total)
    - Days 1-7:  50/day (warmup)
    - Days 8-21: 100/day (plateau)
    - Days 22+: 150/day (peak, watch bounce rate)
  Rationale: Large list, supply-chain quality
  Expected outcome: 200-400 inquiry leads

TIER_2_EMAIL (450 rows)
  Contact method: Email only
  Recommended rate: 25/day (18 days total)
  Rationale: CUI match but no direct contact
  Expected outcome: 15-30 phone-back leads

TIER_3_PHONE (1,200 rows)
  Contact method: Phone research + outreach
  Recommended rate: Manual outreach (not email campaign)
  Rationale: No CUI, need verification before outreach
  Expected outcome: 30-60 qualified leads

TOTAL CAMPAIGN:
  Email sends: 8,384 (TIER_1 + CEREAL + TIER_2)
  Phone outreach: 2,000+ (TIER_1 + TIER_3)
  Timeline: 79 days (CEREAL_BUYERS rate-limiting)
```

## Execution Steps

```python
# Load validated CSV
df = pd.read_csv('_workspace/03_analyst_validated.csv', dtype=str)

# Segment 1: TIER_1
tier1 = df[df['_quality_tier'] == 'TIER_1'].copy()
tier1.to_csv('DATA/MASTER_TIER1_READY_TO_CALL.csv', index=False)
# Count: 808

# Segment 2: Cereal buyers (CAEN 4621 or 4622)
caen_list = ['4621', '4622', '4621.0', '4622.0']
buyers = df[df['caen'].isin(caen_list)].copy()
# Filter: has phone OR has email
buyers = buyers[
    (buyers['phone'].notna() & (buyers['phone'] != '')) |
    (buyers['email'].notna() & (buyers['email'] != ''))
]
buyers.to_csv('BUYERS/cereal_buyers_romania.csv', index=False)
# Count: ~7,934

# Segment 3: TIER_2 with email
tier2 = df[(df['_quality_tier'] == 'TIER_2') & 
           (df['email'].notna()) & (df['email'] != '')]
# Count: ~450

# Segment 4: TIER_3 with phone
tier3 = df[(df['_quality_tier'] == 'TIER_3') & 
           (df['phone'].notna()) & (df['phone'] != '')]
# Count: ~1,200

# Save master copy
df.to_csv('DATA/MASTER.csv', index=False)

# Write send plan
write_send_plan(tier1, buyers, tier2, tier3)
```

## Output Files

1. `DATA/MASTER_TIER1_READY_TO_CALL.csv` — Final TIER_1 (808 rows)
2. `BUYERS/cereal_buyers_romania.csv` — Cereal buyers (7,934 rows)
3. `DATA/MASTER.csv` — Canonical updated copy
4. `_workspace/04_campaign_segments.txt` — Send plan + stats

## Error Handling

- **Empty segment:** Log warning, still output empty CSV (Brevo can handle)
- **Missing CAEN:** Assume not a buyer, exclude from cereal_buyers
- **Duplicate emails across segments:** Keep in both (Brevo deduplicates)
- **Bad phone format:** Include as-is (Brevo may skip during send)

## Next Step

Final CSVs are now ready for:
1. **silozuri-campaign** skill (Brevo email integration)
2. **Manual phone outreach** (TIER_1 + TIER_3 phone lists)
3. **Analytics dashboard** (campaign performance tracking)

---

**Campaign Status:** ✅ Ready to launch
