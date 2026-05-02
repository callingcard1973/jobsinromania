# Todo — HYPER BNDF

## Session 2026-04-20

### Făcut
- PDF catalog + ofertă generate via Puppeteer (raspibig `/tmp/pdfgen/`)
- Antet corporativ HYPER BNDF pe toate paginile
- Fix pagini goale catalog (1 produs/pagină, cover 248mm)
- Conținut mutat în `BOGDAN GAVRA\HYPER BNDF\` (subdirector)
- Toate referințele interne actualizate
- Tentacle CONTEXT.md actualizat
- Skill `puppeteer-html-pdf` creat

- CUI corectat: `33286554` → `RO33286554` (prefix RO adăugat)
- Reg. Com. corectat: `J40/14007/2014` → `J2014007175405`
- Fix aplicat în: oferta HTML, catalog + oferta Puppeteer scripts, CLAUDE.md
- Ambele PDF-uri regenerate cu date corecte

### Pending
- Structura finală: `D:\MEMORY\BUSINESS\BOGDAN GAVRA\HYPER BNDF\`
- Ofertă: `padding-top` actual 8mm, user vrea 10mm la regenerare
- Deploy PDF-uri pe agroevolution.com când Bogdan confirmă

## Session 2026-04-21

### Făcut
- Extras 184.496 candidați CONSILIERI LOCALI din `Candidaturi_locale_2024.xlsx`
- JOIN cu `primarii_export.csv` pe localitate + județ (normalizare diacritice Ş/Ţ→S/T)
- 170.153 matched (92%), 14.343 fără match (localități absente din primarii CSV)
- Output: `DATA/consilieri_locali_2024.csv` (judet, localitate, nume, prenume, partid, pozitie_lista, email_primarie, phone_primarie, primar_nume)
- Script: `CODE/extract_consilieri.py`

### Pending
- Folosit consilieri pentru campanie email/telefon la primării
- Filtru recomandat: `pozitie_lista ≤ 5` pentru consilieri cu șanse mari aleși
- Deploy PDF-uri pe agroevolution.com când Bogdan confirmă

## Session 2026-04-24

### Făcut

**Scraper & Date produse AVP Park:**
- `scraper.py` — 135 produse din 19 categorii, imagini descărcate → `DATA/images/`
- `scraper_gallery.py` — 91 produse galerie (bănci, gazebo, pergole, sport)
- `add_prices.py` — prețuri estimate EUR/RON bazate pe benchmarks competitori
- `extract_pdf_specs.py` — Safety Zone + Volume din PDF via text layer (cost zero), 111/226 matched
- Output final: `PRODUSE/PRODUSE_avp_park_226_cu_preturi_si_specs.csv`

**Research piață & competiție:**
- 15 competitori analizați, prețuri, SEO → `ANALIZA/`
- `competitor_amenajareparc_preturi.csv` — 635 produse scraped, avg complex 69.830 EUR fără TVA
- EN 1176/1177 rezumat → ISCIR NU e necesar pt echipamente statice
- AVP Park are site RO dar FĂRĂ distribuitor → oportunitate exclusivitate (WhatsApp +90 549 659 29 49)

**Lead lists:**
- `LEADS_gradinite_private_1016_contactare_directa.csv` — 1016 grădinițe private ARACIP 2026
- `LEADS_primarii_top300_prioritate_email_campanie.csv` — top 300 primării scored
- `LEADS_firme_instalatori_parcuri_parteneri_potentiali.md`

**Materiale vânzări:**
- `tabel_produse_preturi.html` — 226 produse cu filtre + prețuri
- `pachete_reabilitare_infiintare.html` — pachete Reabilitare/Înființare
- `loc_de_joaca_landing.html` — landing page SEO gata de deploy
- `whatsapp_scripts.md` — 3 template-uri: primar / grădiniță / arhitect
- `email_template_primari.html` — template Brevo cu {{primar_nume}} {{localitate}}

**Infrastructură:**
- `bid_alert.py` pe raspibig — monitorizează și CN/SCN noi (anunțuri participare)
- `DATA/` reorganizat: LEADS/ PRODUSE/ ANALIZA/ INFO/ SURSA/ NOTE/

### Pending
- Agent SEAP prețuri adjudecări reale — încă rulează
- Caută alte site-uri competitoare cu prețuri publice (întrerupt)
- Deploy `loc_de_joaca_landing.html` → agroevolution.com/spatii-verzi/loc-de-joaca/
- Campanie email automată top 300 primării (Brevo 50/zi)
- Fișe tehnice PDF per produs (format arhitecți)
- 3 articole blog SEO agroevolution.com
- Draft WhatsApp exclusivitate AVP Park (+90 549 659 29 49)
- Szabi — cine e? (menționat de Bogdan, neidentificat)
- Traducere denumiri produse turcă → română
- **REGULA: nu șterge fișiere fără confirmare explicită item cu item**

## Session 2026-04-23

### Făcut
- Catalog nou temă vară: `CATALOGS/catalog_vara_2026.html` + `catalog_vara_2026.pdf`
  - Paletă: amber #f59e0b, sky blue #0ea5e9, grass green #16a34a
  - Aceleași 6 produse (AVP-P01..AVP-F01), aceleași imagini IMAGES/
  - Mesaj: "Vine Vara — Locuri de Joacă pentru Comunitatea Ta", livrare 4-6 săpt
  - Antet HYPER BNDF cu bordură galbenă (Puppeteer headerTemplate)
  - Cover height 248mm, 1 produs/pagină (page-break-after:always) — fără pagini goale
- Fix footer CUI în `catalog_bogdan.html`: `CUI 33286554` → `CUI RO33286554 · J2014007175405`
- Ofertă regenerată cu `padding-top: 10mm` (era 8mm): `oferta_comerciala_bogdan_2026-04.pdf`
- Puppeteer script: `CODE/vara_to_pdf.mjs` (raspibig /tmp/pdfgen/)

### Key Files
- `CATALOGS/catalog_vara_2026.html` — catalog vară (HTML)
- `CATALOGS/catalog_vara_2026.pdf` — catalog vară (PDF, gata de trimis)
- `CATALOGS/oferta_comerciala_bogdan_2026-04.pdf` — ofertă cu padding 10mm
- `CODE/vara_to_pdf.mjs` — Puppeteer script catalog vară
- `handoff_bogdan_2026-04-23.md` — draft mesaj WhatsApp + linkuri pentru Bogdan

### Pending
- Deploy `catalog_vara_2026.html` pe agroevolution.com/spatii-verzi/catalog-vara.html (așteaptă confirmare Tudor)
- Deploy PDF-uri cu link download direct pe site
- Campanie email primari: template "Vine Vara" cu `primar_nume` din primarii_campanie_enriched.csv
- Export consilieri `pozitie_lista ≤ 5` cu email primărie → gata pentru campanie

## Session 2026-04-25 (continuare)

### Făcut

**hyperbndf.com — site complet:**
- `index.html` — homepage verde, fără PNRR/iluminat/estimare cost, audit banner fix
- `catalog.html` — 226 produse AVP Park, secțiune "Proiecte Recomandate" (3 pachete)
- `partner.html` — program parteneriat B2B (montatori, peisagiști, revânzători)
- `cautam-partener.html` — pagină recrutare stil job post
- Deploy: toate 4 fișiere live pe `hyperbndf.com/`

**Catalog — Proiecte Recomandate (nou):**
- 3 pachete predefinite: Colț de Joacă (80-100m²), Parcul Verde (150-200m²), Complex Recreere (300-500m²)
- Fiecare: badge EN 1176 TUV, garanție 2+10 ani, buton "Solicită ofertă" → modal
- Modal formular: Nume, Telefon, Email, Mesaj → POST JSON → `hyperbndf.com/send_offer.php`
- Succes: confirmare inline, fallback telefon +40 722 380 349

**Nav simplificat (toate paginile):**
- 3 linkuri: Spații de Joacă · Catalog Produse · Parteneri
- Scos: Căutăm Partener (duplicat), Estimare Cost, Iluminat Inteligent

**Research piață:**
- 10 competitori studiați: Dupex, PlayZone, JUKO, Atlas, Happy Time, Megastol, ArtDecor, Wickey, Loftrek, Urban Market
- Listă potențiali cumpărători (primării cu istoric TED), montatori (CAEN 8130), revânzători
- Firme de interes pentru parteneriat: Loftrek, Happy Time, Megastol, Maksan Techo, Cris Garden

### Idei de Implementat (prioritizate)

1. **Contor proiecte** — "X primării deservite" pe homepage (chiar și 5-10 e credibil)
2. **Garanție 10 ani** — AVP Park are? Dacă da, afișat pe banner + fiecare produs
3. **Livrare rapidă din stoc** — termen explicit "15-30 zile livrare" pe fiecare produs/pachet
4. **Autorizație ISCIR montatori** — dacă partenerii de montaj sunt autorizați, menționat explicit
5. **3D rendering gratuit** — extinde audit teren cu plan 2D/3D orientativ (deja ai pitch-ul)
6. **Prețuri orientative afișate** — "de la X lei" pe pachete → filtrează lead-uri calificate
7. **Proiect emblematic fotografiat** — 1 parc bine documentat > 50 menționări anonime
8. **Transport inclus la prag** — ex: "Transport gratuit la comenzi >25.000 RON"
9. **Segmentare SEO pe material** — pagini separate oțel inox / WPC / HDPE pe hyperbndf.com
10. **Campanie email parteneri** — Loftrek / Happy Time / Megastol: template ofertă distribuție

### Pending
- Campanie email top 300 primării (Brevo, template {{primar_nume}})
- Template email parteneriat pentru Loftrek / Happy Time / Megastol
- Fișe tehnice PDF per produs (format arhitecți/SEAP)
- Deploy loc_de_joaca_landing.html → agroevolution.com/spatii-verzi/
- 3 articole blog SEO pe agroevolution.com
- Draft WhatsApp exclusivitate AVP Park (+90 549 659 29 49)

## Session 2026-04-25 (final)

### Făcut

**8 idei competiție implementate pe hyperbndf.com:**
1. Contor homepage: 226 produse · 10 ani garanție · 15–30 zile livrare · ISCIR autorizat (în loc de EN1176 x2)
2. Garanție 10 ani — hero, step 04, toate pachetele catalog, paginile SEO
3. Livrare 15–30 zile — hero, bullets contact, badge catalog
4. Montaj ISCIR autorizat — hero stat, step 03, badge catalog, pagini SEO
5. Plan 2D/3D gratuit în 48h — audit section pasul 03 extins cu randare + deviz
6. Prețuri orientative pe pachete: 18.000 / 38.000 / 75.000 RON (fără TVA)
7. Transport gratuit >25.000 RON — badge catalog + bullets contact
8. 3 pagini SEO noi: `echipamente-otel-inox.html`, `echipamente-wpc.html`, `echipamente-hdpe.html`

**Modal audit teren:**
- "Programează acum →" din bannerul fix + buton din secțiunea #audit → modal cu formular dedicat
- Câmpuri: Nume+Telefon (obligatorii), Localitate*, Email, Suprafață m², Note
- Submit → `hyperbndf.com/send_offer.php` → email Bogdan
- Succes inline, fallback telefon

**Nav simplificat (toate paginile):**
- 3 linkuri: Spații de Joacă · Catalog Produse · Parteneri
- Scos: Căutăm Partener (duplicat), Estimare Cost, Iluminat Inteligent

**Key files:**
- `deploy/index.html` — homepage cu modal audit
- `deploy/catalog.html` — pachete cu prețuri + badges
- `deploy/echipamente-otel-inox.html` — pagină SEO oțel
- `deploy/echipamente-wpc.html` — pagină SEO WPC
- `deploy/echipamente-hdpe.html` — pagină SEO HDPE
- `deploy/partner.html`, `deploy/cautam-partener.html` — nav fix

### Pending
- Campanie email top 300 primării (Brevo, template {{primar_nume}})
- Template email parteneriat Loftrek / Happy Time / Megastol
- Fișe tehnice PDF per produs (format arhitecți/SEAP)
- 3 articole blog SEO pe agroevolution.com
- Draft WhatsApp exclusivitate AVP Park (+90 549 659 29 49)
- Contor real "X primării deservite" — când Bogdan confirmă numărul
