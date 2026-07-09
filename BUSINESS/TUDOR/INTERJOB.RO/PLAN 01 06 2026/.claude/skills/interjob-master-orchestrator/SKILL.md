---
name: interjob-master-orchestrator
description: "INTERJOB.RO Master Harness — orchestrate full marketplace operation. Coordinates 9 agents (6 email campaigns + 3 new infrastructure/pipeline/reporting) plus 4 daily-roundup skills + campaign dashboard. Automates: daily job catalog pipeline, email campaigns (11 active), bounce/reply handling, infrastructure monitoring, weekly reporting. Use when launching daily operations, investigating infrastructure issues, generating reports, requesting campaign status, or setting up recurring automation."
---

# INTERJOB.RO Master Orchestrator

**Mission:** Fully automated marketplace operation — data pipeline → campaign launch → monitor → report → optimize.

**Deployment:** raspibig + laptop (distributed execution)

**Scope:** 11 email campaigns (440/day capacity) + 9 job catalog domains + PostgreSQL enrichment pipeline + infrastructure health monitoring + daily/weekly reporting.

---

## Team Structure

**Execution mode:** Agent Team (real-time coordination) + Scheduled batch runs (daily/weekly)

### Phase 1: Data Pipeline (Daily 00:30 UTC)
- **pipeline-orchestrator** — Validate ANOFM/EURES/MADR, enrich DB, generate catalogs
- Input: Data source APIs + PostgreSQL
- Output: `pipeline_state.json`, catalog PDFs/HTML, alerts

### Phase 2: Campaign Execution (Daily 06:00 UTC)
- **campaign-launcher** (email-campaigns harness) — Start 11 active campaigns within 440/day cap
- Input: campaigns.json, state.json
- Output: Campaign PIDs, sends initiated

### Phase 3: Daily Roundup (Daily 09:00 UTC)
- **daily-roundup orchestrator** — Aggregate jobs/articles, generate social posts
- Input: Job database, news feeds
- Output: WordPress posts, social media content

### Phase 4: Monitor & Optimize (Continuous, every 30 min)
- **infrastructure-health** — Check raspibig (CPU/disk/memory), crons, DB connections
- **send-optimizer** (email-campaigns) — Analyze delivery patterns, recommend rate changes
- **bounce-monitor** (email-campaigns) — Suppress hard bounces, alert on spikes
- **reply-classifier** (email-campaigns) — Classify responses, segment interested leads
- Input: System metrics, IMAP folders, campaign logs
- Output: Alerts, optimization recommendations, reply classifications

### Phase 5: Daily Reporting (Daily 06:00 UTC)
- **report-generator** — Synthesize metrics, generate daily digest
- Input: Campaign state, pipeline state, infrastructure metrics
- Output: Daily digest email (HTML), blockers list

### Phase 6: Weekly Strategy (Monday 07:00 UTC)
- **report-generator** — Deep analysis, stakeholder report
- **analytics** (email-campaigns) — Aggregate 7-day KPIs, forecast
- Input: 7-30 day historical data
- Output: PDF report, recommendations, executive summary

---

## Delegated Sub-Harnesses (2026-06-24)

The master does not re-implement these — it delegates to the dedicated harness skill for each, which owns the detail. Invoke the sub-harness skill from the matching phase rather than duplicating its logic here.

| Cycle phase | Delegated harness skill | Folder | Role |
|-------------|------------------------|--------|------|
| Phase 1 — Pipeline | `eures-pipeline-orchestrator` | EURES SCRAPER/ | EU job scrape → normalize → classify → Brevo routing |
| Phase 1 — Publish | `wp-job-publisher` | WP PUBLISHER/ | Publish ANOFM/EURES jobs to 9 WordPress sites |
| Phase 1 — SEO pages | `seo-county-pages` | SEO/ | County-level job landing pages (cPanel deploy) |
| Phase 1 — Catalogs | `candidate-catalog-cycle` | CATALOG CANDIDATI/ | Candidate-side catalogs (complements job catalogs) |
| Phase 2/4 — Monitor | `email-classifier-orchestrator` | EMAIL CLASSIFIER/ | Inbox hygiene for manpowerdristor (sits in the 30-min loop) |
| Phase 3 — Distribution | `newsletter-orchestrator` | NEWSLETTER/ | Double-opt-in newsletter sends |

**Stand-alone (NOT under the master — separate domains/products):** RASPIBIG INSPECT (periodic audit), BIROU DE ARHITECTURA (architect marketplace), Universal Classified Ads (cifn.eu product), ANGAJATORI/EXPATSINROMANIA.ORG (own funnels), TEMPLATE/IDEAS (utility/reference).

**Note:** ANOFM pipeline runs on **raspi (.20)**, not raspibig — see ANOFM/CLAUDE.md host-map banner. Restart Claude Code to register the new sub-harness agents/skills.

---

## Workflow Execution

### Initial Deployment (Phase 0)
```
Check .claude/agents/ and .claude/skills/ exist
Load campaigns.json + campaigns state
Verify SSH access to raspibig (192.168.100.21)
Verify PostgreSQL connection (interjob_master on raspibig:5432)
Test email alerts (fruitnature4@gmail.com, Telegram)
```

### Daily Cycle
```
00:30 UTC  → pipeline-orchestrator runs (4-8h duration)
06:00 UTC  → campaign-launcher + report-generator start (parallel)
09:00 UTC  → daily-roundup orchestrator
30-min     → infrastructure-health + send-optimizer + bounce-monitor + reply-classifier (loop)
Each run   → Log to /opt/ACTIVE/INFRA/LOGS/{component}_{YYYYMMDD}.log
Failures   → Alert via email + Telegram, update state.json
```

### Weekly Cycle
```
Monday 07:00 UTC → report-generator (deep analysis)
Monday 09:00 UTC → analytics synthesizes 7-day trends
Output: PDF report + email to fruitnature4@gmail.com
```

---

## Integration Points

### Email Campaigns Harness (Port 8096)
- Reuses: campaign-launcher, send-optimizer, bounce-monitor, reply-classifier, dnc-manager, analytics
- Dashboard: unified campaign state + stats
- State file: `/opt/ACTIVE/EMAIL/CAMPAIGNS/state.json` (daily counts, timestamps)

### Daily Roundup Harness
- Reuses: data-validator, content-creator, publisher, monitor
- Integrated at Phase 3 (09:00 UTC)

### New Agents (Phases 1, 4, 5, 6)
- pipeline-orchestrator (new) — data pipeline orchestration
- infrastructure-health (new) — system monitoring
- report-generator (new) — reporting synthesis

### Data Flow
```
ANOFM API → pipeline → PostgreSQL → job catalog PDF/HTML → A2 Hosting
Company database → enrichment (56 steps) → lead quality scoring → analytics
Campaign state → optimizer → rate recommendations → launcher (next cycle)
System metrics → health monitor → alerts → report-generator
Report → email to Tudor + dashboard
```

---

## Commands & Control

**Start orchestrator:**
```bash
systemctl start campaign-orchestrator  # (if not running)
tail -f /opt/ACTIVE/INFRA/LOGS/orchestrator_$(date +%Y%m%d).log
```

**Check campaign state:**
```bash
cat /opt/ACTIVE/EMAIL/CAMPAIGNS/state.json | jq .
```

**Check pipeline state:**
```bash
cat pipeline_state.json | jq .
```

**Health check:**
```bash
ssh tudor@192.168.100.21 "free -h && df -h /opt && ps aux | grep campaign"
```

**Manual pipeline run:**
```bash
ssh tudor@192.168.100.21 "python3 /opt/ACTIVE/DAILY/jobs_daily_anofm.py"
```

---

## Monitoring & Alerts

**Alert channels:**
- Email: fruitnature4@gmail.com
- Telegram: @expatsinromania_news (-1003830000766)
- Dashboard: port 8096

**Alert conditions:**
1. Pipeline failure (any source unreachable >2 hours)
2. Campaign launch failed (0 sends when cap >0)
3. Bounce spike (>15% in single run)
4. Infrastructure critical (CPU >85%, disk >95%, connections >90)
5. Cron job failures >5 consecutive

**Error recovery:**
- Retry pipeline on transient failure (API timeout)
- Skip unavailable source, continue with others
- On campaign launch failure: escalate to campaign-launcher for manual investigation
- On infrastructure alert: infrastructure-health recommends action

---

## Phase 0: Context Confirmation

**Before each run:**
1. Check `_workspace/` for prior state
   - Exists + user requests "resume" → resume from last incomplete phase
   - Exists + user requests "new run" → backup to `_workspace_prev/`, start fresh
   - Not exists → initialize new run
2. Load campaign list (campaigns.json), verify enabled status
3. Check PostgreSQL connection (retry 3x on timeout)
4. Test email recipient (send test message)

---

## Test Scenarios

**Normal flow:**
```
1. Confirm all systems ready (SSH, DB, email)
2. Run pipeline-orchestrator → generates pipeline_state.json
3. Run campaign-launcher → sends within daily caps
4. Monitor infrastructure-health → no critical alerts
5. Generate report-generator → sends daily digest
6. Success: all phases complete, no blockers
```

**Error flow (pipeline source down):**
```
1. pipeline-orchestrator detects ANOFM API unreachable
2. Retries 2x, then escalates to report-generator
3. Report includes "ANOFM unavailable since 00:45, using cache from 2026-06-22"
4. Continues with EURES + MADR
5. Alert sent: "Pipeline degraded — 1/3 sources available"
6. campaign-launcher proceeds with normal caps
7. Monitoring continues
```

**Error flow (critical infrastructure alert):**
```
1. infrastructure-health detects disk 95% full
2. Sends critical alert to infrastructure-health team
3. Escalates to report-generator with recommendation
4. campaign-launcher checks disk before launch, may reduce send cap
5. Daily digest includes "DISK CRITICAL — recommend cleanup before next run"
```

---

## References

- Email Campaigns Harness: `EMAIL CAMPAIGNS/CLAUDE.md`
- Daily Roundup Harness: `DAILY/CLAUDE.md`
- Campaign Config: `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json`
- Enrichment Scripts: `/opt/ACTIVE/SILOZURI/enrich_*.py`
- Catalog Generator: `CATALOG JOBURI/build_job_catalogs.py`
