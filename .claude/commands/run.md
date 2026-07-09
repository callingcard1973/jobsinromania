---
description: Run DB pipeline step directly without loading full context
syntax: /run step{N}
example: /run step22
---

Execute pipeline step N directly using Bash with psql. NEVER load context.

## Database
- **Host**: 127.0.0.1:5433
- **DB**: interjob_master
- **User/Pass**: tudor/tudor

## Scripts Location
`D:\MEMORY\CODE\ACTIVE\CAMPAIGNS\EMAIL PERSONAL\CODE\step{N}.py` or `.sql`

## Execution
```bash
# Python step
python "D:\MEMORY\CODE\ACTIVE\CAMPAIGNS\EMAIL PERSONAL\CODE\step$1.py"

# SQL step
PGPASSWORD=tudor "/c/Users/apami/pg18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master -f "D:\MEMORY\CODE\ACTIVE\CAMPAIGNS\EMAIL PERSONAL\CODE\step$1.sql"
```

## Examples
- `/run step22` → executes step22_import_procurement_buyers.sql
- `/run step13` → executes step13_fr_pattern_enrich.py

Return the exact command output + any errors.