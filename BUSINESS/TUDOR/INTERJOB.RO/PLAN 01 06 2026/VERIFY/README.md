# VERIFY — INTERJOB verification toolkit

Single entrypoint for code + harness + runtime verification. No CI server; runs locally / pre-deploy.

## Usage

```powershell
.\verify.ps1                  # local layers: python lint + harness validator
.\verify.ps1 -All             # + DB-contract + smoke (needs SSH to raspi/raspibig)
.\verify.ps1 -Path "..\ANOFM" # scope python/harness to one folder
.\verify.ps1 -Db              # only DB contracts
.\verify.ps1 -Smoke           # only smoke tests
```

Or call any layer directly: `python verify_python.py ..`

## Layers

| Script | What | Needs |
|--------|------|-------|
| `verify_python.py` | ruff (bug-class rules in `ruff.toml`) + py_compile sweep + 250-line rule (advisory) | `pip install ruff` |
| `verify_harness.py` | `.claude/agents/*.md` frontmatter (name/description/model/tools), unique names, valid model ids; `SKILL.md` trigger phrases | pyyaml |
| `verify_db.py` | asserts each contract's table+columns exist, over SSH (DBs are localhost-only) | SSH to host |
| `verify_smoke.py` | remote `py_compile` of scheduled scripts + optional side-effect-free `--dry-run` | SSH to host |

## Config files (extend these as the system grows)

- `ruff.toml` — lint rules. Bug-class focus (F, E9, B, PLE), not style. `--fix` auto-fixes most.
- `db_contracts.json` — table/column contracts per script. Add an entry when a script gains a new DB dependency.
- `scheduled_scripts.json` — scripts to smoke-test before deploy/enable. Set `dry_run` only if side-effect-free.

## Known baseline (2026-06-24, after deep inspection)

**No deployed/scheduled script is broken** — every script in cron/timers compiled clean (smoke PASS). All findings below are local source files only.

- **Syntax errors:** the "1153 invalid-syntax" is cascade noise from just **~6 broken local files**, NONE scheduled:
  - `HANDOFF DAILY/write_handoff.py` — a text doc mis-saved as `.py` (rename to `.md`).
  - `SILOZURI/CODE/build_silozuri_db.py` — scrambled (imports after use, orphan `continue`).
  - `SILOZURI/CAMPAIGN/CODE/run_silozuri_with_checkpoints.py:3` — docstring opens with `"` not `"""`.
  - `CATALOG JOBURI/CODE/build_factoryjobs_en_html.py:137` — unterminated `ro=set("…")` string.
  - `CODE/drain_terenuri.py` — Romanian curly quotes „ " instead of ASCII.
- **F821 undefined-name (parse-OK → runtime crash):**
  - `RASPIBIG INSPECT/CRONTAB/_deploy/extract_candidates.LIVE.py` (`pdfs`) — STALE snapshot of an already-fixed prod bug (see CV parser fix 2026-06-19), not live.
  - `SILOZURI/CODE/create_silozuri_db.py:2` (`NUL`) — Windows `>NUL` redirect artifact pasted into source.
- **Cosmetic (auto-fixable via `ruff --fix`):** 332 empty f-strings (F541), 316 unused imports (F401), 84 unused vars. ~664 safe auto-fixes.
- **Config note:** `target-version` MUST be py313 — py39 falsely flags all 3.12+ f-strings as invalid-syntax.
- Harness: older harnesses (SUPERMARKETURI no frontmatter, SILOZURI missing `tools`) flagged; the 13 built 2026-06-24 pass.

Fix incrementally; wire `verify.ps1` into `deploy.ps1` as a pre-deploy gate when ready.
