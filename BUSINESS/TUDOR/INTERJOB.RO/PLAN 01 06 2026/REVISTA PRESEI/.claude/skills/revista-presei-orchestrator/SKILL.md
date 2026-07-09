---
name: revista-presei-orchestrator
description: Orchestrate the REVISTA PRESEI daily press-review pipeline for expatsinromania.org — fetch RSS → summarize+translate → WordPress publish + RSS deploy → social fan-out → health monitor. Use when running the press review, regenerating the daily review, republishing, debugging a failed/missing review, adding sources, or checking press-review health. Triggers: "run the press review", "rerun press review", "regenerate today's review", "publish press review", "press review status", "why didn't the press review post", "press review failed", "add a press source", "redo the press review publish/social/fetch".
---

# revista-presei-orchestrator

Coordinates the 5-agent REVISTA PRESEI press-review harness. **Execution mode: agent team** (pipeline pattern — sequential stages with file-based handoff). All agents `model: opus`.

Live pipeline on raspibig `/opt/ACTIVE/EVENT_PUBLISHER/`, cron daily 08:50 UTC. This orchestrator reproduces/repairs/extends that run from Claude Code.

## Team
| Stage | Agent | Skill | Output artifact |
|-------|-------|-------|-----------------|
| 1 | rss-fetcher | press-rss-fetch | `_workspace/01_rss-fetcher_articles.json` |
| 2 | content-summarizer | press-summarize | `_workspace/02_*_body.html` + `_articles.json` |
| 3 | wp-publisher | press-wp-publish (+ a2-wp-bootstrap) | `_workspace/03_*_result.json` |
| 4 | social-distributor | press-social-distribute | `_workspace/04_*_result.json` |
| 5 | press-monitor | infrastructure-health | `_workspace/05_*_health.json` |

## Phase 0: context check (run first)
- `_workspace/` absent → **initial run**: full pipeline 1→5.
- `_workspace/` present + user asks partial ("redo publish", "just the social", "re-fetch") → **partial re-run**: invoke only the named stage(s) onward, reusing upstream artifacts.
- `_workspace/` present + new input (new sources, force) → **new run**: move `_workspace/` → `_workspace_prev/`, start fresh.

## Phase 1: fetch
Spawn rss-fetcher. Hard gate: 0 articles → STOP, report per-source status. Do not run downstream on empty.

## Phase 2: summarize
Spawn content-summarizer on the article JSON. Ollama/translate failures degrade gracefully (fallback summaries) — continue, note degraded mode.

## Phase 3: publish
Spawn wp-publisher. Respects `already_posted(today)`. Missing WP creds → persist DB, skip WP, report. Produces wp_url.

## Phase 4: distribute
Spawn social-distributor ONLY if Phase 3 yielded wp_url + wp_post_id. Best-effort per channel.

## Phase 5: monitor
Spawn press-monitor (read-only). Emits the daily verdict: OK | DEGRADED | FAIL + blockers.

## Data protocol
File-based handoff under `_workspace/`, naming `{NN}_{agent}_{artifact}.{ext}`. Intermediate files preserved for audit; only the live WP post + feed.xml are the external outputs.

## Error handling
- One retry per stage; on second failure proceed without that stage's output and record the gap in the monitor verdict.
- Conflicting/duplicate articles: dedup by URL hash, never delete — keep source attribution.
- Stages 1 (empty) and 3 (no wp_url) are hard gates for their downstream; all else is best-effort.

## Test scenarios
- **Happy path:** fetch 15 → summarize → WP post live → FB+Mastodon+Telegram posted → monitor OK.
- **Ollama down:** Phase 2 fallback summaries for all → still publishes → monitor DEGRADED (notes fallback).
- **WP creds missing:** Phase 3 persists DB, skips WP, no wp_url → Phase 4 skipped → monitor FAIL (blocker: WP_PASS).
- **Already posted:** Phase 3 gate hits → report existing URL, skip 4 → monitor OK (no-op).

## Follow-up keywords
"rerun", "redo", "update", "regenerate", "republish", "just the {stage}", "fix the press review", "press review status".
