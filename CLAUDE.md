# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

Each has its own CLAUDE.md with commands, architecture, and data details.

| Directory | What |
|-----------|------|
| `A2_SITE_DEPLOYER/` | Deploy sites to cPanel + SEO |
| `ARTICLES/` | LLM articles → 11 languages → deploy |
| `AUTOREPLY/` | Sort 30 email accounts + autoresponders |
| `CONSTRUCTION PROJECTS/` | TED contractors + agency registries (400 workers project) |
| `CV/` | CV scanner, web UI, file watcher |
| `DELIVERY/` | ANOFM employer extraction → enrichment → Brevo campaigns |
| `FACTORYJOBS/` | Deep-enriched employer database (3,751 companies) |
| `FACTORYJOBS_PDF/` | Recruitment PDFs (6 campaigns × 38 languages) |
| `PLASARE 400 MUNCITORI/` | Master 400-worker placement: Bulgaria, Norway, agencies, EURES |
| `SITE_PAGES/` | Local mirror of all site HTML |
| `llm_tasks/` | LLM task framework: spam, bounces, articles, monitoring |
| `MR ANUP/SLOVENIA/` | Slovenia market entry: 63K AJPES companies, EURES contacts, 50-col unified schema |
| `OPT/` | Partial copy of raspibig /opt/ (scrapers, credentials) |
| `LLM DOWNLOAD/` | PicoClaw expansion (20 task types), model benchmarking, OPENDATA products |

## Email (all 28 domains)

Server: nl1-cl8-ats1.a2hosting.com — IMAP 993, SMTP 465/587. Username = full email. Every domain has office@, dmarc@, unsubscribe@.
Passwords in `OPT/opt/EMAIL/.env` and `A2_SITE_DEPLOYER/env/*.env`.

## Conventions

- SSH: always use `192.168.100.21`, not hostname `raspibig` (Tailscale routing issue)
- SCP to Windows: forward slashes `"D:/MEMORY/path/"`
- SSH from Windows: single quotes around command (prevent `$variable` expansion)
- Scrapers: max 2 concurrent on raspibig. Run Playwright locally.
- A2 docroot: `~/domainname/` (NOT `~/public_html/`)
- RTL languages (ar, ur, ps): `dir="rtl"` in HTML
- All apply links → `https://interjob.ro/apply.html`

## API Keys & Credentials

**OpenCage Geocoding:** `geocoding_skill.py` at `d:\MEMORY\geocoding_skill.py` (laptop), `/opt/SKILLS/geocoding_skill.py` (raspibig). Key in `OPENCAGE_API_KEY` env var. See skill file for usage.

## Sensitive Files

`raspi.json`, `OPT/opt/EMAIL/.env`, `A2_SITE_DEPLOYER/env/*.env` — do not share.
