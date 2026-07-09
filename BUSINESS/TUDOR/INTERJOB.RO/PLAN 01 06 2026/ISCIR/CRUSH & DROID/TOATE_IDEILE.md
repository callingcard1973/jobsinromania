# TOATE IDEILE DE MONETIZARE ISCIR — UNIFICAT

Sursa: MONETIZARE.md (10 idei) + IDEI.md (22 idei) + audit date (67K firme, ANAF, triangulare)
Data: 2026-06-27

---

## INVENTAR DATE (ce avem ACUM)

| Dataset | Randuri | Email | Telefon | Extra |
|---------|---------|-------|---------|-------|
| clienti_iscir_enriched.csv | 67.401 | 2.009 (3%) | 59.931 (89%) | ANAF: status, adresa, TVA, inactiv, 42 judete complete — 31.368 judete extrase din ANAF azi |
| clienti_finali_iscir.csv (triangulati) | 114.461 | 7.862 (6.9%) | 81.341 (71%) | Scor: food_boiler(95K), sector_size(15K), eu_funds(1.9K), procurement(41) |
| clienti_finali_CORE.csv | 1.019 | ~65% | 99% | Multi-semnal sau licitatie — lista prioritara de atac |
| operatori_rsvti_pj_enriched.csv | 1.250 | 1.050 (84%) | 1.201 (96%) | Segment, status, CUI — 441 expirati, 311 suspendati |
| rsvti_ce_face.csv | 1.250 | — | — | Site target, servicii, note |
| autorizatii_suspendate_enriched.csv | 311 | 47 | 190 | Contactabil: 237 |
| clienti_pe_judet/ | 42 CSV | — | — | Liste gata, acum complete pe toate judetele |
| websites_operatori/ | 926 HTML | — | — | **Deployat** pe interjob.ro/iscir/operatori/ |
| pages/ | 42 HTML | — | — | Cu CTA "Vreau demo" — de actualizat cu judetele complete |
| ANAF cache | 67K | — | — | Status TVA, inactiv(10K), radiere(21K), suspendare(2.7K) |
| Template-uri site | `templates/firm_default.html` | — | — | Token-based %%NAME%%, %%PHONE%% etc. — schimbi design fara cod |

---

## A. VANZARE DIRECTA DATE / LEADURI (cash rapid)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 1 | **Lead Packs pe judet** — liste clienti ISCIR pe judet la operatori | MONETIZARE #1 | 1.050 operatori | 99 RON/judet/luna | 5.200 RON/luna | Mic — doar campanie email |
| 2 | **Lead Packs pe CAEN** — liste filtrate pe tip echipament (ex: toate cazanele din Cluj) | Audit | 1.050 operatori | 149 RON/CAEN | 3.000 RON/luna | Mic — aceeasi infra |
| 3 | **Lead Packs NDT** — clienti pt laboratoare incercari nedistructive (CAEN 7120: 5.699 firme) | Audit | NDT labs | 199 RON/lista | 2.000 RON/luna | Mic — campanie separata |
| 4 | **Lista suspendati+expirati** — 311+441 firme in criza, nevoie urgenta de re-autorizare | MONETIZARE #2 | 752 firme | 497-1.497 RON | 15.000 RON (one-shot) | Mic — template email + script tel |
| 5 | **CORE 1.019 — lead-uri premium** — firme multi-semnal, 99% telefon, 65% email | HANDOFF | 1.019 firme | 299 RON/lista | 3.000 RON/luna | Mic — datele sunt gata |
| 6 | **Leads pentru vanzatorii de echipament** — firme cu autorizatie expirata = cumpara cazane/stivuitoare/macarale noi | IDEI B.6 | Producatori (Still, Linde, Viessmann, Bosch) | Per lead | 3.000 RON/luna | Mic — listele exista |
| 7 | **Leads pentru scoli de calificare** — fochisti/stivuitoriasti/macaragii = recertificare recurenta obligatorie | IDEI B.7 | 1.250 operatori + detinatori | Per cursant | 2.000 RON/luna | Mic — ai ambele parti |
| 8 | **Leads pentru firme de service echipament** — detinatori fara contract de mentenanta | IDEI B.8 | 7.476 firme autorizate ISCIR | Per lead | 2.000 RON/luna | Mic — filtrare |
| 9 | **Leads de asigurari** — firme cu echipament sub presiune = nevoie de asigurare specifica | MONETIZARE #10 | Brokeri | 20% comision | 2.000 RON/luna | Mediu — parteneriat broker |
| 10 | **Multi-signal Lead Packs** — 983 firme cu 2+ semnale (scor 5-10) | Audit | 1.050 operatori | 299 RON/lista | 1.500 RON/luna | Mic |

## B. SERVICII WEB (productie zero-token, marja ~90%)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 11 | **Site-uri web firme fara pagina** — generezi demo gratis (ai generatorul), vinzi 490/990 RON/an | IDEI A.1 | 999 operatori → 14K detinatori → 2,14M total RO | 490-990 RON/an | 10.000 RON/luna | Mic — deja ai 926 HTML gata, e doar upsell |
| 12 | **Operator Demo Site upgrade** — site-urile deja generate, deployate pe interjob.ro, vinzi domeniu propriu | MONETIZARE #4 | 926 operatori | 29-99 RON/luna | 3.000 RON/luna | Mediu — DNS + config A2 |
| 13 | **Director public SEO** — „Operatori RSVTI autorizati in [judet]" + pagini SEO pe judet/oras | IDEI A.2 | Trafic organic | Listare premium | 4.000 RON/luna | Mic — pagini deja generate |
| 14 | **Hosting + mentenanta** — abonament recurent pe site-urile vandute | IDEI A.3 | Clienti sites | 29 RON/luna | 2.000 RON/luna | Mic — lock-in |
| 15 | **Badge „Verificat ISCIR/RSVTI"** — marca de incredere pentru site-ul operatorului | IDEI A.4 | 1.250 operatori | 9 RON/luna | 1.000 RON/luna | Mic — doar un badge |
| 16 | **Google Maps/SEO Optimization** — firma apare pe Google Maps | Adaugat | 1.250 operatori | 199 RON/luna | 4.000 RON/luna | Mediu — creare conturi |
| 17 | **Social Media Presence** — pagina Facebook/Instagram gestionata | Adaugat | 1.250 operatori | 99 RON/luna | 2.000 RON/luna | Mediu — template-uri |
| 18 | **Pachet „Prezenta digitala IMM"** — site + Google Business + listare director + SMS, bundle | IDEI F.21 | Micro-firme | 99 RON/luna | 5.000 RON/luna | Mediu — bundle |

## C. MATCHING / MARKETPLACE (intentie dovedita, detii ambele parti)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 19 | **ISCIR Market** — matching detinator <-> operator (recomanzi 3 operatori in zona) | MONETIZARE #5 | 67.401 firme | 50 RON/lead | 5.000 RON/luna | Mare — platforma |
| 20 | **Lead-gen invers** — firma cauta „operator RSVTI [oras]" → o rutezi catre un operator | IDEI B.5 | 67.401 firme | Per lead/contract | 5.000 RON/luna | Mediu — directorul exista |
| 21 | **Equipment second-hand** — conectare vanzatori-cumparatori utilaje ISCIR | MONETIZARE #5 | 10.409 fabricanti | 5% comision | 3.000 RON/luna | Mare — platforma |

## D. RECRUTARE (leaga de masina de bani InterJob)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 22 | **Recrutare catre detinatori** — fabrici metalice/constructii/alimentar angajeaza sudori, mecanici, stivuitoristi, fochisti = exact deficitul ANOFM | IDEI E.16 | Detinatori | Fee plasare | 10.000 RON/luna | Mediu — foloseste pipeline InterJob |
| 23 | **Catalog candidati → detinatori** — trimiti catalog de meseriasi disponibili | IDEI E.17 | Detinatori | Per catalog | 3.000 RON/luna | Mic — interjob-catalog skill |
| 24 | **Plasare deserventi calificati** — detinatorii au nevoie de fochisti/stivuitoristi autorizati | IDEI E.18 | Detinatori + scoli | Per plasare | 5.000 RON/luna | Mediu — leaga de scolile din B.7 |

## E. CALL CENTER / CANAL TELEFON (canalul real — telefon 85%)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 25 | **Serviciu broadcast SMS/WhatsApp** — campanii pe telefon catre firme | IDEI D.14 | Orice | Per campanie | 3.000 RON/luna | Mediu — infrastructura |
| 26 | **Call-center / appointment-setting** — suni detinatorii (99% tel in CORE), califici, vinzi | IDEI D.15 | Detinatori CORE | Per apel/contract | 5.000 RON/luna | Mare — agenti/automation |
| 27 | **Re-Authorization Assistance (telefon)** — suni 311 suspendati, oferi kit re-autorizare | MONETIZARE #2 | 237 contactabili | 497-1.497 RON | 15.000 RON one-shot | Mic — script + template |

## F. PRODUSE DE DATE B2B (marja pura, recurent)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 28 | **Abonament date ISCIR** — set complet (operatori + detinatori + echipament + CAEN + geo) | IDEI C.10 | Asiguratori, vendori, consultanti | 1.999 RON/luna | 6.000 RON/luna | Mic — datele sunt gata |
| 29 | **Raport „Inteligenta de piata"** — densitate echipament pe judet/tip | IDEI C.11 | Investitori, producatori | 1.999 RON/raport | 4.000 RON/luna | Mic — layout + PDF |
| 30 | **Monitorizare conformitate** — flux alerte: „cine si-a pierdut autorizatia in judetul tau" | IDEI C.12 | Operator, asiguratori | 99 RON/luna | 2.000 RON/luna | Mediu — alertare automata |
| 31 | **API de verificare** — „e firma X autorizata ISCIR?" endpoint platit | IDEI C.13 | Platforme, achizitori | 999 RON/luna | 3.000 RON/luna | Mare — API infra |
| 32 | **ANAF Risk Reports** — stare platitor TVA, inactiv, radiat per firma | Adaugat | Oricine | 29 RON/raport | 1.000 RON/luna | Mediu — pagina + Stripe |

## G. CAMPANII EMAIL (dupa enrichment la 30%+)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 33 | **Email Campaign Service B2B** — trimiti campanii in numele operatorului catre clienti | MONETIZARE #6 | 1.250 operatori | 199-799 RON | 10.000 RON/luna | Mediu — 30%+ email coverage |
| 34 | **Newsletter ISCIR lunar** — noutati, termene, oportunitati | Adaugat | Firme + operatori | 0 (gratis) | Trafic/BRAND | Mic — content lunar |

## H. REPLICARE / SCALARE (multiplici playbook-ul)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 35 | **ANRE (electricieni)** — acelasi playbook, folderele exista | IDEI F.19 | Electricieni | Acelasi model | 10.000 RON/luna | Mediu — scraping + template |
| 36 | **ANCOM (telecom)** — acelasi playbook | IDEI F.19 | Telecom | Acelasi model | 5.000 RON/luna | Mediu |
| 37 | **ITM + IGSU (PSI) + DSVSA + metrologie** — orice firma cu obligatie legala recurenta | IDEI F.20 | Toate | Acelasi model | 20.000 RON/luna | Mare — extensie |

## I. SAAS (parcat, revii mai tarziu)

| # | Idee | Origine | TAM | Pret | Estimat | Efort |
|---|------|---------|-----|------|---------|-------|
| 38 | **Compliance Vault SaaS** — calendar scadente + dosar digital multi-tenant | MONETIZARE #3 + IDEI G.22 | 67.401 firme | 49-199 RON/luna | 15.000 RON/luna | Foarte mare — spec gata |
| 39 | **Equipment Registry SaaS** — platforma gestiune echipamente ISCIR online | MONETIZARE #7 | 67.401 firme | 49 RON/luna | 10.000 RON/luna | Foarte mare |
| 40 | **ISCIR Training Marketplace** — cursuri RSVTI/PTS/sudura | MONETIZARE #8 | 1.250 operatori | 15% comision | 5.000 RON/luna | Mare — platforma |

---

## PRIORITIZARE FINALA

### FA ACUM (0 efort, datele exista, cash rapid)

```
#1  Site-uri web (11)        — 10.000 RON/luna — ai 926 HTML gata, e doar upsell
#4  Suspendati+expirati (4)   — 15.000 RON one-shot  — email + telefon
#11 Demo Site upgrade (12)    — 3.000 RON/luna — site-urile sunt deja LIVE
#1  Lead Packs pe judet (1)   — 5.200 RON/luna — doar campanie email
#2  Lead Packs pe CAEN (2)    — 3.000 RON/luna — aceeasi infra
#3  Recrutare (22)            — 10.000 RON/luna — foloseste InterJob existent
```
**Total pas 1: ~46.000 RON/luna + 15.000 RON one-shot**

### CONSTRUIESTE (efort mediu, sapt. 2-4)

```
#13 Director SEO (13)         — 4.000 RON/luna
#16 Google Maps/SEO (16)      — 4.000 RON/luna
#7  Abonament date (28)       — 6.000 RON/luna
#9  Raport inteligenta (29)   — 4.000 RON/luna
```

### DEPOZITE (efort mare, luna 2+)

```
#5  ISCIR Market (19)         — 5.000 RON/luna
#6  Equipment Marketplace (21) — 3.000 RON/luna
#8  Email campaigns (33)      — 10.000 RON/luna (needs enrichment)
#12 Compliance Vault (38)     — 15.000 RON/luna (spec gata)
```

### STRATEGIC (luna 3+)

```
#14 Replicare ANRE (35)       — 10.000 RON/luna
#15 Replicare ANCOM/ITM (36-37) — 25.000 RON/luna
```

---

## NOTA STRATEGICA (din IDEI.md originala)

Nu vinde un singur lucru — **stivuiesc**: aceeasi firma-detinator poate cumpara site (11) + primeste candidati (22) + e listata in director (13) + e lead pentru vendor (6). Un contact, mai multe fluxuri. Canalul = telefon (suna, nu trimite email).

## DATE NOI DESCOPERITE LA AUDIT (2026-06-27)

- **31.368 judete extrase din ANAF** — acum 42 judete complete. BUCURESTI: 10.561 (era 8.209).
- **2.582 telefoane noi din ANAF** — acoperire 89% (era 85%).
- **10.255 firme inactive ANAF** (15%) — de filtrat sau vandut ca date risc.
- **21.015 radiate** (31%) — nu mai sunt active.
- **5.699 testeri CAEN 7120** — potential NDT. 113 email, 4.082 tel.
- **924 operatori fara site** (74%) — site-uri deja generate si LIVE pe interjob.ro/iscir/.
- **441 operatori cu autorizatie expirata** (35%) — lead urgent Compliance + reinoire.
- **983 firme cu 2+ semnale triangulare** — lead-uri incredere ridicata.
