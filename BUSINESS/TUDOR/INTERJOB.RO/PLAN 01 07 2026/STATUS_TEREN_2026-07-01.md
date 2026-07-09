# STATUS TEREN — verificat 2026-07-01 (nu harta)

Verificat direct pe raspibig (.21) si raspi (.20) la 2026-07-01 ~09:15 EEST.
Inlocuieste STATUS_TEREN_2026-06-28.md (pastrat ca referinta istorica).

Harta CLAUDE.md actualizata la 5 directii (de la 3). Routing orchestrator extins.

## 1. COOP GOSPODARII DE ALTADATA
- Campanie **COOP_EXPORT** `enabled=True` pe raspibig (`/opt/ACTIVE/EMAIL/CAMPAIGNS/COOP_EXPORT`).
- 202 leads (`leads_coop_export.csv`), template `template_export_op.txt`, sent log activ.
- Migrate in Iulie: `DATA/DATE_leads_coop_export_202.csv` + `CODE/campanie_export/`.

## 2. INTERJOB MANPOWER
- **ANOFM 7/7 LIVE** pe raspi: 4 timere rulate azi 2026-07-01:
  scraper 08:25, ingest 09:00, audience-rebuild 09:10, daily-report 04:00 (toate fresh).
- **EURES_OUTREACH** `enabled=True` pe raspibig.
- **DEAL SONOMA** (06-30): plasare 35 muncitori textile/saci PP; campanii
  SONOMA_FABRICI/SONOMA_AGENTII in orchestrator (gentle Gmail 50/zi).
- Migrate: CODE/anofm (35), CODE/catalog_candidati (9), CODE/eures (6); DATA candidati+angajatori.

## 3. ISCIR
- Date migrate: clienti 67.401, operatori 1.250, clienti finali 114.541; CODE 39 fisiere.
- Demo-site operatori pe A2 (interjob.ro/iscir/operatori/{CUI}.html) — 926 pagini.

## 4. SILOZURI (NOU top-level din 06-30)
- Campanie cereale 11 judete LIVE (yahoo->Gmail, non-yahoo->Brevo).
- Baza 7.934 comercianti CAEN 4621 (`DATA/DATE_cereal_buyers_demand.csv`).
- Structura: CODE/ DATA/ CAMPAIGN/ BUYERS/ ANOFM/ + CLAUDE.md.
- **OPEN: suprapunere cu TRADING ROBOT FRUIT pe audienta cereale** (vezi nota).

## 5. TRADING ROBOT FRUIT (NOU din 06-28, activ 07-01)
- Desk automat trading agro: poll IMAP -> offer extractor -> price book -> matcher -> deals.
- Inboxuri read-only: `apaminerala@yahoo.com` (furnizori F&V+cereale), `cumparlegume@gmail.com` (replii).
- **Cron LIVE pe raspibig:**
  - `0 8 * * *` `cd /opt/ACTIVE/TRADING_ROBOT_FRUIT && python3 CODE/fv_publish_all.py --post` (publica FB+TG+WP, dedup+cap).
  - `0 9 * * 1` `mega_image_imap_fetch.py` (fetch saptamanal oferte Mega Image).
- PUBLISHING_ROBOT V2 multi-business: cumparlegume (WP+TG+FB LIVE) + expats (partial: WP merge; FB token expirat, TG bot nu e admin pe @expatsinromania_news).
- Regula HARD: nu se publica date de contact individuale pe canale publice (doar office@cumparlegume.com).

## INFRA (verificat 2026-07-01)
- **Dashboard 8096 LIVE** pe raspibig (HTTP 200 confirmat).
- campaigns.json: `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json`.
- **DNC unificat canonical raspibig:** `/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_list.csv` = 8.494 linii
  + `dnc_bounces.txt` + `SCRIPTS/SHARED/dnc_utils.py` + `PROCESSORS/merge_dnc.py`.
- **Mirror DNC pe laptop populat:** `CODE/02_dnc_suppression/` (sync_dnc_from_raspibig.ps1, rulat OK 07-01, 8.494 linii).
- Email cron: daily_roundup 09:00 (`/opt/ACTIVE/EVENT_PUBLISHER/orchestrator.py`).

## OPEN / DE REZOLVAT
1. **Dubla pipelina cereale:** SILOZURI (CAMPAIGN outbound) vs TRADING ROBOT FRUIT (7.934 comercianti in ledger). Decide canonical inainte de a rula ambele pe aceeasi audienta.
2. **Expats publishing:** refresh FB token (pagina 288102411055455) + adauga botul ca admin pe @expatsinromania_news.
3. **CODE/ shared cleanup:** ~100 fisiere vechi Iunie (apply/wordpress/horeca/template) in `CODE/` root nu apartin shared-infra; de mutat in `_ALTE_DOMENII/WEB` sau ARCHIVE.
4. **01_senders_brevo** inca gol (.gitkeep); Brevo senders per domeniu nedocumentati aici (sursa reala: raspibig campaigns.json).
5. **18 agenti unwired** in `.claude/agents` (dead weight; orchestrator delega deja prin nume).
