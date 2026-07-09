---
name: ukraine-pipeline-orchestrator
description: Orchestrate the Ukraine exporter-document intelligence pipeline — extract text from Ukrainian agri-exporter catalogs (PDF/DOC/DOCX), dedup near-identical content, and produce a clean deduplicated CSV + summary. Use when asked to "run the Ukraine pipeline", "extract the Ukraine docs", "dedup the Ukrainian exporters", "rebuild the Ukraine dataset", or when working in the UKRAINE folder.
---

# ukraine-pipeline-orchestrator

Coordinates the 2-agent Ukraine document-intelligence harness. **Execution mode: agent team** (linear pipeline, file handoff). All agents `model: opus`. Source = Ukrainian agri-exporter catalogs + Stepan Gordienko docs. Deliverable = a clean, deduplicated exporter dataset for market analysis.

## Team
| Stage | Agent | Output |
|-------|-------|--------|
| 1 | doc-extractor | `all_files_extracted.csv` + `_workspace/01_*.json` |
| 2 | dedup-analyst | `all_files_deduplicated.csv` + `_workspace/02_*.json` |

## Phase 0: context check
- `_workspace/` absent → full run (extract → dedup).
- partial ("just re-dedup") → run dedup on existing extract.
- new source docs → re-extract; move `_workspace/` → `_workspace_prev/`.

## Phase 1: extract
doc-extractor → flat CSV (file/type/page/text). Tolerates per-file failures; logs missed files. 0 rows → STOP (no source or extractor broken).

## Phase 2: dedup
dedup-analyst: inventory → similarity analysis (report first) → write deduplicated CSV → final summary with dedup ratio + missed files.

## Error handling
One retry per stage. Never overwrite a prior good deduplicated CSV with an empty result.

## Test scenarios
- **Normal**: 3 PDFs + DOC set → 742 rows → dedup → 634 rows, 108 dupes removed, summary lists 0 missed.
- **Bad source**: a .doc extractor missing → that file in missed[], pipeline completes on the rest.
