# Full Database Enrichment Plan
Generated: 2026-03-15

## Database Inventory

### Raspibig (192.168.100.21) - 18 databases
| Database | Purpose | Key Tables |
|----------|---------|------------|
| interjob_master | MASTER - 178M companies | companies, contacts, agencies, ted_awards, tenders, insolvency |
| romania | RO companies 4.95M | companies, procurement |
| romania_emails | RO campaign contacts 60K+ | contacts |
| bulgaria_emails | BG B2B data 143K | companies |
| norway_emails | NO campaign 155K | norway_emails |
| denmark_emails | DK campaign | contacts |
| moldova | MD companies | companies |
| csv_raw | Raw imports 4,293 tables | various |
| opendata | Open data archive | various |
| eures | EU job data | jobs |
| cifn_eu | EU funding portal | funding_calls |
| email_sender | Send logs | send_log, responses |
| carbon_credits | Agri carbon | projects |
| food_distribution | Food sector | producers |

### Raspi (192.168.100.20) - 11 databases
| Database | Purpose | Key Tables |
|----------|---------|------------|
| email_sender | Send logs (backup) | send_log |
| bounce_processor | Bounce tracking | bounces |
| listmonk | Campaign management | subscribers |
| romania | RO data (backup) | companies |
| master_db | Legacy master | contacts |
| eures | EU jobs (backup) | jobs |
| csv_raw | Raw imports | various |

## Enrichment Strategy

### Phase 1: Country DB to Master (PRIORITY)
Pull unique emails/phones from country DBs into interjob_master

1. **Norway** - 155K companies with email → master
2. **Bulgaria** - 143K companies → master
3. **Denmark** - contacts → master
4. **Moldova** - companies → master
5. **Romania emails** - 60K contacts → master

### Phase 2: Master to Country DBs
Push enriched data from master back to country DBs

1. **TED wins** - tag companies with tender wins
2. **Insolvency flags** - mark insolvent companies
3. **Agency flags** - mark recruitment agencies

### Phase 3: Cross-DB Sync
1. **Bounce sync** - raspibig ↔ raspi bounce lists
2. **DNC sync** - unified do-not-contact list
3. **Send log sync** - unified campaign tracking

### Phase 4: Email Extraction
Extract emails from csv_raw tables (4,293 tables)

## SQL Commands

### Norway → Master (Running)
```sql
UPDATE companies c
SET enriched_email = n.email
FROM norway_email_temp n
WHERE LOWER(TRIM(c.name)) = n.lname
AND c.country = 'NO'
AND c.email IS NULL
AND c.enriched_email IS NULL;
```

### Bulgaria → Master
```sql
-- Export from bulgaria_emails
\copy (SELECT LOWER(TRIM(name)) as lname, email FROM companies WHERE email IS NOT NULL) TO '/tmp/bulgaria_emails.csv' CSV HEADER;

-- Import to interjob_master
CREATE TABLE bulgaria_email_temp (lname text, email text);
\copy bulgaria_email_temp FROM '/tmp/bulgaria_emails.csv' CSV HEADER;

-- Enrich
UPDATE companies c
SET enriched_email = b.email
FROM bulgaria_email_temp b
WHERE LOWER(TRIM(c.name)) = b.lname
AND c.country = 'BG'
AND c.email IS NULL
AND c.enriched_email IS NULL;
```

### TED Wins → All Countries
```sql
WITH ted_counts AS (
    SELECT winner_name, winner_country, COUNT(*) as wins
    FROM ted_awards
    WHERE winner_name IS NOT NULL
    GROUP BY winner_name, winner_country
)
UPDATE companies c
SET ted_wins = t.wins
FROM ted_counts t
WHERE LOWER(TRIM(c.name)) = LOWER(TRIM(t.winner_name))
AND c.country = t.winner_country
AND (c.ted_wins IS NULL OR c.ted_wins = 0);
```

## Progress Tracking (Updated 2026-03-15 03:15 UTC)

| Task | Status | Rows Affected |
|------|--------|---------------|
| SEAP wins (Romania db) | DONE | 61,910 |
| Insolvent flag (Romania db) | DONE | 222,658 |
| Norway email enrich | DONE | name-matched |
| Bulgaria CUI enrich | DONE | CUI-matched |
| Moldova email enrich | DONE | 65 matches |
| Denmark email enrich | DONE | 2,460 matches |
| Agency flag (178M master) | RUNNING | ~45 min |
| Insolvency flag (178M master) | RUNNING | ~43 min |
| TED wins → All | PENDING | ~6.2M awards |
| Bounce sync | PENDING | ~579+ |

## Notes

- 178M row table updates take 45+ minutes each
- Name matching yields low match rates (different naming conventions)
- CUI matching works better when identifiers available
- Country filtering speeds up queries significantly
