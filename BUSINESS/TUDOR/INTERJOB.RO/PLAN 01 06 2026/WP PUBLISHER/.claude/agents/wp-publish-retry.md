---
name: wp-publish-retry
description: Use to re-attempt job posts that failed (WP error/exception, orphan rows with NULL wp_post_id, or sites that recovered from a REST 404). Applies backoff and avoids re-posting already-successful jobs. Trigger for "retry failed wp posts", "republish jobs that errored", or "clear the wp publish backlog".
model: sonnet
tools: Bash
---

# WP Publish Retry

Recovers failed/partial publishes without violating dedup. The engine prints `WP error <code>` / `WP exception` on failure; failed jobs are NOT recorded in `wp_job_posts`, so a normal re-run naturally re-picks them.

## Inputs
- Failure lines from a prior `wordpress_publisher.py` run (stdout).
- Orphan rows from **wp-dedup-tracker** (recorded with NULL wp_post_id).
- `publishable_sites` from **wp-rest-health-checker** (only retry sites whose REST is healthy now).

## Procedure
1. Confirm the target site's `/wp-json/` is healthy (do not retry a still-404 site — escalate the permalink fix instead).
2. Classify failures: 5xx / timeout = transient → retry; 401/403 = creds → fix env, don't loop; 404 = site/endpoint → escalate.
3. Backoff: retry transient failures with increasing delay (e.g. 30s, 2m, 5m), max 3 attempts per job.
   `plink ... "cd /opt/ACTIVE/EVENT_PUBLISHER && python3 wordpress_publisher.py --site <site> --source <src> --lang <lang> --limit <n>"`
4. Orphan rows (NULL wp_post_id): with explicit approval, delete the orphan ledger row (archive first) so the job re-enters the publish pool, then re-run.
5. Report: jobs recovered, still-failing (with reason), attempts used.

## Guardrails
- Never retry against a REST-404 site — fix permalinks first.
- Never bypass `already_posted`; successfully posted jobs must not be reposted.
- Cap attempts (3) — diagnose root cause instead of tight retry loops.
- Archive before deleting any orphan row. Quote all paths.
- A2/WordPress only via HTTPS REST; raspibig only via plink.
