# STATE.md — Live Infrastructure Status

**Last updated: 2026-06-07 07:58 UTC**  
**Verification method: Direct psql + systemctl + plink SSH**

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
