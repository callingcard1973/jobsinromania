---
name: matcher-orchestrator
description: Orchestrate the candidate-job marketplace loop — match fw_candidates to active ij_jobs by occupation+location, notify both sides (worker job digests + employer candidate leads), and report yield. Use when asked to "run the matcher", "match candidates to jobs", "notify workers about jobs", "send match digests", "matcher status", or when working in the MATCHER folder. This is the InterJob marketplace core — it turns the inbound candidate funnel + job feed into actual leads.
---

# matcher-orchestrator

Coordinates the 3-agent matcher harness. **Execution mode: agent team** (pipeline, file + DB handoff via `ij_matches`). All agents `model: opus`. Connects the WhatsApp/email candidate intake (`fw_candidates`) to the job feed (`ij_jobs`) — the link that makes InterJob a marketplace rather than two databases.

## Team
| Stage | Agent | Skill | Output |
|-------|-------|-------|--------|
| 1 | match-finder | candidate-job-match | `ij_matches` rows (status='new') + `_workspace/01_*.json` |
| 2 | match-notifier | match-notify | notified rows + `_workspace/02_*.json` |
| 3 | match-monitor | (read-only) | `_workspace/03_*.json` |

## Phase 0: context check
- `_workspace/` absent → full run (find → notify → report).
- partial ("just re-notify", "match only new candidates", "dry-run the notify") → run named stage(s), reuse `ij_matches`.
- `ij_matches` is the durable state — it persists across runs; `_workspace/` is per-run scratch.

## Phase 1: find
match-finder scores unmatched candidates × active jobs, inserts new pairs. Occupation required, location soft (relocation is normal). Deficit occupations weighted. 0 jobs/candidates → STOP, do not notify.

## Phase 2: notify
match-notifier — **default dry-run**. DNC + ledger dedup first. Worker gets ONE digest of top 3-5 jobs (ASCII, occupation-routed); employer/sales gets a candidate digest. Live only on explicit instruction. Channel down → leave status='new', retry.

## Phase 3: report
match-monitor verdict OK | DEGRADED | FAIL + the business signal: unmatched backlog by occupation (lost-revenue indicator), notify lag, matches/candidate sanity.

## Error handling
One retry per stage, then continue noting failure. Never mark a match notified without a confirmed send. Never notify on an empty/loose match set.

## Test scenarios
- **Normal**: 40 new candidates → 180 matches (occupation+location) → dry-run shows 38 worker digests + 1 employer digest → user approves live → notified, monitor OK.
- **Open loop**: 312 candidates, 0 ij_matches rows → finder was never run → monitor FAIL "matcher not running, 312 unmatched".
