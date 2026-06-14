# RASPIBIG INSPECTION — 2026-06-13 (Verification Round)

## Status after handoff fixes + verification

### ✅ Verified Working
- **ingest_anofm.py** — Fix applied and running (380 jobs inserted in last run)
- **Hermes xAI key** — Installed on both machines + `grok` wrapper created
- **wordpress_publisher.py** — Reconnect logic present

### 🔴 Still Critical
- **10+ services in restart loop** (same as Jun 12):
  - seap-scraper, interjob-governor, a2-email-monitor, fb_messenger, whatsapp-backend, etc.
  - Root cause not yet resolved (WorkingDirectory or config issues)

### FB Jobs
- Script now lives at `/opt/ACTIVE/FB/fb_jobs_post.py`
- Page 61590749303510 token issue still open

### Next Actions (ranked)
1. Clean junk files + 3.7GB tar in /home/tudor
2. FB jobs page 61590749303510 — add missing token to fb_jobs_by_page.py
3. Hermes xAI — add credits at console.x.ai
4. Update CLAUDE.md with real current state


## Fixes Applied (2026-06-13 — session 2)

### a2-email-monitor — 2,199 restarts → active
- **Root cause:** `cat >> heredoc` injection artifact left 22 lines of bash code embedded in Python source (`/opt/ACTIVE/email_monitor/monitor.py` lines 194-215). Bash shell commands (`echo`, `cat >>`) + truncated Python function caused SyntaxError on every start.
- **Fix:** Truncated file to line 193 (natural `if __name__ == "__main__"` end). Backup at `monitor.py.bak_*`.
- **Verified:** `python3 -m py_compile` syntax OK → `systemctl restart` → `active`.

### redis-cache-monitor — loop on PG health=False
- **Root cause:** `Restart=always` + script exits naturally when PostgreSQL health check fails (PG under load or temporarily unavailable). Caused permanent restart storm when PG busy.
- **Fix:** Drop-in `/etc/systemd/system/redis-cache-monitor.service.d/no-loop.conf`: `Restart=on-failure`, `RestartSec=300`, `StartLimitBurst=3` / `StartLimitIntervalSec=900`.
- **Effect:** Only restarts on actual failure (non-zero exit); 5 min between retries; max 3 per 15 min window.

### unified-dashboard — 306 restarts → throttled
- **Fix:** Drop-in `/etc/systemd/system/unified-dashboard.service.d/restart-limit.conf`: `StartLimitBurst=3` / `StartLimitIntervalSec=600`, `RestartSec=120`.
- **Effect:** Service never stopped; restarts capped at 3 per 10 min, 2 min between retries.

---

## Fixes Applied (2026-06-13 verification)

- **seap-scraper.service** — Fixed WorkingDirectory (`/opt/ACTIVE/SEAP_BIDDING` → `/opt/ACTIVE/SEAP`), then disabled
- **interjob-governor.service** — Disabled (was exiting with code 1)

Restart storm reduced. Remaining activating units: 9 (verified 2026-06-13 05:35)

---

## 🔴 LIVE STATE 2026-06-13 05:35 (verified)

**Load: 30.07** (critical — romania-nightly + postgres COPY running simultaneously)
**RAM: 68 MiB free** of 15 GiB (12 GiB used)

### Service states (verified via `systemctl is-active`):

| Service | State | Notes |
|---|---|---|
| a2-email-monitor | activating (loop) | exits code 1 — script error |
| droid-daemon | ✅ active | OK |
| hermes | ✅ active | gateway running, no inference (no credits) |
| redis-cache-monitor | activating (loop) | "ERROR: Unknown issue" then exits |
| unified-dashboard | activating (loop) | **306 restarts** — major CPU drain |
| whatsapp-backend | ✅ active | node/WhatsApp gateway OK |
| anofm-scraper | activating (starting) | USB remount in progress |
| padina-tracker | failed | disabled but not cleared |
| romania-nightly | activating (starting) | postgres COPY running 05:31 |

### Top memory hogs:
- `postgres: interjob_master COPY` — 9.8% RAM (1.6 GB) since 04:27
- `postgres: checkpointer` — 6.9% RAM (1.1 GB)
- `postgres: tudor romania UPDATE` — 4.4% RAM (737 MB) — romania-nightly
- `node index.js` (N8N + WhatsApp) — 3.5% + 3.4% RAM

---

## Fixes Applied (2026-06-14 — raspi post-reboot cleanup)

### failover-monitor.service — inactive after reboot → active + enabled
- **Root cause:** Unit file had stale paths (`/opt/SKILLS`, `/opt/venv/bin/python3`) — fix from previous session only updated in-memory, not on disk.
- **Fix:** Rewrote `/etc/systemd/system/failover-monitor.service` with correct paths (`WorkingDirectory=/opt/ACTIVE/INFRA/SKILLS`, `ExecStart=/usr/bin/python3 /opt/ACTIVE/INFRA/SKILLS/failover_manager.py --monitor`). Re-enabled + started.
- **Verified:** `systemctl is-active failover-monitor` → `active`

### hw_monitor.sh — dead cron `/tmp/hw_monitor.sh` → permanent
- **Root cause:** Crontab called `/tmp/hw_monitor.sh` which is wiped on every reboot. Script didn't exist anywhere on disk — silently failing every hour.
- **Fix:** Created `/opt/ACTIVE/INFRA/hw_monitor.sh` (memory + disk + temp snapshot, 500-line rotation). Updated crontab: `/tmp/hw_monitor.sh` → `/opt/ACTIVE/INFRA/hw_monitor.sh`.
- **Verified:** Script runs, outputs to `/opt/LOGS/hw_monitor.log`.

### heartbeat.log — `/tmp` path → permanent
- **Root cause:** `server_heartbeat.py` cron redirected to `/tmp/heartbeat.log` — wiped on reboot.
- **Fix:** Updated crontab redirect to `/opt/LOGS/heartbeat.log`.

### Connectivity verified
- laptop → raspi: ✅ (plink direct)
- raspibig → raspi: ✅ (ssh via hop, no host key prompt)

---

### Priority actions:
1. **unified-dashboard** — disable immediately (306 restarts = pure CPU waste): `systemctl disable --now unified-dashboard`
2. **padina-tracker** — clear failed state: `systemctl reset-failed padina-tracker`
3. **a2-email-monitor** — check script, likely missing dep or config
4. **redis-cache-monitor** — check what "Unknown issue" means
5. **romania-nightly** — wait for current run to finish, then check if it should keep running
6. Load will normalize once unified-dashboard loop stops + romania-nightly finishes
