# CLAUDE.md — D:\MEMORY

**v1.6.9 | 2026-06-08**

---

## OPERATIONAL MODE (v1.6.9 Update)

**Claude execution authorization (2026-06-08):**
- ✅ SSH to raspibig (192.168.100.21) automatically for all infrastructure tasks
- ✅ Execute PowerShell scripts via computer-use from laptop without asking
- ✅ Maintain persistent SSH sessions (ControlMaster pooling, 15-min persistence)
- ✅ Offer numbered responses with actionable options
- ✅ Propose solutions, ask for selection, execute automatically
- ✅ Report results without preamble

**Response format:** Numbered list (1, 2, 3...) with brief explanations. No "Would you like..." — present as numbered options, wait for selection.

---

## CANONICAL CONTEXT (read these first)

Persistent context for every project lives in 5 ABOUT folders at this root. Read the relevant one before substantive work:

- `ABOUT TUDOR/` — persona, communication style, decision framework, legal cases, infrastructure context
- `ABOUT RASPIBIG/` — 192.168.100.21 production hub: services, crons, coding rules, what not to do
- `ABOUT RASPI/` — 192.168.100.20 scraper node
- `ABOUT A2 HOSTING/` — 30 domains, cPanel-only quirks, deploy patterns, domain list
- `ABOUT BUSINESSES/` — InterJob, FarmWorkers, AgroEvolution, ExpatsInRomania

These are the single source of truth. Do NOT duplicate them inside individual project folders.

---

## Style

**Numbered. Direct. No preamble. Max 4 lines unless explaining. Staccato. Imperative. Quantify. File:line refs. Self-coaching. No transitions/softeners.**

---

## CHANGE LOG

**See STATE.md for live infrastructure status, queue metrics, and scraper state.**

v1.6.8 additions (2026-06-07):
- **FastAPI Job Publishing Pipeline:** Complete 6-step deployment (SEO → Deploy → WordPress → Social → Meta Graph) with 2,800+ lines, 91% coverage, 78/78 tests passing. 6 reusable skills created. All 4 database tables + migrations deployed.
- **Documentation Consolidation:** 5 core reference files synced to all 3 machines (CLAUDE.md, STATE.md, INFRASTRUCTURE_MASTER_REFERENCE.md, QUICK_REFERENCE_CARD.txt, DEPLOYMENT_CHECKLIST.md). Verification & cleanup scripts created.
- **Infrastructure Status:** FastAPI on raspibig:8000, reverse proxy via Caddy (api.interjob.ro), PostgreSQL 15.15, 640 Python skills with on-demand sync, 25+ crons active.

v1.6.7 additions (2026-06-04):
- **News Empire integration:** press_review.py posts to WordPress + Facebook daily (7/7) at 08:50 UTC. city_news_aggregator posts to Mastodon+Telegram at 09:30 UTC. Fixed 3 critical bugs (credentials, datetime, dedup).
- **Jobs schedule 5/7:** daily_roundup.py (09:00) + fb_jobs_by_page.py (11:30) weekdays only (Mon-Fri). News runs every day.

v1.6.6 additions:
- Cleanup completed: Removed 20+ unnecessary root files/dirs
- Final structure: 6 root items (CODE, BUSINESS, DATA, PERSONAL, .claude, .gitignore)
- PERSONAL detailed: LUCIU (10.322 RON), BILIE (3.250 EUR), ASOC PROP (9510), HEALTH

---

## Infrastructure

| Machine | IP | Role |
|---------|-----|------|
| Windows laptop | localhost | Python 3.14, D:\MEMORY |
| WSL2 Debian | 172.21.138.13 | PostgreSQL 15.15, Ollama |
| raspibig | 192.168.100.21 | FastAPI:8000, N8N, campaigns, email |
| raspi | 192.168.100.20 | Scrapers, ProtonVPN |
| A2 Hosting | nl1-cl8-ats1.a2hosting.com | 30 domains (cPanel only) |

**DB:** PostgreSQL **15.15** (Debian; verified 2026-06-07 — NOT 17/18), interjob_master | **cPanel:** loaiidil | `K9ATCMHPKVSKUV2M97447JLY45EH29KQ` ✅ verified live 2026-06-07 (200 AUTH OK; old MK0W… token dead) | **PG pass:** in `~/.pgpass` (chmod 600 — psql wasn't auto-reading it)

---

## Directories (Active)

**ROOT (High-frequency):**
- `STATE.md` — Live infrastructure status, queue metrics, scraper state
- `CLAUDE.md` — This file, style guide, coding standards
- `AGENTS.md` — Skills inventory reference

**CODE/ACTIVE/ (High-frequency):**
- `SKILLS/` — 640 Python skills (agents, scrapers, infrastructure); sync via `sync_skills.ps1` on-demand
- `CAMPAIGNS/` — Brevo email (1,560→2,560/day)
- `WEB/` — Dashboard, feeds, employer pages
- `INFRA/` — AUTOMATE (queue_worker, email_poller), WEBPAGES (30 domains), FASTAPI (Job Publishing Pipeline: SEO→Deploy→WP→Social→Meta)

**BUSINESS/ACTIVE/ (High-frequency):**
- `AGROEVOLUTION.COM/` — 9,658 land listings
- `PARTNERS/` — JIM TURNBULL, BOGDAN GAVRA, VIRGIL BUDASCA, EEATINGH, ANCA POPIAN, PAUL IUREA, MISHA KAZA, GHEORGHE VLAD, FUQIANG SONG, FLORIN ROATA CASCADOR, CRISTINEL DEACONESCU
- `TUDOR/` — Tudor's projects (AGROEVOLUTION, CUMPARLEGUME, AJWANG, NURTEKS, COOP, TERENURI)
- `COOP/` — CAP GOSPODARII DE ALTADATA, DELECROIX
- `AJWANG.ORG/` — Africa data, treaties

**BUSINESS/IDEAS/ (Medium-frequency):**
- 135 strategic opportunities, research projects

**DATA/ACTIVE/ (High/Medium-frequency):**
- `OPENDATA/` — EU data downloader (continuous)
- `OPENTENDER/` — Tender scraper + parquet processing
- `DB/` — SQL imports, views, enrichment scripts
- `EBRD/` — Procurement monitors
- `ONAC_RU/` — Russian market data

**ARCHIVE/ (Low/never used):**
- `CODE/ARCHIVE/DEPRECATED/` — Old infrastructure, experiments
- `CODE/ARCHIVE/RESEARCH/` — IDEAS TO IMPROVE CODE
- `DATA/ARCHIVE/EXPORTS/` — MASTER_PROFESSIONALS, ROMANIA exports
- `DATA/ARCHIVE/OLD/` — HAMBARUL ROMANESC, restaurant data, old projects

**PERSONAL:**
- LUCIU (contract arrears 10.322 RON, evidence), BILIE (rent arrears 3.250 EUR, executor campaign), ASOC PROP (housing association case 9510, Dorombach abuses), HEALTH (gout research)

---

## Key Conventions

- SSH raspibig: `192.168.100.21` (always IP, not hostname)
- SSH ControlMaster+ControlPersist 15m active
- **raspibig SSH from Windows laptop (no key):** `plink -batch -pw 'bucare' tudor@192.168.100.21 "<cmd>"` | Plink path: `C:\Program Files\PuTTY\plink.exe`
- A2 docroot: `~/domainname/` (not ~/public_html/)
- Email: manpower.dristor@gmail.com
- Apply link: https://interjob.ro/apply.html

---

## Execution Tools (New in v1.6.9)

**PowerShell Scripts (D:\MEMORY\COWORK):**
- `EXECUTE_FASTAPI_FIX.ps1` — Fix FastAPI systemd service via SSH
- `SETUP_PERSISTENT_SSH.ps1` — Configure SSH ControlMaster for persistent pooling

**Batch Scripts (D:\MEMORY):**
- `FIND_AND_FIX_FASTAPI.bat` — Alternative to PowerShell, uses plink directly
- `VERIFY_EVERYTHING_NOW.bat` — 10-point system health check

**SSH Execution Model:**
```
Claude desktop tool → PowerShell window → plink SSH → raspibig:22
Result: Automatic execution without user interaction, persistent connection reuse
```

**Response Pattern:**
```
# Present as numbered options (not "Would you like")
1. Fix FastAPI service (5 min)
2. Setup persistent SSH (1 min) 
3. Both in sequence
4. Skip for now
```

---

## Coding Standards

- **250-line max** per file
- **Python**: `#!/usr/bin/env python3`, one-liner docstring, `main()`, `if __name__`
- **Data safety**: Archive before delete. SELECT count → INSERT archive → DELETE
- **Async I/O**: aiohttp/asyncio for email/API/file ops
- **Local LLM**: Ollama on raspibig:1234. Claude API only for strategic/user-facing
- **Comments**: WHY only, no WHAT
- **Error handling**: Only at system boundaries

---

## Epistemic Standards

1. Flag uncertainty: "I'm not certain, but..." 
2. Cite numbers or mark "unknown"
3. Never invent sources (URLs, studies, quotes)
4. Note knowledge cutoff (Feb 2025)
5. Don't attribute quotes without certainty

**CRITICAL:** Legal cases (LUCIU 10.322 RON, BILIE 3.250 EUR, ASOC PROP 9510) — source every claim.

---

## Task Tracking (Automatic)

**Create tasks without asking.** Mark as `in_progress` when starting, `completed` when done. Multi-step work benefits from tracking. Use TaskCreate + TaskUpdate (never ask user for permission).

---

## Skills Synchronization

**640 Python skills** on laptop (`D:\MEMORY\CODE\ACTIVE\SKILLS\`). Sync to raspibig on-demand via PowerShell script.

**v1.6.9 (2026-06-08):** Implemented on-demand sync system (replaces non-functional `weekly_skills_sync.py`).

```powershell
# From laptop — push all skills to raspibig
D:\MEMORY\COWORK\INFRA\sync_skills.ps1

# Or integrate into deployment (add to deploy.ps1 after FastAPI deployment)
& D:\MEMORY\COWORK\INFRA\sync_skills.ps1
```

**Optional scheduled sync:** Windows Task Scheduler Sunday 4 AM (if laptop is on)
```powershell
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-File D:\MEMORY\COWORK\INFRA\sync_skills.ps1"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 4AM
Register-ScheduledTask -TaskName "SyncSkills" -Action $action -Trigger $trigger
```

**Paths:**
- Laptop source: `D:\MEMORY\CODE\ACTIVE\SKILLS\` (640 .py files)
- raspibig target: `/opt/ACTIVE/SKILLS/` (synced on-demand)

---

## Low Token Strategy

1. Run locally (DB, campaigns, scrapers = scripts, not LLM)
2. Use subagents: pg-enricher (DB), brevo-sender (campaigns), cpanel-deployer (A2), madr-scraper (land)
3. Grep/Glob first — never read full codebase
4. MCP for DB — configured in `.mcp.json`
5. Minimal context — load PROJECT.md + STATE.md only

---

## Next Maintenance (2026-06-28)

- Weekly SSL check (nepalezi.com auto-renewal)
- Monthly full audit (30 domains)
- Monitor EURES metrics pipeline
- Test cache effectiveness (post-warmup TTFB)
