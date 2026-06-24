---
name: newsletter-orchestrator
description: Use when operating the in-house Brevo newsletter for interjob.ro / expatsinromania.org — triggers include "run the newsletter", "send the daily newsletter", "confirm a subscriber", "process opt-ins", "newsletter status", "clean newsletter bounces", "unsubscribe a subscriber", or when working in the NEWSLETTER folder. Coordinates double opt-in validation, segmentation, daily WP-sourced send, and bounce/unsubscribe reconciliation.
---

# Newsletter Orchestrator Skill

Entry point for the NEWSLETTER harness. Routes to the right agent and runs the daily cycle.

## When to use
- "Run / send the daily newsletter" → full cycle below.
- "Newsletter status" / "how many subscribers" → `newsletter-optin-validator`.
- "Confirm subscriber <token>" → `newsletter-optin-validator`.
- "Unsubscribe <token>" / "clean bounces" → `newsletter-bounce-reconciler`.
- "Dry-run the send" → `newsletter-send-runner` with `--dry-run`.

## System facts
- Sites: `expatsinromania.org` (en), `interjob.ro` (ro).
- Scripts on raspibig: `/opt/ACTIVE/EMAIL/CAMPAIGNS/newsletter_subscribe.py` + `newsletter_sender.py`.
- DB: `interjob_master.newsletter_subscribers`. Brevo per-site API key in `.env`.
- raspibig access: `"C:\Program Files\PuTTY\plink.exe" -batch -pw '<pass>' tudor@192.168.100.21 "<cmd>"`.

## Full daily cycle (steps)
1. Health gate: `--status` to confirm DB + per-site counts.
2. Opt-in pass (`newsletter-optin-validator`): confirm pending tokens, report active/pending/unsub, flag stale unconfirmed (>14d).
3. Send pass (`newsletter-send-runner`): per site dry-run → verify post + count (≤300) → live send. Skip sites with no WP post or 0 subscribers.
4. Reconcile (`newsletter-bounce-reconciler`): process unsubscribes + hard bounces, sync to Brevo.
5. Summarize sent/failed, new confirms, suppressions. Stop — present data, wait for instruction.

## Guardrails
- Double opt-in is mandatory (GDPR) — never set confirmed=TRUE without a real token.
- Brevo free tier = 300/day per account; flag and stop if exceeded.
- raspibig via plink only; A2/WordPress deploys via cPanel API only; never SSH to A2.
- Quote all paths (spaces in folder names).
