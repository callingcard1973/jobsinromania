# CLAUDE.md — PLAN 01 07 2026 (Iulie)

**v1.0 | 2026-06-28** · Tranzitie din `PLAN 01 06 2026` (Iunie)

Foloseste mereu harness. Verifica mereu terenul (raspibig/raspi/DB/A2), nu harta.
Raspunsuri NUMEROTATE (1, 2, 3...), fara intrebari in proza. Romana.

---

## SCOP

Folderul de lucru pentru Iulie 2026. In Iunie lucrul era imprastiat pe ~60 de
foldere. In Iulie consolidam pe **5 directii de business** + **2 foldere comune**
(CODE, DATA). Fiecare director si fiecare script are nume clar, descriptiv.
Directiile 4-5 (SILOZURI, TRADING ROBOT FRUIT) au aparut post-scaffold (06-30 /
07-01) si sunt acum top-level; COOP ramane sursa F&V, SILOZURI + TRADING ROBOT
FRUIT acopera cereale + desk de trading agro.

```
PLAN 01 07 2026/
├── CLAUDE.md                          <- acest fisier (spec master)
├── IDEI_NOI_IULIE.md                  <- idei noi propuse din munca pe Iunie
├── .claude/
│   ├── skills/plan-iulie-orchestrator/SKILL.md   <- orchestrator root (router)
│   └── agents/                        <- 1 router + 3 sefi de directie
│
├── CODE/                              <- cod COMUN intre directii (nu per-directie)
│   ├── 00_SHARED_orchestrare_si_config/  config campanii, runner unic
│   ├── 01_senders_brevo/                 conturi/relee Brevo (per domeniu)
│   └── 02_dnc_suppression/               DNC unificat, opt-out, bounce
│
├── DATA/                             <- date COMUNE intre directii
│   └── 00_SHARED_leads_si_dnc/          master leads, dnc.csv, sent_log
│
├── COOP GOSPODARII DE ALTADATA/      <- DIRECTIA 1: cooperativa + export legume-fructe
│   ├── CLAUDE.md  ├── CODE/  ├── DATA/  └── SURSE_IUNIE/ (6 foldere Iunie)
│
├── INTERJOB MANPOWER/                <- DIRECTIA 2: recrutare / forta de munca
│   ├── CLAUDE.md  ├── CODE/  ├── DATA/  └── SURSE_IUNIE/ (14 foldere Iunie)
│
├── ISCIR/                            <- DIRECTIA 3: date reglementare ISCIR (echipamente)
│   ├── CLAUDE.md  ├── CODE/  └── DATA/
│
├── SILOZURI/                         <- DIRECTIA 4: campanie cereale (grau/porumb/orz/naut/floarea-soarelui), 11 judete
│   ├── CLAUDE.md  ├── CODE/  ├── DATA/  ├── CAMPAIGN/  ├── BUYERS/  └── ANOFM/
│
├── TRADING ROBOT FRUIT/              <- DIRECTIA 5: desk automat trading agro (F&V + cereale, acelasi ledger)
│   ├── CLAUDE.md  ├── CODE/  ├── DATA/  ├── PUBLISHING_ROBOT/  └── .claude/ (fv-trading-orchestrator)
│
├── _ALTE_DOMENII/                    <- nu fac parte din cele 3 directii (land/agro/web/news):
│   │  AGROEVOLUTION, TERENURI, PROPRIETATI RURALE, WEB, REVISTA PRESEI, SEO, etc. (21)
│
└── _INFRA_SI_OPERARE/               <- cross-cutting: campanii, infra, inspect, docs, tooling (16)
       EMAIL CAMPAIGNS, EMAIL CLASSIFIER, DB, DAILY, VERIFY, RASPIBIG/RASPI INSPECT, etc.
```

**Cele 3 surse June migrate** stau in `<DIRECTIE>/SURSE_IUNIE/` (intacte, ca referinta).
Codul/datele NOI de Iulie merg in `<DIRECTIE>/CODE/` si `<DIRECTIE>/DATA/` cu nume clare.
Originalele raman si in `PLAN 01 06 2026/` (backup complet).

**Regula de nume (HARD):** orice director si orice fisier de cod nou poarta un
nume care spune CE face (ex: `extrage_producatori_op_legume.py`, nu `script1.py`;
`DATE_coop_rnca_2795.csv`, nu `data.csv`). Prefix numeric pentru ordine
(`00_`, `01_`...) cand conteaza secventa.

---

## CELE 5 DIRECTII

| # | Directie | Ce e | Sursa Iunie | Canal | Stare |
|---|----------|------|-------------|-------|-------|
| 1 | **COOP GOSPODARII DE ALTADATA** | Cooperativa export legume-fructe; outreach producatori + OP + cumparatori | `CUMPARLEGUME.COM`, `SUPERMARKETURI`, `FURNIZORI`, `Legume fructe agri zootehnie` | email `office@cumparlegume.com` (Brevo relay) | COOP_EXPORT LIVE (202 leads) |
| 2 | **INTERJOB MANPOWER** | Recrutare / plasare forta de munca; joburi deficit, catalog candidati, matching, EURES | `ANOFM`, `EURES`, `CATALOG CANDIDATI`, `MATCHER`, `AGENTII DE MUNCA TEMPORARA` | email multi-sender + FB + site | ANOFM 7/7 LIVE, EURES LIVE, SONOMA deal LIVE |
| 3 | **ISCIR** | Date reglementare echipamente sub presiune; firme client + operatori RSVTI; demo-site upsell | `ISCIR` | telefon 85% + email + demo-site | iscir-operations LIVE |
| 4 | **SILOZURI** | Campanie cereale (grau/porumb/orz/naut/floarea-soarelui) 11 judete; baza 7.934 comercianti CAEN 4621 | (nou Iulie, ex-SILOZURI sub COOP) | yahoo->Gmail, non-yahoo->Brevo | campanie cereale LIVE |
| 5 | **TRADING ROBOT FRUIT** | Desk automat trading agro: poll IMAP -> offer extractor -> price book -> matcher -> deals; publica FB+TG+WP | (nou Iulie) | inbox `apaminerala@yahoo.com` + `cumparlegume@gmail.com`; publish FB+TG+WP | cron 08:00 fv_publish_all LIVE pe raspibig; PUBLISHING_ROBOT V2 multi-business |

**Relatie COOP <-> SILOZURI <-> TRADING ROBOT FRUIT:** toate 3 sunt agro-trading.
COOP = outreach producatori F&V; SILOZURI = campanie cereale outbound; TRADING
ROBOT FRUIT = desk automat (ledger + price book + publish). **Atentie dubla
pipelina cereale** (vezi nota la REGULI): decide canonical inainte de a rula
ambele in paralel.

Detaliile fiecareia in `<DIRECTIE>/CLAUDE.md`.

---

## WORKERS (verifica terenul)

| Masina | IP | Rol | Acces |
|--------|----|----|-------|
| Laptop | localhost | sursa cod, D:\MEMORY | local |
| **raspibig** | 192.168.100.21 | hub automatizare: EURES, COOP_EXPORT, ISCIR campaigns, dashboard 8096, orchestrator email, DB `public.companies` | `plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21` |
| **raspi** | 192.168.100.20 | nod scraper: ANOFM 7/7, scrapere, IMAP purge; ARE root (`echo 'RASPI_PW_REDACTED' \| sudo -S`) | `plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.20` |
| A2 Hosting | nl1-cl8 | 34 domenii cPanel (demo-site ISCIR, site-uri employer); fara root | cPanel API |

DB productie: PostgreSQL 15.17 pe raspibig:5432, `interjob_master`. User `tudor` (~/.pgpass).
Laptop are mirror separat (`companies_clean`). **Verifica unde rulezi inainte de UPDATE.**

---

## HARNESS

Orchestrator root: skill `plan-iulie-orchestrator` (`.claude/skills/`). Ruteaza
cererea catre seful directiei corecte (agentii `coop-lead`, `manpower-lead`,
`iscir-lead`) sau, pentru directiile 4-5 + PUBLISHING_ROBOT, deleaga la
harness-urile lor proprii (`fv-trading-orchestrator` in `TRADING ROBOT FRUIT/.claude`,
SILOZURI per `<SILOZURI>/CLAUDE.md`). Cererile cross-directie deleaga la
harness-urile de domeniu deja existente din Iunie (NU le reconstrui). Detalii in SKILL.md.

**Trigger:** orice cerere despre munca de Iulie pe InterJob — "ruleaza COOP",
"trimite campanie ISCIR", "build catalog candidati", "stare plan iulie".

---

## REGULI (din root CLAUDE.md — se aplica)

- Niciun `git commit`/`push` fara instructiune explicita de la Tudor.
- **Nu crea triggere/wakeup de monitorizare** ("cererea de revenire") dupa pornirea unei campanii; raporteaza status doar la cerere.
- Nicio campanie pornita ad-hoc: orice campanie noua = inregistrata in
  orchestrator + dashboard 8096 + DNC/monitoring.
- Email: numai ASCII. Sender per domeniu (vezi `CODE/01_senders_brevo/`).
- **Destinatari @yahoo => se trimit DOAR de pe Gmail** (Yahoo DMARC strict), restul pe Brevo.
- **Gmail app passwords: sursa de adevar = raspibig `/opt/ACTIVE/SKILLS/email_accounts*.py`** (format cu spatii, 16 car). Verifica prin login SMTP inainte de folosire; laptopul/memoria au avut valori corupte. Valorile NU se scriu in fisiere sync-uite — citeste-le de pe raspibig (aliase: cumparlegume, vegetables, fructexport, manpower, elena).
- **Sender custom in orchestrator email (raspibig)** trebuie sa accepte `--limit --delay --daily-cap` (altfel exit 2); orchestrator reincarca campaigns.json doar la `systemctl restart campaign-orchestrator.service`.
- **Enrich silozuri/agro din DB = email-poor** (master_romania_companies email la 1.5%); email-enrich nu aduce destinatari — valoarea e curatarea firmelor `radiata` (struck-off), nu insolventele (au administrator). Laptop are acum `interjob_master` local (master_emails, master_romania_companies, master_dnc) — login `tudor`/`tudor`.
- Leads keyed pe email (non-null), nu pe CUI.
- Arhiveaza inainte de stergere; niciodata `rm` direct.
- Nu publica date personale (nume/telefon/email) in fisiere sync-uite pe GitHub.
- **DNC unificat: sursa canonica = raspibig** `/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_list.csv` + `dnc_bounces.txt` + `SCRIPTS/SHARED/dnc_utils.py` + `PROCESSORS/merge_dnc.py`. Laptopul tine un mirror in `CODE/02_dnc_suppression/` (sync script + pointer); nu mentine DNC separat per directie.
- **Dubla pipelina cereale (OPEN):** SILOZURI (CAMPAIGN outbound 11 judete) si TRADING ROBOT FRUIT (7.934 comercianti CAEN 4621 in ledger) se suprapun. Pana la unificare, marcheaza clar care ruleaza pentru ce audienta; nu trimite acelasi lead din ambele.

---

## CHANGE LOG

| Data | Schimbare |
|------|-----------|
| 2026-06-28 | Scaffolding initial: CLAUDE.md + harness + 3 directii (COOP/MANPOWER/ISCIR) + CODE/DATA comune. Tranzitie din PLAN 01 06 2026. |
| 2026-06-30 | Harness inspect: regenerated both INDEX.md from disk; added frontmatter to 6 A2/ops agents; marked 18 imported agents as unwired (router uses only the 3 leads + plan-router). |
| 2026-06-30 | SILOZURI mutat top-level + campanie cereale 11 judete LIVE (yahoo->Gmail, non-yahoo->Brevo); reguli noi (yahoo-gmail, gmail-pw-source=raspibig, sender --daily-cap, enrich-email-dead-end); laptop populat cu interjob_master local. |
| 2026-06-30 | DEAL SONOMA: plasare 35 muncitori textile/saci PP. Skill nou `worker-placement-outreach` (cablat in manpower-lead) + campanii SONOMA_FABRICI/SONOMA_AGENTII in orchestrator (gentle Gmail 50/zi). Cititor zero-token `extrage_candidati_sonoma_pdf.py`. Regula noua `mailul oficial intotdeauna`. |
| 2026-07-01 | Aliniere harta la teren: CLAUDE.md trecut de la 3 la 5 directii (adaugat SILOZURI + TRADING ROBOT FRUIT top-level). Routing orchestrator extins cu directiile 4-5 + PUBLISHING_ROBOT. `CODE/02_dnc_suppression/` populat cu pointer + sync script spre DNC canonical raspibig. Nota OPEN: dubla pipelina cereale (SILOZURI vs TRADING ROBOT FRUIT) de unificat. |
