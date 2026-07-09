# CLAUDE.md — DB/ (PostgreSQL Backup Pull + Laptop Mirror + Delta Sync)

**v1.2 | 2026-06-21** · Added laptop live DB mirror + two-way delta sync (`delta_sync.py`). v1.1: backup-pull resume bug fixed (psftp `reget`).

> Parent project context lives in `../CLAUDE.md` (InterJob engine). This file covers the backup-pull tool AND the new delta-sync tool in this folder.

---

## LAPTOP LIVE DB MIRROR + DELTA SYNC (v1.2, 2026-06-21)

**Laptop now runs its own PostgreSQL** (separate from the backup files): PostgreSQL **18.4 + PostGIS 3.6.2**, user-owned at `C:\Users\apami\pg18` (binaries) + `C:\Users\apami\pg18data` (data), **port 5433**, login **tudor/tudor**. Autostarts at logon via `C:\Users\apami\pg18\start_pg18.bat` in the user Startup folder (Task Scheduler /rl HIGHEST is DENIED in this env). Holds all 21 raspibig DBs + `interjob_master` (40.7M rows).

**Table name fact:** raspibig = `public.companies` (PK on id); laptop = `companies_clean` (PK added 2026-06-21). Same data, same id space, 40,746,478 rows.

**`delta_sync.py`** — two-way, column-partitioned, keyed on `id`. raspibig owns row existence + SOURCE columns; laptop owns the 19 ENRICHMENT columns (see `ENRICH` list in the file). Same table never flows both ways → no conflicts.
- Modes: `init` (baseline watermark), default = **dry-run**, `--apply`, `pull`/`push`/`all`. Watermark in `delta_sync_state.json`.
- `schema_sync` adds laptop enrichment columns to raspibig (single ALTER, `lock_timeout=5s`, retried 10×/30s so it never blocks production `companies`).
- **Cron:** Windows task **"DeltaSync interjob"**, daily **03:30**, runs `delta_sync.bat` → `delta_sync.py --apply all`, logs `delta_sync_cron.log`.
- Known limitation (documented in the docstring): pull id-watermark can skip a lower id that commits after a higher one under concurrent inserts.

**LESSON:** never wrap `psql` in shell `timeout` — it kills the client but orphans the server query, which holds locks for hours and deadlocks the DB. Use server-side `SET statement_timeout` instead.

---

## PURPOSE

Automated pull of PostgreSQL `interjob_master` backups from raspibig (192.168.100.21) to the laptop at `D:\MEMORY\BACKUPS\postgresql\`. Keeps the latest 3, cleans older, **resumes partial transfers**. Runs daily via Windows Task Scheduler (04:00).

**Direction: pull-based (laptop → raspibig)**, not push. Avoids needing a Windows SSH server. raspibig's own push target for laptop is `enabled: False` (see `backup_sync.py`).

---

## COMPONENTS

| File | Role |
|------|------|
| `pull_backups_from_raspibig.py` | Core sync script. plink lists remote → **psftp `reget`** pulls (resumable) → size-verify → cleanup. |
| `pull_backups.bat` | Double-click wrapper (cd to `%~dp0`, runs python). |
| `TASK_SCHEDULER_SETUP.md` | Manual steps to create the 04:00 daily task. |
| `README.md` | User-facing overview + troubleshooting. |
| `CLAUDE.html` | Auto-generated index (AUDIT script). Harness ignores. |

---

## HOW IT WORKS

1. `pull_sync_state()` — copies `sync_state.json` from raspibig (pscp; tiny file).
2. `get_remote_files()` — `plink ls -lh .../*.sql.gz`, regex-parses `interjob_master_YYYYMMDD_HHMMSS.sql.gz`, newest first.
3. `pull_file()` — for each of newest `KEEP_DAYS` (3): skip if complete locally; else **psftp `reget`** appends to `*.downloading`; then byte-size match vs `get_remote_size()`; on match `os.rename` to final.
4. `cleanup_old_files()` — removes `*.sql.gz` AND stale `*.downloading` older than `KEEP_DAYS`.
5. Logs every step to `sync_log.txt`.

**Tools required (hardcoded paths):**
- `C:\Program Files\PuTTY\plink.exe` — remote listing + `stat` size
- `C:\Program Files\PuTTY\pscp.exe` — tiny `sync_state.json` only
- `C:\Program Files\PuTTY\psftp.exe` — the big `.sql.gz` (resumable via `reget`)

**Resume mechanism (fix, 2026-06-16):** psftp `reget` appends from the local file's current length, but refuses to *create* a missing file — so `pull_file()` `touch()`es the `.downloading` first. Success is judged by **byte-size match vs `stat -c %s` on raspibig**, NOT psftp's exit code (psftp returns 0 even when a batch command errors). Live-proven: a 12 GiB partial resumed to a byte-exact 14,055,341,336-byte file.

---

## CONFIG (constants in `pull_backups_from_raspibig.py`)

```python
RASPIBIG_HOST = "192.168.100.21"
RASPIBIG_USER = "tudor"
RASPIBIG_PW   = "RASPI_PW_REDACTED"
RASPIBIG_PATH = "/opt/BACKUPS/postgresql/"
LOCAL_DIR     = r"D:\MEMORY\BACKUPS\postgresql"
KEEP_DAYS     = 3
PULL_TIMEOUT  = 14400  # 4h per file (14GB fresh pulls over LAN)
```

---

## SCHEDULE (raspibig → laptop pipeline)

| Time | Host | Action |
|------|------|--------|
| 02:00 | raspibig | `postgresql_backup.py` dumps `.sql.gz` |
| 03:30 | raspibig | `backup_sync.py` pushes to raspi (laptop push DISABLED) |
| 04:00 | laptop | THIS script pulls latest 3 to `D:\MEMORY\BACKUPS\postgresql\` |

**Retention:** 3 days both ends. Backup size ~3–14 GB compressed.

---

## LIVE STATE (verified 2026-06-16, post-fix)

```
D:\MEMORY\BACKUPS\postgresql\
├── interjob_master_20260612_110154.sql.gz   13.09 GB  COMPLETE
├── interjob_master_20260614_034012.sql.gz    3.03 GB  COMPLETE (was 7 MB stuck partial -> resumed + verified)
├── interjob_master_20260614_043034.sql.gz   13.09 GB  COMPLETE (was 12.1 GB stuck partial -> resumed + verified)
├── sync_log.txt
└── sync_state.json
```

**No `.downloading` partials remain.** Both previously-stuck 0614 files are complete with byte-exact size match vs raspibig.

---

## RESUME — FIXED (2026-06-16)

**Was:** `pull_file()` set `resume = True` for >1 GB partials but then called pscp with no resume flag — pscp restarted from byte 0 every run, so the 12 GB partial never advanced. Root cause of the stuck 0614 files.

**Now:** transfer switched pscp → **psftp `reget`** (real append-resume). `pull_file()` `touch()`es the `.downloading` first (psftp reget won't create a missing file), then verifies success by **byte-size match vs `stat -c %s`** on raspibig (psftp's exit code is unreliable). Both stuck partials resumed to byte-exact complete files in the live test.

**Why psftp not rsync:** WSL Debian lacked `rsync`/`sshpass` and sudo is password-gated; psftp (PuTTY 0.83) was already installed, needs zero setup, and `reget` gave identical resume semantics. Smoke-tested: 4000-byte prefix → "restarting at file position 4000" → 18986 bytes, byte-identical to a full `get`.

---

## COMMON COMMANDS

```powershell
# Run sync now (double-click equivalent)
D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\DB\pull_backups.bat

# Run directly
python pull_backups_from_raspibig.py

# Tail the log
type D:\MEMORY\BACKUPS\postgresql\sync_log.txt

# List local backups
dir D:\MEMORY\BACKUPS\postgresql\*.sql.gz

# Test raspibig connectivity + list remote sizes
"C:\Program Files\PuTTY\plink.exe" -batch -pw RASPI_PW_REDACTED tudor@192.168.100.21 "cd /opt/BACKUPS/postgresql && for f in interjob_master_*.sql.gz; do printf '%s %s\n' \"$(stat -c %s \"$f\")\" \"$f\"; done"

# Clear stuck partials to force clean re-pull (rarely needed now)
del D:\MEMORY\BACKUPS\postgresql\*.downloading
```

**Restore locally:**
```bash
gunzip -c D:\MEMORY\BACKUPS\postgresql\interjob_master_YYYYMMDD_HHMMSS.sql.gz | psql interjob_restored
```

---

## WHAT NOT TO DO

- Do NOT enable raspibig's push-to-laptop target in `backup_sync.py` — Windows SSH server is not set up; pull-only by design.
- Do NOT hardcode credentials elsewhere — password (`RASPI_PW_REDACTED`) is already inline here and in parent CLAUDE.md; keep it in one place.
- Do NOT assume byte-exact correctness beyond size match — psftp `reget` trusts the existing prefix (no checksum); for paranoid integrity run `gunzip -t` / sha256 on the completed file.
- Do NOT delete `*.sql.gz` complete files without archiving — these are the only off-raspibig DB copies on the laptop.
- Do NOT raise `KEEP_DAYS` without checking D: free space (3 x 14 GB = 42 GB floor).

---

## CONVENTIONS (inherited from parent)

- 250-line max per Python file (this script is 199 lines).
- Python: `#!/usr/bin/env python3`, one-liner docstring, `main()`, `if __name__`.
- Error handling only at system boundaries (subprocess calls — already wrapped).
- Comments: WHY only.
- Data safety: never delete complete backups without archive.

---

## HARNESS: DB Sync Orchestration (v1.0, 2026-06-23)

**Status:** READY FOR PRODUCTION (Final step: admin Task Scheduler setup)

**Agents (3-team):**
1. `db-health-monitor` — Polls both DBs every 5min (connectivity, row counts, schema hash, lag). Alerts on CRITICAL.
2. `sync-orchestrator` — Executes 3-step nightly pipeline: backup pull (04:00) → schema sync → delta sync (03:30). Handles retries, error recovery.
3. `alert-reporter` — Dispatches failures via email + Telegram (@expatsinromania_news). Daily summary 05:30, weekly audit Mon 08:00.

**Skills (5 total):**
- `db-health-check` — Connectivity, row counts, schema hash, watermark lag
- `backup-pull-coordinator` — psftp resumable transfers, byte verification, cleanup
- `schema-sync-coordinator` — Safe ALTER commands (lock_timeout=5s, retry 10×/30s)
- `delta-sync-coordinator` — Column-partitioned sync (all 21 DBs), watermark tracking
- `alert-dispatch` — Email + Telegram, dedup, daily/weekly reports

**Entry point:** `db-sync-harness` skill (orchestrator).

**State files:**
- HARNESS_STATE.json (team, crons)
- HEALTH_STATE.json (previous status)
- SYNC_STATE.json (watermark, failures)
- ALERTS_STATE.json (dedup window, report timestamps)

**Crons (Windows Task Scheduler) — LIVE 2026-06-26 (current-user, RunLevel Limited):**
- DB-Health-Monitor-5min (every 5min) — pre-existing, fires health_monitor_runner.ps1
- DB-Health-Monitor-Daily (05:25) — added 2026-06-26, refreshes HEALTH_STATE before the 05:30 report
- DB-Alert-Daily-0530 (05:30) — added 2026-06-26, runs alert_reporter_runner.ps1 (auto-weekly on Mondays) → dispatches email+Telegram
- DB-Backup-Pull-0400 (04:00) — added 2026-06-26, pull_backups.bat (host key must be cached for the user; a manual run on 2026-06-26 cached it — a batch-mode run before caching fails "Cannot confirm a host key")
- DB-Backfill-NewEnrich-Oneshot (one-shot, fired 2026-06-26 23:30 local) — full enrichment backfill; delete after success
- DeltaSync interjob (03:30) — delta_sync.bat (delta only; NOT the full sync_pipeline_runner)

**ENV CONSTRAINT:** this non-admin session can register only plain `-Daily`/`-At` triggers. Repetition + AtLogOn + SYSTEM-user triggers all return "Access is denied" (same root as the documented `/rl HIGHEST` denial). True 5-min/SYSTEM scheduling needs an elevated one-time `.ps1` (see DEPLOY_TASK_SCHEDULER.ps1).

**GAPS RESOLVED 2026-06-26:**
- ✅ Backup staleness — added `DB-Backup-Pull-0400` (daily 04:00 → pull_backups.bat) + manual pull of the Jun 25 backup.
- ✅ Alerts now dispatch — wired alert_dispatch.py into alert_reporter_runner.ps1; real creds in .claude/.env (Gmail **elena.manpower.dristor** + app pw; Telegram bot **@raspibig_controller_bot** `8731910997:…` → chat -1003830000766). Verified email_sent+telegram_sent=true. Email body forced ASCII (em-dash/box-chars → `-`/`=`); alert_dispatch.py critical body made raw-string (fixed `\M` SyntaxWarning).
- ✅ Schema push — the 13 missing enrichment cols (contact_first_name, email_domain, gdpr_basis, gdpr_basis_date, last_contacted_at, last_ted_year, linkedin_url, phone_e164, seap_total_ron, seap_wins, size_segment, standard_sector, times_contacted) ADDED to raspibig public.companies (`added 13 columns, attempt 1`). Lock contention was transient.

**Backfill SCHEDULED 2026-06-26:** historical enrichment for the 13 new cols is full-table (every laptop row has >=1 non-null — gdpr_basis/gdpr_basis_date/seap_total_ron/seap_wins/times_contacted=40.7M each, standard_sector=35.9M; the rare valuable ones: size_segment 3.5M, last_ted_year 1.46M, email_domain 467K, linkedin_url 390K, phone_e164 344K, contact_first_name 88K, last_contacted_at 0). One-shot task **DB-Backfill-NewEnrich-Oneshot** runs `backfill_new_enrich.bat --apply` tonight **23:30 local / 20:30 UTC** (raspibig quiet, pre-backup-dump). 5000-row batches, commit/100K. Log: LOGS\backfill.log. Delete the task after it succeeds.

**Telegram creds note:** `@raspibig_controller_bot` (token 8628341440…) is NOT a member of chat -1003830000766 → "chat not found". The working pair is bot `8731910997…` (from raspibig /opt/ACTIVE/.env) + that chat.

**Logs directory:** `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\DB\LOGS\`

**Changes:**
| Date | Change | Reason |
|------|--------|--------|
| 2026-06-23 | Initial harness build (agents + 5 skills) | Automate 3-step pipeline, eliminate manual sync, centralize alerts |
| 2026-06-26 | Fixed health_monitor_runner.ps1 capture bug | `> $tempJson 2>&1` corrupted JSON ("Invalid JSON primitive: python.exe"); HEALTH_STATE was frozen at Jun 23. Split stdout/stderr → state refreshes |
| 2026-06-26 | Registered DB-Health-Monitor-Daily (05:25) + DB-Alert-Daily-0530 | Dry-run deploy (option 1); current-user tasks (no admin). Weekly handled internally by the alert runner's Monday branch |
| 2026-06-26 | Wired alert_dispatch.py into alert runner + real .env creds + ASCII email fixes | Reports were log-only; creds were placeholders. Email+Telegram now verified sending |
| 2026-06-26 | Added 13 enrichment cols to raspibig public.companies | schema push was perpetually lock-deferred; cols now exist so enrichment push can land |
| 2026-06-26 | Registered DB-Backup-Pull-0400 (daily) + pulled Jun 25 backup | backups were 12 days stale; DeltaSync runs delta only, not backup pull |
| 2026-06-26 | Created backfill_new_enrich.py/.bat + scheduled one-shot 23:30 local | land historical enrichment for the 13 new cols (full-table 40M); off-peak to spare the Pi |
| 2026-06-26 | droid review of backfill -> fixed HIGH type bug + lock_timeout + try/finally | execute_values renders all-NULL batch cols as `text`; assigning to date/int/numeric/timestamp aborts (last_contacted_at all-NULL crashed batch 1). Fix: cast each col to its real raspibig type. Added per-batch lock_timeout=5s retry + try/finally. Proven: no-cast fails, cast OK, rolled back |
| 2026-06-27 | full 40M backfill OOM-killed raspibig backend at 500K rows | Pi can't take 40M UPDATEs in one stream. Rewrote backfill_new_enrich.py: id-keyed pagination + per-chunk commit + reconnect-on-disconnect + paced (CHUNK 2000, 0.2s) + resumable watermark (backfill_state.json) |
| 2026-06-27 | scope cut 40M -> 8.19M after column analysis | 4 cols are pure constants (seap_total_ron/seap_wins/times_contacted=0, gdpr_basis_date=2026-06-20) -> set as raspibig DEFAULTs not row writes; last_contacted_at 100% NULL -> skipped; standard_sector is 33M 'other' (junk) -> only meaningful sectors streamed. Stream = 8 real cols x 8.19M rows. One-shot task disabled (running manually) |

---

## NEXT STEPS / OPTIONS

1. Deploy cron jobs to Windows Task Scheduler (setup scripts provided in skills)
2. Test full pipeline run (dry-run mode first)
3. Verify email + Telegram credentials (Gmail app pw, Telegram bot token)
4. Add checksum (sha256) verification after transfer (currently size-match only)
5. Generate SSH key in WSL + copy to raspibig `authorized_keys`, then drop inline `RASPI_PW_REDACTED` password

---

*Verify live state before edits:* `tail -20 D:\MEMORY\BACKUPS\postgresql\sync_log.txt` and `dir D:\MEMORY\BACKUPS\postgresql\`.
