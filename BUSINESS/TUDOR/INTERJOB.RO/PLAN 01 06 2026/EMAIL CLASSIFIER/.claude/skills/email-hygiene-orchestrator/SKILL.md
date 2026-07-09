---
name: email-hygiene-orchestrator
description: Orchestrate inbox hygiene + form-lead routing — gently purge CV-attachment emails across all A2/Gmail/Yahoo inboxes (saving attachments first), and route web3forms submissions into fw_candidates / form_employer_leads. Use when asked to "clean the inboxes", "purge CV emails", "free mailbox quota", "process form submissions", "route site leads", "run email hygiene", or "drain the form inbox".
---

# email-hygiene-orchestrator

Coordinates the 2-agent email-hygiene harness (sibling to the email-classifier harness in this folder). **Execution mode: agent team** (two independent streams, not a chain). All agents `model: opus`. Wraps `ANOFM/CODE/cv_purge.py` + `form_router.py`.

## Two streams (run independently)
| Stream | Agent | Source | Sink |
|--------|-------|--------|------|
| Inbox purge | inbox-purger | 31 A2 + 4 Gmail/Yahoo inboxes | CV store + expunge |
| Form routing | form-router | web3forms EML inbox | fw_candidates / form_employer_leads |

These do not depend on each other — run either alone or both. They share only the CV_INBOX storage root.

## Phase 0: context check
- partial request ("just purge", "just route forms") → run that stream only.
- otherwise → run both.

## Inbox purge
inbox-purger over A2 (chunked, reconnecting, ~2s pause — A2 rate-limit/socket-EOF friendly) + Gmail/Yahoo. **Save attachment before expunge, always.** Rate-limited account → back off + resume, never lose a chunk.

## Form routing
form-router classifies worker vs employer (default worker), inserts with site-derived occupation, dedups (phone|email / contact). DB down → leave EMLs, DEGRADED, reprocess next run. Never delete an EML pre-commit.

## Deployment note
Both run as **systemd timers** on their hosts (purge gentle/frequent; form-router 30 min Persistent=true), NOT crontab — campaign deploy scripts do full `crontab -` REPLACE and evict cron lines (classifier was dead 6 days from this). Prefer systemd timers.

## Lead-hygiene rule
Never suppress on temporal/negative signals. Every CV and every submission is a lead; dedup prevents doubles, it does not drop people.

## Test scenarios
- **Purge**: 508 CV mails across 35 inboxes → saved + deleted in chunks, 0 lost, 2 A2 accounts rate-limited (resumed).
- **Route**: 28 form EMLs → 28 workers, 0 employers (site forms attract workers) → inserted, dupes skipped.
