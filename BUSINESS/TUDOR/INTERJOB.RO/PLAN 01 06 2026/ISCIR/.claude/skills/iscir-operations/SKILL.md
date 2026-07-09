---
name: iscir-operations
description: "Operate the ISCIR regulatory-compliance data domain — audit 6 datasets (67K client firms, 1.2K operators, 114K triangulated owners), enrich via ANAF API + DB cross-ref, generate county CSVs, build operator demo sites on A2, generate email campaigns. Use when asked to 'run ISCIR enrichment', 'audit ISCIR data', 'generate ISCIR campaigns', 'deploy operator sites', 'fix ISCIR county data', or work in the ISCIR/ folder."
---

# ISCIR Operations Skill

**Purpose:** Monetize ISCIR regulatory-compliance data assets — 67,401 pressure-vessel/equipment owners, 1,250 authorized RSVTI operators, 114,541 triangulated firm owners. Channel: phone (85%), email (3%), upsell demo sites.

**Domain:** ISCIR (Romanian state inspection for pressure equipment). Data under `ISCIR/DATA/`, scripts under `ISCIR/CODE/`. See `ISCIR/CLAUDE.md` for full spec.

## Datasets

| File | Rows | Email | Phone | Notes |
|------|------|-------|-------|-------|
| `clienti_iscir_enriched.csv` | 67,401 | 3.0% (2,010) | 89% (57K) | ANAF-enriched, 99.997% county coverage |
| `operatori_rsvti_pj_enriched.csv` | 1,250 | 84% (1,047) | 96% (1,200) | 924 operators have no website |
| `rsvti_ce_face.csv` | 1,250 | — | — | Activity segments (NDT, welding, design, consulting) |
| `autorizatii_suspendate_enriched.csv` | 311 | 15% (47) | 61% (190) | Suspended/revoked authorizations |
| `clienti_finali_iscir.csv` | 114,541 | 6.9% (7.9K) | 71% (81K) | Triangulated via procurement/eufunds/food regs |
| `clienti_pe_judet/*.csv` | 42 files | By county | By county | Lead lists per county |

## Pipeline

### 1. Enrichment (re-runnable, zero-token)
1. **ANAF API** — `POST https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva`, batch 100 CUI/call, <=1 req/s. Free, no auth. Extracts address (incl county), status (active/inactive/radiat), VAT info.
   - Script: `CODE/anaf_enrich.py`
   - County fix: `CODE/fix_county_anaf.py` — regex `JUD\.\s*([^,]+)` + `MUNICIPIUL BUCURE.TI` special case
2. **DB cross-ref** — `romania.companies_master` (2.9M firms, localhost:5433 PG18 or raspibig:5432 PG15, user tudor/tudor). Join on CUI.
   - Scripts: `CODE/phone_db_match*.py`, `CODE/crossref_me.py`, `CODE/enrich_cui_fast.py`
3. **Name/domain match** — fallback fuzzy match on company name.
   - Scripts: `CODE/enrich_name_only.py`, `CODE/enrich_domain_only.py`, `CODE/enrich_name_domain.py`

### 2. County extraction
- `CODE/fix_county_anaf.py` — extracts county from ANAF `address` field. Returns 31,368 counties in batch. Handles `JUD. BUCURESTI` (standardized to `BUCURESTI`), mixed case, trailing commas. 99.997% coverage.

### 3. Campaign email generation
- `CODE/gen_campaign_emails.py` — reads template `templates/firm_default.html`, replaces `%%TOKEN%%` tokens, writes personalized CSVs to `DATA/campaigns/`.
- Templates use `%%NAME%%`, `%%PHONE%%`, `%%ACT_TITLE%%`, `%%LOC%%`, `%%CAENLBL%%`, `%%SERVICII%%`, `%%TEL_BTN%%`, `%%CTA%%`, `%%CONTACT%%`, `%%LOC_IN%%`
- 3 campaigns generated:
  1. `campania1_lead_packs.csv` — 930 sends, Lead Packs upsell
  2. `campania2_site_uri.csv` — 737 sends, demo site upgrade
  3. `campania3_suspendati.csv` — 47 sends, re-authorization kit
- **ASCII only, no diacritics** — campaign files are CSVs compatible with Brevo/SMTP

### 4. Operator demo site deployment
- 926 HTML sites deployed to `https://interjob.ro/iscir/operatori/{CUI}.html`
- Generated via PHP bootstrap on A2 (cPanel API `Fileman/save_file_content` with PHP generator)
- PHP scripts kept on server:
  - `CODE/_gen_index.php` — live index rebuild
  - `CODE/_deploy_operatori.php` — one-time site generator (CSV upload + batch HTML creation)
- Banner upsell: "Pagina de prezentare generata — o vrei publicata pe domeniul tau? Suna-ne."
- Searchable index at `https://interjob.ro/iscir/`
- Template-based: `templates/firm_default.html` drives all 926 sites. Supports tokens: `%%NAME%%`, `%%ACT_TITLE%%`, `%%CAENLBL%%`, `%%LOC%%`, `%%LOC_IN%%`, `%%PHONE%%`, `%%SERVICII%%`, `%%CONTACT%%`, `%%TEL_BTN%%`, `%%CTA%%`, `%%EXTRA_INFO%%` (J-number + address), `%%AUTH_NR_SHORT%%` / `%%AUTH_NR_LBL%%` (authorization number), `%%EXPIRY_DATE%%` (expiry date), `%%ADDRESS_LINE%%` (street address in contact)
- Generator `CODE/gen_operator_sites.py` now auto-loads `operatori_pj_full.csv` (from `iscir-pdf-extract` skill) and merges on CUI to populate auth data tokens
- **cPanel gotcha:** `Fileman/mk_dir`, `Fileman/delete_files` endpoints broken on A2 — workaround via PHP `mkdir()` + `unlink()` bootstrap

### 5. Monetization ideas
- See `CRUSH & DROID/TOATE_IDEILE.md` — 40 unified ideas merged from MONETIZARE.md + IDEI.md + audit findings
- See `OPENCODE/PROPUNERE.md` — formal proposal: email enrichment plan, 5 new products, competitive edge

## Hard rules
- Never fabricate email addresses
- Never suppress on temporal signals (ANAF debts, insolvency)
- Email outbound ASCII only, no diacritics
- Phone is real channel for client firms (85%); email for operators (84%)
- No `--data-urlencode` for PHP file content on A2 — use `--data` with escaped content

## Key scripts reference
| Script | Purpose |
|--------|---------|
| `anaf_enrich.py` | Batch ANAF API enrichment (CUI batch 100) |
| `fix_county_anaf.py` | Extract county from ANAF address field |
| `gen_campaign_emails.py` | Generate personalized email campaigns |
| `gen_operator_pages.py` | Generate county pages from DB |
| `gen_operator_sites.py` | Generate operator HTML sites locally; loads `operatori_pj_full.csv` for auth data |
| `extract_pj_full.py` | PDF extraction (pdfplumber) — 1,102 operators with auth numbers, addresses, expiry |
| `iscir_fetch.py [--all]` | Chrome fetcher over Cloudflare (iscir.ro) |
| `iscir_normalize.py` | PDF ISCIR -> CSV |
| `load_leads_pg.py <host> <port>` | Load leads CSV into DB as iscir_* tables |
| `owners_match.py` | Triangulate firm owners via procurement/eufunds/food |
| `web_inspect_chrome.py` | Inspect company websites over Cloudflare |

## Change history
| Date | Change | Reason |
|------|--------|--------|
| 2026-06-27 | Initial skill created | ISCIR domain ops from current session work |
| 2026-06-28 | PDF extraction integration + template upgrade | `iscir-pdf-extract` skill created; 4 new template tokens for auth data; generator merges PDF CSV automatically |
