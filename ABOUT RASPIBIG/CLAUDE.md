# ABOUT RASPIBIG — operating reference

**Reconstructed 2026-06-25** (the canonical folder file was missing; rebuilt from sourced memory + root CLAUDE.md). Operating reference for **raspibig (192.168.100.21)** — the always-on production hub. Read before any raspibig work. Do NOT duplicate elsewhere. Verify live state (SSH + check) before claiming something exists.

---

## Role

Primary 24/7 automation + production hub. Hosts PostgreSQL, the email-campaign orchestrator, local LLM, MARM, and the bulk of crons/systemd timers. Heavy scraping is kept OFF this box (runs on raspi .20) to keep raspibig responsive. Source: `feedback_raspibig_raspi_rules`, root CLAUDE.md infra table.

## Access

- **SSH from Windows laptop (no key):** `plink -batch -pw '<pw>' tudor@192.168.100.21 "<cmd>"`. Password is in memory `raspibig_ssh_password` (redacted in GitHub-synced docs). Plink path: `C:\Program Files\PuTTY\plink.exe`. Key-based SSH (BatchMode) also works. Source: root CLAUDE.md key conventions, `raspibig_ssh_password`.
- **Always use IP `192.168.100.21`, never hostname.** ControlMaster + ControlPersist 15m active.

## Key services (sourced)

| Service | Port | Notes |
|---------|------|-------|
| PostgreSQL | 5432 | `interjob_master` DB, companies_clean ≈40.8M rows. **Version: root CLAUDE.md says 15.17** (STATE.md once said 15.15; one memory said "18" — treat 15.17 as canonical, verify live). Source: root CLAUDE.md DB line. |
| Email campaign orchestrator + dashboard | 8096 | "Campaign Command Center". Single source of truth = `campaigns.json` (loaded ONCE at startup → restart after edits). 11 campaigns, ~440/day capacity. Source: `campaign_dashboard_final_2026_06_13`, INTERJOB CLAUDE.md. |
| Local LLM (llama-coder / llama-server) | 8082 | `llama-coder.service` runs qwen3-4b; `llama-server.service` is a DUPLICATE → disabled (same model+port). llama-coder stopped 2026-06-24 to reclaim swap (still `enabled`; returns on reboot; `systemctl start llama-coder` to restore). Source: `raspibig_llama_swap_reclaim_2026_06_24`, `raspibig_cron_audit_2026_06_14`. |
| MARM memory MCP | 8011 | Systemd, auto-start, Restart=always. (Laptop 8001, raspi 8021.) Port 8011 chosen to avoid an existing :8001 conflict. Source: `marm_triple_node_2026_06_15`. |
| Ollama | 11434 | PRIMARY local LLM per ops rules. Source: `feedback_raspibig_raspi_rules`. |

Other services seen in sources (verify live before relying): n8n (5678), redis (6379), postfix, rspamd, caddy, email-poller, queue-worker, raspibig_controller_bot, Hermes/Nous gateway (KEEP per user). Source: `feedback_raspibig_raspi_rules`, STATE.md.

## /opt/ACTIVE/ layout

- Production code lives in `/opt/ACTIVE/` — **never `/home/tudor/`** for production. Source: `feedback_raspibig_raspi_rules`.
- Logs: `/opt/ACTIVE/INFRA/LOGS/` (per-campaign dated logs `campaigns/*_YYYYMMDD.log`).
- Skills sync target: **`/opt/ACTIVE/SKILLS`** — 640 Python skills, laptop is master source. Source: root CLAUDE.md skills sync.
- Cron monitor: `/opt/ACTIVE/INFRA/monitor_crons.py`. DB scripts under `/opt/ACTIVE/DB/`.

## Cron / systemd + monitoring

- Jobs run as a mix of **tudor crontab + ~34 systemd timers + `/etc/cron.d/`** (certbot, madr_scraper, mautic, opendata-*, task_queue, etc.). Crontab being short is NOT a wipe — jobs migrated to timers. Source: STATE.md 2026-06-19.
- **`monitor_crons.py`** auto-detects all active crons; alerts on failure via email (fruitnature4@gmail.com) + Telegram (@expatsinromania_news) + daily digest (08:00 UTC). Status: `/opt/ACTIVE/INFRA/LOGS/cron_status.json`; history `cron_history.log` (7-day rotation). Telegram token via env var (no hardcoded default). Source: root CLAUDE.md cron monitoring, `raspibig_cron_audit_2026_06_14`.
- As of 2026-06-14 audit: 37/37 crons passing, 0 failed systemd units. Source: `raspibig_cron_audit_2026_06_14`.

## Nightly backup window (high load)

- pg_dumpall|gzip of the whole cluster runs **00:00–03:15 UTC** (root cron `0 3 * * *` = 03:00 EEST = 00:00 UTC, `nightly_maintenance.sh`). Does NOT overlap the 06:00 UTC campaign/roundup jobs. Source: `raspibig_llama_swap_reclaim_2026_06_24`.
- Load reaches ~13 on 4 cores during this window (single disk, ~3h). Known, lower-priority. A prior "backup storm" (two overlapping backup systems on a ~112GB DB → load 8–10, swap 100%) was fixed with a shared flock lock (`/opt/ACTIVE/INFRA/LOGS/pg_backup.lock`, `flock -w 14400` serial). Source: `raspibig_backup_storm_fix_2026_06_12`.

## Coding rules (apply on this box)

- 250-line max per Python file. `#!/usr/bin/env python3`, one-liner docstring, `main()`, `if __name__ == '__main__'`.
- Async I/O (aiohttp/asyncio); wrap sync psycopg2 in `asyncio.to_thread()` when needed.
- Comments: WHY only. Error handling only at system boundaries.
- Data safety: archive before delete (SELECT count → INSERT archive → DELETE). No TODO placeholders.
- Local LLM (Ollama/llama) for routine work; Claude API only for strategic/user-facing.
- 70–80% of the system already exists — SSH and check `/opt/ACTIVE/` before writing anything new. Never recreate live DB tables. Fixes go directly to raspibig; local mirrors are snapshots only ("raspibig is authoritative").
Source: root CLAUDE.md coding standards, `feedback_raspibig_raspi_rules`, `raspibig_cron_audit_2026_06_14`.

## psql gotcha

Always pass `-h localhost` to psql via plink: `psql -h localhost -U tudor -d interjob_master -c "..."`. Without it, psql tries the Unix socket and errors "Invalid data directory for cluster". In psycopg2 set `host="localhost"` explicitly. The `~/.pgpass` entry is for user **tudor** (mode 600). Source: `feedback_psql_raspibig`, root CLAUDE.md.

## What NOT to do

1. **Never disable/remove a systemd service without telling the user first.** User was explicit. Announce, then wait for confirmation. Source: `raspibig_cron_audit_2026_06_14`.
2. **Never wrap psql/pg_dump in a shell `timeout`** — it orphans the server-side query and can deadlock a lock. Use server-side `statement_timeout` instead. Source: `laptop_db_mirror_delta_sync_2026_06_21` (MEMORY index lesson).
3. **Mind the nightly backup window** (00:00–03:15 UTC) — load ~13. Don't schedule heavy work into it. Source: `raspibig_llama_swap_reclaim_2026_06_24`.
4. **Never auto-commit/push.** Git is user-triggered only; never push secrets (local history has plaintext creds; pre-push hook blocks). Source: root CLAUDE.md GIT RULES.
5. **No secrets/PII in this file** — it is GitHub-synced. Credentials live in memory entries / `.env` on the box.
6. Keep heavy scraping on raspi .20, not here. Never deploy to A2 via SSH (cPanel only). Source: `feedback_raspibig_raspi_rules`.

---

## Gaps / uncertainties (verify live)

- **PostgreSQL version** conflicts across sources (15.17 / 15.15 / "18"). Canonical = root CLAUDE.md 15.17 — confirm with `psql -h localhost -U tudor -c "select version()"`.
- Exact current systemd-timer count and live service list drift over time — `systemctl list-timers` / `--failed` before asserting.
- companies_clean row count (~40.8M) is the root-CLAUDE.md figure; re-count if precision matters.
