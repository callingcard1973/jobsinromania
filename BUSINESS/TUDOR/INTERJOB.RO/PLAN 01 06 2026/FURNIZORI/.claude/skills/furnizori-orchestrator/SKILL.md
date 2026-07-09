---
name: furnizori-orchestrator
description: Orchestrate the Romanian supplier (furnizori) scraper pipeline — scrape Lidl + Kaufland producer directories, consolidate into a deduped CUI-keyed master, and hand a campaign-ready supplier lead list to the email harness. Use when asked to "scrape suppliers", "refresh Lidl/Kaufland producers", "rebuild the supplier master", "run furnizori", "supplier leads status", or when working in the FURNIZORI folder.
---

# furnizori-orchestrator

Coordinates the 2-agent supplier-scraper harness. **Execution mode: agent team** (pipeline, file handoff). All agents `model: opus`. Sources are public producer directories (Lidl Piata Lidl API, Kaufland Producatori Locali); the deliverable is a deduped B2B supplier lead master.

## Team
| Stage | Agent | Skill | Output |
|-------|-------|-------|--------|
| 1 | supplier-scraper | (scraper scripts) | `_workspace/01_supplier-scraper_summary.json` + per-source CSV/JSON |
| 2 | supplier-consolidator | (dedup/merge) | `furnizori_master.csv` + `_workspace/02_consolidator_result.json` |

## Phase 0: context check
- `_workspace/` absent → full run (scrape all → consolidate).
- partial ("just Kaufland", "reconsolidate") → run named source/stage, reuse upstream.
- forced new → move `_workspace/` → `_workspace_prev/`.

## Phase 1: scrape
supplier-scraper `--source all`. Per-source isolation: a dead source FAILs alone; the other proceeds. 0 rows for a source → flag, continue.

## Phase 2: consolidate
supplier-consolidator merges all sources + existing Profi into the deduped master (CUI → email fallback). Strips master_emails + DNC before marking campaign-ready. Headline = net unique suppliers with contact.

## Hand-off
The supplier master feeds the shared email-campaign harness for sending — this harness builds and refreshes the asset, it does not send. Lead-hygiene: never suppress on temporal/negative signals here.

## Error handling
One retry per source, then continue noting the gap. Never block consolidation on one missing scrape.

## Test scenarios
- **Normal**: Lidl 92 + Kaufland 98 + Profi 745 → dedup → ~880 unique, ~600 with email → master written.
- **Source down**: Kaufland layout changed (0 rows) → scrape FAILs Kaufland only, consolidates Lidl+Profi, monitor notes Kaufland gap.
