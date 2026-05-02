# Data-DB Tentacle

## Scope
D:\MEMORY\DATA\ — databases, scraped datasets

## DB
PostgreSQL 18, port 5433, interjob_master
Connect: PGPASSWORD=tudor psql -U tudor -h 127.0.0.1 -p 5433 -d interjob_master

## Key tables
- companies_clean: 33M rows (master company DB)
- master_emails: 1.03M (quality_tier 1-4)
- ted_awards: 6.2M (EU procurement winners)
- tenders: 5.1M (EU tenders)
- seap_ro_awards: growing (RO SEAP)
- solonet_orders: live placement orders

## Enrichment pipeline
D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\CODE\
Steps 1-46 built. Steps 22,23,25-27,31,32,35,36 interrupted — resume with batch in CLAUDE.md

## Rules
- Never delete data without confirming duplicate exists
- No auto-increment on companies_clean.id — use MAX(id)+ROW_NUMBER()
- Always use COALESCE(email, enriched_email)
