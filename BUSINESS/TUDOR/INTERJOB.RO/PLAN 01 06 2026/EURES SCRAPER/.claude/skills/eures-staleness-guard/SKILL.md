---
name: eures-staleness-guard
description: Detect a stalled/stale EURES pipeline before it silently rots — check state.json last_run age, stats.db scraper success in the last 24h, eures_jobs row-count delta, and dashboard service health, then alert or auto-retry. Use when asked "is EURES fresh", "check EURES staleness", "did EURES run today", "EURES data is old", or as a guard before building EURES Brevo segments.
---

# eures-staleness-guard

A read-first health guard for the EURES pipeline, used by the `eures-health` agent. The failure mode it catches: the scraper hangs, `eures_jobs` stops growing, but downstream campaigns keep reading the same stale rows — nobody notices until leads dry up.

## Signals (raspibig `/opt/ACTIVE/EURES/`)
1. **state.json** → `last_run` age. >24h since last successful run = STALE.
2. **stats.db `runs`** → was the *scraper* stage status=success within 24h? (A run that started but failed the scrape is worse than no run.)
3. **eures_jobs row delta** vs yesterday → flat or declining = probable scraper failure even if `last_run` looks recent.
4. **dashboard service** → `systemctl status eures_dashboard` (port 8098) up?

## Verdict + action
- **OK**: fresh (<24h) + scraper success + positive/stable delta.
- **STALE**: >24h or flat delta → alert; optionally trigger a retry via the eures-orchestrator with the timeout watchdog.
- **ERROR**: dashboard down or stats.db unreadable → infra alert.

Return `{status, last_run_age_h, jobs_today, scraper_last_success, action_needed}`.

## Why a guard, not just a dashboard
The dashboard shows current numbers; it doesn't *judge* them. "147 jobs" looks fine until you see yesterday was also 147 — a frozen count. This skill encodes the judgment (age + delta + stage success together) so a single check returns a yes/no on "is EURES actually working".

## Gate use
Run this BEFORE `eures-classify-router` builds Brevo segments — segmenting on stale data sends yesterday's (or last week's) jobs as if new. STALE → fix the scrape first, don't segment.

## Validation
```bash
plink -batch -pw 'REDACTED' tudor@192.168.100.21 "cat /opt/ACTIVE/EURES/state.json; systemctl is-active eures_dashboard"
```
