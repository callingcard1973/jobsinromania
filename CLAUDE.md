# CLAUDE.md

## What This Is

`D:\MEMORY` — operational hub for InterJob European Recruitment Network. 28 websites, email campaigns, scrapers, CV processing, multilingual content.

## Infrastructure

- **Windows laptop**: Python 3.12, `D:\MEMORY` in PATH, LM Studio at localhost:1234
- **raspibig** (tudor@192.168.100.21, SSH key auth): scrapers, enrichment, campaigns, Node-RED
- **A2 Hosting** (nl1-cl8-ats1.a2hosting.com, SSH 7822, cPanel user `loaiidil`): production web host

## Domains (28)

**Job (15):** careworkers.eu, factoryjobs.eu, buildjobs.eu, electricjobs.eu, farmworkers.eu, horecaworkers.eu, meatworkers.eu, mechanicjobs.eu, warehouseworkers.eu, aluminumrecyclehub.com, expatsinromania.org, interjob.ro, mivromania.info, mivromania.online, nepalezi.com
**Static (5):** internaltransfers.eu, horecaworkers2026.com, horecaworkers2026.eu, horecaworkers2026.online, weddnesday.org
**WordPress (8):** cumparlegume.com, seicarescu.com, agroevolution.com, ajwang.org, baneasa39.com, cifn.info, haritina.com, mivromania.com

## Directory Index

| Directory | What |
|-----------|------|
| `A2_SITE_DEPLOYER/` | Deploy sites to cPanel + SEO |
| `ARTICLES/` | LLM articles → 11 languages → deploy |
| `AUTOREPLY/` | Sort 30 email accounts + autoresponders |
| `CONSTRUCTION PROJECTS/` | TED contractors + agency registries |
| `CV/` | CV scanner, web UI, file watcher |
| `DELIVERY/` | ANOFM employer extraction → enrichment → Brevo |
| `FACTORYJOBS/` | Deep-enriched employer database (3,751 companies) |
| `FACTORYJOBS_PDF/` | Recruitment PDFs (6 campaigns × 38 languages) |
| `PLASARE 400 MUNCITORI/` | 400-worker placement: Bulgaria, Norway, EURES |
| `SITE_PAGES/` | Local mirror of all site HTML |
| `llm_tasks/` | LLM task framework: spam, bounces, articles |
| `MR ANUP/SLOVENIA/` | Slovenia: 63K AJPES companies, EURES contacts |
| `OPT/` | Partial copy of raspibig /opt/ (scrapers, creds) |
| `LLM DOWNLOAD/` | PicoClaw, model benchmarking, OPENDATA |

## Conventions

- SSH: always `192.168.100.21`, not hostname (Tailscale routing issue)
- SCP to Windows: forward slashes `"D:/MEMORY/path/"`
- SSH from Windows: single quotes around command
- Scrapers: max 2 concurrent on raspibig. Playwright locally.
- A2 docroot: `~/domainname/` (NOT `~/public_html/`)
- RTL languages (ar, ur, ps): `dir="rtl"` in HTML
- All apply links → `https://interjob.ro/apply.html`
- Email: nl1-cl8-ats1.a2hosting.com — IMAP 993, SMTP 465/587. Passwords in `OPT/opt/EMAIL/.env`

## Sensitive Files
`raspi.json`, `OPT/opt/EMAIL/.env`, `A2_SITE_DEPLOYER/env/*.env` — do not share. OpenCage key in `OPENCAGE_API_KEY` env var.

---

## LOW TOKEN USAGE STRATEGY

**5,869 Python files in CODE/** � NEVER read full codebase. Use:

### 1. Run Locally, NOT in LLM
- DB enrichment: run `step*.py` scripts directly via `bash`
- Campaign: run `campaign_manager.py` directly
- Scrapers: run on raspibig, not here
- LLM is for DECISIONS only, not execution

### 2. Use Subagents (parallel)
| Agent | Use For |
|-------|---------|
| `pg-enricher` | Pipeline steps, row counts, schema |
| `brevo-sender` | Campaign status, quota, bounce |
| `cpanel-deployer` | A2 deploys |
| `madr-scraper` | MADR county scrape |

### 3. Use Skills On-Demand
`skill{name}` when task matches: code-reviewer, fastapi-endpoint, frontend-design, python-pro

### 4. Grep/Glob First
- Find: `grep{pattern}` NOT read all files
- Locate: `glob{pattern}` for filenames

### 5. MCP for DB
Configured in `.mcp.json` � use for queries, not `psql.exe` manually

### 6. Minimal Context
- Pass subagent: task scope + ONE relevant CLAUDE.md section only
- Resume projects: load `PROJECT.md` + `STATE.md` only
- No full context dumps