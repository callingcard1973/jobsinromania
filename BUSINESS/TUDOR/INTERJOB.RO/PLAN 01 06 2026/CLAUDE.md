# INTERJOB.RO — Index

**v2.2 | 2026-06-23** — Master Harness deployed

## 🎯 Harness: INTERJOB.RO Master Operations

**Goal:** Fully automated marketplace operation — data pipeline → email campaigns → monitoring → reporting.

**Trigger:** Use `interjob-master-orchestrator` skill for operational workflow tasks. Coordinates:
- 11 email campaigns (440/day capacity)
- Job catalog generation (9 domains, PDF+HTML)
- Daily data pipeline (ANOFM, EURES, MADR lands, enrichment)
- Infrastructure health monitoring (raspibig, PostgreSQL, crons)
- Daily + weekly reporting (dashboard + email)

**Team:** 9 registered agents (6 reused email + 3 new) + 4 daily-roundup skills
- Reused agents: campaign-launcher, send-optimizer, bounce-monitor, reply-classifier, dnc-manager, analytics
- New agents: pipeline-orchestrator, infrastructure-health, report-generator
- Daily-roundup skills (not agents): data-validator, content-creator, publisher, monitor

**Daily cycle:**
| Time (UTC) | Component | Agent | Status |
|----------|-----------|-------|--------|
| 00:30 | Data Pipeline | pipeline-orchestrator | → catalog PDF/HTML + pipeline_state.json |
| 06:00 | Campaign Launch + Daily Report | campaign-launcher + report-generator | → sends + digest email |
| 09:00 | Daily Roundup | daily-roundup harness | → social posts |
| 30 min loop | Monitor + Optimize | infrastructure-health + send-optimizer + bounce-monitor + reply-classifier | → alerts + recommendations |
| Monday 07:00 | Weekly Report | report-generator + analytics | → PDF report + stakeholder email |

**Change history:**
| Date | Change | Component | Reason |
|------|--------|-----------|--------|
| 2026-06-23 | Master harness deployed | .claude/agents/ + .claude/skills/ | Unified marketplace automation |
| 2026-06-23 | 3 new agents created | pipeline-orchestrator, infrastructure-health, report-generator | Data pipeline, infrastructure monitoring, reporting |
| 2026-06-26 | A2 Operations harness deployed | .claude/agents/ + .claude/skills/ | Cross-site publishing, WP config, disk cleanup automation |

---

## 🔧 Harness: A2 Hosting Operations

**Goal:** Manage 34 domains on the `loaiidil` A2 Hosting account — publish content, configure WordPress, free disk quota, run site audits.

**Trigger:** Use `a2-operations-orchestrator` skill for any A2 file operations, cross-site publishing, WP config changes, disk cleanup, or site audits. Direct questions about domains can be answered without the skill.

**Team:** 5 sub-agents: site-inspector, content-publisher, wp-mutator, space-reclaimer, verify-agent.
- Skills: `a2-content-publish`, `a2-wp-bootstrap`, `a2-disk-cleanup`, plus global `a2-cpanel` + `cross-site-publish`
- Orchestrator: `a2-operations-orchestrator` (hybrid pipeline: inspect → publish → WP → cleanup → verify)

**Current blocker:** `loaiidil` account at 100% disk quota — electricjobs.eu WP config blocked. `Fileman/delete_files` endpoint broken.

---

## 📥 Harness: WhatsApp CV Intake (inbound candidate funnel)

**Goal:** Capture CVs sent via WhatsApp Web → parse → dedup → land in `fw_candidates`, with health monitoring. The inbound counterpart to the outbound email campaigns.

**Trigger:** Use `whatsapp-cv-orchestrator` skill to process WhatsApp CVs, ingest/extract/match, or check intake health. Folder: `WHATSAPP/`.

**Team:** 4 agents (cv-ingestor → cv-extractor → candidate-matcher → whatsapp-monitor), agent-team pipeline, all opus. Gateway on raspi `192.168.100.20`.

**Change history:** 2026-06-26 — initial build (4 agents + 4 skills + orchestrator).

---

## 📣 Harness: Facebook Publishing (outbound job posts)

**Goal:** Auto-publish InterJob deficit/EURES job content to Tudor's Facebook pages/groups — sourced from `ij_jobs`, deduped, page-targeted, dry-run gated.

**Trigger:** Use `fb-publish-orchestrator` skill for any Facebook publishing in `PUBLISHING IN MY FB/` — "publish jobs to facebook", "post to my FB pages", "FB publish status", "dry-run the FB posts", "check FB token health". Default dry-run; live only on explicit instruction.

**Team:** 3 sub-agents (fb-content-curator → fb-publisher → fb-monitor), pipeline, all opus. Reuses `fb_jobs_by_page.py` + `FacebookNewsPublisher`; tokens from raspibig `fb_pages.json`.

**Change history:** 2026-06-26 — initial build (3 agents + 3 skills + orchestrator).

---

## 🌐 Harness extension: WEB A2 domain pages

**Added 2026-06-26:** two skills on the existing WEB harness (`web-orchestrator` agent + `web-publish`):
- `web-domain-pages` — config-driven bilingual sector/county SEO page generation for the 9–10 job domains (used by page-builder).
- `web-a2-audit` — read-only docroot + backdoor audit across 34 A2 domains (used by web-monitor).

---

## 🌾 Harness: MADR Land Offers (TERENURI — land brokerage + data product)

**Goal:** Scrape the MADR agricultural-land sale-offers feed (Legea 17/2014 extravilan), extract Anexa 1B fields (seller, email, phone, area, price, county) with a ZERO-TOKEN local OCR stack, load deduped `land_offers`. Feeds AgroEvolution inventory + land-liquidity-by-county data product + SEO county-land pages.

**Trigger:** Use `terenuri-orchestrator` skill to scrape MADR land offers, refresh terenuri, backfill the land archive, or get agricultural land for sale. Folder: `TERENURI/`. Runs on raspibig (.21).

**Team:** 3 agents (madr-offer-crawler → anexa-extractor → land-offer-loader), agent-team pipeline, all opus. Driver `scrape_madr_offers.py`. Zero-token extraction: pdftotext (digital ~30%) / tesseract ron+eng OCR (scanned ~70%) → regex / optional local Ollama; NEVER a paid API. County+locality free from URL; email+phone = lead-gold.

**Change history:** 2026-06-26 — initial build (3 agents + 3 skills + orchestrator + scraper).

---

## 🔗 Harness: Candidate↔Job Matcher (marketplace core)

**Goal:** Pair `fw_candidates` (inbound workers from WhatsApp/forms/CVs) to active `ij_jobs` by occupation+location, notify both sides, turn two data piles into actual leads. The link that makes InterJob a marketplace.

**Trigger:** Use `matcher-orchestrator` skill to run the matcher, match candidates to jobs, notify workers/employers, or check match yield. Folder: `MATCHER/`.

**Team:** 3 agents (match-finder → match-notifier → match-monitor), agent-team pipeline, all opus. Durable state in new `ij_matches` ledger (UNIQUE candidate+job). Occupation required, location soft (relocation normal); 7 deficit occupations weighted. Notify default dry-run, ASCII, DNC+dedup gated.

**Change history:** 2026-06-26 — initial build (3 agents + 3 skills + orchestrator).

---

## 🚨 Harness: Infra Alert Triage (raspibig/raspi Telegram alerts)

**Goal:** Turn a one-line health alert (cron monitor, OpenData watchdog, failed systemd units, table anomalies, swap pressure) into identified cause → evidence → numbered fix, with read-only diagnosis automatic and any state change gated.

**Trigger:** Use `infra-alert-triage` skill whenever an infra alert is pasted/mentioned — "OPENDATA Cleanup STALE", "failed units: cv-matcher.service", "log not updated in 6+ hours", "companies_old_pre_cleanup", swap-storm, "triage this alert", "what's failing on raspibig", "re-run the triage".

**Team:** `alert-triage` dispatcher (runbook matcher) + reuses `infrastructure-health` (.21) and `raspi-inspector` (.20). Runbook `references/runbook.md` maps known alerts→fixes. Hybrid: front-line read-only diagnosis direct; deep host checks delegated. Never drops/restarts/commits without a numbered approval.

**Change history:** 2026-06-27 — initial build (1 agent + orchestrator + runbook). Seeded with OPENDATA stale-cleanup + cv-matcher IMAP-auth runbook entries.

---

## 🗂️ Harness Backlog (2026-06-26 code audit) — ALL 6 BUILT

Audited all code: 32 `.claude` harnesses already deployed. The 6 gaps below were built 2026-06-26 (uncommitted).

1. ✅ **job-catalog** (`CATALOG JOBURI/`) — 3 agents (catalog-builder→deployer→monitor) + 2 skills + `job-catalog-orchestrator`. Builds reuse global `interjob-catalog`; deploy client variant to `domain.eu/catalog/`. Trigger: "build the job catalog".
2. ✅ **furnizori-scrapers** (`FURNIZORI/`) — 2 agents (supplier-scraper→consolidator) + `furnizori-orchestrator`. Lidl+Kaufland→deduped CUI-keyed master. Trigger: "scrape suppliers".
3. ✅ **ukraine-pipeline** (`UKRAINE/`) — 2 agents (doc-extractor→dedup-analyst) + `ukraine-pipeline-orchestrator`. Exporter PDFs→deduped intel CSV. Trigger: "run the Ukraine pipeline".
4. ✅ **CODE map** (`CODE/`) — 1 agent (code-navigator) + `code-map-orchestrator` + `CODE/CLAUDE.md`. Map+guardrail over 98 loose scripts; STALE-default. Trigger: "find/run a CODE script".
5. ✅ **email-hygiene** (`EMAIL CLASSIFIER/`) — 2 agents (inbox-purger, form-router) + `email-hygiene-orchestrator`. Wraps `cv_purge.py`+`form_router.py`. Trigger: "clean the inboxes" / "route form leads".
6. ✅ **eures-staleness-guard** skill (`EURES SCRAPER/`) — added to existing EURES harness; used by eures-health. Trigger: "is EURES fresh".

**Added 2026-06-26:** `dnc-mailbox-scan` skill + `dnc-scanner` agent — scan all 125+ A2 Hosting mailboxes for campaign opt-out/unsubscribe/stop replies, confirm via body text, generate DNC CSV. Trigger: "scan mailboxes for opt-outs" / "check for unsubscribes". Role: `dnc-scanner`. Location: `.claude/skills/dnc-mailbox-scan/`.

Empty/drift harnesses still to populate-or-delete: `OCTOGENT`, `RASPIBIG INSPECT/CRONTAB`, `WEB/CATALOG JOBURI`.

---

## 🏭 Harness: ISCIR Operations (regulatory compliance data domain)

**Goal:** Monetize 67K pressure-vessel owners, 1.2K RSVTI operators, 114K triangulated firm owners — via demo site upsell, email campaigns, data products.

**Trigger:** Use `iscir-operations` skill for any ISCIR work — "run ISCIR enrichment", "audit ISCIR data", "generate ISCIR campaigns", "deploy operator sites", "fix ISCIR county data". Folder: `ISCIR/`.

**Current state (2026-06-27):** 67K firms ANAF-enriched with 99.997% county coverage. 926 operator demo sites live at `https://interjob.ro/iscir/operatori/{CUI}.html`. 3 email campaigns built (930 + 737 + 47 ready to send). 42 county CSVs regenerated with phone column. 1,102 full operator records extracted from PDF (authorization numbers, addresses, phones, emails, expiry dates).

**Team:** `.claude/skills/iscir-operations/` with 37 scripts in `CODE/`. `.claude/skills/iscir-pdf-extract/` — separate skill for PDF extraction. See `ISCIR/CLAUDE.md` for full spec.

---

## 📍 Scraper Locations

**All 335 web scrapers:** See `D:\MEMORY\SCRAPER_LOCATIONS.md` for complete reference

**InterJob-related scrapers:**
- EU wholesale (CumparLegume): `D:\MEMORY\SCRAPERS/scrapers/eu_wholesale/` (735 vendors)
- Jobs (ANOFM): In progress (assigned to Phase 2)
- Land (MADR): `D:\MEMORY\SCRAPERS/scrapers/romania_land/` (14K+ listings)

---

## Business Model

B2B2C marketplace: clients → verified specialists. Start vertical: architects. Pay-per-lead + subscriptions. Expandable to engineers, designers, constructors.

**Differentiators:** full RO localization, city/category SEO, mobile-first, OAR verification.

## Subdirectories with details

| Dir | Topic | Read when |
|-----|-------|-----------|
| [EMAIL CAMPAIGNS/](EMAIL CAMPAIGNS/CLAUDE.md) | Campaign infrastructure, orchestrator, sender.py, all 11 campaigns | Working on email |
| [ANOFM/](ANOFM/CLAUDE.md) | ANOFM daily report + ANOFM_ANGAJATORI campaign | Working on ANOFM |
| [BIROU DE ARHITECTURA/](BIROU DE ARHITECTURA/) | architect_hunter agent, architect outreach | Working on architects |
| [PRIMARII/](PRIMARII/) | Mayor campaign | Working on PRIMARII |
| [SILOZURI/](SILOZURI/) | Silo campaign | Working on SILOZURI |
| [RASPIBIG INSPECT/](RASPIBIG INSPECT/) | Infrastructure inspection reports | Debugging raspibig |
| [ISCIR/](ISCIR/CLAUDE.md) | Regulatory data domain (67K firms, 1.2K operators) | ISCIR enrichment/campaigns |

## Roadmap (1-liner)

MVP → reviews/chat/premium → mobile/SMS/AI → vertical+geographic expansion

## Revenue (1-liner)

Y1: 360K RON | Y2: 1.26M RON | Y3: 3M RON. MVP budget: ~9K EUR.
