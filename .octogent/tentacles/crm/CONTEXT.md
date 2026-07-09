# crm

Employer/worker/deal pipeline connecting campaign replies to revenue.

## Scope

- `CODE/CRM/` — deal CRUD, worker matching, Solonet sync, bot commands, schema
- Tables: `crm_employers`, `crm_deals`, `crm_interactions`, `solonet_orders`, `master_applicants`

## Key Decisions

- **CRM is read-only on upstream tables** — `leads`, `contacts`, `master_emails`, `companies_clean` are never modified by CRM scripts. CRM pulls from them, writes only to `crm_*` tables.
- **DSN fallback pattern** — every script detects socket path (`/var/run/postgresql`) to auto-switch between raspibig and laptop. Don't break this two-environment DSN pattern.
- **`crm_deals` is the revenue record** — stage progression: `lead → qualified → intro_sent → interview → offer → placed → paid`. `placed_at` and `paid_at` stamped automatically on advance.
- **Solonet orders feed deals** — `solonet_orders` (partner placement requests) link to `crm_deals.id` via `crm_deal_id`. Unlinked orders show in pipeline as open work.
- **Worker matching is keyword-based** — `match.py` maps job titles to sector keywords, then queries `applications` table with `ILIKE`. No ML. Country preference scores first.

## Conventions

- All scripts use `psycopg2` + `RealDictCursor` — rows accessed as dicts, not tuples.
- CLI pattern: `python deal.py <command> [args]` — no argparse for `advance/note/show/list`, raw `sys.argv`.
- `get_or_create_employer()` in `deal.py` — always upsert-style lookup before inserting a deal. Don't insert raw employer names.
- Notes on deals append, never overwrite: `COALESCE(notes || E'\\n', '') || %s`.
- Always check `dnc_list` before any outreach triggered from CRM data.
- Never DELETE from `leads`, `contacts`, `master_emails`, `companies_clean`.

## DB Connection

```python
import os, psycopg2
DSN = os.getenv("DATABASE_URL",
    "host=/var/run/postgresql dbname=interjob_master user=tudor password=scraper123"
    if os.path.exists("/var/run/postgresql") else
    "host=127.0.0.1 port=5433 dbname=interjob_master user=tudor password=tudor"
)
```

## Key Commands

```bash
python CODE/CRM/pipeline.py            # view deal board + open solonet orders
python CODE/CRM/deal.py list           # list all deals
python CODE/CRM/deal.py add --employer "ABC GmbH" --job welder --country DE --workers 3
python CODE/CRM/deal.py advance <id>   # move to next stage
python CODE/CRM/match.py <deal_id>     # find matching workers
python CODE/CRM/match.py <deal_id> --assign <applicant_id>
```
