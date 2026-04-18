# Primarii Romania — Research pentru Campanie Echipamente Loc de Joacă (AVP Park)

**Data:** 2026-04-18

---

## Surse de date existente în D:\MEMORY\

### 1. `D:\MEMORY\Z.AI\PRIMARII\primarii_romania.csv`
- **Rows:** 3,181
- **Cu email:** 2,965 (93%)
- **Câmpuri:** name, email, phone, fax, county, address, website, detail_url
- **Sursa originala:** ghidulprimariilor.ro (scrapat)
- **Calitate:** Buna — include telefon si adresa fizica pentru cele mai multe

### 2. `D:\MEMORY\Z.AI\PRIMARII\primarii_datagov_emails.csv`
- **Rows:** 3,186
- **Cu email:** 2,954 (93%)
- **Câmpuri:** judet_cod, judet, cod_siruta, name, email
- **Sursa originala:** data.gov.ro (open data oficial)
- **Calitate:** Buna — include cod SIRUTA (unic per UAT, util pentru deduplicare)

### 3. `D:\MEMORY\Z.AI\PRIMARII\vimishor_primarii.csv`
- **Rows:** 3,181
- **Cu email:** 385 (12%)
- **Câmpuri:** name, locality, email, phone, fax, website, address, county, siruta, cod_postal
- **Calitate:** Slaba ca sursa primara de email, dar buna pentru completat telefon/adresa

### 4. `D:\MEMORY\Z.AI\CUMPARFERME\output\primarii_romania.csv`
- **Rows:** 3,181 (probabil duplicat al sursei #1)

### 5. `D:\MEMORY\ARCHIVE\Z.AI_SUPERMARKETS\DATA\seap_romania_construction.csv`
- **Rows:** 3,340
- **Continut:** Contracte SEAP/SICAP — autoritatea contractanta include PRIMARIA SECTORULUI 4 etc.
- **Utilitate pentru campanie:** Poate fi folosit sa identifici primarii care deja achizitioneaza prin SEAP (au experienta cu proceduri de achizitie publica) — nu contine emailuri directe

### 6. ISC_DATA (`D:\MEMORY\MADR VANZARE TEREN\ISC_DATA\`)
- Diriginti de santier si RTE — persoane fizice autorizate, NU primarii
- **Nerecomandat** pentru aceasta campanie

---

## Rezumat: ce avem gata de utilizat

| Sursa | Primarii totale | Cu email | Recomandata |
|-------|-----------------|----------|-------------|
| primarii_romania.csv | 3,181 | 2,965 | **DA — primara** |
| primarii_datagov_emails.csv | 3,186 | 2,954 | DA — cross-check |
| vimishor_primarii.csv | 3,181 | 385 | Secundar (telefon) |

**Lista finala recomandata: ~3,000 emailuri unice** (dupa deduplicare pe siruta/name intre primele doua surse).

---

## Abordare recomandata

### Pasul 1 — Merge + deduplicare (1-2 ore scripting)
```python
# Merge primarii_romania.csv + primarii_datagov_emails.csv
# Deduplicare pe name normalizat sau cod_siruta
# Output: primarii_merged.csv cu ~3,000 randuri
```

### Pasul 2 — Filtrare comune mici (optional, PNRR C10)
- PNRR C10 tinteste localitati <10K locuitori
- Sursa populatie: INS open data (recensamant 2021) sau `date.gov.ro/datasets/resurse/populatie-localitati`
- Join pe cod SIRUTA → filtreaza la <10K → ~2,200-2,400 comune (din 3,181 total)
- Efort estimat: 2-3 ore (descarca CSV INS + join pe siruta)

### Pasul 3 — Campanie email
- **Tool recomandat:** Brevo API (deja configurat in sistem, expeditor disponibil)
- **Script:** adapteaza `D:\MEMORY\MADR VANZARE TEREN\send_campaign.py` sau scripting nou
- **Template:** deja exista la `D:\MEMORY\BUSINESS\BOGDAN GAVRA\email_template_primarii.txt`
- **Ritm:** 100-200/zi (pastreaza bounce rate sub 5%)
- **Durata:** 15-30 zile pentru toate primarii

### Pasul 4 — Personalizare (optional, creste rata de raspuns)
- Adauga camp `{judet}` si `{localitate}` in template
- Exemplu: "Stimate Primar al comunei Pianu, jud. Alba..."

---

## Surse externe (daca vrei sa completezi emailuri lipsa)

1. **data.gov.ro** — `Registrul national al unitatilor administrativ-teritoriale` — open data, gratuit, contine emailuri oficiale (sursa #2 de mai sus vine de aici)
2. **ghidulprimariilor.ro** — scraping deja facut (sursa #1); poate fi re-scraped pentru date actualizate
3. **e-guvernare.ro/transparenta** — unele primarii public emailuri oficial
4. **SEAP/SICAP** (sicap.e-licitatie.ro) — fiecare autoritate contractanta are date de contact; util pentru primarii cu bugete active

---

## Efort estimat total

| Task | Efort |
|------|-------|
| Merge + dedup primarii (script Python) | 1-2 ore |
| Filtru populatie <10K (INS join) | 2-3 ore |
| Setup campanie Brevo | 1 ora |
| Trimitere + monitorizare | automat, 15-30 zile |
| **Total activ** | **4-6 ore** |

---

## Concluzie

**Nu trebuie strans date noi.** Exista deja ~3,000 emailuri de primarii in `D:\MEMORY\Z.AI\PRIMARII\`. Primul pas este un script de merge/dedup care produce lista finala, apoi lansezi campania Brevo cu templateul existent.

Prioritizarea comunelor mici (<10K locuitori) necesita un join cu date INS, dar este optional — poti lansa si pe intreaga lista si filtrezi raspunsurile manual.
