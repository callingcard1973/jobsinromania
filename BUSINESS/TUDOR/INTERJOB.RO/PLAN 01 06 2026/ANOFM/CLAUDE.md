# ANOFM — Daily Report + Email Campaigns

**v2.4 | 2026-06-21** · **Structure:** CODE/ (scripts) + DATA/ (reports) + HANDOFF_2026_06_18.md + **HARNESS (new)**

> **Verified live 2026-06-19** on raspibig. **NEW: Harness system deployed for raspi (2026-06-21)** — independent ANOFM pipeline on raspi with 5-agent team orchestration. See "Harness" section below.

> **⚠️ CANONICAL HOST MAP (verified 2026-06-24):** The **entire ANOFM pipeline runs on raspi (192.168.100.20)** — `anofm_scraper.py` + `ingest_anofm.py` (systemd timers), campaign cron (`0 9 * * 1-5 … campaign_anofm_angajatori.py --limit 150`), and the **daily report** (`anofm-daily-report.timer` 04:00, migrated from raspibig 2026-06-24). Report reads `anofm_db.ij_jobs` (NOT interjob_master), runs via `/usr/bin/python3` (raspi has no venv), `PGHOST=localhost`. **raspibig (192.168.100.21)** now holds only a legacy `anofm` DB mirror; its daily-report timer is **disabled**. The `.claude/` harness targets raspi .20. Older inline lines below that say "raspibig (.21)" are STALE.

---

## 🔧 HARNESS: ANOFM on Raspi (2026-06-21)

**NEW (2026-06-23):** 3 reusable skills learned from deployment:
- **postgresql-diagnostics** — Fix PostgreSQL socket/connection issues (PGHOST fix pattern)
- **cron-job-automation** — Set up reliable cron jobs with logging & monitoring
- **pipeline-recovery** — Recover multi-phase pipelines from partial failures (idempotent re-runs)

**Status:** ✅ Deployed  
**Target:** raspi (192.168.100.20)  
**Execution:** Agent team (5 specialists) + Orchestrator  
**Trigger:** Use skill `anofm-orchestrator` when:
- "Activate ANOFM on raspi" (initial setup)
- "Run full ANOFM cycle" (scrape → ingest → send → monitor)
- "Check ANOFM health" (diagnostics)
- "Resume ANOFM after failure" (error recovery)

**Components:**

| Component | Type | Purpose |
|-----------|------|---------|
| **Scheduler** | Agent | Manage systemd timers (enable/disable/verify) |
| **Scraper Monitor** | Agent | Validate CSV output (schema, row counts) |
| **Ingest Monitor** | Agent | Load CSV → anofm_db (schema mapping, dedup) |
| **Campaign Monitor** | Agent | Send emails (150/day cap, DNC updates) |
| **Health Checker** | Agent | Monitor overall health (score 0–100, alerts) |
| **anofm-scraper-launch** | Skill | SSH to raspi, run scraper, validate output |
| **anofm-ingest-run** | Skill | CSV→DB ingestion with error recovery |
| **anofm-campaign-send** | Skill | Brevo SMTP, rate limiting, bounce management |
| **anofm-pipeline-health** | Skill | System metrics, trending, alerts |
| **anofm-orchestrator** | Skill | Central coordinator (activate agents, manage flow) |

**Change history:**

| Date | Change | Reason |
|------|--------|--------|
| 2026-06-21 | Harness deployed (5 agents + 4 skills + orchestrator) | Provide automated pipeline orchestration for independent raspi ANOFM |
| 2026-06-19 | Raspi handoff completed (16,429 rows synced, tested) | Foundation for harness deployment |

---

---

## Directory Structure

```
ANOFM/
├── CLAUDE.md (this file)
├── HANDOFF_2026_06_18.md (deployment guide)
├── CODE/ (local reference scripts for raspibig)
│   ├── anofm.py* (main campaign — ANOFM_ANGAJATORI)
│   ├── constructii.py (sector variant)
│   ├── factory.py* (FACTORY_RO variant)
│   ├── horeca.py (sector variant)
│   ├── primarii.py* (PRIMARII variant)
│   ├── productie.py (sector variant)
│   ├── sme.py* (SME variant)
│   ├── transport.py (sector variant)
│   ├── sender.py* (Brevo SMTP client)
│   ├── export_at.py* (AT export, 3 formats)
│   ├── enable_export.py* (toggles export)
│   └── disable_necalificati.py* (filter unskilled)
└── DATA/ (daily reports archive)
    ├── anofm_report_2026-06-03.html (9,087 jobs)
    ├── anofm_report_2026-06-04.html (9,087 jobs)
    └── anofm_report_today.html (snapshot 2026-06-03)
```

---

## Daily Report (Production)

**Live Script (raspibig):** `/opt/ACTIVE/INTERJOB/anofm_daily_report.py`
**Output Location:** `/opt/ACTIVE/INTERJOB/anofm_report_YYYY-MM-DD.html`
**Data source:** `interjob_master.ij_jobs` WHERE `source='anofm' AND status='active'`
**Current Data (2026-06-19):** ~12,976 active jobs | 10 sectors | 20 counties (refreshed after ingest fix)

**systemd timers (raspibig) — verified 2026-06-19:**
```
anofm-scraper.timer          Mon-Fri 08:25, 12:25, 15:59  → run_anofm_autofeed.sh (scrape 85pg ~8min, CSV + segments + auto-feed)
anofm-ingest.timer           Mon-Fri 09:00, 13:00, 16:30  → ingest_anofm.py (CSV → ij_jobs, ~400-580 inserts/day, dedup)
anofm-audience-rebuild.timer Mon-Fri 09:10, 13:10, 16:40  → anofm_angajatori_rebuild.py (CSV → anofm_angajatori_dedup.csv, campaign audience)
anofm-daily-report.timer     daily 04:00                  → anofm_daily_report.py (HTML + Telegram)
```

**Scripts (raspibig):**
- Scraper: `/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/ANOFM/DOCKER/PROGRAMS/anofm_api_scraper_fixed.py` → CSV to `/mnt/hdd/SCRAPER_DATA/csv/ANOFM/`. **Streaming + dedup** (refactored 2026-06-19): writes per-page to `.tmp` via a `sink` callback, dedups by `job_id` (fallback `company|title|city`) with a `seen` set, then `os.replace` atomic rename — no full memory buffer, no partial CSV consumed on kill. Backup: `anofm_api_scraper_fixed.py.bak_20260619_stream`.
- Ingest: `/opt/ACTIVE/INTERJOB/ingest/ingest_anofm.py` (uses `latest_csv()`, upserts `ij_jobs` by `source_job_id`/`content_hash`)
- Audience rebuild: `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/anofm_angajatori_rebuild.py` (latest CSV → `DATA/anofm_angajatori_dedup.csv`: one row per company, top job by positions, business email only, excludes sent+DNC; atomic write + backup)
- Report: `/opt/ACTIVE/INTERJOB/anofm_daily_report.py`

**Manual execution:**
```bash
plink -batch -pw 'REDACTED' tudor@192.168.100.21 "systemctl start anofm-scraper.service"        # scrape now
plink -batch -pw 'REDACTED' tudor@192.168.100.21 "systemctl start anofm-ingest.service"          # ingest latest CSV
plink -batch -pw 'REDACTED' tudor@192.168.100.21 "systemctl start anofm-daily-report.service"    # gen report now
```

**Known gap — ingest was unscheduled 2026-06-13..19** (cron removed during systemd migration; ij_jobs frozen at Jun 18 02:30). Fixed 2026-06-19: ingest timer re-added. If ij_jobs goes stale again, check `systemctl status anofm-ingest.timer` + `/opt/ACTIVE/INFRA/LOGS/ingest_anofm.log`.

---

## Campaign Variants (Production on raspibig)

| Campaign | Script | Audience | Cap | Status |
|----------|--------|----------|-----|--------|
| **ANOFM_ANGAJATORI** | `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/campaign_anofm_angajatori.py` | 1,470 businesses | 150/day | ✅ Live |
| **PRIMARII** | `/opt/ACTIVE/EMAIL/CAMPAIGNS/PRIMARII/primarii.py` | 2,904 mayors | 50/day | ✅ Live |
| **FACTORY_RO** | `/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_RO/factory.py` | 728 factories | 50/day | ✅ Live |
| **CANDIDATE_BROADCAST** | `/opt/ACTIVE/EMAIL/CAMPAIGNS/CANDIDATE_BROADCAST/candidate_broadcast.py` | 3,668 candidates | 10/day | ✅ Live |

### CANDIDATE_BROADCAST (added 2026-06-19)

"Thank you — we received your CV" email (English) to the candidate base (`fw_candidates`, deduped → 3,668 emails). Announces Telegram bot (`t.me/interjob_apply_bot`), WhatsApp group (`chat.whatsapp.com/DvnchNG3vYBLnLuqY3DW9K`), Facebook group (`facebook.com/groups/3115280525381395`). Sender: Elena Vasilescu (`elena.manpower.dristor@gmail.com`), reply-to `office@interjob.ro`. **10/day, no end date** ("until I modify").

- Wired in **3 places** (all share `DATA/sent.json` + `--daily-cap 10` → can never exceed 10/day):
  1. **Orchestrator:** `campaigns.json` entry `CANDIDATE_BROADCAST` (enabled, primary sender).
  2. **Cron:** daily `30 9 * * *` → `CANDIDATE_BROADCAST/run.sh` (flock safety-net).
  3. **Template (local source):** `ANOFM/DATA/TEMPLATE EMAIL WORKERS/email_candidate.txt` → deployed to `CANDIDATE_BROADCAST/TEMPLATES/email_candidate.txt`.
- To change rate: edit `daily_cap`/`extra_args` in `campaigns.json` + `run.sh`, restart orchestrator. To pause: `"enabled": false` + remove cron. Backup: `campaigns.json.bak_20260619_candbcast`.

**Orchestrator:** `campaign-orchestrator.service` (systemd, `active (running)`, `Restart=on-failure` via drop-in `/etc/systemd/system/campaign-orchestrator.service.d/restart-policy.conf`). Config: `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json`. State: `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaign_orchestrator_state.json`. Singleton via `fcntl.flock` on `campaign_orchestrator.lock` (writes MainPID). (Legacy `email-orchestrator.service` does NOT exist — do not reference it.)

**Governor task DISABLED 2026-06-19:** `/opt/ACTIVE/INFRA/GOVERNOR/tasks/campaign_orchestrator_start.json` `enabled:false` (was starting a second orchestrator at 08:00 Mon-Fri → flock conflict → systemd crash-loop). systemd is the SOLE supervisor. Do NOT re-enable the governor task.

### ANOFM_ANGAJATORI audience — auto-refresh (fixed 2026-06-19)

- `anofm_angajatori_rebuild.py` regenerates `DATA/anofm_angajatori_dedup.csv` from the latest scraper CSV 3x daily (timer `anofm-audience-rebuild.timer`, 09:10/13:10/16:40).
- One row per company (top job by `positions_available`), business email only (no free providers), excludes DNC + `sent.csv`. Atomic write + timestamped backup (`anofm_angajatori_dedup.csv.bak_*`).
- Audience grows with each scrape (e.g. 1,470 → 1,529 on 2026-06-19 after first rebuild). Sorted by positions DESC so highest-value employers send first.
- Scraper auto-feed (`anofm_targets.py --feed-new`) still inserts new employers into `romania_emails.contacts` (~545K anofm pool) for cross-campaign use; the campaign itself reads the curated dedup CSV.

---

## Scripts in CODE/ — Reference Index

All scripts are **read-only local copies.** Production versions live on raspibig at `/opt/ACTIVE/EMAIL/CAMPAIGNS/`.

### Campaign Scripts (3 Live)

| Script | Audience | CSV Rows | Daily Cap | Status |
|--------|----------|----------|-----------|--------|
| **anofm.py** | Business angajatori | 1,470 | 150 | ✅ Live |
| **factory.py** | Factories (CUI) | 728 | 50 | ✅ Live |
| **primarii.py** | Mayors | 2,904 | 50 | ✅ Live |
| **sme.py** | SME <50 empl | ~4,000 | — | Ready |
| constructii.py | Construction | ~1,800 | — | Reference |
| horeca.py | Hospitality | ~1,200 | — | Reference |
| productie.py | Manufacturing | ~1,600 | — | Reference |
| transport.py | Transport | ~900 | — | Reference |

### Utility Scripts

- **sender.py** — Brevo + Gmail SMTP client (shared module)
- **export_at.py** — AT export (JSON/CSV/XLSX formats)
- **enable_export.py** — Toggle export flag in campaigns.json
- **disable_necalificati.py** — Filter unskilled jobs from CSV

### Code Pattern

```python
sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED")
import sender

BASE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/[CAMPAIGN_NAME]")
CSV_FILE = BASE / "DATA" / "[name]_dedup.csv"
DNC_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt")

def main():
    for row in csv.DictReader(open(CSV_FILE)):
        if row['email'] in dnc or row['email'] in sent:
            continue
        sender.send_brevo(BREVO_KEY, SENDER, SENDER_NAME, to, subject, body)
```

### CLI Arguments (All Scripts)

```bash
--dry-run           # Print instead of send
--limit N           # Max N emails per run
--daily-cap N       # Skip if already sent N today
--delay SECONDS     # Wait between emails (default: 8)
```

Example:
```bash
python3 anofm.py --dry-run --limit 10 --delay 2
python3 factory.py --limit 50 --delay 480
```

### Deployment Workflow

1. Edit locally: `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ANOFM\CODE\`
2. Test on raspibig: `python3 [script].py --dry-run --limit 5`
3. Deploy: Copy to `/opt/ACTIVE/EMAIL/CAMPAIGNS/[CAMPAIGN]/`
4. Restart: `sudo systemctl restart campaign-orchestrator.service` (NOT `email-orchestrator`)
5. Verify: `systemctl status campaign-orchestrator.service` + dashboard port 8100 (ab-dashboard) / unified-dashboard

## ram_monitor note (verified 2026-06-19)

`/opt/ACTIVE/INFRA/SKILLS/ram_monitor.py` restarts "high-priority" services when swap > 80% AND RAM > 70% (threshold raised from 50% → 80% on 2026-06-19). `anofm-scraper.service` was REMOVED from `HIGH_PRIORITY_SERVICES` — do NOT re-add it: the scraper is an 8-9 min oneshot and kill-restarting it mid-run prevented CSV output. Backups: `ram_monitor.py.bak_20260619*`. Swap root cause was idle `llama-server` (qwen3-4b, `--no-mmap`, 3.9GB swapped) — left in place; threshold change stops the thrash.

---

## Deployment Handoff

See **HANDOFF_2026_06_18.md** for:
- Full infrastructure map (3 machines)
- Campaign config (campaigns.json)
- Email orchestrator details
- Monitoring + alerts
