# CODE — junk-drawer index

**v1.0 | 2026-06-26** — pre-infrastructure trial code, ~98 loose Python files.

## Harness: CODE map + guardrail

**Goal:** Find the right script fast and avoid running STALE code that clobbers live state.

**Trigger:** Use `code-map-orchestrator` skill (agent `code-navigator`) for any "which/where/run/is-it-used" question about CODE scripts. Direct factual questions can be answered without the skill.

**Rule:** Unknown/unreferenced scripts default to STALE. ACTIVE = referenced in a cron/systemd/handoff doc. Run via `python script.py` entrypoints only (import has side effects).

## 5 buckets
| Bucket | Where | Canonical entrypoint | Host |
|--------|-------|----------------------|------|
| ingest | `ingest/*` | `ingest_anofm.py`, `ingest_eures.py` | raspi .20 (systemd) |
| build | `build/*`, `build_pages*.py`, `generate_*.py`, `seo_*.py` | `build/build_pages.py`, `build_sitemap.py` | laptop |
| deploy | `deploy/*`, `deploy_*.py`, `upload_*.py` | `deploy/deploy_cpanel.py`, `deploy_wordpress.py` | → A2/WP |
| farmworkers | `farmworkers/*` | `daily_generate_deploy.py` | daily pipeline |
| diagnostics | `verify_*.py`, `probe_*.py`, `query_candidates.py` | read-only | any |

## STALE — do not run
`campaigns/*` (superseded by raspibig Email Campaigns v2.0, 2026-06-23) · most root `fix_*`/`add_*`/`patch_*` (one-time) · `eures_malta_employers.py` · `alembic/` (empty).

**Change history:** 2026-06-26 — initial map harness (1 agent + 1 skill + this index).
