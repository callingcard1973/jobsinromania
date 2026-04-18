# Where To Apply Zero-Token Email Scraper (2026-04-12)

## CURRENTLY RUNNING ON RASPIBIG (3 jobs, 90 workers)

| Job | Input | Total | Progress | Est. Finish |
|-----|-------|-------|----------|-------------|
| OSM hotels EU | osm_hotels_europe.csv | 9,651 | ~1,800 | ~30 min |
| Wikidata hotels | wikidata_hotels.csv | 30,000 | ~200 | ~2h |
| France hotels | france_hotels_clean.csv | 21,155 | ~1,000 | ~1.5h |

## CSV FILES WITH WEBSITE BUT NO EMAIL (local D:\MEMORY)

### Already scraped:
- Romania agencies (2,968) → agentii_scraped.csv ✅ DONE
- OSM hotels EU (9,651) → RUNNING
- Wikidata hotels (30,000) → RUNNING
- France hotels (21,155) → RUNNING

### TO DO — from local CSVs:
(Results from scan — update when scan completes)

## DATABASE TABLES (raspibig interjob_master) — WEBSITE WITHOUT EMAIL

### Known results:
- **ted_winners:** 544,714 with website, ALL have email → 0 gap ✅

### Pending queries (running on 208M+ rows):
- **companies** (208M) — website vs email gap: PENDING
- **master_romania_companies** (8.8M) — PENDING
- **ro_companies_onrc** (4.1M) — PENDING
- **agencies** — PENDING

### Query to check any table:
```sql
SELECT count(*) as total,
  count(*) FILTER (WHERE website IS NOT NULL AND website != '') as has_web,
  count(*) FILTER (WHERE email IS NOT NULL AND email LIKE '%@%') as has_email,
  count(*) FILTER (WHERE website IS NOT NULL AND website != '' 
    AND (email IS NULL OR email NOT LIKE '%@%')) as web_no_email
FROM table_name;
```

## HOW TO SCRAPE ANY NEW DATASET

### From CSV:
```bash
# On raspibig (24/7, 30 workers)
scp INPUT.csv tudor@192.168.100.21:/opt/ACTIVE/FLIGHTS/
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/FLIGHTS && /opt/ACTIVE/INFRA/venv/bin/python3 scrape_emails_from_websites.py INPUT.csv --url-col COLUMN_NAME --workers 30 --output OUTPUT_enriched.csv'
scp tudor@192.168.100.21:/opt/ACTIVE/FLIGHTS/OUTPUT_enriched.csv "D:/MEMORY/AIR TICKETS/"
```

### From PostgreSQL:
```bash
# Export websites without email to CSV
ssh tudor@192.168.100.21 "psql -U tudor -d interjob_master -c \"
COPY (SELECT id, name, website FROM table_name 
      WHERE website IS NOT NULL AND website != '' 
      AND (email IS NULL OR email NOT LIKE '%@%')
      LIMIT 50000) 
TO '/tmp/to_scrape.csv' CSV HEADER;
\"" 

# Scrape
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/FLIGHTS && /opt/ACTIVE/INFRA/venv/bin/python3 scrape_emails_from_websites.py /tmp/to_scrape.csv --url-col website --workers 30 --output /tmp/scraped_emails.csv'

# Import back
ssh tudor@192.168.100.21 "psql -U tudor -d interjob_master -c \"
CREATE TEMP TABLE email_import (id int, name text, website text, _url_used text, _status text, emails_found text, email_count int, phones_found text, socials_found text, pages_checked int);
COPY email_import FROM '/tmp/scraped_emails.csv' CSV HEADER;
UPDATE table_name t SET enriched_email = i.emails_found FROM email_import i WHERE t.id = i.id AND i.email_count > 0;
\""
```

## SKILL LOCATION
- Script: `/opt/ACTIVE/FLIGHTS/scrape_emails_from_websites.py`
- Local: `D:\MEMORY\AIR TICKETS\scrape_emails_from_websites.py`
- Skill doc: `C:\Users\apami\.claude\skills\zero-token-website-scraper.md`
