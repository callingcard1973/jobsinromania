# SESSION HANDOFF — 14-15 Aprilie 2026
# DB Enrichment + Cleanup + TED Campaign + Orchestrator Fix + Laptop PG18

---

## CE S-A FACUT

### 1. Orchestrator Audit — 6 dead Brevo keys fixed
- 3 keys moarte (INTERJOB, NEPALEZI, HORECAWORKERS2026_COM) blocau 26 sectoare
- +3 keys moarte (MIVROMANIA_ONLINE, FARMWORKERS, HORECAWORKERS_COM)
- Toate 26 referintele remapate pe keys funcionale
- Norway trimtea 0/zi, acum deblocat (16 sectoare active)
- Validator cron: `/opt/ACTIVE/EBRD/validate_campaigns.py` zilnic 6AM

### 2. Enrichment — Ce a functionat
- **RO CUI matches:** master_romania 5,811 + romania_campaign 498 + insolvency 415 + unique_emails 187 = **6,911 emailuri noi RO**
- **FR pattern enrichment (raspibig):** 30,400+ emailuri (info@domain din MX check)
- **FR+NO website scraping (raspibig):** ~4,400+ emailuri (inca ruleaza)
- **RO domain guess (laptop):** ~300 emailuri
- **TED cross-ref RO (laptop):** 1,700 emailuri

### 3. Enrichment — Ce a esuat (LECTIE)
- TED cross-ref pe normalized name (ALL countries) → 8.8M false matches
- Cauza: short names (3 char) matchuiau mii de firme nerelated
- Placeholder emails (bruker@domene.no, user@domain.com) propagate
- Revert partial facut; companies table inca poluat pt non-RO
- **LECTIE: companies (209M) e data warehouse, nu sursa de campanie**

### 4. TED Campaign — CREAT, 374,989 emailuri
- `ted_campaign` table separata (nu in companies)
- Deduplicate, fara placeholders, indexuri create
- 5 configs: DE 64K, FR 55K, SE 30K, ES 25K, PL 22K
- 250/zi per tara = 1,250/zi total
- Template: workforce for EU procurement winners
- **Toate enabled: false — asteapta aprobare Tudor**

### 5. D3 AgroEvolution + D4 Insolvency (sesiunea precedenta, inca active)
- premium.php LIVE pe agroevolution.com
- alerte-insolventa.html LIVE pe cifn.eu + cifn.info
- 3 campanii configurate (1,111 + 2,451 + 2,190 contacte)

---

## CE ASTEAPTA APROBARE TUDOR

| # | Campanie | Emailuri | Ritm | Config |
|---|----------|---------|------|--------|
| 1 | TED Germany | 64,063 | 250/zi | ted_campaign_de.json |
| 2 | TED France | 55,182 | 250/zi | ted_campaign_fr.json |
| 3 | TED Sweden | 29,557 | 250/zi | ted_campaign_se.json |
| 4 | TED Spain | 25,126 | 250/zi | ted_campaign_es.json |
| 5 | TED Poland | 22,490 | 250/zi | ted_campaign_pl.json |
| 6 | Norway accelerare | 154,438 | 200→500/zi | norway.json daily_limit |
| 7 | EBRD Romania | 685 | 50/zi | ebrd_constructori.json |
| 8 | EBRD 5 tari | 1,844 | 50/zi each | 5 configs |
| 9 | AgroEvolution premium | 1,111 | 100/zi | agroevolution_premium.json |
| 10 | Insolventa liquidatori | 2,451 | 50/zi | cifn_insolvency.json |
| 11 | Insolventa companii | 2,190 | 50/zi | cifn_insolvency_companies.json |
| 12 | Agencies D2 | 18,133 | 500/zi | recruitment_agencies.json |
| **TOTAL** | | **~377K** | **~2,500/zi** | |

---

## CE TREBUIE FACUT URMATOAREA SESIUNE

### P1: Cleanup companies table (NOAPTE, cron)
- companies (209M) e poluat cu emailuri false din TED cross-ref
- Revert: NULL email WHERE updated_at 2026-04-14 AND country NOT IN ('RO','NO')
- Rulat partial, trebuie finalizat
- PLAN complet: `D:\MEMORY\IDEAS\PLAN_DB_CLEANUP_ENRICHMENT.md`

### P2: Accelerare Norway (5 min, Tudor aproba)
- 154K pending, daily_limit 200 → 500
- Keys fixate, 16 sectoare active

### P3: Activare TED campaigns (Tudor aproba)
- 5 configs, set enabled: true
- 374K emailuri, 1,250/zi

### P4: Gumroad data packages (Tudor creeaza cont)
- 5 CSV-uri gata, EUR 29-199 fiecare

### P5: Data quality cron
- Zilnic verifica: email counts per country, placeholders, duplicates >5

---

## DB STATE (14 Aprilie 2026)

### Tabele de campanie (CURATE, gata de folosit):
| Tabel | Rows | Cu email | Status |
|-------|------|----------|--------|
| ted_campaign | 374,989 | 374,989 | NOU, curat |
| norway_campaign | 154,984 | 154,438 | OK |
| romania_campaign | 372,224 | 357,084 | OK |
| master_emails | 1,008,280 | 1,008,233 | OK |

### Tabel mare (POLUAT, de curatat la noapte):
| Tabel | Rows | Cu email (corect) | Cu email (actual) |
|-------|------|-------------------|-------------------|
| companies | 209,480,390 | ~440K | ~9M (poluat) |

### Brevo API Keys Status (14 Apr):
**Working (13):** AGROEVOLUTION, BPPLTD, BUILDJOBS, CAREWORKERS, CIFN, CUMPARLEGUME, EXPATSINROMANIA, FACTORYJOBS, HORECAWORKERS2026_EU, MEATWORKERS, MIVROMANIA, SEICARESCU, WAREHOUSEWORKERS
**Dead (6):** INTERJOB, NEPALEZI, HORECAWORKERS2026_COM, MIVROMANIA_ONLINE, FARMWORKERS, HORECAWORKERS_COM

### Cron jobs activi:
- Orchestrator: 5min cycle, 38 sender groups
- EBRD procurement monitor: zilnic 9AM
- Insolvency monitor: zilnic 7AM
- Campaign validator: zilnic 6AM
- Enrichment FR+NO: ruleaza pe raspibig (pattern + scrape)
- Domain guess RO: ruleaza pe laptop

---

## LECTII INVATATE

1. **companies (209M) = warehouse, nu sursa campanie** — campaniile au tabele proprii
2. **Cross-ref pe name: min 8 chars, COUNT inainte** — altfel false positives explodeaza
3. **CUI match > name match** — CUI e unic, name nu
4. **Brevo keys mor silentios** — validator zilnic obligatoriu
5. **Nu rula UPDATE-uri paralele pe aceeasi tabela** — deadlocks
6. **Pi5 + HDD = lent pe 209M rows** — accepta realitatea, lucreaza cu tabele mici

---

## LAPTOP POSTGRESQL (adaugat 15 Aprilie 2026)

### Setup complet
- **PG18** pe port **5433** (nu 5432)
- **Data dir:** D:\DATABASES\pgdata18
- **208,499,297 companies** + 293 tabele — mirror complet raspibig
- **SSD** — queries 10-50x mai rapide decat Pi HDD
- **Dump:** D:\DATABASES\interjob_master.dump (14 GB) — poate fi sters dupa confirmare

### Connect
```bash
PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master
```

### Start/Stop
```bash
"/c/Program Files/PostgreSQL/18/bin/pg_ctl.exe" start -D "D:/DATABASES/pgdata18" -l "/d/DATABASES/pg18.log"
"/c/Program Files/PostgreSQL/18/bin/pg_ctl.exe" stop -D "D:/DATABASES/pgdata18"
```

### C: Drive cleanup facut
- .lmstudio (103 GB) — de mutat pe D: sau I: (nu s-a facut inca)
- Jan.ai (19 GB) — de sters (Qwen e pe raspibig)
- Temp + npm + gpt4all + recycle bin: sterse (+9 GB)
- C: de la 99% → 84% (87 GB free)

### Ce urmeaza pe laptop DB
1. Cleanup companies table (revert TED pollution) — RAPID pe SSD
2. Safe CUI enrichment (ONRC, master_romania, romania_campaign)
3. TED cross-ref cu min 8 chars (COUNT first)
4. Dump slim DB, push back la raspibig
5. Sterg dump-ul de 14 GB dupa confirmare

### Orchestrator raspibig — TRIMITE ACUM
- Norway: CONSTRUCTION 79, RETAIL 148, HORECA 88, SHIPYARD 43 per pass
- ANOFM: Lucian 40, Virgil 29, Gmail 12 per pass
- **~800+ emailuri/zi** (de la 50/zi inainte de fix)
