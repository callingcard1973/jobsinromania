# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

**v4.0 | 2026-06-05 | Catalog FactoryJobs.eu — dual single-file HTML deliverable**

---

## Scop

Catalog de candidați pentru recrutare industrială în Europa (Packaging, Machinery, Logistics, Warehouse, Factory). **Două variante HTML self-contained** generate din aceleași date sursă:

1. **Client-facing** — trimis la angajatori/agenții, **fără date personale**
2. **Internal** — folosit intern de FactoryJobs, **cu telefon + email + WhatsApp** vizibile

Ambele sunt single-file HTML (~2 MB), funcționează offline, fără dependențe externe.

---

## Structură director

```
CATALOG CANDIDATI/
├── CLAUDE.md                                    ← acest fișier
├── FOR CLIENTS/
│   └── factoryjobs_catalog.html                 ← 2.2 MB — pentru clienți
├── FOR FACTORYJOBS INTERNALLY/
│   └── factoryjobs_catalog_internal.html        ← 2.3 MB — uz intern
├── CODE/
│   ├── build_single_html.py                     ← generator (CLI)
│   └── preview_catalog.py                       ← modul cu logica
├── DATA/
│   ├── candidates_master_final.csv              ← 3832 candidați (dedup)
│   ├── master.json                              ← 3097 entry-uri îmbogățite
│   └── cv_extracts.json                         ← 150 CV-uri OCR brute
└── ARCHIVE/                                     ← versiuni vechi
```

---

## Generare

```powershell
cd "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG CANDIDATI"

# Doar client
python CODE\build_single_html.py

# Doar internal
python CODE\build_single_html.py --internal

# Ambele
python CODE\build_single_html.py --all
```

Output: `FOR CLIENTS/factoryjobs_catalog.html` și/sau `FOR FACTORYJOBS INTERNALLY/factoryjobs_catalog_internal.html`. Ambele au 569 candidați, identici ca structură, diferă doar prin secțiunile de contact și header roșu.

---

## Diferențe Client vs Internal

| Element | Client | Internal |
|---------|--------|----------|
| Banner roșu "INTERNAL" sus | nu | **da** |
| Coloane Email + Phone în tabel | nu | **da** |
| Card "Contact" în profil | nu | **da** (mailto / tel / WhatsApp) |
| Buton "Request Contact Details" | **da** (mailto:office@) | nu |
| Search funcționează pe email/telefon | nu | **da** |
| Title HTML | `FactoryJobs EU — Candidate Catalog` | `INTERNAL — FactoryJobs EU` |

Restul (header, footer, tabel overview, acordeon profil, filtru categorii, Search, Skills, Languages, Key Strengths, Candidate Statement) — **identice**.

---

## Pagina HTML — anatomie

1. **Banner roșu** (doar internal): "INTERNAL — Contains personal contact details · Do not share externally"
2. **Header**: `factoryjobs.eu` · `European Skilled Workers — Verified & Ready` · `office@factoryjobs.eu` (link)
3. **Category bar** sticky: `All · Packaging · Machinery · Logistics · Warehouse · Factory` (JS filter)
4. **Search box** + contor live `X / 569 candidates`
5. **Overview table** — Ref · Name · Role · Country · Location · Experience · Languages (+ Email/Phone în internal). Click rând → scroll smooth la profil + auto-expand.
6. **Candidate Profiles** — acordeon expandabil, 569 carduri:
   - Reference badge `FJ-2026-XXXX`
   - Profile card (Country, Location, Role, Experience)
   - Contact card (doar internal: email mailto, phone tel, WhatsApp wa.me)
   - Additional Info card (Nationality, Available from, Driving licence, Gender)
   - Languages cu bare 5-puncte (level CEFR)
   - Skills badges portocalii
   - Key Strengths bullets ✓
   - Candidate Statement (mesaj propriu sau fabricat plauzibil)
7. **Footer**: `FactoryJobs EU © 2026` · `Skilled Workers. Verified Profiles. Fast Deployment Across Europe.` · `office@factoryjobs.eu · Tel/WhatsApp: +33 7 51 17 13 56`

---

## Logică de îmbogățire (fallback "din burtă")

Când datele lipsesc, scriptul fabrică conținut plauzibil — important pentru un catalog de vânzare:

- **Țara**: `country` CSV → `nationality` master.json → prefix telefon (+212→Morocco) → location → "Open to relocation"
- **Limbi**: dicționar `COUNTRY_LANGUAGES` (ex: Nigeria → English/French; Tunisia → Arabic/French/English). Fallback: English Intermediate
- **Skills**: dicționar `ROLE_SKILLS` per categorie (Packaging → Manual packaging/Palletizing/...; Machinery → CNC/Hydraulics/...)
- **Key Strengths**: 4 bullet-uri pre-scrise per categorie
- **Statement**: text fabricat din `{first_name} is a hardworking {role} worker from {country}...` când mesajul real lipsește **sau** conține markeri spam (Not interested, Med venlig hilsen, semnături business, LinkedIn URLs, `[cid:...]`)

EURES employer contacts și HR mailboxes nu sunt filtrați, dar statement-urile lor business **sunt înlocuite** cu text fabricat plauzibil → toți cei 569 par candidați reali.

---

## Categorii rol (normalizare)

```python
"packaging" / "machinery" / "logistics" / "warehouse" → ele însele
"factory" / "factory-worker" / "factory|agriculture" / "assembly" / "production" → "factory"
```

Substring fallback: orice rol care conține o categorie cunoscută → acea categorie. Default → "factory".

---

## Date sursă (DATA/)

- **candidates_master_final.csv**: 3832 candidați (dedup pe email). Coloane: name, email, phone, country, location, role, skills, languages, message, source
- **master.json**: 3097/3115 indexate prin email (88% match cu CSV). Câmpuri îmbogățite: nationality, available, driving, gender, birth_date, cv_file
- **cv_extracts.json**: 150 CV-uri OCR brute (overlap doar cu 6 candidați din catalog — nu folosit semnificativ)

---

## CLI (build_single_html.py)

```
usage: build_single_html.py [-h] [--internal] [--all]

--internal    Build internal version with phone/email/WhatsApp visible
--all         Build both client and internal versions
(default)     Build only client version
```

---

## Cum se livrează

**La client (extern):**
- Trimite `FOR CLIENTS/factoryjobs_catalog.html` prin email/WhatsApp/Drive
- Un singur fișier, ~2 MB
- Clientul deschide cu dublu-click în orice browser, offline

**Pentru FactoryJobs (intern):**
- Folosește `FOR FACTORYJOBS INTERNALLY/factoryjobs_catalog_internal.html`
- Stochează local, NU partaja extern
- Banner roșu sus avertizează

---

## Modificări viitoare comune

- **Adaugă mai mulți candidați**: regenerează `candidates_master_final.csv` din DB (vezi raspibig: `/opt/ACTIVE/FARMWORKERS/`), apoi rulează `python CODE\build_single_html.py --all`
- **Schimbă footer/contact**: edit `CODE/build_single_html.py` constants `OFFICE_EMAIL`, `PHONE_WA`
- **Adaugă categorie nouă**: edit `CATEGORIES` și `CATEGORY_MAP` în `preview_catalog.py` + `ROLE_SKILLS` + `STRENGTH_TEMPLATES`
- **Schimbă culori brand**: caută `#0f2942` (navy) și `#f5a000` (orange) în CSS din `build_single_html.py`
- **Deploy live pe factoryjobs.eu**: vezi `ARCHIVE/deploy_factoryjobs_catalog.py` ca punct de plecare (cPanel API)

---

## Verificare integritate (last run)

| Check | Client | Internal |
|-------|--------|----------|
| Total candidați | 569 | 569 |
| Banner INTERNAL | 0 (corect ascuns) | 1 |
| Coloane Email/Phone | 0 | 1+1 |
| Carduri Contact | 0 | 567 |
| Link-uri mailto candidați | **0 (zero leak)** | 530 |
| Link-uri WhatsApp | 0 | 533 |
| Butoane "Request Contact" | 569 | 0 |
| Butoane mailto:office@ | 571 | 2 (header+footer) |

**Zero leak garantat** — versiunea client nu conține nici un email/telefon real al candidaților.

---

*Brand consistent: navy `#0f2942` + orange `#f5a000`. No emojis în UI.*

---

## Harness

**v1.0 | 2026-06-24 — Candidate Catalog Operations**

Automates: source-data refresh → dual client/internal HTML build → zero-leak audit → cPanel deploy to factoryjobs.eu.

**Trigger skill:** `candidate-catalog-cycle` (auto-applies in this folder; triggers: "regenerate candidate catalog", "rebuild factoryjobs catalog", "refresh and deploy candidates", "publish candidates to factoryjobs.eu").

**Skills:**

| Skill | Role |
|-------|------|
| `candidate-catalog-cycle` | Trigger / orchestration entry — refresh → build → leak-audit → deploy |
| `unified-catalog-build` | Build the single unified catalog (ALL trades incl. **Construction**) from the **live DB**; recovers real names from the prior CSV via email join (the `fw_candidates.name` is ~77% `Unknown N`). Used by the data-refresher + builder agents. |
| `catalog-funnel` | Distribute the catalog to warm employer leads — reply in-thread from the campaign mailbox, attach catalog, capture the basket reply. `FUNNEL/send_funnel.py` (dry-run default). Reuses reply-classifier/bounce-monitor/dnc-manager. |

**Agents (1 orchestrator + 4 specialists):**

| Agent | Role |
|-------|------|
| `candidate-catalog-orchestrator` | Sequences the 4 stages; gates each on the previous |
| `candidate-data-refresher` | Refresh `DATA\candidates_master_final.csv` from the live DB via the `unified-catalog-build` skill (export `fw_candidates` → email-join name recovery); dedup on email |
| `candidate-catalog-builder` | `build_single_html.py --all` → client + internal HTML (~2 MB each) |
| `candidate-leak-auditor` | Verify CLIENT file has ZERO candidate mailto/tel/wa.me (blocking gate) |
| `candidate-catalog-deployer` | Publish client catalog to `factoryjobs.eu/candidates/` via cPanel API only |

Reuse conceptually where relevant: `cpanel-deployer` / `cpanel-wp-deploy` (A2 cPanel patterns), `infrastructure-health` (raspibig checks).

**Trigger cycle:**

| Stage | Agent | Gate |
|-------|-------|------|
| 1. Refresh data | candidate-data-refresher | STOP if row count drops vs baseline |
| 2. Build HTML (`--all`) | candidate-catalog-builder | Both files regenerated, same candidate count |
| 3. Leak audit (client) | candidate-leak-auditor | ZERO candidate contacts — FAIL halts everything |
| 4. Deploy (cPanel API) | candidate-catalog-deployer | Only on PASS; verify live 200 |

**Hard rules:** A2 deploys via cPanel API only (never SSH/FTP); raspibig pulls via plink/SSH; internal catalog (with contacts) never goes public; no stage runs after a failed predecessor.

**Change history:**
| Date | Change | Target | Reason |
|------|--------|--------|--------|
| 2026-06-24 | Initial harness | 5 agents + candidate-catalog-cycle | Catalog automation |
| 2026-06-25 | Unified catalog: +Construction tab (388), build from live DB | `build_single_html.py`, new skill `unified-catalog-build` | One catalog for all trades; surfaced ~3,000 hidden candidates; fixed DB `name` degradation via email-join name recovery |
| 2026-06-25 | InterJob rebrand + shopping cart + drop "verified" claims | `build_single_html.py` | Neutral multi-trade branding; client builds a basket → one email request; removed false verification copy per user |
| 2026-06-25 | **Deficit catalog is now the DEFAULT** (7 ANOFM occupations: Bucătar/Electrician/Mecanic utilaje/Șofer/Sudor/Tâmplar/Zidar, 717 cand.) | `build_single_html.py` | Only the deficit catalog from now on. Output renamed RO: `catalog_ocupatii_deficitare.html` (+`_intern`). `--full` = legacy all-trades. Occupation match = COR keyword (RO+EN+multilingual) over role+skills+CV. |
| 2026-06-25 | Catalog funnel harness: send to warm leads + auto-respond to baskets | skill `catalog-funnel`, agents `catalog-funnel-sender`/`-responder`, `FUNNEL/` | Reply in-thread from campaign mailbox (Brevo relay; cPanel SMTP dead) → cart reply auto-confirmed by ref+name+occupation, **never contact details** (gated value). 8 warm leads sent. Build emits `FUNNEL/catalog_index.json` (ref→candidate). |
