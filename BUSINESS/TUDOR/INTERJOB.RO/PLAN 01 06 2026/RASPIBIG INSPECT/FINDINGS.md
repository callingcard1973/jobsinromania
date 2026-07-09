# RASPIBIG INSPECT — FINDINGS

**Date:** 2026-07-02 | Host: raspibig 192.168.100.21 | Harness: raspibig-deep-inspect
**(Previous round 2026-06-26 — most CRITICAL items now RESOLVED, see below)**

## Host health — OK (load high but legitimate)
- Load avg **22.98 / 23.86 / 23.14** on 4 cores (~6x). NOT a restart storm this time.
- Swap **2.9Gi/8.4Gi (35%)** — recovered from 92% on 06-26.
- RAM 10Gi/15Gi used, 5.1Gi available. Disk / at 47% (103G/235G) — OK.
- Load drivers = real workload: `ollama runner` (qwen, 177% CPU) + ~9 concurrent EURES Playwright/Firefox scrapers (eures-scraper/nordic/western/expansion all parallel). Lever if needed: stagger EURES scrapers, not systemd throttles.

## Systemd — CLEAN
- `list-units --state=activating,failed` = **0 units**. No restart loops, no failed units.
- Only unit with lifetime restarts: `llm-email-processor` (43, already self-throttled via drop-in, currently stable).
- **All five 06-26 offenders RESOLVED:** llama-server (unit removed), eures_orchestrator (0 restarts, clean exit), universal-bounce-monitor (Restart=no), romania-nightly (correct oneshot), cv-matcher (no loop).

## Crons / timers / data freshness — mostly healthy
- **postgresql-backup RESOLVED** — ran 02:32 today, produced `/mnt/hdd/BACKUPS/postgresql/interjob_master_20260702_023227.sql.gz` (7.7GB gz), rotated old. (Doc-reconciler flagged "no log" but the backup FILE exists — logs land elsewhere/journald, so this is OK, not FALSE.)
- **monitor_crons FRESH** — cron_status.json updated 13:00 today (was 8 days stale on 06-26). 25 jobs checked, 2 flagged.
- **ij_jobs FRESH** — 19,989 rows, max updated_at 2026-07-02 13:00 (was frozen 06-24). Active jobs = 6,688 (below 8–12K target — investigate expiry/ingest yield).
- **fw_candidates** 3,881, fresh (08:11 today).
- **land_offers = 122** (was 0 on 06-26 — loader now produces rows, but low volume for a nightly pipeline).

### Cron minor issues
| Job | Issue |
|-----|-------|
| eures_cron.sh | logs to `/tmp/eures_cron.log` (ephemeral, lost on reboot) — move to /opt/.../LOGS |
| telegram_spam_cleanup.py | daily 06:00, log file never created — silent success or silent crash, unknown |
| viaprofi_monthly.py | `/opt/ACTIVE/FURNIZORI/scrapers/REPORTS/` dir missing → false FAIL in monitor. `mkdir -p` fixes |

## Email campaigns — FULL INSPECTION (2026-07-02)

**Config:** `campaigns.json` = **52 campaigns, 27 enabled**. Supervisor `campaign_orchestrator_24_7.py` PID 2007973 (since Jul01), no loop.

### Enabled campaigns — send state today (log mtime / activity)
| Campaign | Activity today | Verdict |
|----------|----------------|---------|
| PRIMARII | mt 08:00, remaining=0 | EXHAUSTED-but-enabled |
| FACTORY_RO | mt 08:00 | sending |
| SME_DEFICIT | mt 15:44, active | SENDING |
| DEFICIT_CONSTRUCTII | no LOG_FILE env | logs elsewhere; last sent Jul01 |
| DEFICIT_HORECA/PRODUCTIE/TRANSPORT | no LOG_FILE env | sending (per inspector), path mismatch |
| ANOFM_TUDOR | no activity | STALE DUP — real ANOFM on raspi (.20) |
| EXPORT_AT | mt 08:00 | sending |
| BDA_ARHITECTI | relaunch every ~8min after limit=15 | LOOPING |
| EURO_DEALERS_FRANCE/GERMANY/SOUTHCENTRALEU | mt 08:00 | sending |
| CANDIDATE_BROADCAST | mt 10:08, active | SENDING |
| SUPERMARKETURI | mt 11:30, eligible=0 | EXHAUSTED stages |
| COOP_EXPORT | mt 12:40, 31 lines | SENDING (most active) |
| EURES_OUTREACH | no sends ("Brevo publish not implemented") | BROKEN — 0 delivered |
| SILOZURI_CEREALE_11JUD | mt 08:00 | sending (Brevo) |
| SILOZURI_CEREALE_11JUD_GMAIL_x3 | eligible=0 | EXHAUSTED-but-enabled |
| SONOMA_AGENTII/G1/G2/G3 | mt 08:00–10:25 | sending |
| SONOMA_BREVO_BPPLTD/FACTORYJOBS | mt 08:37, 19 lines | SENDING |

**Enabled but effectively idle/broken:** ANOFM_TUDOR (dup), EURES_OUTREACH (unimplemented send), BDA_ARHITECTI (looping), PRIMARII + SILOZURI_CEREALE_GMAIL×3 + SUPERMARKETURI (audience exhausted).
**25 disabled** (correct): EXPORT_PEPENI×6, BG_*, RO_*, old SILOZURI×7, SONOMA_FAB×3, NECALIFICATI, ANOFM_ANGAJATORI, VIAPROFI.

### Dashboard 8096 — root cause + FIX APPLIED
- Root cause: `unified-dashboard.service` runs `UNIFIED/dashboard.py`; the index page renders BOTH live orchestrator campaigns AND the dead legacy `UNIFIED/configs/*.json` (DB-backed, send_log tables frozen since April) → "April 2026" ghosts. `daily_counts` in `campaign_orchestrator_state.json` is empty, so no live per-campaign send numbers render.
- The live 52-campaign truth already exists at **`:8096/all-campaigns/`** (reads `campaigns.json` via `/api/orchestrator/status`).
- **SECURITY LEAK FOUND + FIXED:** `/api/orchestrator/status` returned every campaign's `env` in plaintext (BREVO_API_KEY, GMAIL_APP_PASSWORD, SMTP keys) on LAN-bound `0.0.0.0:8096`. Patched `bp_orchestrator.py` to redact KEY/PASSWORD/TOKEN/SMTP_USER/SECRET (backup `.bak_20260702`), restarted service — verified 48 fields now `***REDACTED***`, zero plaintext keys.
- **Still open (display):** legacy April configs still shown on `:8096/` root; `daily_counts` not persisted so no live send tallies. Decision pending.

## (archived) Email campaigns — supervisor alive, several dead/exhausted entries
- Supervisor `campaign_orchestrator_24_7.py` PID 2007973 (since Jul 01), no loop. 52 campaigns, 28 enabled.
- **Dashboard 8096 STILL STALE** — returns April 2026 old campaign set; the 52 current campaigns are invisible. Persistent known gap.
- **Sending today (confirmed):** DEFICIT_HORECA/PRODUCTIE/TRANSPORT, EXPORT_AT, EURO_DEALERS x3, COOP_EXPORT, SILOZURI_CEREALE_11JUD (Brevo), CANDIDATE_BROADCAST, SONOMA (AGENTII/G1/G2/G3/BREVO_BPPLTD/BREVO_FACTORYJOBS), BDA_ARHITECTI.
- **Dead/broken enabled campaigns:**
  - **ANOFM_TUDOR — STALE DUPLICATE, not lost capacity.** ANOFM moved to raspi (.20); the real orchestrator runs there daily 09:00 (verified 2026-07-02: 67 sends across ELECTRIC/BUILD/YAHOO/FACTORY/WAREHOUSE, HORECA 200 queued). The raspibig ANOFM_TUDOR entry is a dead leftover pointing at April-era `UNIFIED/run_anofm.sh` — should be **disabled on raspibig** to prevent any double-send, not "fixed".
  - **EURES_OUTREACH — zero sends.** Entry points at the data-pipeline script ("Brevo publish not implemented — skipping"). 150/day configured, 0 delivered.
  - **BDA_ARHITECTI looping** — hits daily limit 15 then relaunches every ~8 min (749 log lines/day). Rate-limit risk, wasted cycles.
- **Exhausted but still enabled:** PRIMARII (2,823 sent, remaining=0), SILOZURI_CEREALE_11JUD_GMAIL_x3 (eligible=0), SUPERMARKETURI (both stages eligible=0).
- DEFICIT_CONSTRUCTII — no activity today (log-path/env mismatch, last sent Jul01).

## Docs reconciliation
- **Resolved since 06-26:** llama loop, swap storm, ij_jobs refresh, pg-backup, cron monitor freshness.
- **Still STALE/FALSE:**
  - ROOT CLAUDE.md "monitor_crons alerts via email + Telegram" — Telegram env vars NOT set → alert delivery non-functional (JSON written, no push). FALSE.
  - Dashboard 8096 "live" — endpoint HTTP 200 but serves deprecated April data. STALE.
  - ROOT CLAUDE.md cron count "37 passing" — 34 active now. Minor drift.
- **Junk dir still present:** `/home/tudor/D:\MEMORY\OPTIMIZE TOKENS\logs` — flagged 06-26, never archived.

---

## Actions applied 2026-07-02 (this session)
- **Dashboard secret leak FIXED** — redacted env in `/api/orchestrator/status`, restarted `unified-dashboard.service`; 48 fields `***REDACTED***`, 0 plaintext keys. Backup `bp_orchestrator.py.bak_20260702`.
- **campaigns.json cleaned** (backup `campaigns.json.bak_20260702`), orchestrator restarted (enabled 27→20, verified):
  - Disabled: PRIMARII, ANOFM_TUDOR (raspi dup), SUPERMARKETURI, EURES_OUTREACH (broken send), SILOZURI_CEREALE_11JUD_GMAIL ×3 (audience exhausted).
  - **BDA_ARHITECTI loop FIXED** — restart_delay 480s→86400 (480s was the exact 8-min relaunch cause).
- **raspi (.20) rebooted** at user request — back up clean: 0 failed units, ANOFM timers scheduled, 10 crons intact, PostgreSQL active.
- **#1 Dashboard root now shows LIVE view** — `:8096/` 302→`/all-campaigns/` (reads campaigns.json); legacy April DB configs moved to `/legacy`. Patched `bp_pages.py` (backup `.bak_20260702`), restarted service, verified.
- **#3 monitor_crons Telegram alerts FIXED** — added `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (token from live reply-classifier service, chat 547047851) to the `*/30` cron line. Test message delivered (ok:true).
- **#4 Junk dir archived** — `D:\MEMORY\OPTIMIZE TOKENS\logs` (single literal-backslash dirname) → `/home/tudor/JUNK_ARCHIVE_20260702/`; no residual `D:/MEMORY` dirs left.
- **#2 Exhausted campaigns — NO refresh possible.** PRIMARII (2,823 sent = full ~2,904 primarii universe; CSV 2,672 fully consumed) and SILOZURI_CEREALE_11JUD_GMAIL×3 (eligible=0) have their entire target universes contacted. Kept disabled — re-enabling would re-spam contacted addresses. Needs a genuinely new lead source to refresh, not a CSV swap.

## Ranked proposals (impact × effort) — remaining

1. **Disable ANOFM_TUDOR on raspibig** — stale duplicate; real ANOFM runs on raspi (.20), verified sending today. Disabling prevents double-send risk. LOW effort / removes a false gap.
2. **Stop BDA_ARHITECTI relaunch loop** — add "no relaunch after daily-limit" guard. MED impact / LOW effort.
3. **Disable exhausted enabled campaigns** (PRIMARII, 3× SILOZURI_CEREALE_GMAIL, SUPERMARKETURI) until CSVs refreshed. LOW impact / LOW effort.
4. **EURES_OUTREACH** — either implement the Brevo send step or repoint entry to a real sender; otherwise disable to stop false "150/day". MED / MED.
5. **Fix/deprecate dashboard 8096** — repoint to live campaigns.json or retire it. MED visibility / MED.
6. **Set monitor_crons Telegram env** (TOKEN+CHAT_ID) so alerts actually deliver. MED / LOW.
7. **Cron log hygiene** — move eures_cron.sh off /tmp; `mkdir -p` viaprofi REPORTS/; confirm telegram_spam_cleanup runs. LOW / LOW.
8. **Archive junk dir** `/home/tudor/D:\MEMORY\OPTIMIZE TOKENS\logs`. LOW / LOW.
9. **Investigate ij_jobs active=6,688** (below 8–12K) and **land_offers=122** (low for nightly). MED intel / MED.
