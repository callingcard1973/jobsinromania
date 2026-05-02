# CODE INSPECTOR FOR RASPI

Deployment map and reuse guide for all code running on raspi (192.168.100.20).

## Scope

- `/opt/ACTIVE/` — all active deployments (803+ scripts in INFRA/SKILLS alone)
- `/opt/SANDBOX/` — experimental scrapers (EU suppliers by country)
- `/opt/WORKERS/` — worker data
- `~/.node-red/` — Node-RED orchestration flows

## What's Running (systemd services)

| Service | Port | Purpose |
|---|---|---|
| `cifn-api.service` | — | CIFN.eu Company Intelligence REST API (Docker) |
| `eures-scraper.service` | — | Continuous EURES job scraper |
| `applicant-dashboard.service` | — | Web UI for applicant management |
| `nodered.service` | 1880 | Node-RED — ALL scheduling (not cron) |
| `postgresql@17-main` | 5432 | Main DB: `interjob_master` |
| `caddy.service` | 80/443 | Reverse proxy |
| `php8.4-fpm.service` | — | PHP for web apps |

## Code Departments

### `/opt/ACTIVE/INFRA/SKILLS/` — Master Skill Library (803 scripts)

The authoritative tool collection. Everything is callable standalone or imported.

Key categories (from SKILLS/CLAUDE.md):
- **Data:** `csv_summarizer`, `contact_dedup`, `master_contacts`, `data_quality_checker`, `onrc_filter`, `agency_splitter`
- **Scrapers:** `scraper_monitor`, `scraper_quality`, `scraper_tester`, `scraper_prerun`, `crowdfunding_scraper`
- **Email:** `bounce_manager`, `failover_sender`, `a2_warmup`, `brevo_spam_check`, `campaign_cleaner`, `email_organizer`
- **Campaign auto:** `scraper_to_campaigns`, `system_capacity`, `campaign_llm_manager`, `brevo_warmup_continuous`
- **CV/Applicants:** `applicant_search`, `cv_manager`, `cv_processor`
- **Ops:** `health_monitor`, `path_fixer`, `backup_restore`, `sync_manager`, `blacklist_checker`
- **Campaigns control:** `campaign_command_center_skill.py` — reusable Flask+CLI controller: pause/start/status/limit for any campaign dir

Campaign command pattern:
```bash
python3 /opt/ACTIVE/INFRA/SKILLS/campaign_command_center_skill.py \
  --campaign-dir /opt/ACTIVE/<CAMPAIGN> --status
```

### `/opt/ACTIVE/FLIGHTS/` — Email Enrichment Agents (13 scripts)

Zero-token batch agents that run nightly on cron/Node-RED:

| Script | Agent # | Job |
|---|---|---|
| `agent_warmth_scorer.py` | 34+36+38+37 | Score + clean master_emails (SQL only) |
| `agent_auto_campaign_builder.py` | 35+22+31 | Auto-build campaigns when >500 new emails |
| `agent_mx_validator.py` | — | Validate MX records |
| `agent_email_guesser.py` | — | Guess missing emails from name+domain |
| `agent_anaf_enrichment.py` | — | ANAF API company data enrichment |
| `email_enrichment_pipeline.py` | — | Pipeline: find websites→scrape emails→update 20+ DB tables |
| `agent_sitemap_miner.py` | — | Extract emails from sitemaps |
| `agent_whois_email.py` | — | WHOIS contact email extraction |
| `agent_cross_db_enrichment.py` | — | Cross-table enrichment |
| `agent_campaign_launcher.py` | — | Launch campaigns from Node-RED trigger |
| `agent_company_registry_sync.py` | — | Sync company registry data |
| `agent_ted_enricher.py` | — | TED procurement enrichment |
| `agent_duplicate_detector.py` | — | Cross-DB dedup |

All agents: `psql -U tudor -d interjob_master` via subprocess. Logs to `/opt/ACTIVE/FLIGHTS/logs/`. State in JSON files.

### Telegram Sector Bots (`*_bot/` dirs)

Three bots, all from the same template (clone-ready pattern):

| Dir | Bot | Sector |
|---|---|---|
| `meatworkers_bot/` | Meat Workers EU | Meat processing |
| `buildjobs_bot/` | BuildJobs EU | Construction |
| `factoryjobs_bot/` | FactoryJobs EU | Factory/manufacturing |

Each bot: multilingual CV intake via Telegram conversation flow. Saves to `cv_submissions/` CSV + `db_applications.py` (PostgreSQL). Config block at top — swap `BOT_NAME/SECTOR/WEBSITE` to clone for new sector.

### `/opt/ACTIVE/event_publisher/` — Social Job Publisher

Posts jobs to 6 Telegram channels (see memory: Event & Job Auto-Publisher):
- `job_publisher.py` — reads EURES CSVs + ANOFM CSVs, translates RO→EN via Argos (offline), posts to `@jobsineurope` / `@jobsinromania`
- `publisher.py` — generic multi-platform publisher
- `image_gen.py` — job image generation
- `scraper.py` — event data scraper

Apply links always → `https://interjob.ro/apply.html`

### `/opt/ACTIVE/AGENTS/TERENURI/` — Land/Agri Intelligence Agents

LLM agents for MADR land sale data (agroevolution.com). 5 agents defined.

### `/opt/ACTIVE/EU_FUNDING/` — EU Funds

Scrapers for PNRR/EU beneficiary data. Feeds campaigns.

### `/opt/ACTIVE/EURES/` — EURES Import

`import_eures_contacts.py` — imports scraped EURES employer contacts to DB + Brevo.

### `/opt/ACTIVE/PRODUSMONTAN/` — Produs Montan Catalog

Mountain product catalog (1,507 producers, 4,686 products). Separate DATA/CODE/catalog dirs.

## Key Conventions

- **DB access:** always `psql -U tudor -d interjob_master` via subprocess (not psycopg2 directly in agents)
- **Scheduling:** Node-RED only, not cron (except legacy). UI at `http://localhost:1880`
- **Logs:** each module writes to its own `/opt/ACTIVE/<MODULE>/logs/` dir
- **State:** JSON files alongside scripts (not DB) for pause/resume state
- **Max workers:** 20 concurrent HTTP in FLIGHTS pipeline; 2 max scraper workers on raspibig
- **Venv:** `/opt/ACTIVE/INFRA/venv/` — shared across most scripts

## Reuse Checklist

Before writing new code, check INFRA/SKILLS first — 803 scripts means it probably exists:
1. `grep -rl "keyword" /opt/ACTIVE/INFRA/SKILLS/` to find relevant script
2. Check SKILLS/CLAUDE.md categories
3. Import directly: `sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')`

## Mapping to Other Tentacles

| raspi code | Owner tentacle |
|---|---|
| FLIGHTS agents | ai-agents |
| EMAIL/CAMPAIGNS | campaigns |
| SCRAPERS/, EURES | scrapers |
| PostgreSQL, enrichment | data-db |
| Node-RED, systemd, INFRA | infra |
| `*_bot/`, applicant-dashboard | crm |
| PRODUSMONTAN, AGENTS/TERENURI | business-ops |
| event_publisher | campaigns |
