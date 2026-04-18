# DB Cleanup + Safe Enrichment + ULTRAPLAN Activation

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revert the bad TED cross-ref (8.8M false emails), safely re-enrich companies using CUI-only methods, then activate ULTRAPLAN campaigns on clean data.

**Architecture:** Phase 1 reverts all TED-polluted emails (reset to pre-enrichment state for non-RO). Phase 2 re-enriches safely using CUI matches only. Phase 3 activates campaigns on verified data.

**Tech Stack:** PostgreSQL on raspibig (192.168.100.21), SSH, psql

---

## Problem Summary

On 2026-04-14, a TED winners cross-ref using normalized company names propagated 183K unique emails to 8.8M company rows. Short names (3-4 chars) caused massive false positives. Example: "AB" matched thousands of unrelated companies.

**Pre-enrichment baseline (from ULTRAPLAN_STATUS.md 2026-04-10):**
- RO: 27,905 emails | NO: 314,116 | BG: 26,024 | MD: 8,706
- PL: 4,222 | UA: 4,714 | GR: 3,816 | DE: 375 | FR: 2,589

**Current (polluted):**
- RO: 355,652 | NO: 344,607 | UA: 4,649,270 | FR: 1,214,266
- PL: 621,004 | DE: 377,732 | BG: 157,285 | GR: 69,822 | MD: 50,142

---

## Phase 1: Revert Bad Enrichment (30 min)

### Task 1: Full revert of TED cross-ref

The TED UPDATE ran ~3-4 hours ago. All affected rows have `updated_at` in that window. Safest approach: NULL out email for ALL rows updated in that window, EXCEPT rows that had email BEFORE (from legitimate sources).

**Files:** None — pure SQL on raspibig

- [ ] **Step 1: Count what to revert per country**

```sql
SELECT country, COUNT(*) as to_revert
FROM companies
WHERE updated_at > '2026-04-14 01:00:00'
  AND email IS NOT NULL AND email != ''
GROUP BY country ORDER BY to_revert DESC;
```

Expected: millions for UA, FR, PL, DE. Low thousands for RO (legitimate CUI matches mixed in).

- [ ] **Step 2: Revert ALL non-RO countries (they had no CUI matches, only bad TED name matches)**

```sql
UPDATE companies SET email = NULL, website = NULL, updated_at = NOW()
WHERE updated_at > '2026-04-14 01:00:00'
  AND country NOT IN ('RO', 'NO')
  AND email IS NOT NULL;
```

Why exclude NO: Norway had 314K emails BEFORE enrichment + only 30K added (legitimate pattern enrichment from raspibig, not TED). 
Why exclude RO: had legitimate CUI matches (master_romania 5,811 + romania_campaign 498 + insolvency 415 + ONRC pending). Need selective revert.

- [ ] **Step 3: Revert RO rows that came from TED (not CUI)**

RO legitimate sources updated ~7K rows via CUI. TED updated ~320K rows via name. Revert the name-matched ones:

```sql
-- Revert RO companies where the email exists in ted_winners but NOT in master_romania/romania_campaign/insolvency
UPDATE companies c SET email = NULL, updated_at = NOW()
WHERE c.country = 'RO'
  AND c.updated_at > '2026-04-14 01:00:00'
  AND c.email IS NOT NULL
  AND c.email NOT IN (
    SELECT email FROM master_romania_companies WHERE email IS NOT NULL AND email != ''
    UNION
    SELECT email FROM romania_campaign WHERE email IS NOT NULL AND email != ''
    UNION
    SELECT company_email FROM insolvency WHERE company_email LIKE '%@%'
  );
```

- [ ] **Step 4: Verify counts match pre-enrichment baseline**

```sql
SELECT country, COUNT(CASE WHEN email != '' THEN 1 END) as with_email
FROM companies
WHERE country IN ('RO','NO','BG','MD','PL','UA','GR','DE','FR')
GROUP BY country ORDER BY with_email DESC;
```

Expected:
- RO: ~35,000 (28K original + 7K legitimate CUI enrichment)
- NO: ~344K (314K + 30K pattern enrichment)
- Others: back to original counts

- [ ] **Step 5: Also revert placeholder/junk emails globally**

```sql
DELETE FROM companies WHERE email LIKE '%@domene.no';
UPDATE companies SET email = NULL WHERE email LIKE '%@domain.com';
UPDATE companies SET email = NULL WHERE email LIKE '%sentry%';
UPDATE companies SET email = NULL WHERE email LIKE '%example.com';
UPDATE companies SET email = NULL WHERE email = '';
```

---

## Phase 2: Safe Re-Enrichment (1 hour)

Rules from feedback_enrichment_crossref_rules.md:
- CUI match > name match. Always.
- Min 8 chars normalized name if no CUI.
- COUNT before UPDATE.
- Sequential, never parallel UPDATEs on same table.

### Task 2: RO enrichment via CUI (safe, unique identifier)

- [ ] **Step 1: ONRC → companies by CUI**

```sql
SELECT COUNT(*) FROM ro_companies_onrc o
JOIN companies c ON o.cui = c.cui AND c.country='RO'
WHERE o.email LIKE '%@%' AND (c.email IS NULL OR c.email='');
-- Only if count < 50K, proceed:
UPDATE companies c SET email = o.email, updated_at = NOW()
FROM ro_companies_onrc o
WHERE o.cui = c.cui AND c.country='RO'
  AND o.email LIKE '%@%' AND (c.email IS NULL OR c.email='');
```

- [ ] **Step 2: master_romania → companies by CUI**

Same pattern: COUNT first, UPDATE if reasonable.

- [ ] **Step 3: romania_campaign → companies by CUI**

Same pattern.

- [ ] **Step 4: Verify — no email on >3 companies**

```sql
SELECT email, COUNT(*) FROM companies
WHERE country='RO' AND email != '' AND updated_at > NOW() - INTERVAL '1 hour'
GROUP BY email HAVING COUNT(*) > 3 ORDER BY COUNT(*) DESC LIMIT 10;
```

### Task 3: Safe TED cross-ref (name >= 8 chars, with verification)

- [ ] **Step 1: COUNT with strict filters**

```sql
SELECT COUNT(DISTINCT c.id)
FROM companies c
JOIN ted_winners t ON 
  UPPER(REGEXP_REPLACE(c.name, '[^a-zA-Z0-9]', '', 'g')) = 
  UPPER(REGEXP_REPLACE(t.contractor, '[^a-zA-Z0-9]', '', 'g'))
WHERE (c.email IS NULL OR c.email = '')
  AND t.contractor_email LIKE '%@%'
  AND LENGTH(REGEXP_REPLACE(c.name, '[^a-zA-Z0-9]', '', 'g')) >= 8
  AND t.contractor_email NOT LIKE '%@domene.no'
  AND t.contractor_email NOT LIKE '%@domain.com';
```

If count > 100K: too many, increase min length to 10.
If count < 50K: proceed with UPDATE.

- [ ] **Step 2: UPDATE with same filters**

- [ ] **Step 3: Verify no over-propagation**

### Task 4: Continue raspibig enrichments (already running)

- [ ] Check pattern_fr.log (30K+ found, should be done)
- [ ] Check enrichment_fr.log and enrichment_no.log
- [ ] Upload any laptop domain_guess results

---

## Phase 3: ULTRAPLAN Campaign Activation (1 hour)

With clean data, activate the revenue-generating campaigns.

### Task 5: Verify email capacity (Brevo keys)

- [ ] Run validate_campaigns.py
- [ ] Confirm 13 working Brevo keys
- [ ] Confirm orchestrator picks up fixed configs

### Task 6: Activate campaigns (Tudor approval needed for each)

Priority order (revenue impact):

- [ ] **P1: Norway accelerare** — change daily_limit 200→500 in norway.json
  - 154K pending, all 16 sectors with working keys now
  
- [ ] **P2: EBRD Romania** — enable ebrd_constructori.json
  - 685 companies, 50/day, 9 contractors with direct contact

- [ ] **P3: EBRD 5 countries** — enable poland/ukraine/moldova/bulgaria/greece configs
  - 1,844 companies total, 50/day each

- [ ] **P4: AgroEvolution premium** — enable agroevolution_premium.json
  - 1,111 producers, 100/day

- [ ] **P5: Insolvency alerts** — enable cifn_insolvency.json + cifn_insolvency_companies.json
  - 4,641 contacts, 50/day each

- [ ] **P6: Agencies D2** — enable recruitment_agencies.json (NEEDS TEMPLATE APPROVAL)
  - 18,133 agencies, 500/day

### Task 7: Monitor first sends

- [ ] Wait for business hours (8-9 AM Romania/Norway)
- [ ] Check orchestrator.log for "Sent:" lines
- [ ] Verify no bounces in first batch
- [ ] Check Brevo dashboard for delivery rates

---

## Phase 4: Revenue Pipeline (ongoing)

### Task 8: TED Winners dedicated campaign (NEW — not cross-ref)

Instead of polluting companies table, create SEPARATE campaign table:

```sql
CREATE TABLE ted_campaign AS
SELECT DISTINCT ON (contractor_email)
  contractor as company, contractor_email as email,
  contractor_country as country, contractor_city as city,
  cpv, contract_value
FROM ted_winners
WHERE contractor_email LIKE '%@%'
  AND contractor_email NOT LIKE '%@domene.no'
  AND contractor_email NOT LIKE '%@domain.com'
ORDER BY contractor_email, id DESC;
```

Then configure 5 campaign configs (DE, FR, ES, PL, SE) pointing to ted_campaign table.
370K unique emails, 250/day per country = 1,250/day total.

### Task 9: Data quality cron

Create daily cron that:
1. Counts emails per country in companies (detect unexpected spikes)
2. Checks for placeholder emails
3. Alerts if any email appears on >5 companies
4. Logs to /opt/ACTIVE/EBRD/data_quality.log

---

## Success Criteria

- [ ] Companies table email counts match pre-enrichment + legitimate CUI enrichment only
- [ ] RO: ~35K emails (28K + 7K CUI)
- [ ] NO: ~345K (314K + 31K pattern)
- [ ] Others: back to original counts
- [ ] Orchestrator sending >500/day (up from 50)
- [ ] No emails on >5 companies (except legitimate chains)
- [ ] TED campaign as separate table, not polluting companies
- [ ] validate_campaigns.py passes with 0 DEAD_KEY issues

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|-------------|
| Phase 1: Revert | 30 min | None |
| Phase 2: Safe re-enrich | 1 hour | Phase 1 done |
| Phase 3: Activate campaigns | 30 min | Phase 2 verified + Tudor approval |
| Phase 4: TED campaign + quality cron | 1 hour | Phase 1 done |
| **Total** | **3 hours** | |
