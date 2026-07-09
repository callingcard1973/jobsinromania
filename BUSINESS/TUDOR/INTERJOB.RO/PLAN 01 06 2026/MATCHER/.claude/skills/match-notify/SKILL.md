---
name: match-notify
description: Notify both sides of new candidate-job matches — send the worker their top matching jobs (ASCII email / WhatsApp) and surface the candidate to the employer/internal team — gated by DNC + ledger dedup, dry-run by default. Use when asked to "notify matches", "tell workers about jobs", "send match digests", or "alert employers about candidates".
---

# match-notify

Turn `ij_matches` rows (status='new') into outbound notifications on both sides. This is where matches become leads. Reuses the shared brevo-sender (worker email), the raspi WhatsApp gateway, and dnc-manager (suppression).

## Gating (in order)
1. **Dedup**: skip any pair already `notified_worker=true`. The ledger is the guard against re-spamming.
2. **DNC**: strip suppressed candidates (dnc-manager). Never message an opt-out.
3. **Dry-run default**: print exactly what would send + to whom. Live send only when the user explicitly says so.

## Sending
- **Worker**: ONE digest of their top 3-5 matching jobs (not one email per job) — relevance over volume. Occupation-routed sender domain. **ASCII subject+body**, NFKD-fold names/occupations. WhatsApp via gateway = plain text.
- **Employer/internal**: a digest of new candidates by occupation to the sales inbox — the revenue side (pay-per-lead).
- On confirmed send only: set `notified_worker=true, notified_at=now()`.

## Why dry-run default + digest
A bad match batch (loose scoring, wrong occupation map) emailed live damages sender reputation and trust. Dry-run lets you eyeball the batch; the digest format caps volume so one worker never gets 15 emails.

## Failure modes
- Channel down (Brevo/gateway) → leave rows status='new', report DEGRADED, retry next run. **Never** mark notified without a confirmed send — that silently drops the lead.
- Email creds missing → do worker WhatsApp + employer digest, skip email, report.
