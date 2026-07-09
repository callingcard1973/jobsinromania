---
name: candidate-job-match
description: Pair fw_candidates against active ij_jobs by occupation/COR + location, score, and persist to the ij_matches ledger (dedup by UNIQUE candidate+job). Use when asked to "match candidates to jobs", "find jobs for candidates", "run the matcher", "refresh matches", or "match this new candidate". The marketplace core — turns two data piles into pairings.
---

# candidate-job-match

Produce ranked candidate↔job pairings on raspibig `interjob_master`. Both sides already exist (`fw_candidates`, `ij_jobs`); this builds the missing link.

## Ledger (create once, idempotent)
```sql
CREATE TABLE IF NOT EXISTS ij_matches (
  candidate_id UUID, job_id BIGINT, score INT, status TEXT DEFAULT 'new',
  notified_worker BOOL DEFAULT false, notified_at TIMESTAMP, created_at TIMESTAMP DEFAULT now(),
  UNIQUE(candidate_id, job_id));
```
The UNIQUE constraint is the dedup — re-runs never double-insert a pair.

## Occupation key — LIVE REALITY (verified 2026-06-26)
`fw_candidates.target_jobs` is **empty for all 3,875 rows** — do NOT key on it. Key on `role` (English buckets). `ij_jobs.sector` is **Romanian**. Required map:
| candidate.role | job.sector |
|----------------|------------|
| farm-worker / farm% | agricultura |
| care | sanatate |
| hospitality | horeca |
| logistics / driver | transport |
| construction | constructii |
| factory / packaging / machinery | productie |

`role='unknown'` (1,280) + empty role (~580) are **unmatchable until role is enriched** (re-run cv_extract or infer from `skills`/`message`) — count them as a backlog, don't force-match. ~2,016 candidates are matchable today.

## Scoring (deterministic, explainable)
1. **Occupation (required).** Map candidate `role` → job `sector` via the table above. No overlap → no match (don't manufacture pairings). The 7 ANOFM deficit occupations (Bucatar, Electrician, Mecanic, Sofer, Sudor, Tamplar, Zidar) score higher — those are the jobs employers pay to fill; refine via job `title` keyword within sector.
2. **Location (soft, +).** Same county boosts; never penalize international/mobile candidates — most relocate. Location is a tiebreak, not a gate.
3. **Skills/recency (tiebreak).** Skill-keyword overlap; newer candidates first.

## Why occupation-required, location-soft
A welder in Cluj and a welding job in Timis is a real match — relocation is the norm for this labor pool. Gating on county would discard most valid pairings. Gating on occupation is correct: a cook is not a welder.

## Procedure
1. Ensure `ij_matches` exists.
2. Candidates without a ledger row (or `--candidate <id>`) × active jobs → score → insert pairs above threshold as status='new'.
3. Write `_workspace/01_match-finder_result.json` (counts + by_occupation).

## Failure modes
- 0 active jobs or 0 candidates → empty result, do not notify.
- Scoring yields >20 matches/candidate → threshold too loose; tighten before notifying (spam risk).
