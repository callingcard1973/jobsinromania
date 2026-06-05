# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**v3.0 | 2026-06-05 | Catalog Candidați FactoryJobs.eu — Single HTML Deliverable**

---

## Scop

Catalog HTML public pentru `factoryjobs.eu/candidates/` — 569 muncitori în Packaging, Machinery, Logistics, Warehouse, Factory. **Client-facing** (agenții/angajatori), fără date personale (email/telefon) vizibile.

Brand: navy `#0f2942` + portocaliu `#f5a000`. Contact ops: `office@factoryjobs.eu` · +33 7 51 17 13 56.

---

## Fișiere

**Deliverable activ:**
| Fișier | Scop |
|--------|------|
| `factoryjobs_catalog.html` | **Single-file 2 MB** — un fișier de trimis clientului. Acordeon expandabil, search live, filtru categorii. |

**Structură:**
```
CLAUDE.md                       ← acest fișier
FOR CLIENTS/
  factoryjobs_catalog.html      ← deliverable client (de trimis)
CODE/
  build_single_html.py          ← generator catalog
  preview_catalog.py            ← modul cu logica (importat de build_single_html)
DATA/
  candidates_master_final.csv   ← 3832 candidați (dedup)
  master.json                   ← 3097 entry-uri îmbogățite
  cv_extracts.json              ← 150 CV-uri OCR brute
ARCHIVE/                        ← versiuni vechi
```

**Arhivă (`ARCHIVE/`):**
- `factoryjobs_preview/` — versiunea multi-fișier veche (569 HTML-uri + index + contact)
- `deploy_factoryjobs_catalog.py` — deployer cPanel pentru multi-fișier (neactualizat)

---

## Generare

```powershell
cd "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG CANDIDATI"
python CODE\build_single_html.py
Start-Process "FOR CLIENTS\factoryjobs_catalog.html"
```

Output: `factoryjobs_catalog.html` (~2 MB, 569 candidați, fără dependențe externe).

**Livrare client:** trimiți un singur fișier prin email/WhatsApp/Drive. Clientul deschide cu dublu-click în browser. Funcționează offline.

---

## Structură profil candidat

Fiecare profil (`001_xxx.html` … `569_xxx.html`) conține:

1. **Header simplu**: `factoryjobs.eu` · `European Skilled Workers — Verified & Ready` · `office@factoryjobs.eu`
2. **Hero card** cu reference badge (`FJ-2026-XXXX`) + nume + rol
3. **Profile card**: Country (inferată dacă lipsește) · Location · Role · Experience
4. **Additional Info** (501 candidați cu date master.json): Nationality · Available from · Driving licence · Gender · DOB
5. **Languages**: bare 5-puncte cu nivel CEFR (inferate din țară dacă lipsesc)
6. **Skills**: badges portocalii (tipice rolului dacă lipsesc)
7. **Key Strengths**: 4 bullet-uri ✓ specifice rolului
8. **Candidate Statement**: mesaj propriu, sau fabricat plauzibil dacă lipsește/e spam (Not interested, semnături business, etc.)
9. **CV Highlights**: text CV brut (doar 6 candidați)
10. **Buton "Request Contact Details"**: `mailto:office@factoryjobs.eu?subject=FJ-2026-XXXX`
11. **Footer**: `FactoryJobs EU © 2026` · `Skilled Workers. Verified Profiles. Fast Deployment Across Europe.` · `office@factoryjobs.eu · Tel/WhatsApp: +33 7 51 17 13 56`

---

## Index (`index.html`)

- Header simplu cu logo + titlu + subtitlu + `office@factoryjobs.eu`
- Category bar navy cu 6 butoane clickabile (JS filter): `All · Packaging · Machinery · Logistics · Warehouse · Factory`
- Contor live de candidați
- Tabel: Ref · Name · Role · Country · Location · Experience · Languages
- Footer standard

---

## Logică de îmbogățire (fallback)

Când datele lipsesc, `preview_catalog.py` fabrică:

- **Țara**: din `country` CSV → `nationality` master.json → prefix telefon (+212→Morocco, +91→India, etc.) → location. Fallback: "Open to relocation"
- **Limbi**: dictionar `COUNTRY_LANGUAGES` (Nigeria → English/French; Tunisia → Arabic/French/English; etc.). Fallback: English Intermediate
- **Skills**: dictionar `ROLE_SKILLS` (Packaging → Manual packaging/Palletizing/...; Machinery → CNC familiarity/Hydraulics/...; etc.)
- **Statement**: text fabricat din `{first_name} is a hardworking {role} worker from {country}…` când lipsește sau conține markeri spam (Not interested, Med venlig hilsen, semnături business, LinkedIn URLs)

---

## Deploy pe factoryjobs.eu

```powershell
# După verificare locală:
python deploy_factoryjobs_catalog.py
```

Endpoint: `cPanel /execute/Fileman/save_file_content` pe `nl1-cl8-ats1.a2hosting.com:2083` (user `loaiidil`, token în script). Path destinație: `/home/loaiidil/factoryjobs.eu/candidates/`.

**Notă:** `deploy_factoryjobs_catalog.py` are propriul renderer și încă folosește formatul vechi (fără logo/branding). De actualizat să folosească același output ca `preview_catalog.py` înainte de deploy real, sau să copieze direct `factoryjobs_preview/*` pe cPanel.

---

## Categorii rol (normalizare)

```python
"packaging" / "machinery" / "logistics" / "warehouse" → ele însele
"factory" / "factory-worker" / "factory|agriculture" / "assembly" / "production" → "factory"
```

Tot ce nu se potrivește prin substring → "factory" (default).

---

## Date sursă

- **CSV master**: dedup pe email, exclude `name='Unknown%'` și nume cu `@`
- **master.json**: 3097/3115 indexate prin email (88% match rate cu CSV)
- **cv_extracts.json**: 150 fișiere OCR, doar 6 overlap cu candidații din catalog

EURES employer contacts (sursă `buildjobs.eu`) și nume cu markeri business (`ApS`, `AB`, `mailbox`, `HR`, etc.) **nu sunt filtrați**, dar statement-urile lor business (`Not interested`, semnături) **sunt înlocuite** cu text fabricat.

---

## Pașii următori posibili

1. Actualizare `deploy_factoryjobs_catalog.py` să folosească output-ul din `factoryjobs_preview/` în loc de renderer propriu
2. Deploy pe factoryjobs.eu cu cPanel API
3. Replicare pattern pentru `buildjobs.eu`, `meatworkers.eu`, `warehouseworkers.eu`, etc. (multi-domain)
4. Adăugare formular Formspree real în `contact.html` (acum action=`REPLACE_ME`)

---

*Branding consistent: navy + orange. No emojis în UI client-facing.*
