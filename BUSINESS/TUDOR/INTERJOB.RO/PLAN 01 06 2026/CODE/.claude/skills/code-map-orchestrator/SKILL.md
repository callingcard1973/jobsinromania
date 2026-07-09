---
name: code-map-orchestrator
description: Navigate and safely run scripts in the CODE/ junk-drawer (~98 loose Python files, no structure). Routes any "which/where/run/is-it-used" question about CODE scripts through the code-navigator map, classifies ACTIVE vs STALE, and guards against running superseded code. Use when asked to "run a CODE script", "find the right script", "what's in CODE", "is this script still used", "build/deploy/ingest from CODE", or when working under the CODE folder.
---

# code-map-orchestrator

A **map + guardrail**, not a restructure. CODE/ is pre-infrastructure trial code: ~98 Python files, only a handful active (ingest on raspi, build→output, a few deployers). The risk is running STALE code (old campaign senders, one-time fixers) that clobbers live state. This harness routes every CODE request through the `code-navigator` agent first.

## Execution mode: single agent (code-navigator)
No pipeline — this is a lookup + safety gate. The orchestrator is the policy; code-navigator is the index.

## The 5 buckets
ingest · build · deploy · farmworkers · diagnostics. Full map + canonical entrypoints + the STALE list live in `code-navigator.md`.

## Procedure
1. Any "run X / where is X / which script" → ask code-navigator for the verdict (path, bucket, ACTIVE|STALE|LIBRARY, invocation).
2. **STALE → refuse to run**; name the replacement (e.g. campaigns/* → raspibig Email Campaigns v2.0). Run only on explicit override.
3. **ACTIVE → run via its `if __name__` entrypoint** (never import — side effects). Respect the host: ingest runs on raspi .20, deploy targets A2, build is local.
4. **LIBRARY → don't run standalone**; it's imported by an entrypoint.

## Why route everything through the map
Without a CLAUDE.md, the only signal of "is this current?" is cron/systemd references. Defaulting unknown scripts to STALE prevents the classic failure: re-running a 2-month-old deployer that overwrites a fixed site.

## Test scenarios
- **Lookup**: "where's the sitemap builder?" → `build/build_sitemap.py`, build bucket, LIBRARY→entrypoint, generates output/sitemap.xml.
- **Guard**: "send the Malta campaign" → code-navigator flags `campaigns/send_malta*.py` STALE, points to raspibig orchestrator, refuses without override.
