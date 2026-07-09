---
name: whatsapp-candidate-match
description: Dedup parsed WhatsApp CV records against fw_candidates by phone/email, classify occupation into InterJob verticals, and upsert into interjob_master without creating duplicates. Use when asked to "save candidates", "merge into the database", "add CVs to fw_candidates", or as stage 3 of the whatsapp-cv pipeline.
---

# whatsapp-candidate-match

Land parsed CVs in `fw_candidates` (interjob_master on raspi) cleanly. Reuse `backend/db.py:upsert_candidate`. This is the stage that grows the lead pool — its correctness is the pipeline's whole value.

## Dedup model
- Indexes already exist: `(phone, source)` and `email`.
- Precedence: **phone first** (WhatsApp's strong identity), then email. Same phone = same person → merge, keeping the richer field set.
- `source = 'whatsapp'`. Never clobber a candidate's existing non-whatsapp source — preserve cross-source history.

## Occupation routing
Map `target_jobs` (already produced upstream) to verticals: factory, warehouse, care, build, horeca, agriculture, driver. Wrong vertical only mis-routes outreach; never drop a candidate over it.

## Lead-hygiene rule
Do not suppress on temporal/negative signals. Every parsed candidate is a lead; state changes over time. This pipeline only adds — suppression lives in the DNC/campaign layer, not here.

## Procedure
1. If `_workspace/03_pending_upserts.json` exists, drain it FIRST (retry prior DB failures).
2. Read `_workspace/02_cv-extractor_parsed.json`; upsert each via the host-side `db.py`.
3. Write `_workspace/03_candidate-matcher_result.json` (`{inserted, updated, merged_dupes, by_vertical}`). Headline = net new candidates.

## Failure modes
- DB unreachable → persist the would-be upserts to `_workspace/03_pending_upserts.json`, report DEGRADED. Never lose parsed candidates; next run drains the queue.
- Single-row constraint/encoding error → skip + log that row, continue.
