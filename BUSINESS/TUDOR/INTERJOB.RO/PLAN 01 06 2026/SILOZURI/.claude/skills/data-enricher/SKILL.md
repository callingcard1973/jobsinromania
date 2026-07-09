---
name: data-enricher
description: Enrich silos with phone, email, CUI via CUI-join to master_romania_companies and master_emails. Use when the user says "enrich silozuri", "fill missing contacts", "backfill phone and email", or when orchestrator initiates enrichment phase. Normalizes phone to E.164, fills only blanks, reports coverage before/after.
---

# Data Enricher Skill

CUI-join enrichment: phone/email/CUI backfill from raspibig DB + ANAF.

## When to Use

- User: "Enrich the data", "Add phone numbers and emails", "Backfill contacts"
- Orchestrator: Enrichment phase (after collector)
- Scenario: New enrichment sources available (master_romania_companies, master_emails updated on raspibig)

## Files to Work With

**Input:**
- `_workspace/01_collector_raw_merged.csv` (from collector, or `DATA/MASTER.csv` if re-enriching)

**Enrichment sources:**
- **raspibig DB (via SSH plink to 192.168.100.21, user tudor):**
  - `public.companies_clean` table — CUI index, phone, email, county, CAEN (run `enrich_master.py` or extract via `psql -U tudor -d interjob_master`)
  - `public.master_emails` table — email-keyed lookup (run `enrich_email.py` or extract via psql)
- **Local fallback:**
  - `DATA/raw/ANAF/od_firme.csv` (CUI + county fallback)

**Output:**
- `_workspace/02_enricher_enriched.csv`
- `_workspace/02_enricher_coverage.txt` (report)

## Enrichment Logic

### 1. Build CUI Index

```python
# Load master_romania_companies.csv
mrc = pd.read_csv('master_romania_companies.csv', dtype=str)

# Index by CUI (first occurrence)
cui_index = {}
for idx, row in mrc.iterrows():
    cui = row.get('cui', '')
    if cui and cui not in cui_index:
        cui_index[cui] = row
```

### 2. Fill Blanks Only

```python
# For each silo record:
for idx, silo in master.iterrows():
    cui = silo['cui']
    
    if cui in cui_index:
        mrc_row = cui_index[cui]
        
        # Fill only empty/null fields (never overwrite)
        for col in ['email', 'phone', 'county', 'city', 'caen', 'website']:
            if pd.isna(silo[col]) or silo[col] == '':
                val = mrc_row.get(col, '')
                if val and val != '':
                    silo[col] = val
```

### 3. Phone Normalization

Convert all phone numbers to E.164 format: `+40...`

```python
def normalize_phone(phone):
    if not phone:
        return ''
    # Strip non-digits
    digits = ''.join(c for c in str(phone) if c.isdigit())
    # Convert 0040 → +40, 007 → +407
    if digits.startswith('0040'):
        return '+' + digits[2:]
    elif digits.startswith('0'):
        return '+4' + digits
    elif digits.startswith('40'):
        return '+' + digits
    return '+' + digits if digits else ''
```

### 4. Secondary Email Lookup

If email still blank after CUI-join, try `master_emails.csv` (different schema, email-keyed):

```python
emails = pd.read_csv('master_emails.csv', dtype=str)
email_map = {}
for idx, row in emails.iterrows():
    entity_name = row.get('entity_name', '')
    email = row.get('email', '')
    if entity_name and email:
        email_map[entity_name.upper()] = email

# Try fuzzy match on silo name
silo_name_upper = silo['name'].upper().strip()
if silo_name_upper in email_map and not silo['email']:
    silo['email'] = email_map[silo_name_upper]
```

### 5. ANAF Fallback

If county still missing after CUI-join:

```python
anaf = pd.read_csv('DATA/raw/ANAF/od_firme.csv', dtype=str)
anaf_by_cui = {row['cui']: row for _, row in anaf.iterrows()}

if silo['cui'] in anaf_by_cui and not silo['county']:
    silo['county'] = anaf_by_cui[silo['cui']].get('county', '')
```

## Coverage Report

Output to `_workspace/02_enricher_coverage.txt`:

```
ENRICHMENT REPORT
=================

Before enrichment:
  email:   2,000 (15.0%)
  phone:   3,000 (22.6%)
  cui:     8,500 (63.8%)
  county: 10,700 (80.5%)

After enrichment:
  email:   5,200 (39.1%)
  phone:   8,000 (60.2%)
  cui:     8,500 (63.8%)
  county: 10,700 (80.5%)

Fields filled by source:
  master_romania_companies (CUI-join): 2,200
  master_emails (email-keyed):           500
  ANAF od_firme (county fallback):       200

✅ Enrichment complete
```

## Error Handling

- **raspibig CSV unavailable:** Use local copy if exists, or skip that source (continue with others)
- **CUI mismatch:** If enriched value differs from existing, keep existing and flag in report
- **Phone parse failure:** Keep as-is, log malformed phone number
- **Empty enrichment source:** Skip that source, continue

## Output Files

1. `_workspace/02_enricher_enriched.csv` — Enriched data
2. `_workspace/02_enricher_coverage.txt` — Coverage stats before/after
3. (Optional) `_workspace/02_enricher_errors.log` — Any warnings

## Next Agent

Pass `_workspace/02_enricher_enriched.csv` to **Data Analyst** for validation + tier assignment.
