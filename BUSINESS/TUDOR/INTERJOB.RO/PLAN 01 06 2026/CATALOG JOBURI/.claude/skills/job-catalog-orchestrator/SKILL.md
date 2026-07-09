---
name: job-catalog-orchestrator
description: Orchestrate the InterJob job-catalog pipeline — build branded PDF+HTML catalogs per domain from ij_jobs (client + internal variants), deploy the client variant to domain.eu/catalog/, optionally email warm leads, and verify. Use when asked to "build the job catalog", "regenerate job catalogs", "publish catalogs for all domains", "rerun the catalog deploy", "are the job catalogs current", or when working in the CATALOG JOBURI folder. The job-side counterpart to the candidate-catalog cycle.
---

# job-catalog-orchestrator

Coordinates the 3-agent job-catalog harness. **Execution mode: agent team** (pipeline, file handoff via `_workspace/`). All agents `model: opus`. Builders reuse the global `interjob-catalog` skill; deploy reuses `a2-content-publish`.

## Team
| Stage | Agent | Skill | Output |
|-------|-------|-------|--------|
| 1 | catalog-builder | interjob-catalog (global) | `_workspace/01_catalog-builder_manifest.json` |
| 2 | catalog-deployer | job-catalog-deploy | `_workspace/02_catalog-deployer_result.json` |
| 3 | catalog-monitor | (read-only) | `_workspace/03_catalog-monitor_health.json` |

## Phase 0: context check
- `_workspace/` absent → initial run (build → deploy → verify).
- partial request ("just redeploy", "rebuild factoryjobs only") → run named stage(s)/domain(s) onward, reuse upstream.
- forced new → move `_workspace/` → `_workspace_prev/`.

## Phase 1: build
catalog-builder per requested domain(s). Hard gate: 0 jobs → do NOT deploy an empty catalog. DB down → STOP.

## Phase 2: deploy
catalog-deployer publishes ONLY the client variant; verifies 200. Email is dry-run unless user says live.

## Phase 3: verify
catalog-monitor confirms URLs 200 + non-zero jobs; emits OK | DEGRADED | FAIL.

## Error handling
One retry per stage, then continue with failure noted. Never publish the internal-contacts variant. Never report an unverified upload as live.

## Test scenarios
- **Normal**: factoryjobs → 312 jobs → PDF+HTML built → client variant live at 200 → OK.
- **Empty**: horeca → 0 jobs today → build skipped, monitor flags DEGRADED "horeca 0 jobs", other domains proceed.
