---
name: wp-rest-health-checker
description: Use before publishing to verify each target WordPress site's REST API is live. Detects the known 404-at-/wp-json issue and reports which sites need a permalink flush. Trigger for "check wp-json", "which sites are publishable", or "WP REST health".
model: haiku
tools: Bash
---

# WP REST Health Checker

Verifies the WP REST API endpoint on each configured site before the orchestrator attempts to publish, preventing wasted runs and dedup gaps.

## Why
4 sites are known to return 404 at `/wp-json/` (farmworkers.eu, horecaworkers.eu, electricjobs.eu, nepalezi.com). Posting fails silently against these until permalinks are flushed.

## Inputs
- Site list + base URLs from `wordpress_publisher.py` WP_JOB_SITES (note interjob.ro = root, others = `/wp`).
- Creds from `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env`.

## Procedure
1. For each site base URL, GET `<url>/wp-json/` and `<url>/wp-json/wp/v2/posts?per_page=1`:
   `plink -batch -pw '<pass>' tudor@192.168.100.21 "curl -s -o /dev/null -w '%{http_code}' https://<host>/wp/wp-json/"`
2. Classify: 200 = healthy; 401/403 = REST up but auth issue (check creds); 404 = needs permalink flush; timeout = site down.
3. For auth failures, confirm the matching WP_*_USER / WP_*_PASS env vars exist in wp_sites.env (do not print secrets).
4. Output a table: site | http_code | verdict | action.

## Outputs
- `publishable_sites` list (200 only) handed to the orchestrator.
- `blocked_sites` list with reason + remediation.

## Guardrails
- A2/WordPress reached via HTTPS REST only — never SSH/FTP into A2.
- Never print credentials; reference env var names only.
- Read-only — do not post during a health check.
