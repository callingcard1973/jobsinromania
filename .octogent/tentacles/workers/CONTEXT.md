# Workers Tentacle

## What This Is
Worker supply pipeline: CV intake, candidate DB, catalog, solonet orders, placement tracking.

## Key Assets
- **master_applicants.db** — 758+ workers, SQLite at `/opt/ACTIVE/OPENDATA/DATA/master_applicants.db`
- **Workers catalog HTML** — 160 candidates, 8 categories, `build_catalog_cv.py`
- **CV Generator** — FastAPI :5050 on raspibig, `factoryjobs.eu/cv/`, qwen2.5:1.5b streaming
- **Solonet pipeline** — `/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py`, DB: `interjob_master.solonet_orders`
- **Worker router** — `/opt/ACTIVE/INFRA/SKILLS/worker_router.py`, auto-routes applications + reply with apply form

## Telegram Commands
`/workers` — worker stats
`/solonet` `/send_solonet_X` `/solonet_placed_X <w> <eur>` — solonet orders
`/responses` `/leads` — inbound tracking

## Apply Flow
All apply links → `https://interjob.ro/apply.html`
Worker applications → `master_applicants.db` + auto-reply
Romanian employer leads → solonet draft order (Tudor approves via `/send_solonet_X`)

## Catalog Send
Script: `/opt/ACTIVE/CATALOGS/` | Brevo PDF attachment | reply-to: manpower.dristor@gmail.com
Command: `/send_catalog` via Telegram bot | 9 sectors

## Solonet Pipeline States
`draft → sent → responded → placed`
Auto follow-up after 3 days. Revenue tracked via `/solonet_placed_X <workers> <eur>`.

## Key Directories
- `D:\MEMORY\CODE\INFRA\CV\` — CV generator source
- `D:\MEMORY\CODE\INFRA\CATALOGS\` — catalog scripts
- `/opt/ACTIVE/CV/` — raspibig CV scanner + web UI
- `/opt/ACTIVE/CATALOGS/` — catalog send system
