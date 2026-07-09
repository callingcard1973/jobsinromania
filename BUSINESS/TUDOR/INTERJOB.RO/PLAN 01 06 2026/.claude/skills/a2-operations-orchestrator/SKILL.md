---
name: a2-operations-orchestrator
description: "Orchestrate A2 Hosting operations on the loaiidil account (34 domains, InterJob network). Full pipeline: inspect site → publish content → configure WP → free disk quota → verify results. Also handles partial runs: 'redo publish', 'fix electricjobs wp', 'clean up space', 'audit all domains', 'check what's published', 'update article', 'rerun verify'. Trigger on ANY request involving A2 file operations, WP config, cross-site publishing, disk cleanup, or site audits on interjob.ro / buildjobs.eu / factoryjobs.eu / electricjobs.eu / mechanicjobs.eu / horecaworkers.eu / farmworkers.eu / meatworkers.eu domains."
---

# A2 Operations Orchestrator

Orchestrate end-to-end A2 Hosting operations: publish, configure, cleanup, verify across the InterJob domain network.

## Execution mode: Sub-agent (hybrid pipeline)

| Phase | Agent | Mode | Purpose |
|-------|-------|------|---------|
| Phase 0 | Direct | Check | Context check for partial re-runs |
| Phase 1 | site-inspector | Sub-agent | Audit target sites |
| Phase 2 | content-publisher | Sub-agent (fan-out) | Publish to N domains in parallel |
| Phase 3 | wp-mutator | Sub-agent | Configure WP sites |
| Phase 4 | space-reclaimer | Sub-agent | Free disk quota |
| Phase 5 | verify-agent | Sub-agent | Verify published content |

## Phase 0: Context Check

1. Check if `_workspace/` exists
2. If yes + user asks partial re-run → skip completed phases, re-run only requested ones
3. If yes + user provides new input → archive old `_workspace/` to `_workspace_prev_YYYYMMDD_HHMMSS/`, start fresh
4. If no → initial run, proceed to Phase 1

## Phase 1: Site Inspection

**Run:** `Agent(subagent_type="Explore", name="site-inspector", model="opus")`

Inspect the target domain(s). Use `site-inspector` agent definition from `.claude/agents/site-inspector.md`.

**Input:** Domain name(s) from user
**Output:** `_workspace/01_inspector_report.md` with file tree, WP creds, disk usage

## Phase 2: Content Publishing (fan-out)

**Run:** N parallel `Agent(subagent_type="general-purpose", name="content-publisher-N", model="opus", run_in_background=true)`

One agent per target domain. All use `a2-content-publish` skill + `a2-cpanel` global skill.

**Input:** Article HTML, OG tags config, cross-link config
**Output:** Published files on each domain, `_workspace/02_publish_report.md`

## Phase 3: WP Configuration

**Run:** `Agent(subagent_type="general-purpose", name="wp-mutator", model="opus")`

Use `a2-wp-bootstrap` skill. Blocked if disk quota is exceeded (check Phase 2 result first).

**Input:** Domain + WP settings (title, tagline, permalink, post changes)
**Output:** `_workspace/03_wp_report.md`

## Phase 4: Disk Cleanup

**Run:** `Agent(subagent_type="general-purpose", name="space-reclaimer", model="opus")`

Use `a2-disk-cleanup` skill. Only if disk quota is blocking.

**Input:** Cleanup candidates from Phase 1 report
**Output:** `_workspace/04_cleanup_report.md`

## Phase 5: Verification

**Run:** `Agent(subagent_type="general-purpose", name="verify-agent", model="opus")`

Use `verify-agent` definition. Check HTTP 200, OG tags, cross-links.

**Input:** URLs from Phases 2+3
**Output:** `_workspace/05_verify_report.md`

## Data Flow

```
Phase 0: Context → Phase 1: site-inspector → 01_inspector_report.md
                                                       ↓
Phase 2: content-publisher (fan-out to N domains) → 02_publish_report.md
                                                       ↓
Phase 3: wp-mutator → 03_wp_report.md
                         ↓ (if blocked by quota)
Phase 4: space-reclaimer → 04_cleanup_report.md → retry Phase 3
                         ↓
Phase 5: verify-agent → 05_verify_report.md
                         ↓
              Final summary to user
```

## Error Handling

| Situation | Response |
|-----------|----------|
| Disk quota exceeded anywhere | Stop, run Phase 4, then retry the failed phase once |
| Phase 2 agent fails (1 domain) | Mark domain FAILED, continue other domains |
| Phase 3 fails (quota) | Skip, report BLOCKED, recommend Phase 4 |
| Phase 5 finds HTTP errors | Re-run Phase 2 for failing domains only |
| cPanel API timeout | Retry once with 10s longer timeout |

## Test Scenarios

### Normal: Full pipeline
1. Request: "Publish article to all domains"
2. Phase 0: no workspace → fresh run
3. Phase 1: site-inspector checks all 8 domains
4. Phase 2: 8 content-publisher agents in parallel
5. Phase 5: verify-agent checks all published URLs
6. Output: verification report with all pass/fail

### Error: Disk quota blocking
1. Request: "Fix electricjobs.eu WP config"
2. Phase 1: inspect electricjobs.eu
3. Phase 3: wp-mutator tries to write PHP → "Disk quota exceeded"
4. Error handler triggers Phase 4: space-reclaimer 
5. Phase 4 frees space
6. Retry Phase 3 → success
7. Phase 5: verify WP settings applied
8. Output: "WP configured. Quota was X MB, freed Y MB."
