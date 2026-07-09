# Renewal Radar ISCIR — One-Page Spec

**Angle:** "Autorizatia / echipamentul ISCIR expira → pierzi dreptul de operare." Sub-brand al **ISCIR Compliance Vault** (Product 1, VALIDATED) cu hook pe scadente + reautorizari. Pricing/kit citate din `PRODUCT_PORTFOLIO.md` — neschimbate.

---

## 1. Target Segments

| Segment | Volum | Sursa | Hook |
|---------|-------|-------|------|
| Operatori RSVTI (persoane juridice) | **1.250** | `Operatori-RSVTI-PJ.pdf` / registru ISCIR | Urmaresc scadente pentru clientii lor |
| RSVTI / firme cu autorizatie **EXPIRATA** | **441** | registru ISCIR | Durere acuta, deja descoperiti — outreach prioritar |
| Firme cu autorizatie **suspendata / retrasa** | **311** | `Autorizatii-suspendate.pdf` | Reautorizare urgenta |
| TAM firme cu echipamente ISCIR (CAEN-tinta) | **~42.000** | `comunicat-coduri-CAEN.pdf` | Cold pool de top-funnel |
| Portofoliu de referinta (contractori pressure-eq.) | 7.502 | PRODUCT_PORTFOLIO.md | Cifra de market din portofoliu |

Prioritizare outreach: **441 expirati → 311 suspendati → 1.250 RSVTI → 42K rece.**

---

## 2. Kit Contents + Pricing (din PRODUCT_PORTFOLIO.md — citat)

**Starter Kit — 160 EUR** (COGS 40 EUR, marja 120 EUR), plata unica:
- Seif metalic ignifug 300×400×250 mm
- RFID starter pack: 10 etichete + cititor
- 7 formulare ISCIR laminate
- Checklist de conformitate quick-reference (= lead magnet 12 puncte)
- 30 zile SaaS inclus

**SaaS (lunar):**
| Plan | Pret | Limite |
|------|------|--------|
| Starter | **25 EUR/luna** | 100 documente, 1 utilizator |
| Pro ← target | **45 EUR/luna** | 1.000 documente, 5 utilizatori |
| Enterprise | **90 EUR/luna** | nelimitat, multi-locatie |

Add-on (din portofoliu): tier premium +10–15 EUR/luna = "Tender alerts + compliance" (CPV 51720, 71520 — pressure equipment).

---

## 3. SaaS Features (Renewal Radar core)

1. **Cert/PV upload + OCR** — scanezi procesul-verbal pe telefon → extragere automata date (serie, data, scadenta).
2. **Registru echipamente** — pe serie/numar de inventar (cazane, recipiente, macarale, stivuitoare, ascensoare).
3. **Renewal calendar** — fiecare autorizatie RSVTI + VTP echipament cu data scadenta.
4. **Alerte 90 / 60 / 30 zile** — e-mail + calendar; escaladare la -30 catre responsabilul desemnat.
5. **Audit PDF export** — dosar complet gata de control in cateva secunde.
6. **Team / multi-locatie** — Pro 5 useri, Enterprise nelimitat.
7. **Seif fizic ca backup** — strat dublu (cloud + original RFID-tagged).

Conformitate citata din prescriptiile tehnice: PT CR 4 (RSVTI/evidenta), PT C1/C2/C4/C7/C9/C11 (sub presiune), PT R1/R2 (ridicat), PT CR 6 (sudura/END).

---

## 4. Go-to-Market Phases

**Faza 1 — Durere acuta (sapt. 1–2):** outreach catre cei **441 expirati** + **311 suspendati**. Mesaj: "autorizatia ta figureaza expirata/suspendata — reautorizeaza si nu mai rata urmatoarea scadenta." Lead magnet = checklist 12 puncte. CTA = demo.
**Faza 2 — RSVTI PJ (sapt. 3–4):** cei **1.250** operatori RSVTI. Pitch: gestioneaza scadentele tuturor clientilor dintr-un singur radar (Enterprise 90 EUR/luna).
**Faza 3 — TAM rece (sapt. 5+):** cele **~42.000** firme CAEN-tinta, cold email gentil + webinar "3 firme care si-au pierdut statutul ISCIR".
**Faza 4 — Tender add-on:** alerte licitatii pressure-equipment (CPV) ca upsell premium.

**Conversie tinta:** B2B 2% pe segmentele calde. Break-even kit la luna 7 (per portofoliu).

**Gate:** asset-only. Niciun deploy A2/cPanel si niciun send fara aprobare explicita (vezi skill `iscir-campaign-run`).
