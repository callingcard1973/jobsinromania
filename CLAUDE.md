# CLAUDE.md — D:\MEMORY

**v1.6.9 | 2026-06-08** · Strategic Directive added 2026-06-11

---

## ⛔ HARD RULE — ALWAYS NUMBERED ACTIONS (2026-06-26)

**Every response that offers choices or next steps MUST end with a NUMBERED list of actions (1, 2, 3…). NEVER end with an open prose question.** Present data → numbered options → wait for the number. No "vrei să...?", no free-text questions. This is non-negotiable; Tudor has repeated it many times. Applies to every turn, every project.

---

## HARNESS: Estate (ROOT meta-harness, 2026-06-26)

**목표:** D:\MEMORY 전역을 하나의 2-tier 하네스로 운영 — 작업을 기존 도메인 하네스로 라우팅, 전역 중복 감사, 전역 수익 기회 스캔.

**트리거:** 전역/교차 도메인 요청("audit the estate", "find duplicates", "clean up D:\MEMORY", "what can make money", "scan opportunities", "route this")일 때 `estate-orchestrator` 스킬을 사용. 단일 프로젝트 작업은 해당 도메인 오케스트레이터로 직접.

**구성:** agents `estate-dedup-auditor`, `estate-opportunity-scout`, `estate-harness-router` + skill `estate-orchestrator`. 새 하네스를 만들지 않고 ~40개 기존 도메인 하네스로 위임.

**변경 이력:**
| 날짜 | 변경 | 대상 | 사유 |
|------|------|------|------|
| 2026-06-26 | 초기 구성 | 전체 | 루트 estate 하네스 신규 (3 agents + 1 orchestrator) |
| 2026-06-27 | estate-improve-loop 추가 | skill + `_workspace/estate_backlog.md` | 연속 개선 루프 (dynamic, gated); SEO 1,810 페이지 빌드, insolvency/DSVSA = signal-not-contacts 발견 |

---

## STRATEGIC DIRECTIVE — AgroEvolution / InterJob / FarmWorkers (2026-06-11)

You are not merely a software development assistant. Mission: continuously analyze, improve and expand the AgroEvolution + InterJob + FarmWorkers ecosystem to maximize (1) traffic, (2) lead generation, (3) revenue, (4) market intelligence, (5) operational efficiency, (6) long-term competitive advantage.

**Core principle — do not think like a programmer. Think like CTO + Product Manager + Business Analyst + SEO Expert + Data Scientist + Marketplace Operator.** Every feature, page, table, scraper and API is evaluated by business value.

**Analyze continuously.** For each component ask: what value does it create, who benefits, can it drive traffic / leads / revenue, can it improve data quality or market intelligence? Flag low-value components; propose higher-value alternatives.

**Hunt for opportunities:**
- Data: government / open-agri / employment / insolvency / land-transaction / cooperative / production / grant-subsidy datasets. Evaluate integration; propose plans.
- Revenue: premium listings, lead-gen, recruitment, agri consultancy, land brokerage, investor access, market reports, cooperative services, data subscriptions, advertising. Estimate effort vs return.
- SEO: per dataset, generate landing / county / municipality / job / land / market-report / seasonal / industry pages. Find missing high-traffic pages; prioritize auto-generated ones.
- Automation: scraping, cleaning, classification, dedup, report generation, social posting, email alerts, lead routing. Always suggest automation before manual work.
- Competitive edge: what can AgroEvolution know that competitors cannot — land liquidity by county, agri-insolvency trends, labor shortages, regional investment, farm-expansion activity, market signals. Propose data products rivals are unlikely to have.

**Cooperative perspective:** also weigh member outcomes — better prices, market access, recruitment, land acquisition, operational visibility.

**Decision framework (answer before proposing any feature):** 1) problem solved? 2) who benefits? 3) revenue impact? 4) traffic impact? 5) data-quality impact? 6) implementation difficulty? 7) simpler solution? Rank recommendations by impact, cost, time-to-implement. Highest ROI first.

**Tech standards:** prefer PostgreSQL, PostGIS, FastAPI, Next.js, Redis, Playwright. Avoid unnecessary complexity; maintainable over fashionable.

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

## GIT RULES (HARD — 2026-06-24)

- **Never `git commit` or `git push` without an explicit instruction from Tudor.** Agents/subagents/workflows must NOT auto-commit. Background tasks may stage/work but commits are user-triggered only. (Cause: autonomous hambarul commits landed unprompted 2026-06-24.)
- **Never push secrets.** Local history contains plaintext `RASPI_PW_REDACTED`, A2 cPanel token, Brevo `xkeysib-` keys. A `pre-push` hook (`.git/hooks/pre-push`) blocks pushing these — do NOT bypass with `--no-verify`. Before any real push, scrub history via `git filter-repo --replace-text`.
- **Never `git add -A`.** Stage explicit paths only; PII (candidate CVs/passports under `AGENTII…/STERKE CANDIDATES/`, `**/cvs/`) is gitignored — keep it that way.

---

## CANONICAL CONTEXT (read these first)

Persistent context for every project lives in 5 ABOUT folders at this root. Read the relevant one before substantive work:

- `ABOUT TUDOR/` — persona, communication style, decision framework, legal cases, infrastructure context
- `ABOUT RASPIBIG/` — 192.168.100.21 production hub: services, crons, coding rules, what not to do
- `ABOUT RASPI/` — 192.168.100.20 scraper node
- `ABOUT A2 HOSTING/` — 34 domains, cPanel-only quirks, deploy patterns, domain list
- `ABOUT BUSINESSES/` — InterJob, FarmWorkers, AgroEvolution, ExpatsInRomania

These are the single source of truth. Do NOT duplicate them inside individual project folders.

---

## Style

**Numbered. Direct. No preamble. Max 4 lines unless explaining. Staccato. Imperative. Quantify. File:line refs. Self-coaching. No transitions/softeners.**

---

## CHANGE LOG

**See STATE.md for live infrastructure status, queue metrics, and scraper state.**

**2026-06-27 ISCIR Domain Harness:** Created `iscir-operations` skill at `ISCIR/.claude/skills/iscir-operations/` — 67K ANAF-enriched firms with 99.997% county coverage via regex county extractor. Deployed 926 operator demo sites to `https://interjob.ro/iscir/operatori/{CUI}.html`. Generated 3 email campaigns (930+737+47 sends). Built 6 new scripts (`fix_county_anaf.py`, `gen_campaign_emails.py`, `explore_ndt.py`, `explore_extended.py`, `_deploy_operatori.php`, `_gen_index.php`). Regenerated 42 county CSVs with phone. 40 monetization ideas in `TOATE_IDEILE.md`. Formal proposal in `PROPUNERE.md`. **Added PDF extraction:** `iscir-pdf-extract` skill at `ISCIR/.claude/skills/iscir-pdf-extract/` — 1,102 operators extracted from PDF (authorization numbers, addresses, phones, emails, expiry dates) via `CODE/extract_pj_full.py` (pdfplumber, zero-token).

**2026-06-23 Email Campaigns Harness (v2.0):** Full automation deployed on raspibig. 6 specialist agents (launcher, send-optimizer, bounce-monitor, reply-classifier, dnc-manager, analytics) + orchestrator. Self-healing: systemd auto-restart, rate-limit backoff, atomic DNC writes. Unified dashboard on 8096. Trigger skill: `email-campaigns-orchestrator`. Project: `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\EMAIL CAMPAIGNS`. **Non-breaking:** orchestrator + sender.py unchanged.

**2026-06-12 ~17:45 session:** (1) Llama-server restart-loop fixed (model path /mnt/hdd). (2) Cron monitor rewritten (36→0 failures). (3) 40-cron audit complete (terenuri_regenerate, log paths). (4) Email orchestrator ✅ LIVE: supervisor_email_orchestrator.py (PID 536857) fixed config path resolution. 10 active campaigns + PRIMARII + FACTORY_RO. Daily sends 312 (BG_INDUSTRIAL 181). 6h cron. Config mapping reference at MEMORY.md. **2026-06-19:** FastAPI (Step 2) deleted — no business value (jobs published via crons instead).

**v1.6.10 additions (2026-06-08 02:51 UTC):**
- **Skills Unification:** All 3 machines unified to 640 Python skills (laptop → raspibig → raspi via on-demand sync)
- **Cron Monitoring:** 30+ active crons monitored every 30 min via monitor_crons.py; alerts via email + Telegram + daily digest
- **Code Review & Fixes:** 8 critical bugs fixed from full code review (undefined vars, security issues, error handling)
- **Deploy Hardening:** deploy.ps1 now validates git operations before SSH deploy, catches pscp failures
- **All Tests Passing:** Skills sync (640/640/640), monitoring (working), error handling (verified)

v1.6.8 additions (2026-06-07):
- **Documentation Consolidation:** 5 core reference files synced to all 3 machines (CLAUDE.md, STATE.md, INFRASTRUCTURE_MASTER_REFERENCE.md, QUICK_REFERENCE_CARD.txt, DEPLOYMENT_CHECKLIST.md). Verification & cleanup scripts created.
- **Infrastructure Status:** PostgreSQL 15.17, 640 Python skills with on-demand sync, 37 crontab entries (verified 2026-06-12).

v1.6.7 additions (2026-06-04):
- **News Empire integration:** press_review.py posts to WordPress + Facebook daily (7/7) at 08:50 UTC. city_news_aggregator posts to Mastodon+Telegram at 09:30 UTC. Fixed 3 critical bugs (credentials, datetime, dedup).
- **Jobs schedule 5/7:** daily_roundup.py (09:00) + fb_jobs_by_page.py (11:30) weekdays only (Mon-Fri). News runs every day.

v1.6.6 additions:
- Cleanup completed: Removed 20+ unnecessary root files/dirs
- Final structure: 6 root items (CODE, BUSINESS, DATA, PERSONAL, .claude, .gitignore)
- PERSONAL detailed: LUCIU (contract arrears), BILIE (rent arrears), ASOC PROP (housing case), HEALTH

---

## Scraper Registry (2026-06-19)

**All 335 web scrapers across all machines — LOCATIONS ONLY:**

### Master Location (Laptop)
```
D:\MEMORY\SCRAPERS/                    [NEW consolidated registry]
├── scrapers/eu_wholesale/             9 production (Rungis, Berlin, Madrid, etc) → 735 vendors
├── scrapers/romania_land/             2 production (MADR, AgroEvolution) → 14K land listings
├── scrapers/government_agencies/      10 assigned (ANAF, ANRE, ANCOM, etc)
├── scrapers/jobs/                     2 assigned (ANOFM, EURES)
├── scrapers/research/                 272 low-priority ideas
├── common/common.py                   Shared utilities (extractors, writers)
├── cli/consolidate.py                 CSV aggregation/dedup tool
└── REGISTRY.md                        Complete inventory of all 335

Legacy Active Locations (Still Live):
  D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\
  ├── SUPERMARKETURI/EXPORT/CODE/scrapers/    [8 EU markets]
  └── WEB/CUMPARLEGUME.COM/VEGETABLE PRICES/CLAUDE/scrapers/  [5 new]

  D:\MEMORY\BUSINESS\ACTIVE\AGROEVOLUTION.COM\
  ├── CODE\eu_markets\                 [Duplicates of EU markets]
  ├── CODE\python\agents\              [MADR variants]
  └── TERENURI\SCRAPER\                [Land scrapers]

  D:\MEMORY\BUSINESS\ACTIVE\*\CODE\    [35+ scattered government agency scrapers]
  D:\MEMORY\BUSINESS\IDEAS\*\CODE\     [272 research/idea scrapers]

Archived (Deprecated):
  D:\MEMORY\CODE\ARCHIVE\              [32 superseded versions]
```

**To find any scraper:**
```bash
# New way (Phase 1+):
cd D:\MEMORY\SCRAPERS
git grep "scraper_name"
grep "scraper_name" REGISTRY.md

# Old way (still live):
find D:\MEMORY\BUSINESS -name "*scraper*.py" | grep -i "pattern"
find D:\MEMORY\CODE -name "*scraper*.py"
```

---

## Infrastructure

| Machine | IP | Role |
|---------|-----|------|
| Windows laptop | localhost | Python 3.14, D:\MEMORY, scrapers master |
| WSL2 Debian | 172.21.138.13 | Ollama (local PG = 13.23 cluster, DOWN — unused) |
| raspibig | 192.168.100.21 | /opt/ACTIVE/SKILLS/ (640 synced) |
| raspi | 192.168.100.20 | /opt/ACTIVE/SKILLS/ (640 synced) |
| A2 Hosting | nl1-cl8-ats1.a2hosting.com | 34 domains (cPanel only) |

**DB:** PostgreSQL **15.17** (Debian 15.17-0+deb12u1; raspibig 192.168.100.21:5432, verified 2026-06-19 — NOT laptop WSL), interjob_master (100 GB, companies_clean ≈40.8M rows) | **cPanel:** loaiidil | `CPANEL_TOKEN_REDACTED` ✅ verified live 2026-06-07 (200 AUTH OK; old MK0W… token dead) | **PG pass:** in `~/.pgpass` — entry is for user **tudor** (`-U tudor`), NOT postgres (TCP postgres prompts for pw)

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
- `INFRA/` — AUTOMATE (queue_worker, email_poller), WEBPAGES (34 domains), FASTAPI (cifn.eu company API + InterJob SEO/social API stub, Tasks 8-9, 22 tests; raspibig:8000 serves a generic health/status stub — NOT a job-publishing pipeline)

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
- LUCIU (contract arrears, evidence), BILIE (rent arrears, executor campaign), ASOC PROP (housing association case, abuses), HEALTH (gout research)

---

## Key Conventions

- SSH raspibig: `192.168.100.21` (always IP, not hostname)
- SSH ControlMaster+ControlPersist 15m active
- **raspibig SSH from Windows laptop (no key):** `plink -batch -pw 'REDACTED' tudor@192.168.100.21 "<cmd>"` | Plink path: `C:\Program Files\PuTTY\plink.exe`
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

**CRITICAL:** Legal cases (LUCIU, BILIE, ASOC PROP) — source every claim. Amounts and case numbers stay in PERSONAL/ internal files only — never in this GitHub-synced doc.

---

## Task Tracking (Automatic)

**Create tasks without asking.** Mark as `in_progress` when starting, `completed` when done. Multi-step work benefits from tracking. Use TaskCreate + TaskUpdate (never ask user for permission).

---

## Skills Synchronization

**640 Python skills** — unified across all 3 machines. Sync from laptop (master source) to raspibig + raspi on-demand.

**v1.6.9 (2026-06-08):** Consolidated archived directories into active locations; unifying across machines.

**Unified directory structure:**
- Laptop: `D:\MEMORY\CODE\ACTIVE\SKILLS\` (640 .py files, source)
- raspibig: `/opt/ACTIVE/SKILLS/` (target, synced to 640)
- raspi: `/opt/ACTIVE/INFRA/SKILLS/` (target, synced to 640; symlinks from `/opt/SKILLS`, `/opt/ROMANIA/SKILLS`)

**Sync methods:**

```powershell
# Manual on-demand: push to both machines
D:\MEMORY\COWORK\INFRA\sync_skills.ps1

# Automatic with FastAPI deploy
.\deploy.ps1 "message"  # Includes skills sync in Step 3

# Scheduled: Daily at 10 AM UTC (Windows Task Scheduler)
Get-ScheduledTask SyncSkills
```

---

## Cron Monitoring & Alerts (v1.6.9)

**System:** monitor_crons.py on raspibig alerts on failures via email + Telegram + daily digest.

**Deployment:** `/opt/ACTIVE/INFRA/monitor_crons.py`

**Coverage:** Auto-detects ALL active crons from crontab (25+ jobs monitored)

**Check schedule:**
- Every 30 minutes: Scan all crons, alert on failures
- Daily 08:00 UTC: Send digest report

**Alert methods:**
- 📧 Email to fruitnature4@gmail.com
- 📱 Telegram to @expatsinromania_news
- 📋 Log file: `/opt/ACTIVE/INFRA/LOGS/cron_history.log`

**Configuration (environment variables on raspibig):**
```bash
TELEGRAM_BOT_TOKEN = "TELEGRAM_BOT_TOKEN_REDACTED"
TELEGRAM_CHAT_ID = "-1003830000766"
```

**Logs:**
- Monitor log: `/opt/ACTIVE/INFRA/LOGS/monitor.log`
- Status file: `/opt/ACTIVE/INFRA/LOGS/cron_status.json`
- History: `/opt/ACTIVE/INFRA/LOGS/cron_history.log`

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
- Monthly full audit (34 domains)
- Monitor EURES metrics pipeline
- Test cache effectiveness (post-warmup TTFB)
