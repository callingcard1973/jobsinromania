# DATABASE ENRICHMENT PLAN — 2026-03-15

Cross-reference and enrich data between 31 databases to maximize value.

---

## PRIORITY 1: HIGH-VALUE CROSS-MATCHES

### 1.1 TED Awards → Companies (6.2M → 178.8M)
**Goal:** Add procurement history to company records

```sql
-- Match by company name + country
UPDATE companies c
SET ted_wins = (
    SELECT count(*) FROM ted_awards t
    WHERE t.winner_name ILIKE c.name
    AND t.winner_country = c.country
),
ted_total_value = (
    SELECT sum(contract_value) FROM ted_awards t
    WHERE t.winner_name ILIKE c.name
),
last_ted_win = (
    SELECT max(award_date) FROM ted_awards t
    WHERE t.winner_name ILIKE c.name
);
```

**Value:** Companies with TED wins = proven government contractors = high-value targets

---

### 1.2 Insolvency → Companies (1.03M → 178.8M)
**Goal:** Flag distressed companies, identify available workers

```sql
-- Add insolvency status to companies
ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_insolvent BOOLEAN DEFAULT FALSE;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS insolvency_date DATE;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS insolvency_type VARCHAR(50);

UPDATE companies c
SET is_insolvent = TRUE,
    insolvency_date = i.filing_date,
    insolvency_type = i.procedure_type
FROM insolvency i
WHERE c.cui = i.cui OR c.vat_id = i.vat_id;
```

**Value:**
- Insolvent companies = workers seeking jobs
- Equipment/assets available for purchase
- Competitor intelligence

---

### 1.3 Contacts → Companies (555K → 178.8M)
**Goal:** Add verified email/phone to company records

```sql
-- Enrich companies with contact info
UPDATE companies c
SET email = ct.email,
    phone = ct.phone,
    contact_name = ct.name,
    contact_title = ct.title
FROM contacts ct
WHERE c.cui = ct.cui
   OR c.vat_id = ct.vat_id
   OR LOWER(c.name) = LOWER(ct.company_name);
```

**Value:** 555K companies become campaign-ready

---

### 1.4 Agencies → Companies (148K → 178.8M)
**Goal:** Flag recruitment agencies for partnership campaigns

```sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_agency BOOLEAN DEFAULT FALSE;

UPDATE companies c
SET is_agency = TRUE
FROM agencies a
WHERE c.name ILIKE '%' || a.name || '%'
   OR c.email = a.email
   OR c.website = a.website;
```

**Value:** Agencies = direct partners for worker placements

---

## PRIORITY 2: ROMANIA CROSS-ENRICHMENT

### 2.1 romania.companies ↔ romania_emails.contacts
**Goal:** Merge 4.95M companies with 82K enriched contacts

```sql
-- Add enriched contacts to romania.companies
UPDATE romania.companies c
SET email = rc.email,
    phone = rc.phone,
    enriched = TRUE,
    enriched_date = NOW()
FROM romania_emails.contacts rc
WHERE c.cui = rc.cui;
```

### 2.2 romania.contacts → romania.companies
**Goal:** 8.2M contacts matched to 4.95M companies

```sql
-- Create lookup index
CREATE INDEX IF NOT EXISTS idx_romania_contacts_cui ON romania.contacts(cui);
CREATE INDEX IF NOT EXISTS idx_romania_companies_cui ON romania.companies(cui);

-- Match and enrich
UPDATE romania.companies c
SET primary_contact_email = ct.email,
    primary_contact_phone = ct.phone,
    contact_count = (SELECT count(*) FROM romania.contacts WHERE cui = c.cui)
FROM romania.contacts ct
WHERE c.cui = ct.cui
AND ct.email IS NOT NULL;
```

### 2.3 food_distribution → romania.companies
**Goal:** Tag food sector companies

```sql
ALTER TABLE romania.companies ADD COLUMN IF NOT EXISTS is_food_sector BOOLEAN DEFAULT FALSE;
ALTER TABLE romania.companies ADD COLUMN IF NOT EXISTS food_category VARCHAR(50);

UPDATE romania.companies c
SET is_food_sector = TRUE,
    food_category = fd.category
FROM food_distribution.contacts fd
WHERE c.cui = fd.cui OR LOWER(c.name) = LOWER(fd.company);
```

---

## PRIORITY 3: CROSS-COUNTRY ENRICHMENT

### 3.1 norway_emails → interjob_master.companies
**Goal:** Add 155K Norway contacts to master

```sql
INSERT INTO interjob_master.contacts (company_name, email, phone, country, source)
SELECT company_name, email, phone, 'NO', 'norway_emails'
FROM norway_emails.norway_emails
ON CONFLICT (email) DO UPDATE SET
    phone = EXCLUDED.phone,
    updated_at = NOW();
```

### 3.2 bulgaria_emails → interjob_master.companies
**Goal:** Add 143K Bulgaria companies to master

```sql
-- Merge Bulgaria companies
INSERT INTO interjob_master.companies (name, country, email, source)
SELECT name, 'BG', email, 'bulgaria_emails'
FROM bulgaria_emails.companies
WHERE email IS NOT NULL
ON CONFLICT (name, country) DO UPDATE SET
    email = EXCLUDED.email;

-- Add TED notices
INSERT INTO interjob_master.ted_awards (winner_name, winner_country, source)
SELECT company_name, 'BG', 'bulgaria_ted'
FROM bulgaria_emails.ted_notices
ON CONFLICT DO NOTHING;
```

---

## PRIORITY 4: CSV_RAW PROCESSING

### 4.1 Identify valuable tables (4,293 total)

```sql
-- Find tables with email columns
SELECT table_name,
       pg_size_pretty(pg_total_relation_size('public.' || table_name)) as size
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name ILIKE '%email%'
ORDER BY pg_total_relation_size('public.' || table_name) DESC;
```

### 4.2 Extract and dedupe

```bash
# Use existing skill
python3 /opt/ACTIVE/INFRA/SKILLS/csv_email_extractor.py --scan
python3 /opt/ACTIVE/INFRA/SKILLS/cross_db_dedup.py --databases csv_raw,interjob_master
```

### 4.3 Merge into master

```sql
-- Template for each valuable csv_raw table
INSERT INTO interjob_master.contacts (email, company_name, country, source)
SELECT DISTINCT email, company, country, 'csv_raw_' || 'table_name'
FROM csv_raw.table_name
WHERE email IS NOT NULL
  AND email NOT IN (SELECT email FROM interjob_master.contacts);
```

---

## PRIORITY 5: PROCUREMENT CHAIN ENRICHMENT

### 5.1 tenders → ted_awards → companies
**Goal:** Connect tender opportunities to past winners

```sql
-- Find companies that won similar tenders
CREATE MATERIALIZED VIEW procurement_recommendations AS
SELECT
    t.id as tender_id,
    t.title as tender_title,
    t.cpv_code,
    ta.winner_name,
    ta.winner_country,
    c.email,
    COUNT(*) as similar_wins
FROM tenders t
JOIN ted_awards ta ON ta.cpv_code = t.cpv_code
JOIN companies c ON LOWER(c.name) LIKE '%' || LOWER(ta.winner_name) || '%'
WHERE c.email IS NOT NULL
GROUP BY t.id, t.title, t.cpv_code, ta.winner_name, ta.winner_country, c.email
ORDER BY similar_wins DESC;
```

**Value:** Match current tenders to qualified bidders

### 5.2 insolvency → ted_awards
**Goal:** Find contracts needing replacement contractors

```sql
-- Insolvent TED winners = contracts at risk
SELECT ta.*, i.filing_date, i.procedure_type
FROM ted_awards ta
JOIN insolvency i ON LOWER(ta.winner_name) LIKE '%' || LOWER(i.company_name) || '%'
WHERE i.filing_date > ta.award_date
  AND ta.contract_end_date > NOW();
```

**Value:** Replacement contractor opportunities

---

## ENRICHMENT SCRIPTS (Ready to Use)

| Script | Purpose | Location |
|--------|---------|----------|
| fuzzy_enrich.py | Name matching + enrichment | /opt/ACTIVE/INFRA/SKILLS/ |
| cross_db_dedup.py | Find duplicates across DBs | /opt/ACTIVE/INFRA/SKILLS/ |
| csv_email_extractor.py | Extract emails from csv_raw | /opt/ACTIVE/INFRA/SKILLS/ |
| table_schema_analyzer.py | Find email/phone columns | /opt/ACTIVE/INFRA/SKILLS/ |
| firme_internal_enrich.py | Match ANOFM/MASTER_ALL | /opt/ACTIVE/INFRA/SKILLS/ |
| anaf_api.py | ANAF phone/address lookup | /opt/ACTIVE/INFRA/SKILLS/ |

---

## EXECUTION ORDER

### Phase 1: Quick Wins (Today)
1. [ ] TED awards → companies (add procurement history)
2. [ ] Contacts → companies (add emails)
3. [ ] Flag agencies in companies table

### Phase 2: Romania Deep Enrichment (This Week)
4. [ ] romania_emails → romania.companies
5. [ ] romania.contacts → romania.companies
6. [ ] food_distribution tagging
7. [ ] NGO registry cross-match

### Phase 3: Cross-Country (Next Week)
8. [ ] norway_emails → master
9. [ ] bulgaria_emails → master
10. [ ] denmark_emails → master

### Phase 4: csv_raw Mining (Ongoing)
11. [ ] Scan all 4,293 tables for emails
12. [ ] Extract and dedupe
13. [ ] Merge valuable records

### Phase 5: Procurement Intelligence (Ongoing)
14. [ ] Build procurement recommendations view
15. [ ] Flag insolvent TED winners
16. [ ] Match tenders to qualified bidders

---

## EXPECTED OUTCOMES

| Enrichment | Before | After | Value |
|------------|--------|-------|-------|
| Companies with email | ~5M | ~15M | 3x campaign reach |
| Companies with TED history | 0 | 6.2M | Qualified leads |
| Flagged insolvent | 0 | 1.03M | Worker pool + assets |
| Flagged agencies | 0 | 148K | Partner targets |
| Romania enriched | 82K | 500K+ | 6x RO campaigns |
| csv_raw extracted | 0 | Est. 2M | New contacts |

---

## MAINTENANCE

### Daily
- New TED awards → match to companies
- New insolvency filings → flag companies

### Weekly
- csv_raw new imports → extract emails
- Cross-DB dedup scan

### Monthly
- Full fuzzy match refresh
- ANAF API bulk enrichment (Romania)

---

Generated: 2026-03-15
