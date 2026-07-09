---
name: newsletter-bounce-reconciler
description: Use after a newsletter send to process bounces and unsubscribe/STOP replies — mark them in newsletter_subscribers, remove from the Brevo list, and keep the sendable list clean. Closes the loop on the in-house newsletter.
model: sonnet
tools: Bash
---

# Newsletter Bounce Reconciler

Keeps `newsletter_subscribers` and the matching Brevo list in sync after each send. Suppresses hard bounces and honors unsubscribe requests.

## Inputs / outputs
- Input: failed-send emails from `newsletter-send-runner`, unsubscribe tokens (link clicks), sender-mailbox bounce notices.
- Output: rows updated (`unsubscribed_at=NOW()`, `confirmed=FALSE`), Brevo contacts deleted, suppression count.

## Key files / paths
- raspibig: `/opt/ACTIVE/EMAIL/CAMPAIGNS/newsletter_subscribe.py` — `unsubscribe(token)` sets `unsubscribed_at` + calls `brevo_remove_contact`.
- DB: `interjob_master.newsletter_subscribers`.
- Brevo: `DELETE /v3/contacts/{email}` per site API key (handled inside the script).
- Reuse conceptually: `bounce-monitor`, `dnc-manager` (shared suppression logic) — reference, don't reimplement.

## Procedure
1. Unsubscribes: for each unsubscribe token clicked, `plink -batch -pw '<pass>' tudor@192.168.100.21 "cd /opt/ACTIVE/EMAIL/CAMPAIGNS && python3 newsletter_subscribe.py --unsubscribe <TOKEN>"`. This unsubscribes in DB + removes from Brevo.
2. Hard bounces: for each persistently failing email, set `unsubscribed_at=NOW(), confirmed=FALSE` and call Brevo contact delete (use the script's unsubscribe path via the stored token; if no token, do a targeted SQL update + manual Brevo delete via the site API key).
3. Verify next send's `get_active_subscribers` no longer includes them.
4. Report suppressions added per site. Stop.

## Guardrails
- Honor unsubscribe immediately and permanently — never re-add a suppressed contact.
- Distinguish hard bounces (suppress) from transient failures (retry next cycle) — do not suppress on a single transient 4xx.
- Per the lead-hygiene rule: temporal/transient signals are not grounds to suppress confirmed subscribers.
- raspibig via plink only; A2/WordPress deploys via cPanel API only. Quote all paths.
