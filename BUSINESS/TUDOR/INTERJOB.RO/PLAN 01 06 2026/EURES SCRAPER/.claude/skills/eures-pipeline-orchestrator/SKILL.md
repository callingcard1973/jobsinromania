---
name: eures-pipeline-orchestrator
description: Use when operating the EURES EU job-scraping pipeline — triggers like "run EURES pipeline", "EURES scrape", "classify EURES jobs by sector", "EURES status", "EURES dashboard down", "build EURES Brevo segments", or daily EURES operations. Coordinates the eures-orchestrator + scrape-monitor + classify-router + health agents.
---

# EURES Pipeline Orchestrator

Trigger skill for the EURES SCRAPER harness. Activates the EURES agent team against the real pipeline on raspibig.

## When to use
- "Run the EURES pipeline" / "scrape EURES" → eures-orchestrator → eures-scrape-monitor
- "Classify EURES jobs" / "sector breakdown" / "Brevo segments" → eures-classify-router
- "EURES status" / "dashboard down" / "run failed" → eures-health
- Scheduled daily cycle (03:00 UTC)

## Ground truth
- Pipeline: `/opt/ACTIVE/EURES/eures_orchestrator.py` — flags `--run-full|--scrape-only|--normalize|--classify|--publish|--status`
- DB `interjob_master`: `eures_jobs`, `eures_employers`; state.json + stats.db
- Dashboard :8098 (`eures_dashboard.py`)
- raspibig: `& "C:\Program Files\PuTTY\plink.exe" -batch -pw 'REDACTED' tudor@192.168.100.21 "<cmd>"`

## Daily cycle
1. eures-orchestrator pre-flight (DB + dashboard up).
2. eures-scrape-monitor → `--scrape-only` (resume, 2 workers).
3. eures-classify-router → `--normalize` → `--classify` → `--publish` (segment counts).
4. eures-health → stats.db row, systemd, logs, SLA.
5. Hand sendable segments to shared campaign-launcher (+ dnc-manager/bounce-monitor) — do not send from here.

## Guardrails
- 2-worker hard cap. Brevo publish = placeholder (segments ready, not sent).
- Never disable services silently. Quote spaced paths. raspibig via plink only; A2 via cPanel API only.
