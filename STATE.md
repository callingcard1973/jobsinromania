# STATE.md — Live Infrastructure Status

**Last updated: 2026-07-12** (ANOFM contact backfill complet; ingest fix; export Anca Popian admin)

---

## 2026-07-12 SESIUNE ANOFM CONTACTS

| Item | Rezultat |
|------|----------|
| Backfill contacte ANOFM | 6808/6986 joburi updatate (97.5%). Inainte: 7 cu telefon. Dupa: 6622 cu telefon (94.7%), 6728 cu email (96.2%) |
| Script | `/opt/ACTIVE/ANOFM_DATA/backfill_anofm_contacts.py` (raspi .20) — sweep API `mediere.anofm.ro`, 75 pagini, ~3 min |
| Ramase fara contact | 178 joburi — nu apar in API curent (expirate pe ANOFM, inca active in DB) |
| Fix ingest | `/opt/ACTIVE/INTERJOB/ingest/ingest_anofm.py` — UPDATE bloc extins cu `phone_2`, `email_2`, pattern `NULLIF(%s,'')`. Backup: `ingest_anofm.py.bak_20260712_contacts` |
| Backfill job_description | 1484 joburi updatate din CSV `anofm_jobs_20260712_122500.csv` |
| Export Anca Popian | `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 07 2026\INTERJOB MANPOWER\DATA\ANCA POPIAN\anca_popian_admin_20260712.csv` — 154 joburi (149 admin fizic Buc+Ilfov + 5 online/remote tara); 148 cu email, 143 cu telefon |
| ij_jobs active | 6993 (raspi anofm_db) |
| ANOFM online/remote | Practic inexistent in ANOFM — 0 joburi marcate remote in descriere; 15 cu "online/remote/domiciliu" in titlu dar majority irelevante (ingrijitor, vanzator la domiciliu) |

**Last updated: 2026-06-12 ~17:45 UTC** (Complete: llama-server fixed, crons 36→0 failures, FastAPI routes deployed internal-only; Caddy public proxy removed. See memories `raspibig_fix_session_2026_06_12_afternoon.md` + `fastapi_step2_deployment_2026_06_12.md`)
**Verification method: Direct psql + systemctl + plink SSH**

---

## 2026-06-19 LIVE SNAPSHOT (supersedes everything below)

Audit + remediation 2026-06-19 (~11:45 EEST). Most of the 2026-06-12 backlog was already resolved.

| Component | Status | Value |
|-----------|--------|-------|
| Load / Swap | 🟢 | load ~5, swap 5.5/8.4 GB, RAM 8.8/15 (3-day uptime, stable) |
| Failed units | 🟢 | romania-nightly **fixed** (was the only failure); padina gone |
| FastAPI | 🗑️ | **FULLY removed**. Was at `/opt/ACTIVE/FASTAPI` (interjob-api.service on :8000), NOT the wrongly-deleted `/opt/ACTIVE/INTERJOB/api`. Stopped+disabled service, disabled interjob-watchdog.timer, killed orphan workers (:8000 empty), archived `~/FASTAPI_archive_20260619.tgz`, removed dir. |
| romania-nightly | 🟢 | **Root cause fixed**: `detect_new_companies()` full-table RO scan (263,631 rows) exceeded global `statement_timeout=10min`. Patched `/opt/ACTIVE/DB/romania_nightly.py` (line ~455): `SET statement_timeout=0` on source session before named cursor. Backup `.bak_20260619`. Manual re-run passed the old failure point, ran 7+ min clean. |
| Hermes agent | ✅ | KEEP (user decision). PID 1445, `~/.local/bin/hermes gateway`. Intentionally retained. |
| Email campaigns | 🟢 | Healthy. 14 enabled, all completed today (last_reset 2026-06-19). PRIMARII actively sending (gentle 3-min pace, last SENT 11:45). FACTORY_RO + DEFICIT_* + SILOZURI + EXPORT_* all ran. `total_sent_today=0` is an **unwired cosmetic counter** (real counts in dated per-campaign logs `/opt/ACTIVE/INFRA/LOGS/campaigns/*_20260619.log`) — not a breakage. |
| Bounce cleaner IMAP | 🟢 | fruitnature4@gmail.com IMAP **AUTH OK** (was failing; app password `mosvghiaptwcxasr` works). |
| Junk dirs / governor.log | 🟢 | Already clean (junk dirs gone, governor.log 0 bytes). |
| Crontab | 🟢 | tudor crontab 5 entries — NOT a wipe; jobs migrated to **34 systemd timers** + `/etc/cron.d/` (certbot, madr_scraper, mautic, opendata-*, task_queue, etc.). |
| New packages (rabbitmq/clamav) | 🟢 | Not listening (5672/15672/3310 empty) — no conflict. |

---

## 2026-06-12 LIVE SNAPSHOT (stale — superseded by 2026-06-19 above)

| Component | Status | Value |
|-----------|--------|-------|
| Reboot | ✅ | Booted 11:01; shell switched to zsh+oh-my-zsh |
| Load | 🟢 | **6.42** (down from 14.48 after llama-server restart-loop fix) |
| Swap | 🟢 | **2.9/8.4 GB** (down from 6.3; 451 MiB RAM free) |
| Monitor crons | 🟢 | **0 failures** (down from 36 after monitor rewrite + 40-cron audit) |
| Failed units | 🟡 | 2 (padina-tracker, romania-nightly) — still need proper disable; 9 loopers pending triage |
| llama-server | 🟢 | Active, `/health` returns ok, model loading from /mnt/hdd path |
| Crontab | ✅ | **40 entries**; all today's crons ran clean (press_review 08:51, roundup 09:01, wp_publisher 11:01, fb_jobs 11:30, cv_pipeline, backup_sync 12:43) |
| ij_jobs active | ✅ | 10,701 (2026-06-12 psql) |
| FastAPI | 🗑️ | DELETED 2026-06-19 — no business value (jobs published via crons) |
| Hermes agent | ⚠️ | Nous Research gateway LIVE (pid 1512, installed ~Jun 8 via curl\|bash) — pending keep/remove decision |
| New packages today | ⚠️ | rabbitmq-server (+mgmt plugin), clamav, htop/ncdu/tree/tmux/screen/zsh — verify listeners |
| PRIMARII campaign | ✅ | 16 sent today (stopped at 16/50 — investigate); cron.log path typo |
| FACTORY_RO campaign | ⚠️ | **LIVE-SENDING** — 20 sent today; cron 09:00 exists WITHOUT flock/log; memory said approval-pending |
| Orchestrator 24/7 | ⚠️ | Running (pid 246748), cycling 9 sectors, total_sent_today: 0 |
| Bounce cleaner | ⚠️ | Working (dnc_list 4,497) but **fruitnature4@gmail.com IMAP AUTH FAILED** |
| governor.log | ⚠️ | 41 MB, no rotation |
| Junk dirs | ⚠️ | Literal `D:` (21M) and `C:\Users\apami\...` (9.2M) dirs in /home/tudor and /opt/ACTIVE; 3.7G raspibig_final.tar in home |

---

## Infrastructure Snapshot

| Component | Status | Value | Last Check |
|-----------|--------|-------|-----------|
| **PostgreSQL** | ✅ Live | 15.15 (Debian) | 2026-06-07 |
| **interjob_master DB** | ✅ Live | 528 tables, 8,815+12,107 jobs | 2026-06-07 |
| **ij_jobs (active)** | ✅ Live | 8,815 / 12,107 total | 2026-06-07 psql |
| **ij_companies** | ✅ Live | 5,162 rows | 2026-06-07 |
| **fw_candidates** | ✅ Live | 6,613 rows | 2026-06-07 |
| **fw_jobs** | ✅ Live | 5,542 rows | 2026-06-07 |
| **Crontab entries** | ✅ Active | 30+ jobs (ANOFM, EURES, news, CV pipeline, etc.) | 2026-06-07 |
| **Systemd units failed** | ⚠️ Pre-fix: 7 | Post-fix expected: 5 | 2026-06-07 (pre-deployment) |
| **Swap usage** | ⚠️ High | 6.4 GB / 8.4 GB total | 2026-06-07 |
| **PG Password** | ✅ Found | `~/.pgpass` (mode 600) | 2026-06-07 |
| **cPanel token (K9AT)** | ✅ Valid | 200 AUTH OK vs UAPI | 2026-06-07 |
| **cPanel token (MK0W)** | ❌ Dead | 403 access denied | 2026-06-07 |

---

## Database Counts (2026-06-07)

**Verified via:**
```
psql -h 127.0.0.1 -p 5432 -U tudor -d interjob_master -c "SELECT count(*) FROM ij_jobs WHERE status='active'"
```

| Table | Count | Notes |
|-------|-------|-------|
| ij_jobs (total) | 12,107 | All statuses |
| ij_jobs (active) | 8,815 | Live / posted |
| ij_companies | 5,162 | Employer profiles |
| ij_cities | ? | (not re-counted) |
| ij_sectors | ? | (not re-counted) |
| fw_jobs | 5,542 | Farm work positions |
| fw_companies | ? | (not re-counted) |
| fw_candidates | 6,613 | CV profiles |
| fw_websites | 14 | Domain config |
| applications | 26 | Job applications |
| job_posts | 2,374 | Social / WP posts |
| **Total tables** | **528** | Entire schema (2026-06-07) |

---

## Systemd Service Status (2026-06-07)

**Failed units BEFORE deployment (2026-06-07 05:00 UTC):**

1. ❌ `postgresql-backup.service` — Timeout at 2h (dump takes ~22min, throttled 80% CPU)
2. ❌ `backup-sync.service` — SHA256 verify timeout 180s (10GB+ files on slow raspi)
3. ❌ `cv-matcher.service`
4. ❌ `cv-parser.service`
5. ❌ `danted.service`
6. ❌ `email-auto-organize.service`
7. ❌ `email-sorter.service`

**Fixes deployed 2026-06-07 05:20 UTC:**
- postgresql-backup: `TimeoutStartSec` 2h → 6h, remove `CPUQuota=80%`
- backup-sync.py: Verify rewritten (instant size check, SSH timeout → warning, Telegram parse_mode fixed)

**Expected post-fix:** 5 failed units (postgresql-backup + backup-sync → passing)

---

## Cron Status (2026-06-07)

**Active crons (30+ entries):**

| Job | Schedule | Status | Last Run |
|-----|----------|--------|----------|
| ANOFM ingest | 02:30 daily | ✅ Active | 2026-06-06 02:30 |
| ANOFM daily report | 04:00 daily | ✅ Active | 2026-06-06 04:00 |
| EURES scraper | 03:00 Mon only | ✅ Active | 2026-06-03 03:00 |
| Press review (WP + FB) | 08:50 daily | ✅ Active | 2026-06-06 08:50 |
| City news aggregator | 09:30 daily | ✅ Active | 2026-06-06 09:30 |
| Daily roundup | 09:00 Mon-Fri | ✅ Active | 2026-06-06 09:00 |
| FB jobs by page | 11:30 Mon-Fri | ✅ Active | 2026-06-06 11:30 |
| CV pipeline | 10:00 daily | ✅ Active | 2026-06-06 10:00 |
| Application fetcher | 09:30 daily | ✅ Active | 2026-06-06 09:30 |
| WP EURES publish | 11:00 daily | ✅ Active | 2026-06-06 11:00 |
| WP ANOFM publish | 13:00 daily | ✅ Active | 2026-06-06 13:00 |

*Full crontab has 25+ additional entries. See CLAUDE.md section "CRONTAB RASPIBIG" for complete list.*

---

## Deployment Status (2026-06-07)

| Phase | Status | Details |
|-------|--------|---------|
| **FastAPI Step 1** | ✅ Complete | Scaffold: main.py, config.py, db.py, routes/, schemas/, services/ |
| **systemd backup fixes** | ✅ Deployed | postgresql-backup timeout 6h, backup-sync verify rewrite |
| **PostHog integration** | ✅ Ready | `api/services/analytics.py` template in PLAN docs |
| **FastAPI Step 2** | ⏳ Pending | Implement GET /jobs, /companies, /applications routes |
| **Weekly skills sync** | ⏳ Pending | Cron: Sunday 4 AM UTC, 1,557 skills across 3 machines |

---

## Resource Usage (2026-06-07)

| Resource | Usage | Capacity | % Used | Notes |
|----------|-------|----------|--------|-------|
| RAM | ? | ? | ? | Not measured 2026-06-07 |
| Swap | 6.4 GB | 8.4 GB | 76% | High (ollama × 2, java, droid, firefox) |
| Disk | ? | ? | ? | Not measured 2026-06-07 |

**Action:** Monitor before scaling FastAPI on same host.

---

## Credentials Status (2026-06-07)

| Credential | Status | Location | Last Verified |
|-----------|--------|----------|----------------|
| PG password | ✅ Found | `~/.pgpass` | 2026-06-07 |
| cPanel token K9AT | ✅ Valid | K9AT... (200 AUTH) | 2026-06-07 |
| cPanel token MK0W | ❌ Dead | MK0W... (403 denied) | 2026-06-07 |
| WP sites.env | ✅ Valid | `/opt/ACTIVE/SCRAPERS/.../wp_sites.env` | 2026-06-04 |
| A2 env | ✅ Valid | `/opt/ACTIVE/SCRAPERS/.../A2HOSTING/.env` | 2026-06-04 |

---

## Next Steps

1. **Verify backup fix (post-deployment):** `systemctl status postgresql-backup backup-sync --no-pager` — expect both active/running
2. **FastAPI Step 2:** Implement routes (/jobs, /companies, /applications) with filtering
3. **Schedule weekly sync:** cron Sunday 4 AM UTC for weekly_skills_sync.py
4. **PostHog events:** Wire up tracking for job creation, deployment, posting events
5. **Monitor swap:** Alert if > 80%, consider reducing ollama instances or moving to dedicated box

---

*Maintained by Claude. Update after major changes (deployments, config updates, data migrations).*
