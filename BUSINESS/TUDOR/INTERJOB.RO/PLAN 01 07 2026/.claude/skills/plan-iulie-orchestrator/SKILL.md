---
name: plan-iulie-orchestrator
description: "Root orchestrator pentru PLAN 01 07 2026 (Iulie) — ruteaza orice cerere InterJob de Iulie catre una din cele 5 directii (COOP GOSPODARII DE ALTADATA, INTERJOB MANPOWER, ISCIR, SILOZURI, TRADING ROBOT FRUIT) prin agentii sefi / harness-uri proprii, sau deleaga cereri cross-directie la harness-urile de domeniu existente. Use cand utilizatorul lucreaza in PLAN 01 07 2026/, cere 'ruleaza/stare plan iulie', 'trimite campanie COOP/ISCIR/manpower/silozuri', 'trading robot / price book / oferte', 'publishing robot / aproba postare', 'build catalog', sau orice munca de Iulie pe InterJob."
---

# Skill: plan-iulie-orchestrator

**Mod:** router cu 1 dispecer + 3 sefi de directie + 2 harness-uri proprii (SILOZURI, TRADING ROBOT FRUIT). Verifica mereu terenul
(raspibig .21 / raspi .20 / DB / A2), nu harta.

## Cand se foloseste
- "Ruleaza COOP / manpower / ISCIR / silozuri / trading robot"
- "Stare PLAN iulie" (status pe cele 5 directii)
- "Trimite campanie <directie>"
- "Build catalog candidati", "scrape ANOFM", "enrich ISCIR"
- "Trading robot / oferte / price book / matcher deal"
- "Publishing robot / aproba postare / publica pe FB+TG+WP"
- Orice munca in `PLAN 01 07 2026/`

## Rutare (alege directia, apoi seful)

| Cererea contine... | Directie | Agent sef / harness |
|--------------------|----------|-----------|
| cooperativa, producatori, legume-fructe, export, cumparlegume, supermarket, furnizori, OP, RNCA | COOP | `coop-lead` |
| candidati, joburi, deficit, ANOFM, EURES, catalog, matcher, recrutare, angajatori, agentii munca, SONOMA | MANPOWER | `manpower-lead` |
| ISCIR, RSVTI, echipament presiune, operatori, autorizatii, NDT, demo-site operator | ISCIR | `iscir-lead` |
| silozuri, cereale, grau, porumb, orz, naut, floarea-soarelui, camepanie cereale, comercianti CAEN 4621 | SILOZURI | `coop-lead` (delegate) + `<SILOZURI>/CLAUDE.md` |
| trading robot, oferte agro, price book, ledger, matcher deal, fv-trader, fv-dealer, mega image imap | TRADING ROBOT FRUIT | skill `fv-trading-orchestrator` (`TRADING ROBOT FRUIT/.claude/skills/`) |
| publishing robot, publish inbox, aproba postare, telegram bot, FB/WP publicare multi-canal, expats publishing | PUBLISHING_ROBOT | `TRADING ROBOT FRUIT/PUBLISHING_ROBOT/` + skill `publishing-robot` |
| seo, frontend, demo-site UI, landing page, offer/lead magnet, conversie/CAC/LTV, analytics/dashboard/SQL/KPI, security review/threat model/secrets/SAST, "agency", coding specialist | AGENCY (coding) | droid `agency-orchestrator` (Factory `.factory/droids/`) + Claude `.claude/agents/` + OpenCode `.opencode/agents/` in `THE AGENCY - CODING AGENTS/` |
| cross-directie / infra / DB / A2 / email general / DNC | — | deleaga la harness domeniu existent (vezi mai jos) |

**Notificare cereale:** SILOZURI (outbound 11 judete) si TRADING ROBOT FRUIT
(7.934 comercianti in ledger) se suprapun pe audienta cereale. Daca cererea e
ambigua, intreaba pe care pipeline il vizeaza inainte de a executa.

## NU reconstrui harness-uri existente
Harness-urile de domeniu din Iunie raman canonice; refoloseste-le prin delegare:
- ANOFM: `PLAN 01 06 2026/ANOFM/.claude` (skill `anofm-orchestrator`, LIVE pe raspi 7/7)
- EURES: campanie orchestrator-driven (campaigns.json `EURES_OUTREACH`, raspibig)
- ISCIR: `PLAN 01 06 2026/ISCIR/.claude` (skill `iscir-operations`, `iscir-pdf-extract`)
- Catalog: skill `interjob-catalog` (ij_jobs PostgreSQL, raspibig)
- COOP export: campanie `COOP_EXPORT` in orchestrator (sender office@cumparlegume.com)
- **SILOZURI:** `PLAN 01 07 2026/SILOZURI/CLAUDE.md` (campanie cereale 11 judete, top-level)
- **TRADING ROBOT FRUIT:** `PLAN 01 07 2026/TRADING ROBOT FRUIT/.claude/skills/fv-trading-orchestrator` (desk agro: poll+extract+price book+matcher+publish; cron 08:00 pe raspibig)
- **PUBLISHING_ROBOT:** `PLAN 01 07 2026/TRADING ROBOT FRUIT/PUBLISHING_ROBOT/` + skill `publishing-robot` (multi-business cumparlegume+expats, aprovare Telegram)
- **THE AGENCY - CODING AGENTS:** `PLAN 01 07 2026/THE AGENCY - CODING AGENTS/` — harness 1 orchestrator + 5 specialisti (SEO, Frontend, Offer/LeadGen, Analytics, AppSec) in 3 formate (Factory droids `.factory/droids/`, Claude `.claude/agents/`, OpenCode `.opencode/agents/`). Rutare cereri coding/agency specialist → `agency-orchestrator`, care deleaga mai departe la specialistul potrivit via Task tool. Necesita reload sesiune pentru a fi invocabil ca subagent_type.
- Email/DNC/dashboard: `email-campaigns-orchestrator` (dashboard 8096; DNC canonical `/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_list.csv`)
- Estate/cross-domeniu: `estate-orchestrator` la root D:\MEMORY

In Iulie, foloseste `PLAN 01 07 2026/<DIRECTIE>/` ca loc de lucru nou (DATA/ CODE/),
dar cheama codul/pipeline-urile LIVE de unde ruleaza deja.

## Faze (full cycle)
1. **Status** — fiecare sef raporteaza starea reala (camp activa? ultim send? leads? bounce?).
2. **Plan** — propune actiuni NUMEROTATE pe directie, ranked pe ROI.
3. **Executa** — dupa selectia lui Tudor; campanii noi = inregistrate in orchestrator + 8096 + DNC.
4. **Verifica** — confirma pe teren (log/DB/dashboard), nu pe harta.
5. **Raporteaza** — rezultate numerotate, fara preambul.

## Reguli
- Output numerotat mereu. Romana. Email ASCII-only.
- Fara commit/push/send fara aprobare explicita numerotata.
- Arhiveaza inainte de stergere.
- Leads keyed pe email non-null.
