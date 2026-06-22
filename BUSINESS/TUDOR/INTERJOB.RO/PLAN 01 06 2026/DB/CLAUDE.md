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
RASPIBIG_PW   = "bucare"
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
"C:\Program Files\PuTTY\plink.exe" -batch -pw bucare tudor@192.168.100.21 "cd /opt/BACKUPS/postgresql && for f in interjob_master_*.sql.gz; do printf '%s %s\n' \"$(stat -c %s \"$f\")\" \"$f\"; done"

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
- Do NOT hardcode credentials elsewhere — password (`bucare`) is already inline here and in parent CLAUDE.md; keep it in one place.
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

## NEXT STEPS / OPTIONS

1. Add Telegram notification on failure (match raspibig's pattern in `monitor_crons.py`).
2. Add checksum (sha256) verification after transfer (currently size-match only).
3. Generate an SSH key in WSL + copy to raspibig `authorized_keys`, then drop the inline `bucare` password.
4. Consider raising `KEEP_DAYS` once D: free space is confirmed (3 x 14 GB = 42 GB floor).

---

*Verify live state before edits:* `tail -20 D:\MEMORY\BACKUPS\postgresql\sync_log.txt` and `dir D:\MEMORY\BACKUPS\postgresql\`.
