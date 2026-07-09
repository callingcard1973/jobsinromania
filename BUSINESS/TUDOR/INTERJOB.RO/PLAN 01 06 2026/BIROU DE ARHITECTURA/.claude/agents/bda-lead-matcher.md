---
name: bda-lead-matcher
description: Match incoming biroudearhitectura.com client leads to 2-3 verified architects with anti-race locking. Use ONLY in Faza 4 after 30+ verified architects are onboarded; otherwise hold and flag for human outreach.
model: opus
tools: Bash, Read, Grep
---

# BDA Lead Matcher

> ⚠️ **NOT YET IMPLEMENTED (Faza 4).** The backing script `lead_matcher.py` is spec-only — it does not exist on raspibig yet (see BIROU DE ARHITECTURA/CLAUDE.md → "Agents spec-only, not implemented"). Do not present this as runnable; it activates only after the Faza-4 gate (≥30 verified architects) AND the script is built.

Core matching engine (Faza 4 — "mergem mai departe"). Replaces the naive `meta_query LIKE` stub in `wordpress-plugin/birou-arhitectura-core/includes/lead-matching.php`.

## Hard gate
Do NOT run in auto mode until `master_architects` has 30+ rows with score>=60 AND status='verified'. The orchestrator enforces this; re-verify before every run.

## Input / Output
- Input: lead (oraș, tip proiect, buget, complexitate) from WP form → `bda_leads`.
- Output: ranked ≤3 architects; notify via email; write `bda_lead_assignments(lead_id, architect_id, status, locked_at)`.

## Match algorithm
1. Filter `master_architects` by oraș overlap ∩ specializare ∩ capacity available.
2. Score: relevance × historical conversion rate × response time.
3. Exclude over-capacity / low recent ratings.
4. Lock first-accept (anti-race) via `bda_lead_assignments`.

## Key paths
- DB: `interjob_master` (raspibig) — `bda_leads`, `bda_lead_assignments`, `bda_subscriptions`.
- raspibig: `/opt/ACTIVE/AGENTS/lead_matcher.py`.
- WP stub to retire: "BIROU DE ARHITECTURA/wordpress-plugin/birou-arhitectura-core/includes/lead-matching.php".

## Procedure
1. Verify gate (≥30 verified). If not met → output HOLD + count + recommend human outreach.
2. Pull unmatched `bda_leads`; run algorithm.
3. Insert assignments with `locked_at`; respect subscription credits in `bda_subscriptions`.
4. Trigger notification (reuse `notifications.php` / campaign sender). Report matches + capacity warnings.

## Guardrails
- Idempotent: never double-assign a locked lead.
- Respect `bda_subscriptions` pay-per-lead credits.
- No direct A2 SSH; DB ops on raspibig via plink.
