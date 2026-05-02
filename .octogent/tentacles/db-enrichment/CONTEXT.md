# Tentacle: db-enrichment

## Machine
raspibig — 192.168.100.21 (SSH key auth)
DB: interjob_master PostgreSQL 18, port 5433, user tudor/tudor

## Local DB (laptop fallback)
PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master

## Scripts Location
D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\CODE\

## Key Tables
| Table | Rows | Notes |
|---|---|---|
| companies_clean | 33M | no auto-increment, use MAX(id)+ROW_NUMBER() |
| master_emails | 1.03M | quality_tier 1-4 |
| ted_awards | 6.2M | buyer=cae_name, winner=win_name |
| no_companies_full | large | konkurs field = NO insolvency |

## Rules (NEVER break)
- Min 8 char normalized name for cross-ref
- COUNT before UPDATE
- CUI > name match priority
- No placeholders, sequential UPDATEs
- COALESCE(email, enriched_email) for all email lookups
- Never drop tables without backup confirmation

## CSV Output
D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\DATA\

## Resume Command
```bash
BASE="/d/MEMORY/CODE/CAMPAIGNS/EMAIL PERSONAL/CODE"
PSQL='"/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master'
PGPASSWORD=tudor eval "$PSQL -f '${BASE}/<step>.sql'" 2>&1 | tail -5
```
