# CLAUDE.md — ISCIR Operations

Regulatory-compliance data domain: 67K pressure-vessel owners + 1.2K RSVTI operators + 114K triangulated firm owners. Harness: `.claude/skills/iscir-operations/`. Sursa full harness: `D:\MEMORY\BUSINESS\IDEAS\ISCIR` (6 agenti + 8 skill-uri + orchestrator). PDF extraction skill: `.claude/skills/iscir-pdf-extract/`.

## DATASETS

| File | Rows | Email | Phone | Notes |
|------|------|-------|-------|-------|
| `DATA/clienti_iscir_enriched.csv` | 67,401 | 3.0% (2,010) | 89% (57K) | ANAF-enriched: +56K phone, status, VAT, inactive |
| `DATA/operatori_rsvti_pj_enriched.csv` | 1,250 | 84% (1,047) | 96% (1,200) | 924 fara site web |
| `DATA/rsvti_ce_face.csv` | 1,250 | — | — | Segmente activitate |
| `DATA/autorizatii_suspendate_enriched.csv` | 311 | 15% (47) | 61% (190) | Autorizatii retrase |
| `DATA/clienti_finali_iscir.csv` | 114,541 | 6.9% (7.9K) | 71% (81K) | Triangulat (achizitii/fonduri UE/alimentar) |
| `DATA/clienti_pe_judet/*.csv` | 42 files | per judet | per judet | Lead list (cu telefon) |
| `DATA/campaigns/campania1_lead_packs.csv` | 930 | 930 | — | Lead Packs upsell |
| `DATA/campaigns/campania2_site_uri.csv` | 737 | 737 | — | Site upgrade upsell |
| `DATA/campaigns/campania3_suspendati.csv` | 47 | 47 | — | Re-authorizare kit |
| `DATA/operatori_pj_full.csv` | 1,102 | 885 | 1,008 | Full PDF-extracted: auth_nr, expiry, rsvti_operatori |

## STATUT CURENT (2026-06-27) — ANAF ENRICHMENT COMPLET

- **ANAF API:** 67,401 firme batch-enriched. 66,726 gasite (99.5%). +56K telefoane. Status, VAT, inactiv pentru toate. Cache: `DATA/anaf_cache.json` (66.726 entries).
- **Judet:** 31,368 extrase din adresa ANAF (regex `JUD\.\s*([^,]+)`). 2 neclasificate. 99.997% acoperire.
- **42 fisiere judet:** regenerate cu coloana `phone` inclusa. Normalizate UPPERCASE.
- **Site-uri operatori:** 926 live la `https://interjob.ro/iscir/operatori/{CUI}.html`. Index cautare: `https://interjob.ro/iscir/`.
- **Campanii email:** 3 generate (`DATA/campaigns/`). Template: `templates/firm_default.html` (token-based %%NAME%%, %%PHONE%%, etc.).
- **PDF extras:** `DATA/operatori_pj_full.csv` — 1.102 operatori cu numar autorizatie, adresa, data expirare, operatori RSVTI. Zero-token, zero-cost.
- **Email cross-ref (agents):** ~18K emails gasite din 7 surse (DB, CSV, fuzzy name, phone join, domain MX inference). Neconsolidate in CSV.
- **TAM analizat:** 24.361 detinatori reali (exclusi 43.040 instalatori/serivice). 18.557 contactabili, 6.099 fara niciun contact.
- **ANAF inactive:** 10.255 (15%). **Radiate:** 21.015 (31%). Total de filtrat: 31.270 (46%).
- **Scripturi NOI:** `anaf_enrich.py` (batch ANAF API + cache), `fix_county_anaf.py`, `gen_campaign_emails.py`, `explore_ndt.py`, `explore_extended.py`, `extract_pj_full.py`
- **PHP pe A2:** `_deploy_operatori.php`, `_gen_index.php`
- **Skill PDF:** `.claude/skills/iscir-pdf-extract/`
- **Propuneri complete:** `PROPUNERI.md` (toate ideile + matrice prioritate)

## SCRIPTURI (CODE/)

### Noi (2026-06-27)
| Script | Ce face |
|--------|---------|
| `anaf_enrich.py` | Batch ANAF API v9 (100 CUI/call, 1.2s rate) — adauga phone, status, VAT, inactiv. Output: clienti_iscir_enriched.csv |
| `fix_county_anaf.py` | Extrage judet din adresa ANAF pentru 31K firme |
| `gen_campaign_emails.py` | Genereaza emailuri personalizate din template |
| `explore_ndt.py` | Exploreaza firme CAEN 7120 (NDT/lab) — 5,699 |
| `explore_extended.py` | Exploreaza datele clienti_finali — 114K |
| `extract_pj_full.py` | Extrage 1.102 operatori din PDF (pdfplumber) |
| `_deploy_operatori.php` | Generator PHP de site-uri operatori (A2) |
| `_gen_index.php` | Generator index cautare (A2) |

### Anterioare
| Script | Ce face |
|--------|---------|
| `gen_operator_pages.py` | Pagini judet din DB |
| `gen_operator_sites.py` | Site-uri HTML operatori (local) |
| `load_leads_pg.py <host> <port>` | Incarca CSV in DB ca tabele iscir_* |
| `iscir_fetch.py [--all]` | Chrome > Cloudflare (iscir.ro) |
| `iscir_normalize.py` | PDF ISCIR -> CSV |
| `owners_match.py` | Triangulare proprietari |
| `phone_db_match*.py` | Potrivire telefon DB |
| `crossref_me.py` | Cross-ref CUI in DB |
| `web_inspect_chrome.py` | Inspecteaza site-uri firme |

## KEY NUMBERS
- 5,699 CAEN 7120 (NDT labs) — 113 email, 4,082 phone
- 1,019 CORE firme (multi-semnal, 99% phone, 65% email)
- **10,255 ANAF inactive + 21,015 radiate = 31,270 de filtrat**
- **TAM real: 24.361 firme** (36.1% din total) — dupa excludere instalatori
- **TAM contactabil: 18.557** (76%) — telefon/email
- **TAM fara contact: 6.099** (25%) — doar fizic
- 924 din 1,250 operatori fara site (74%) — 926 site-uri generate
- Top judete: BUCURESTI 10,561, CLUJ 4,305, TIMIS 3,682

## REGULI
- Email outbound ASCII only, fara diacritice
- NU fabrica emailuri
- NU suprima pe datorii/insolventa (semnale temporale)
- Telefon canalul real (85% firme-client, 96% operatori)
- Fara commit/push fara aprobare explicita
- A2: `--data` in loc de `--data-urlencode` pentru PHP content
- `romania.companies_master` = 2.9M firme (laptop:5433 + raspibig:5432, user tudor/tudor)
- **ANAF API:** `POST https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva` — FREE, no auth, batch 100 CUI, 1 req/s

## CE URMEAZA
- [ ] Consolidare email sources (18K gasite) in clienti_iscir_enriched.csv
- [ ] SMTP validate emails
- [ ] Run email campaigns (Lead Packs + Site-uri + Suspendati)
- [ ] Deploy 42 pagini judet + site-uri operatori pe A2
- [ ] Website crawl pentru restul de email-uri
- [ ] Construieste Compliance Vault SaaS MVP
- [ ] Replica playbook la ANRE, ANCOM, ITM/IGSU
- [ ] Integreaza %%AUTH_NR%%, %%ADDRESS%%, %%J_NUMBER%%, %%EXPIRY_DATE%% in template
