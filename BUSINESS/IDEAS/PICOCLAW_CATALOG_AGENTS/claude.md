# PICOCLAW CATALOG AGENTS (IDEA-046 overflow)

Agenti autonomi pentru generare si deploy cataloage angajatori pe 9 domenii x 20 tari.

## Ce face
- `generate_catalogs.py` — genereaza HTML cataloage din DB PostgreSQL
- `agent_catalog_updater.sh` — actualizeaza zilnic si deploye pe A2 Hosting
- `agent_data_quality.py` — verifica calitate date (emailuri invalide, duplicatri)
- `picoclaw_watchdog.py` — monitorizeaza agentii, restart la crash
- `nodered_agents_flow.json` — flow Node-RED pentru orchestrare

## Status
Parte din IDEA-046 CATALOG GENERATOR PLATFORM. Scripts live pe raspibig.
Deploy target: A2 Hosting via cPanel API.
