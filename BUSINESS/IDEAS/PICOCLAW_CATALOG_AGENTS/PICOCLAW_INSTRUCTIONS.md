# PicoClaw — Instructiuni Agent 3 + Agent 5

## Task Types Noi

### catalog_update
Regenereaza cataloage HTML angajatori pe 9 domenii x 20 tari din PostgreSQL.
Deploy pe A2 Hosting.

**Cum se trimite task:**
```bash
curl -X POST http://localhost:5055/task \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "catalog_update",
    "payload": {"deploy": false},
    "priority": 3
  }'
```

**Ce face:**
1. Interogheaza `no_companies_full` (Norvegia, 1.15M)
2. Interogheaza `master_romania_companies` (Romania, 8.9M)
3. Interogheaza `ted_winners` (20 tari UE, 1.57M)
4. Genereaza HTML per domeniu/tara (max 500 angajatori/pagina)
5. Genereaza sitemap.xml per domeniu
6. Output: `/opt/ACTIVE/WEB/CATALOGS/output/<domeniu>/<tara>/index.html`

**Domenii:** factoryjobs.eu, buildjobs.eu, careworkers.eu, electricjobs.eu, farmworkers.eu, horecaworkers.eu, meatworkers.eu, mechanicjobs.eu, warehouseworkers.eu

**Cron:** duminica 3 AM
**Script:** `/opt/ACTIVE/WEB/CATALOGS/generate_catalogs_raspibig.py`
**Timeout:** 600s (tabele mari)

---

### data_quality_check
Valideaza emailuri, detecteaza duplicate si companii radiate.

**Cum se trimite task:**
```bash
# Dry-run (doar raport, nu modifica nimic)
curl -X POST http://localhost:5055/task \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "data_quality_check",
    "payload": {"table": "master_romania_companies", "fix": false},
    "priority": 2
  }'

# Fix mode (aplica corectii — seteaza emailuri invalide pe NULL)
curl -X POST http://localhost:5055/task \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "data_quality_check",
    "payload": {"table": "master_romania_companies", "fix": true},
    "priority": 1
  }'
```

**Ce face:**
1. Verifica 144K emailuri cu regex strict
2. Detecteaza domenii suspecte (example.com, test.com, etc.)
3. Gaseste duplicate exacte pe email
4. Numara companii radiate care inca au email
5. Genereaza raport text
6. Trimite alerta Telegram daca sunt probleme
7. In fix mode: seteaza emailuri invalide pe NULL + marcheaza data_quality

**Cron:** sambata 4 AM (dry-run)
**Script:** `/opt/ACTIVE/AGENTS/agent_data_quality.py`
**Timeout:** 300s
**Raport:** `/opt/ACTIVE/INFRA/LOGS/data_quality_YYYYMMDD.txt`

---

## Fisiere pe raspibig

```
/opt/ACTIVE/WEB/CATALOGS/
  generate_catalogs.py           — config domenii + HTML templates
  generate_catalogs_raspibig.py  — interogheaza DB, genereaza HTML
  agent_catalog_updater.sh       — cron wrapper

/opt/ACTIVE/AGENTS/
  agent_data_quality.py          — validare + dedup + raport

/opt/ACTIVE/INFRA/GOVERNOR/tasks/
  picoclaw_tasks.py              — plugin PicoClaw (2 task types)
```

## Node-RED

Tab: **"Agents (Catalog + Quality)"**
- Buton "Trigger Catalog Update" — ruleaza generatorul manual
- Buton "Trigger Data Quality" — ruleaza quality check manual
- Output: Telegram alert + debug sidebar

URL: http://192.168.100.21:1880/#flow/tab_agents

## Comenzi rapide

```bash
# Ruleaza catalog manual
cd /opt/ACTIVE/WEB/CATALOGS && python3 generate_catalogs_raspibig.py

# Ruleaza quality dry-run
cd /opt/ACTIVE/AGENTS && python3 agent_data_quality.py --dry-run

# Ruleaza quality cu fix
cd /opt/ACTIVE/AGENTS && python3 agent_data_quality.py --fix

# Verifica output cataloage
ls -la /opt/ACTIVE/WEB/CATALOGS/output/

# Verifica rapoarte quality
cat /opt/ACTIVE/INFRA/LOGS/data_quality_$(date +%Y%m%d).txt

# Verifica cron
crontab -l | grep -E "catalog|quality"
```

## Reguli

- Cataloagele NU publica email/telefon/contact — doar nume firma + oras
- Toate linkurile apply → https://interjob.ro/apply.html
- NU mentiona sursa datelor (ANOFM/EURES/TED)
- Data Quality in dry-run default — fix doar cu aprobare Tudor
- Telegram alerte doar la erori/probleme, nu la succes
