# STATE.md — D:\MEMORY Live Status

**Last updated: 2026-05-29 10:30 UTC**

---

## Queue Status

| Metric | Value | Note |
|--------|-------|------|
| Pending | 928 | 4 workers, 12-15 tasks/min |
| Completed | 979/1,351 (72%) | Since 2026-05-28 09:00 |
| Failed (old) | 428 | Needs archival before merge |
| ETA | 09:45 UTC | 2026-05-28 estimate (stale) |

---

## Service Status

| Service | Status | PID/Location | Note |
|---------|--------|--------------|------|
| email_poller | ✅ RUNNING | 137362 | Daemon, Brevo integration |
| Ollama | ✅ ACTIVE | raspibig:11434 | 107% CPU, scraper reserved |
| PostgreSQL | ✅ ACTIVE | 192.168.100.21:5432 | interjob_master, raspi synced |
| raspi | ❌ OFFLINE | 192.168.100.20 | Unreachable since 2026-05-28 08:12 UTC |
| N8N | ✅ ACTIVE | raspibig:5678 | v1.70.0, workflows imported |

---

## Scrapers Deployed

| Scraper | Status | Region | Last Run |
|---------|--------|--------|----------|
| EURES | ✅ LIVE | EU | 2026-05-28 |
| FINLAND | ✅ LIVE | FI | 2026-05-28 |
| GERMANY | ✅ LIVE | DE | 2026-05-28 |
| SWITZERLAND | ✅ LIVE | CH | 2026-05-28 |
| BULGARIA | ✅ LIVE | BG | 2026-05-17 |
| DENMARK | ✅ LIVE | DK | 2026-05-28 |

---

## Recent Deploys

| Domain | Status | Date | Note |
|--------|--------|------|------|
| agroevolution.com | ✅ LIVE | 2026-05-28 | 9,658 listings, TTFB -35% |
| expatsinromania.org | ⚠️ PARTIAL | 2026-05-23 | Phases 0-3, Phase 4 pending |
| haritina.com | ✅ LIVE | 2026-05-28 | WP Super Cache ✅ |
| mivromania.info | ✅ LIVE | 2026-05-28 | LiteSpeed Cache ✅ |

---

## SSL Expiry (A2 Hosting — Critical)

| Domain | Expires | Days | Action |
|--------|---------|------|--------|
| nepalezi.com | 2026-06-21 | 33 | **AUTO-RENEW QUEUED** |
| Other 11 | varies | <60d | Queue auto-renewal |

**Status:** Gzip ✅ (30/30), DNS ✅, PostHog async ✓

---

## Infrastructure Score: 8.2/10

- ✅ Gzip: 30/30 domains
- ✅ SSL: auto-renew queued
- ✅ DNS: baneasa39.com fixed, cifn.info removed
- ✅ WordPress: WP Super Cache + LiteSpeed Cache
- ✅ PostHog: 9 domains async (no action)
- ✅ EURES: 487 jobs tracked
- ✅ TTFB: -35% improvement (360-409ms → 133-301ms)
- ⚠️ raspi: Offline 19h (needs reboot)
- ⚠️ MADR: EPIPE memory leak on raspi
- ⚠️ expatsinromania: Phase 4 incomplete
