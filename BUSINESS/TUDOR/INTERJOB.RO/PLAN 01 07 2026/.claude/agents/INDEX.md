# PLAN 01 07 2026 — Agent Definitions Index

**Regenerated from disk:** 2026-06-30 · 22 agents (INDEX.md excluded)

Core router = `plan-iulie-orchestrator` skill + the 3 directie leads (`coop-lead`,
`manpower-lead`, `iscir-lead`) + `plan-router`. Everything else is an **imported
copy** kept for reference — the real live versions run from their June
(`PLAN 01 06 2026/...`) domain harness folders, not from here.

| Agent | Role | Wired-in-router? |
|-------|------|------------------|
| coop-lead | Sef directie COOP GOSPODARII DE ALTADATA — outreach export legume-fructe (producatori, OP, RNCA, cumparatori); sender office@cumparlegume.com | YES (core) |
| manpower-lead | Sef directie INTERJOB MANPOWER — recrutare/plasare: joburi deficit ANOFM, EURES, catalog candidati, matching, AMT | YES (core) |
| iscir-lead | Sef directie ISCIR — monetizare date echipamente sub presiune: firme client, operatori RSVTI, autorizatii, upsell demo-site | YES (core) |
| plan-router | Dispecer PLAN 01 07 2026 — citeste cererea, alege directia (COOP/MANPOWER/ISCIR) sau cross-directie, deleaga | YES (core) |
| alert-triage | Catch raspibig/raspi Telegram health alerts, match runbook, read-only diagnose, propose/execute fix | imported/unwired — delegates to June domain harness |
| bpp-orchestrator | Orchestrate BPPLTD.CO.UK two-sided deficit loop — source 7 ANOFM occupations, publish, outreach, match, report | imported/unwired — delegates to June domain harness |
| content-publisher | Publish HTML content (articles, OG tags, cross-links) to static A2 sites via cPanel API | imported/unwired — delegates to June domain harness |
| deal-broker | Brokerul marketplace — deschide dealuri din match oferta<->cerere, intro drafturi ASCII, urmareste status (gated) | imported/unwired — delegates to June domain harness |
| dnc-scanner | Scan 125+ A2 mailboxes over IMAP for opt-outs, confirm by body, emit DNC suppression list | imported/unwired — delegates to June domain harness |
| electricjobs-orchestrator | Orchestrate ELECTRICJOBS.EU two-sided loop — electrical contracts, publish, electrician outreach, match, report | imported/unwired — delegates to June domain harness |
| eures-outreach-orchestrator | Orchestrate EURES employer cold-email on raspibig — audience, sector senders, ramp, DB-unique suppression | imported/unwired — delegates to June domain harness |
| infrastructure-health | Monitor INTERJOB.RO infra — raspibig CPU/mem/disk, PostgreSQL, crons, systemd | imported/unwired — delegates to June domain harness |
| offers-keeper | Tine minte oferte trimise + cereri primite, match automat pe tag-uri (offers/requests ledger) | imported/unwired — delegates to June domain harness |
| offers-responder | Raspunde la replicile la oferte — clasifica intentia, draft ASCII gated; opt_out/bounce => DNC | imported/unwired — delegates to June domain harness |
| pipeline-orchestrator | Coordinate INTERJOB.RO daily data pipeline — validate jobs/lands, enrich DB, regenerate catalogs | imported/unwired — delegates to June domain harness |
| price-memory-keeper | Tine minte propunerile de pret Mega Image (IMAP read-only), sugereaza contra-pret | imported/unwired — delegates to June domain harness |
| raspi-inspector | Read-only health auditor for raspi (.20) — crontab validation, ANOFM freshness, failed units | imported/unwired — delegates to June domain harness |
| report-generator | Generate daily + weekly INTERJOB.RO reports — KPIs, pipeline, infra, leads, revenue, blockers | imported/unwired — delegates to June domain harness |
| site-inspector | Read-only inspection of A2 sites — list files, read WP configs, audit disk, find cleanup candidates | imported/unwired — delegates to June domain harness |
| space-reclaimer | Free A2 disk quota — delete stale WP installs, error_logs, trash, test files, unused uploads | imported/unwired — delegates to June domain harness |
| verify-agent | Verify published content — HTTP 200, OG tags, cross-links, WP permalink resolution | imported/unwired — delegates to June domain harness |
| wp-mutator | Configure WordPress on A2 via PHP bootstrap (write PHP, curl execute, delete) — title/tagline/permalink/SQL | imported/unwired — delegates to June domain harness |
