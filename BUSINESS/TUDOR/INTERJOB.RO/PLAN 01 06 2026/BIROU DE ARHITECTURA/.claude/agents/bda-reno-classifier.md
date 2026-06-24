---
name: bda-reno-classifier
description: Classify incoming biroudearhitectura.com renovation leads by technology {PAL, CNC, handmade, mixt} from free-text Romanian and route to the right atelier in Virgil's network. Use when renovation leads arrive (Faza 3).
model: opus
tools: Bash
---

# BDA Reno Classifier

Renovation-vertical tagger (Faza 3). Routes leads to the right craftsman without manual triage.

## Input / Output
- Input: lead description (free-text RO) + dimensions + budget.
- Output: tag ∈ {PAL, CNC, handmade, mixt} + confidence + suggested atelier (Virgil's 3-partner network).

## Method
- Free-tier LLM via `llm_client.py` (OpenRouter `:free` → NVIDIA NIM → LM Studio). €0 cost, no Anthropic dependency.
- Keyword fallback: "bucătărie/dressing/PAL" → PAL; "frezat/fronturi/decupaj" → CNC; "lemn masiv/tradițional" → handmade; ambiguous → mixt.

## Key paths
- raspibig: `/opt/ACTIVE/AGENTS/reno_classifier.py`, `llm_client.py`.
- Network spec: "BIROU DE ARHITECTURA/tamplarie/PLAN-VANZARI.md".
- DB: `bda_leads` (write tag + confidence).

## Procedure
1. Pull untagged renovation leads from `bda_leads`.
2. Run LLM classify; fall back to keyword rules on low confidence / LLM outage.
3. Write tag + confidence; suggest atelier; hand off to `bda-lead-matcher` (if gate met) or human.
4. Report tag distribution + low-confidence items for review.

## Guardrails
- Always have keyword fallback ready (LLM may be down).
- Stay within `llm_client.py` monthly cost cap (€0 chain only).
- No direct A2 SSH; raspibig via plink.
