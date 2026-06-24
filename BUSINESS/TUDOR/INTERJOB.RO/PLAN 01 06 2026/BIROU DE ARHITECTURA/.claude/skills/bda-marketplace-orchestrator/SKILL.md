---
name: bda-marketplace-orchestrator
description: Use when operating the biroudearhitectura.com architect lead-gen marketplace — triggers include "run BDA cycle", "seed architects", "hunt architects", "match a lead", "classify renovation lead", "deploy BDA plugin/SEO pages", "BDA status", or working in the "BIROU DE ARHITECTURA" folder. Coordinates the 5 BDA agents and enforces the Faza 1→4 phase gate.
---

# BDA Marketplace Orchestrator

Trigger skill for the biroudearhitectura.com architect lead-gen harness. Routes to `bda-orchestrator` and its specialists.

## When to use
- "Run the BDA cycle" / daily marketplace operation.
- Seed/refresh architects, match a client lead, classify a renovation lead, deploy plugin or SEO pages, or get BDA status.
- Any work inside "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\BIROU DE ARHITECTURA".

## Agents
| Agent | Role | Phase |
|-------|------|-------|
| bda-orchestrator | Route + gate + status | all |
| bda-architect-hunter | Seed/score master_architects | Faza 1 |
| bda-reno-classifier | Tag renovation leads | Faza 3 |
| bda-lead-matcher | Match leads to ≤3 architects (gated ≥30 verified) | Faza 4 |
| bda-seo-deployer | SEO pages + WP deploy via cPanel | Faza 4 |

Reuse: campaign-launcher, bounce-monitor, dnc-manager (outreach); cpanel-deployer / cpanel-wp-deploy (A2); infrastructure-health (raspibig/PostgreSQL); brevo-dns-a2, brevo-sender-onboarding.

## Usage steps
1. Read "BIROU DE ARHITECTURA/CLAUDE.md" + "AGENTS.md" for current phase.
2. Invoke `bda-orchestrator`: it counts verified architects and routes the request.
3. For deploys, confirm cPanel API path (no SSH). For raspibig DB/agents, use plink.
4. Return numbered status: counts, blockers, next action. Stop; wait for selection.

## Guardrails
- Hard gate: no auto lead-matching until 30+ verified architects (score≥60, status='verified').
- A2/WP deploys via cPanel API only. Faza 1 outreach is human, not automated.
- LLM tasks use free `llm_client.py` chain (€0).
