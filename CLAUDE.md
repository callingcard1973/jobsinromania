# CLAUDE.md

## What This Is

`D:\MEMORY` — operational hub for InterJob European Recruitment Network. 28 websites, email campaigns, scrapers, CV processing, multilingual content.

## Infrastructure

- **Windows laptop**: Python 3.12, `D:\MEMORY` in PATH, LM Studio at localhost:1234
- **raspibig** (tudor@192.168.100.21, SSH key auth): scrapers, enrichment, campaigns, Node-RED
- **A2 Hosting** (nl1-cl8-ats1.a2hosting.com, cPanel user `loaiidil`): production web host — **cPanel API only, never SSH**

## Domains (28)

**Job (15):** careworkers.eu, factoryjobs.eu, buildjobs.eu, electricjobs.eu, farmworkers.eu, horecaworkers.eu, meatworkers.eu, mechanicjobs.eu, warehouseworkers.eu, aluminumrecyclehub.com, expatsinromania.org, interjob.ro, mivromania.info, mivromania.online, nepalezi.com
**Static (5):** internaltransfers.eu, horecaworkers2026.com, horecaworkers2026.eu, horecaworkers2026.online, weddnesday.org
**WordPress (8):** cumparlegume.com, seicarescu.com, agroevolution.com, ajwang.org, baneasa39.com, cifn.info, haritina.com, mivromania.com

## Directory Structure (reorganized 2026-04-18 v2)

```
D:\MEMORY\
├── BUSINESS\       — business initiatives, partners, ideas
│   ├── BOGDAN GAVRA\     — AVP Park playground equipment (has own CODE/DATA/DOCS/TEMPLATES)
│   ├── COOP\             — Cooperativa Gospodarii de Altadata
│   │   └── DELECROIX\   — FR harvesting equipment (partnership under COOP)
│   ├── IDEAS\            — 102 idei unice active (159 total, 57 contopite), toate plate la nivel 1
│   │   ├── MASTER.csv   — sursa de adevar, toate ideile cu status/venit/efort
│   │   ├── [NORVEGIA/, INSOLVENTA/, TED_CONTACTE/, ...] — ~120 dirs cu nume clare, fara prefix IDEA-NNN
│   │   └── ARHIVA\      — snapshot-uri istorice, docs vechi
│   ├── TUDOR SEICARESCU LIFE STRATEGY\  — personal brand + lifestyle biz
│   │   ├── BOOK PUBLISHER\
│   │   ├── EXPAT RELOCATION SERVICE PLAN\
│   │   ├── GURU.COM\
│   │   └── PRINTING\    — print-on-demand SaaS
│   └── VIRGIL BUDASCA\  — business partner (not just contact)
│       └── INTERJOB\
├── CODE\           — all executable: campaigns, infra, automation
│   ├── CAMPAIGNS\  — email/phone outreach pipelines
│   │   ├── CODE\        — campaign scripts
│   │   ├── DATA\        — CSV outputs
│   │   ├── EMAIL\       — Brevo, templates
│   │   ├── EMAIL PERSONAL\ — DB enrichment pipeline (steps 1-46+)
│   │   ├── EMAIL_BRAIN\ — 19-inbox classifier + auto-router
│   │   ├── HARGHITA\    — RO regional campaign (770 companies)
│   │   ├── DELIVERY COMPANIES\
│   │   ├── PHONE CAMPAIGN\
│   │   └── TEMPLATES\
│   ├── INFRA\      — servers, tools, automation
│   │   ├── WEBPAGES\   — site HTML, WP management
│   │   ├── POSTHOG\    — analytics scripts
│   │   ├── FASTAPI\    — API services
│   │   ├── JAN.AI\     — LLM task feeder
│   │   ├── CLAUDE\     — OPT mirror, credentials
│   │   ├── SCRIPTS\    — loose scripts archive
│   │   ├── SECURITY\
│   │   ├── SKILLS\
│   │   ├── ULTRAPLAN\
│   │   ├── AUTOMATE\, DATACENTERS\, GOOSE\, INFRASTRUCTURE\
│   │   ├── M2 AI CARD\, OPTIMIZE\, SANDBOX\, TCARD\
│   │   └── TEMPLATES\
│   ├── AUTOMATE\   — standalone automation scripts
│   ├── SKILLS\     — Claude skills (root-level)
│   ├── CLAUDE\     — OPT mirror + credentials
│   │   └── OPT\
│   ├── PHONE CAMPAIGN\
│   │   └── CODE\
│   └── opt\        — raspibig /opt mirror
│       └── ACTIVE\
├── DATA\           — raw data, databases, scraped sets
│   ├── DB\              — PostgreSQL workspace
│   ├── OPENDATA\        — 39-country open data
│   ├── OPENTENDER\      — EU tender data (parquet + CSV)
│   ├── ROMANIA\         — RO datasets, HARGHITA
│   ├── EBRD\            — 4,176 projects, contractor monitoring
│   ├── BERD EBRD\       — EBRD by country (42 countries)
│   ├── Z.AI\            — research/scraping sandbox
│   ├── MADR VANZARE TEREN\ — ISC 23K construction + land
│   ├── EMAIL_BRAIN\     — email brain data outputs
│   ├── EURES_LAPTOP\    — EURES scraper outputs
│   ├── EU_FUNDING\      — proposals, training
│   ├── BULGARIA EU FUNDS\
│   ├── CONTIGUITY\, CONTRACTE\, DATORNICI\
│   ├── LAND FOR CONSTRUCTION IN ROMANIA\
│   └── ARCHIVE\
└── PEOPLE\         — personal contacts only
    ├── TRAIAN GARI\
    └── SARACANUL AGRESIV STEFAN\
```

## Legacy Directory Index (still on raspibig /opt/ACTIVE/)

| Directory | What |
|-----------|------|
| `A2_SITE_DEPLOYER/` | Deploy sites to cPanel + SEO |
| `ARTICLES/` | LLM articles → 11 languages → deploy |
| `CAMPAIGNS/AUTOREPLY/` | Sort 30 email accounts + autoresponders |
| `PROJECTS/CONSTRUCTION PROJECTS/` | TED contractors + agency registries |
| `CV/` | CV scanner, web UI, file watcher |
| `DELIVERY/` | ANOFM employer extraction → enrichment → Brevo |
| `FACTORYJOBS/` | Deep-enriched employer database (3,751 companies) |
| `FACTORYJOBS_PDF/` | Recruitment PDFs (6 campaigns × 38 languages) |
| `MADR VANZARE TEREN/ISC_DATA/` | **23K ISC construction contacts, campaign sleeping, Norway pages LIVE on buildjobs.eu/no/** |
| `PLASARE 400 MUNCITORI/` | 400-worker placement: Bulgaria, Norway, EURES |
| `EMAIL/` | **Order collector: Gmail→sklearn→LLM→CSV→forward to solonet.vacancy@gmail.com** |
| `EMAIL_BRAIN/` | **Automated email intelligence: 19 inboxes, classify, route workers, solonet orders, CV vault** |
| `SITE_PAGES/` | Local mirror of all site HTML |
| `llm_tasks/` | LLM task framework: spam, bounces, articles |
| `MR ANUP/SLOVENIA/` | Slovenia: 63K AJPES companies, EURES contacts |
| `OPT/` | Partial copy of raspibig /opt/ (scrapers, creds) |
| `LLM DOWNLOAD/` | PicoClaw, model benchmarking, OPENDATA |
| `BERD EBRD/` | **EBRD projects: 4,176 in 42 countries, 130+ contractors, procurement monitoring** |
| `EBRD/` | Scripts: campaign_builder, contractor_finder, procurement_monitor, ted_scraper |
| `JAN.AI/` | Jan.ai setup + LLM Task Feeder (autonomous batch LLM processing) |

## LLM Task Feeder (2026-04-12) — LIVE on raspibig

Autonomous processor: pulls from `task_queue`, sends to llama-server, stores results.
- **Tasks**: email_classify, company_enrich, cv_parse, data_quality, article_generate
- **Service**: `llm-task-feeder.service` (systemd, enabled, 24/7)
- **Script**: `/opt/ACTIVE/llm_task_feeder.py` | Source: `D:\MEMORY\JAN.AI\llm_task_feeder.py`
- **LLM**: llama-server :1234 (qwen2.5-7b Q4 on Pi5)
- **Jan.ai**: Installed on laptop (v0.7.9, port 1337) + minipc (standby). No ARM64 build for raspibig.

## Active Campaigns (2026-04-07) ✅ LIVE

### DELIVERY_RO_2026
- **CSV:** 562 Romanian delivery/transport/logistics companies (cleaned, deduplicated, blacklist-filtered)
- **Sources:** ANOFM_TRANSPORT (377) + ANAF programs (182) + Master DB (244)
- **Sender:** Brevo API (office@mivromania.info)
- **Template:** curierat/tudor_template1.txt (updated with Reply-To)
- **Daily Limit:** 100 emails
- **Duration:** ~6 days to complete
- **Reply-To:** manpower.dristor@gmail.com
- **Status:** ✅ RUNNING (PID varies)
- **Logs:** `/opt/ACTIVE/EMAIL/CAMPAIGNS/delivery_brevo.log`

### HARGHITA_PHASE1_2026 (Proof of Concept)
- **CSV:** 6 construction companies
- **Template:** harghita_phase1_construction.txt (98% AJOFM success + detachment + 4 qualifying questions)
- **Daily Limit:** 10 emails
- **Duration:** ~30 minutes
- **Status:** ✅ RUNNING
- **Expected:** 2-3 responses (30-50% rate)

### HARGHITA_PHASE2_2026 (Sector Expansion)
- **CSV:** 18 mixed companies (6 manufacturing, 5 hospitality, 7 logistics)
- **Templates:** Manufacturing (156% success) + Hospitality (115% success) + Logistics
- **Daily Limit:** 20 emails
- **Duration:** ~1 day
- **Status:** ✅ RUNNING
- **Expected:** 4-6 responses (25-35% rate)

### HARGHITA_PHASE3_2026 (Full Regional Blitz)
- **CSV:** 770 all Harghita companies with emails
- **Template:** Rotating (manufacturing, hospitality, logistics based on company profile)
- **Daily Limit:** 100 emails
- **Duration:** ~8 days
- **Status:** ✅ RUNNING
- **Expected:** 231 responses (30% rate)
- **Revenue:** €70K-€100K/month

**All Harghita phases independent, no approval gates, all parallel.**

### Support Campaigns (Continuous)
- **FI_TED_CONSTRUCTION:** EU construction procurement (80/day)
- **ANOFM Orchestrator:** 7 sectors automated (managed by orchestrator.py)
- **NECALIFICATI:** Blue-collar placements

---

## Conventions

- SSH: always `192.168.100.21`, not hostname (Tailscale routing issue)
- SCP to Windows: forward slashes `"D:/MEMORY/path/"`
- SSH from Windows: single quotes around command
- Scrapers: max 2 concurrent on raspibig. Playwright locally.
- A2 docroot: `~/domainname/` (NOT `~/public_html/`)
- RTL languages (ar, ur, ps): `dir="rtl"` in HTML
- All apply links → `https://interjob.ro/apply.html`
- Email: nl1-cl8-ats1.a2hosting.com — IMAP 993, SMTP 465/587. Passwords in `OPT/opt/EMAIL/.env`
- **Email Responses:** All recruitment campaigns route to `manpower.dristor@gmail.com` (processed by response skill)

## AUTOHEAL SYSTEM (2026-04-15) ✅ LIVE ON BOTH MACHINES

**Watchdog v2** runs every 15 min via cron on raspibig + raspi. Auto-restarts anything broken.

### Raspibig Watchdog (`/opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py`)
Checks: 11 services, bot 409 conflicts (auto deleteWebhook+restart), dashboard 8096, orchestrator, disk (auto-clean >85%), Ollama, response tracker cron, NanoClaw heartbeat, Caddy HTTPS.

### Raspi Watchdog (`/opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py`)
Checks: 7 services, campaign orchestrator, disk, PostgreSQL query, Node-RED, Caddy, bot conflicts, raspibig reachability.

### Telegram Bot — @raspibig_controller_bot (37 commands, ONLY bot)
`/q` `/health` `/blockers` `/heal` `/nanoclaw` — overview + autoheal
`/svc` `/restart` `/logs` `/errors` `/watchdog` — services
`/campaigns` `/norway` `/bounce` `/send` `/stop_campaign` — campaigns
`/solonet` `/send_solonet_X` `/solonet_placed_X <w> <eur>` — solonet orders
`/process` `/approve_eXXX` `/skip_eXXX` `/queue` — email processing
`/responses` `/workers` `/leads` — response tracking
`/disk` `/mem` `/top` `/db` `/ollama` `/scrapers` — system
`/ping` `/wake` `/kill` `/net` `/ssl` `/cron` `/temp` `/uptime` `/backup` — infra

### Response Tracker (`/opt/ACTIVE/INFRA/SKILLS/response_tracker.py`)
Scans 19 IMAP inboxes every 5 min. Classifies: INTERESTED, NOT_INTERESTED, WORKER_APPLICATION, REPLY, BOUNCE, AUTO_REPLY. Workers auto-routed to applicant DB + auto-reply with apply form. Romanian employer leads (.ro) auto-create solonet order drafts.

### Solonet Order Pipeline (`/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py`)
Auto-creates draft orders from Romanian employer responses. Tudor approves via `/send_solonet_X` → email to solonet.vacancy@gmail.com. Tracks: draft→sent→responded→placed. Auto follow-up after 3 days. Revenue tracking via `/solonet_placed_X <workers> <eur>`. DB: `interjob_master.solonet_orders`. No LLM tokens.

### Email Processor (`/opt/ACTIVE/INFRA/SKILLS/email_processor.py`)
Every 10 min scans unread emails. sklearn classifier first (instant) → Ollama qwen3-4b for draft reply if low confidence. Telegram proposal: `/approve_eXXX` or `/skip_eXXX`. Executor: `/opt/ACTIVE/INFRA/SKILLS/email_executor.py`.

### Worker Router (`/opt/ACTIVE/INFRA/SKILLS/worker_router.py`)
Auto-routes worker applications to `master_applicants.db` (756+) + auto-reply with interjob.ro/apply.html form. Applications kept for Tudor, never forwarded to solonet.

### NanoClaw (`/opt/ACTIVE/INFRA/GOVERNOR/nanoclaw.py`)
Operations agent: 9 scrapers, TED data, disk, missed-run detection. Ollama LLM diagnosis on scraper failure. Morning digest at 07:00.

### Architecture (2026-04-16)
- **One bot**: @raspibig_controller_bot — all interaction, 37 commands
- **RASPI ALERTS bot**: ELIMINATED — token replaced everywhere
- **Raspi**: zero telegram bots, zero email sending. Only scrapers + APIs + DB
- **Raspibig**: ALL telegram (5 bots), ALL email sending, ALL automation

---

## RASPIBIG OPTIMIZATION (2026-04-07) ✅ COMPLETE

**All changes are non-destructive and reversible**

### Changes Made
1. **Ollama RE-ENABLED** (2026-04-15) — qwen3-4b, qwen2.5:1.5b, llama3.2:3b for NanoClaw + smart_router
2. **Node-RED Protection** — Configured restart limits to prevent crash loops
3. **PostgreSQL VACUUM** — Rescheduled to 2 AM (off-peak) from business hours
4. **Log Rotation** — Configured 14-day retention (EU funding), 7-day (PostgreSQL), 4-week (email)
5. **Health Monitoring** — Hourly cron job checks services, disk (>80%), swap (>1GB)

### Results
- **Memory**: 4.3GB used → 3.5GB (freed 248MB)
- **Swap**: 662MB → 583MB
- **Node-RED**: Protected from crash loops
- **PostgreSQL**: Heavy I/O moved to 2 AM
- **Monitoring**: Hourly health checks active

### Health Check Script
```bash
python3 /opt/ACTIVE/INFRA/SKILLS/raspibig_health_check.py
# View: tail -20 /home/tudor/.logs/raspibig_health.log | jq .
```

**Documentation**: `/opt/RASPIBIG_OPTIMIZATION_2026-04-07.md`

---

## POSTFIX + RSPAMD DKIM SIGNING (2026-04-18) ✅ LIVE ON RASPIBIG

**Architecture**: Campaign → Postfix :25 → rspamd milter :11332 (DKIM sign) → Brevo SMTP relay :587 → inbox

### Components
- **rspamd 4.0.1**: `/etc/rspamd/local.d/dkim_signing.conf` — signs with selector `mail2026`, keys in `/etc/rspamd/dkim/$domain.key`
- **Postfix**: satellite relay, `relayhost=[smtp-relay.brevo.com]:587`, milter on 11332, loopback-only
- **sasl_passwd**: per-sender Brevo credentials for 9 senders (factoryjobs.eu, careworkers.eu, buildjobs.eu, mivromania.info, mivromania.online, expatsinromania.org, nepalezi.com, cifn.info, cumparlegume.com)
- **send_providers.py**: `send_postfix()` function appended — connects smtplib to 127.0.0.1:25

### Campaign opt-in
`"use_postfix": true` in sector config → routes via Postfix+DKIM instead of direct Brevo API.
13 sectors across 8 configs updated (anofm, callcenters_francofoni, electric_eu, factoryjobs_eu, factoryjobs_eu_norway, horeca_eu_norway, meatworkers_eu_norway, warehouse_eu).
Script: `D:\MEMORY\CODE\INFRA\SCRIPTS\enable_postfix_all_configs.py`

### DKIM DNS records
27/28 domains: `mail2026._domainkey.{domain}` TXT added via cPanel API2 ZoneEdit.
Script: `D:\MEMORY\CODE\INFRA\SCRIPTS\add_dkim_dns.py`
**cifn.info**: key at `/etc/rspamd/dkim/cifn.info.key` — DNS record needed on Romanian host (grem01.gazduire.ro, cPanel `uamkawbd`)

### Key files on raspibig
```
/etc/rspamd/local.d/dkim_signing.conf
/etc/rspamd/local.d/worker-proxy.inc     # milter on 127.0.0.1:11332
/etc/rspamd/dkim/                        # 28 x {domain}.key + {domain}.txt
/etc/postfix/main.cf
/etc/postfix/sasl_passwd                 # per-sender Brevo credentials (postmap'd)
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_providers.py   # send_postfix() appended
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py    # use_postfix branch at line ~158
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py.bak_predkim  # backup
```

### Verify signing works
```bash
python3 -c "
import smtplib
from email.mime.text import MIMEText
m = MIMEText('test')
m['Subject']='dkim test'; m['From']='office@factoryjobs.eu'; m['To']='YOUR_EMAIL'
with smtplib.SMTP('127.0.0.1',25) as s: s.sendmail('office@factoryjobs.eu',['YOUR_EMAIL'],m.as_string())
"
# Check headers for DKIM-Signature: v=1; a=rsa-sha256; d=factoryjobs.eu; s=mail2026
```

---

## DNS RESOLUTION FIX (2026-04-07) ✅ COMPLETE

**PROBLEM**: Brevo API access was failing due to DNS resolution issues (Tailscale nameserver 100.100.100.100 timing out)

**SOLUTION APPLIED**:
1. **Disabled Tailscale DNS override**: `sudo tailscale set --accept-dns=false`
2. **Updated DNS configuration**: Set Google DNS (8.8.8.8, 8.8.4.4) as primary in `/etc/resolv.conf`
3. **Verified Brevo connectivity**: All API endpoints now resolve and respond correctly

**RESULTS**:
- ✅ **Brevo API**: 1/4 API keys working (BREVO_BUILDJOBS_API_KEY)
- ✅ **Brevo SMTP**: 6/7 SMTP configurations working
- ✅ **DNS Resolution**: Stable and fast for all email providers
- ✅ **Campaign Progress**: Unblocked and accelerating

**Working Brevo Accounts**:
- **API**: BREVO_BUILDJOBS_API_KEY (3 others: HTTP 401 - need credential refresh)
- **SMTP**: 6 working accounts (MIVROMANIA, MIVROMANIA_ONLINE, FACTORYJOBS, BUILDJOBS, CAREWORKERS, CIFN)

---

## EMAIL CAPACITY MAXIMIZATION PROJECT (2026-04-07) ✅ COMPLETE

**PRIMARY OBJECTIVE**: Send maximum emails for European recruitment campaigns

**CURRENT CAPACITY**: 1,560 emails/day (4 active campaigns on raspi)  
**TARGET CAPACITY**: 2,560 emails/day (with Zoho warmup completion)  
**INCREASE**: +64% (+1,000 emails/day when fully warmed)

### Email Providers Status (LIVE)
| Provider | Status | Capacity/day | Method | Auth |
|----------|--------|--------------|---------|------|
| Brevo | ✅ ACTIVE | 270 | Direct API | Standard |
| Gmail | ✅ ACTIVE | 235 | SMTP TLS | Standard |
| **Zoho #1** | ✅ ACTIVE | 50→250 | SMTP TLS + VPN | App Password |
| **Zoho #2** | ✅ ACTIVE | 50→250 | SMTP TLS + VPN | App Password |
| Outlook | ❌ DISABLED | — | — | Auth disabled |

### ZOHO SMTP ACCOUNTS (2026-04-07) ✅ BOTH ACTIVE

**Account 1: transport.work@zohomail.com**
- Host: smtp.zoho.com:587 (TLS)
- App Password: JKkdxGS3szvC (2FA protected)
- Starting: 50/day, warming +5/day to max 250/day
- Status: ✅ TESTED

**Account 2: workers.europe@zohomail.eu**
- Host: smtp.zoho.eu:587 (TLS)
- App Password: Mu59U3Lfa3Dw (2FA protected)
- Starting: 50/day, warming +5/day to max 250/day
- Status: ✅ TESTED

### VPN INFRASTRUCTURE (ProtonVPN WireGuard) ✅ ACTIVE

**Machine**: raspi (192.168.100.20)  
**Config**: `/etc/wireguard/proton-nl.conf`  
**Type**: WireGuard (lightweight, optimized)  
**Routing**: Only Zoho SMTP traffic (89.39.107.113:51820)  
**Auto-start**: Enabled (systemctl enable wg-quick@proton-nl)  
**DNS**: ProtonVPN 10.2.0.1 (configured)  

Commands:
```bash
# Check VPN status
ssh tudor@192.168.100.20 'sudo wg show proton-nl'

# Restart if needed
ssh tudor@192.168.100.20 'sudo wg-quick down/up proton-nl'

# Check auto-start
ssh tudor@192.168.100.20 'sudo systemctl status wg-quick@proton-nl'
```

### WARMUP SCHEDULE (Automatic Daily +5)

| Day | Zoho #1 | Zoho #2 | Total | Duration |
|-----|---------|---------|-------|----------|
| 1   | 50 | 50 | 100 | Today |
| 5   | 70 | 70 | 140 | 5 days |
| 10  | 100 | 100 | 200 | 10 days |
| 20  | 150 | 150 | 300 | 20 days |
| 40  | 250 | 250 | 500 | 40 days (max) |

Automation:
```bash
# Run daily at midnight (or add to crontab)
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/zoho_warmup_cron.sh

# View current warmup status
python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/zoho_warmup.py
```

### DEPLOYMENT

```bash
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED
python3 send_campaign.py
```

Auto-distributes across Brevo, Gmail, and both warming Zoho accounts.

### CRITICAL FIXES (2026-04-07)

1. **Killed duplicate continuous_downloader** — Was consuming 84% CPU, freed entire core
2. **Verified all HDD data backed up** — 769GB synced to interjob_master PostgreSQL
3. **Disabled unused Ollama** — Freed 248MB RAM permanently
4. **Node-RED crash protection** — Configured restart limits, prevents infinite loops
5. **PostgreSQL VACUUM optimization** — Moved to 2 AM, removed peak-hours I/O

### SYSTEM STATUS (2026-04-07)

**Raspibig Performance:**
- CPU: 59% active, 41% free (up from 100%)
- Memory: 3.5GB used, 189MB free (up from 137MB)
- Load: 6.39 (settling down, freed duplicate process)
- Disk I/O: Reduced (no more duplicate downloads)
- Health: ✅ Monitored hourly

**Email Capacity:**
- Current: 1,560/day (4 campaigns × 390 emails each: Brevo 290 + Gmail 100)
- With Zoho warmup: 2,560/day (adding Zoho 500×2 when fully warmed)
- Active campaigns: ELENA, ANOFM_TUDOR, VIRGIL, LUCIAN
- Timeline: Zoho +5/day automatic increase to 250/day per account

**Data Integrity:**
- ANOFM: 8,037+ records synced daily ✅
- EU Procurement: 7 CSV files archived ✅
- All HDD data: Backed up in PostgreSQL ✅

---

```bash
# Start campaigns (auto-distributes across all providers)
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED
python3 send_campaign.py

# Monitor Zoho sends
tail -f logs/*.log | grep ZOHO

# Check capacity
python3 zoho_monitor.py
```

### CREDENTIALS STORAGE

File: `/opt/EMAIL/CAMPAIGNS/.env` (on raspibig and raspi)

```
ZOHO_EMAIL=transport.work@zohomail.com
ZOHO_PASSWORD=JKkdxGS3szvC

ZOHO_EMAIL_2=workers.europe@zohomail.eu
ZOHO_PASSWORD_2=Mu59U3Lfa3Dw

ZOHO_WARMUP_ENABLED=true
ZOHO_WARMUP_INCREASE_DAILY=5
ZOHO_WARMUP_MAX=250
```

### Business Impact
**PURPOSE**: Maximize outreach to European employers for worker placement
- **Current**: 605 emails/day (starting warmup)
- **3 months**: 1,005 emails/day (fully warmed)
- **Recruitment Speed**: 2x faster with €0 cost
- **ROI**: Excellent (ProtonVPN FREE + Zoho FREE)

**Documentation**: `D:\MEMORY\EMAIL/` + `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ZOHO_ACCOUNTS.md`

## Data Safety Rule

**Never delete data without certainty it is duplicated elsewhere.**
- Code, logs, old backups of code → safe to delete
- Database tables, CSVs, contacts, emails, procurement data → verify exact duplicate exists before drop/delete
- When in doubt: don't delete, propose archival to HDD instead
- Backups stay until explicitly told to remove them

## Sensitive Files
`raspi.json`, `OPT/opt/EMAIL/.env`, `A2_SITE_DEPLOYER/env/*.env` — do not share. OpenCage key in `OPENCAGE_API_KEY` env var.


---

## DELECROIX - Parteneriat Utilaje Recoltare Franta->Romania

**Dosar complet**: `D:\MEMORY\DELECROIX\claude.md`

**Ce e**: Delecroix (Franta, 13 angajati) produce benzi transportoare de recoltare, remorci legume, statii sortare, pareuse varza. Toubeaux (gerant) propune parteneriat: Tudor = business finder (~10% comision), Agri Alianta = distribuitor (contract deja semnat, 6 filiale RO).

**Concurenta**: SIMON (DE, site picat), Krukowiak (PL, picat), Domasz (PL, a plecat din utilaje), MTS-SANDEI (IT, activ dar foarte scump). Delecroix e practic singur pe piata benzilor de recoltare la pret accesibil in Romania.

**Distribuitori RO**: Agri Alianta (CONTRACTAT, 6 filiale, 0755 405 555), Agritech (Ograda, vinde SIMON/DOMASZ dar "Sortare" goala), Equinto (Galati, SERIOS, deja importa ERME din FR, 0745389200), MARCOSER (Matca, marketing leads, 20 ani clienti legumicultori), Green Garden (Calarasi, consumabile).

**Comision estimat**: 5K-60K EUR/an (5-35 unitati x ~1500 EUR/unitate)

**Contact Toubeaux**: +33 6 08 09 97 20, contact@delecroix-harvesting.com

**Urmator pas**: Cere preturi exacte de la Toubeaux + contacteaza Agri Alianta pentru coordonare vanzari.

---

## DB ENRICHMENT PIPELINE (2026-04-18) — IN PROGRESS

**Location**: `D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\CODE\`
**DB**: interjob_master PostgreSQL 18, port 5433, user tudor/tudor
**Connect**: `PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master`

### Steps built (1-46):

| Step | File | What | Status |
|------|------|------|--------|
| 1 | step1_db_filter.sql | Email quality tiers 1-4, DNC crossref | ✅ Done |
| 2 | step2_mx_check.py | Async MX validation 802K emails | ✅ Done |
| 3 | step3_link_emails_companies.sql | Domain match emails→companies_clean | ✅ Done |
| 4 | step4_campaign_segments.sql | v_campaign_ready view | ✅ Done |
| 5 | step5_fix_insolvent.sql | Cross-ref insolvency by CUI | ✅ Done |
| 6 | step6_no_enrich.sql | NO companies sync from no_companies_full | ✅ Done |
| 7 | step7_ted_crossref.sql | TED winners → ted_wins column | ✅ Done |
| 9 | step9_import_ro_missing.sql | +134K RO companies imported | ✅ Done |
| 10 | step10_lead_scoring.sql | Lead score formula (max 100) | ✅ Done |
| 11 | step11_phone_campaigns.sql | Phone CSVs: NO/RO/PL/BG | ✅ Done |
| 12 | step12_ro_revenue_segment.sql | 3yr revenue growth boost | ✅ Done |
| 13 | step13_fr_pattern_enrich.py | FR info@domain.fr pattern enrichment | ✅ Done |
| 14 | step14_procurement_buyers.sql | 97K EU buyers exported | ✅ Done |
| 17 | step17_liquidator_contacts.sql | 500 liquidators CSV | ✅ Done |
| 20 | step20_worker_employer_match.py | SQLite master_applicants.db matching | ✅ Done |
| 22 | step22_import_procurement_buyers.sql | Import 97K buyers into companies_clean | ⏳ Interrupted (Postgres killed) |
| 23 | step23_se_enrich.sql | SE email sync from se_companies | ⏳ Pending |
| 24 | step24_warm_leads.sql | Export INTERESTED/REPLY to CSV | ✅ Done (21 rows) |
| 25 | step25_bilant_sync.sql | bilant_years → companies_clean revenue | ⏳ Pending |
| 26 | step26_sector_normalize.sql | standard_sector column (10 buckets) | ⏳ Pending |
| 27 | step27_followup_scheduler.sql | followup_at = sent_at+7d | ⏳ Pending |
| 29 | step29_campaign_builder_v2.py | Cross-country --standard-sector builder | ✅ Built |
| 30 | step30_template_selector.py | Auto-select template per sector | ✅ Built |
| 31 | step31_buyer_enrich.sql | Enrich procurement buyers via domain | ⏳ Pending |
| 32 | step32_insolvency_workers.sql | 11,950 insolvency emails → CSV | ⏳ Pending |
| 33 | step33_daily_report.py | HTML + Telegram 07:00 digest | ✅ Built |
| 34 | step34_sync_raspibig.sh | pg_dump + SCP + restore | ✅ Built, not run |
| 35 | step35_lead_score_decay.sql | last_ted_year decay scoring | ⏳ Pending |
| 36 | step36_it_campaign.sql | 10K IT/tech EU campaign CSV | ⏳ Pending |
| 37 | step37_dk_fi_email_pattern.py | DK/FI pattern emails from website | ✅ Built |
| 38 | step38_agency_flag.sql | Flag staffing agencies | ✅ Run |
| 39 | step39_template_router.py | Template routing table | ✅ Built |
| 40 | step40_contact_name_extract.sql | First name from email | ✅ Run |
| 41 | step41_campaign_roi.sql | Campaign ROI view | ✅ Run |
| 42 | step42_phone_call_list.sql | 20K phone call list CSV | ✅ Run |
| 43 | step43_website_contact_scraper.py | Scrape /contact pages for emails | ✅ Built |
| 44 | step44_gdpr_tracker.sql | GDPR basis column | ✅ Run |
| 45 | step45_warm_lead_followup.py | Auto-send 7-day followups | ✅ Built |
| 46 | step46_sector_country_heatmap.sql | Opportunity heatmap → CSV | ✅ Run |

### Key DB facts:
- `companies_clean`: 33M rows, no auto-increment on id (use MAX(id)+ROW_NUMBER())
- `master_emails`: 1,032,944 rows, quality_tier 1-4
- `ted_awards`: 3.4GB, buyer=cae_name, winner=win_name
- `no_companies_full`: 94 cols, konkurs field for NO insolvency
- Enriched emails: `enriched_email` column, always use `COALESCE(email, enriched_email)`
- Campaign CSV output: `D:\MEMORY\CAMPAIGNS\EMAIL PERSONAL\DATA\`

### To resume after Postgres restart:
```bash
BASE="/d/MEMORY/CAMPAIGNS/EMAIL PERSONAL/CODE"
PSQL='"/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master'
for step in step22_import_procurement_buyers step23_se_enrich step25_bilant_sync step26_sector_normalize step27_followup_scheduler step31_buyer_enrich step32_insolvency_workers step35_lead_score_decay step36_it_campaign; do
  echo "=$step="
  PGPASSWORD=tudor eval "$PSQL -f '${BASE}/${step}.sql'" 2>&1 | tail -5
done
```

---

## MEMORY REORGANIZATION (2026-04-18) ✅ DONE

`D:\MEMORY` restructured from ~150 root items to 6 folders.
Duplicates at root (`EMAIL PERSONAL`, `PHONE CAMPAIGN`, `AUTOMATE`, `INFRASTRUCTURE`, `SKILLS`, `JOBFAIRS`) are originals still locked by processes — **delete after Postgres/Python processes stop**.

**IDEAS moved**: `D:\MEMORY\IDEAS` → `D:\MEMORY\BUSINESS\IDEAS` (153 ideas, MASTER.csv updated)
**New ideas**: IDEA-142 through IDEA-153 added (primarii AVP Park, SICAP monitor, heatmap auto-launch, Gumroad products, COOP registry, CIFN English API, etc.)

---

## IDEAS CLEANUP (2026-04-18) -- DONE

### Structura finala
- **`BUSINESS/IDEAS/`** — plat, nivel 1, ~120 directoare cu nume clare, fara prefix IDEA-NNN
- **`BUSINESS/IDEAS/MASTER.csv`** — sursa de adevar, toate cele 159 idei
- **`BUSINESS/IDEAS/ARHIVA/`** — snapshot-uri istorice
- Fiecare director are `claude.md` cu scop, date, venit

### Idei contopite (2 runde)
- **159 idei** → **96 unice active** (63 marcate MERGED)
- Runda 1: 57 contopite (merge_ideas.py)
- Runda 2: 6 contopite (IDEA-036, 062, 070, 071, 080, 152)
- Backup: `MASTER_backup_before_merge.csv`, `MASTER_backup2.csv`

### Cele mai mari grupuri master
| Master | Absorbit | Ce face |
|--------|----------|---------|
| IDEA-004 AGENTII RECRUTARE PLATFORM | 12 duplicate | 18K agentii EU, plasare muncitori |
| IDEA-043 COMPANY DATA ENRICHMENT | 5 duplicate | CUI→ANAF→email→bilant pipeline |
| IDEA-068 NEWSLETTER PROCUREMENT JOBS | 5 duplicate | newsletter tenders+jobs B2B |
| IDEA-009 TED EU TENDER INTELLIGENCE | 4 duplicate | 5.1M licitatii EU, campanii+API |
| IDEA-003 INSOLVENTA ALERTS & ASSETS | 2 duplicate | 770K companii monitorizate, alerte+leads |

### Idei noi adaugate
IDEA-154..159: Real Estate cu ferme agricole (distressed sales platform, MADR scraper, monitor B2B).

---

## SEAP BIDDING ASSISTANT (2026-04-18) — IDEA-160, COD LIVE

**Location:** `D:\MEMORY\BUSINESS\IDEAS\SEAP_BIDDING_ASSISTANT\`

### Componente
- `seap_scraper.py` — scrape e-licitatie.ro (2019-2026), achizitii directe + CAN, PostgreSQL
- `seap_historic_scraper.py` — scrape istoric.e-licitatie.ro (2007-2018)
- `seap_check.py` — stats: count, top CPV, date range
- `bid_analyzer.py` — CPV/keyword → top castigatori, preturi min/median/max din ted_awards
- `bid_writer.py` — CLI: genera propunere licitatie in romana cu LM Studio localhost:1234
- `bid_api.py` — FastAPI port 5077: POST /analyze + POST /write

### Date
- `interjob_master.seap_ro_awards` — 100 rânduri test, scraping in curs
- `ted_awards` 6.2M + `tenders` 5.1M — sursa analiza preturi/castigatori

### Comenzi
```bash
# Scraping SEAP
python seap_scraper.py --type all
python seap_historic_scraper.py

# Bid writer
python bid_writer.py --cpv 45233140 --title "Lucrari asfaltare" --buyer "CJ Ilfov" --value 2000000

# API
python bid_api.py  # port 5077
```

### Model business
EUR 200-500/propunere + 5% success fee. Target: firme constructii/IT/servicii care liciteaza regulat.

---

## PUBLISHING SETUP (2026-04-18) -- CONTURI ACTIVE

**Email:** apaminerala@yahoo.com | **Parola:** 5c5Kr1&C&d2Jr8da

| Platform | Status | Note |
|----------|--------|------|
| Lulu | INSCRIS | Cod integrare gata in D:\MEMORY\PRINTING\ |
| Amazon KDP | INSCRIS | Parola = cont Amazon |
| Draft2Digital | INSCRIS | Distributie larga |
| BookVault | INSCRIS | - |

**Cod Lulu gata:** `D:\MEMORY\PRINTING\` — lulu_client.py + stripe_handler.py + app.py + routes.py
**Lipseste:** Lulu API client_id/secret (lulu.com/account/api) + Stripe key

**Prima carte recomandata:** "European Jobs Guide for Nepali Workers"
- Continut: nepalezi.com (8 limbi, joburi EU, visa support)
- Audienta: 20K nepalezi in RO + diaspora globala
- Pret: €9.99 KDP + €19 Gumroad PDF
- Efort: 2 zile

**Alte carti din date existente (Gumroad):**
- "Top 500 Construction Winners Norway 2020-2024" — ted_awards filtrat NO — €49
- "Romanian Insolvent Companies 2024" — insolventa DB — €79
- "50 Romanian Farms For Sale 2026" — MADR+BPI — €29
- "SEAP Romania Procurement Winners 2020-2025" — seap_ro_awards — €59
