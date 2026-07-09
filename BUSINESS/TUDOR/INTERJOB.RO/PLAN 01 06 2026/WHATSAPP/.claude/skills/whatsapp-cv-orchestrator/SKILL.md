---
name: whatsapp-cv-orchestrator
description: Orchestrate the WhatsApp CV intake pipeline — discover new inbound CVs on raspi, parse them, dedup+classify, upsert into fw_candidates, and report health. Use when asked to "run the WhatsApp CV pipeline", "process WhatsApp CVs", "ingest and save new CVs", "rerun CV intake", "redo the extract/match", "is WhatsApp CV intake working", "WhatsApp CV status", or when working in the WHATSAPP folder. The two-sided lead-capture counterpart to the email campaigns — this is the inbound candidate funnel.
---

# whatsapp-cv-orchestrator

Coordinates the 4-agent WhatsApp CV harness. **Execution mode: agent team** (pipeline pattern — sequential stages, file-based handoff via `_workspace/`). All agents `model: opus`.

WhatsApp Web gateway runs on raspi `192.168.100.20` (port 3000 webhook + qr_server, FastAPI ingestor :8001). Files land in `/opt/ACTIVE/SCRAPER_DATA/cvs/`. Target table: `interjob_master.fw_candidates`. This orchestrator reproduces/repairs the intake from Claude Code.

## Team
| Stage | Agent | Skill | Output artifact |
|-------|-------|-------|-----------------|
| 1 | cv-ingestor | whatsapp-cv-ingest | `_workspace/01_cv-ingestor_batch.json` |
| 2 | cv-extractor | whatsapp-cv-extract | `_workspace/02_cv-extractor_parsed.json` |
| 3 | candidate-matcher | whatsapp-candidate-match | `_workspace/03_candidate-matcher_result.json` |
| 4 | whatsapp-monitor | (read-only health) | `_workspace/04_whatsapp-monitor_health.json` |

## Phase 0: context check (run first)
- `_workspace/` absent → **initial run**: full pipeline 1→4.
- `_workspace/` present + partial request ("just re-extract", "redo the match", "drain pending upserts") → **partial re-run**: invoke only the named stage(s) onward, reusing upstream artifacts.
- `_workspace/03_pending_upserts.json` present → candidate-matcher drains it FIRST regardless of entry point.
- new run forced → move `_workspace/` → `_workspace_prev/`.

## Phase 1: ingest
Spawn cv-ingestor. Hard gate: host unreachable → STOP, report SSH error (an empty batch from a down host is NOT "no new CVs"). 0 new PDFs but reachable → report OK/empty, skip 2–3, still run monitor.

## Phase 2: extract
Spawn cv-extractor on the batch. Whole-batch unparseable (0/N) → likely host tool regression; flag monitor, do not proceed to match.

## Phase 3: match
Spawn candidate-matcher. Drains pending upserts first. DB down → DEGRADED, queue persisted, never lose candidates. Headline output = net new `fw_candidates`.

## Phase 4: monitor
Spawn whatsapp-monitor (read-only). Emits verdict OK | DEGRADED | FAIL + blockers. Distinguishes idle (gateway up, no CVs) from stalled (gateway/QR down, or backlog rising with 0 ingested).

## Error handling
- One retry per failed stage, then continue with the failure noted in the report (per house rule). Never delete or lose parsed candidates.
- Gateway/QR-expired is the highest-value catch — surface it loudly; it silently zeroes intake.

## Test scenarios
- **Normal**: 12 new PDFs → 11 parsed (1 photo skipped) → 9 inserted + 2 merged → verdict OK.
- **Stalled**: backlog 40 files, 0 ingested, gateway session dead → Phase 1 reports OK/empty but monitor returns FAIL "QR expired — rescan".
