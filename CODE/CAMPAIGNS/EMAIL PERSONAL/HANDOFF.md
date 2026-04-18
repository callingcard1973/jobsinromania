# EMAIL PERSONAL — Contact Pipeline HANDOFF
Date: 2026-04-18

## Location
`D:\MEMORY\CAMPAIGNS\EMAIL PERSONAL\`
- `CODE/` — all scripts
- `DATA/` — all CSVs + export/

## What Was Built
6-stage personal contact pipeline:
```
00_merge.py   → DATA/merged.csv      (99,092 raw rows from all sources)
01_clean.py   → DATA/cleaned.csv
02_dedupe.py  → DATA/deduped.csv
03_score.py   → DATA/scored.csv
04_segment.py → DATA/segmented.csv
05_export.py  → DATA/export/index.html + per-segment CSVs
06_enrich.py  → optional, needs raspibig 192.168.100.21
```

Run everything: `cd CODE && python run_all.py`

## Sources in 00_merge.py (all loaded)

### Google Contacts (4 exports)
- contacts-fruitnature.csv (8,083)
- contacts_FRuitnature2.csv (5,615)
- contacts_fruitnature3.csv (20,737)
- contacts_fruitnature4.csv (23,904)

### Yahoo
- contacts_apaminerala_yahoo.csv (10,000)

### Plain email lists
- insolventa RO (×4 files), cadastristi RO (×2), investitii RO (×2)
- Norway, Sweden, Austria wholesalers txt
- Rungis France TXT
- Austria kontaktdatenverzeichnis csv (94 emails)
- Austria anunturi agenti comerciali (233)
- Infoferma RO (516)
- Exporters spices Poland (210)
- Companii rusesti si rusofone (2,479)

### Email+URL CSV format
- Apicole RO, medicinale, prod trad, legume fructe, reciclare
- Cazare Romania (12,217)
- Austria wholesalers, FEBEV Belgium
- **Germany Grossmarkt x15:** Berlin, Bolzano, Bremen, Dortmund, Duisburg, Essen, Frankfurt, Fruchthof Berlin, Hamburg, Hannover, Köln, Leipzig, München, Stuttgart, Necunoscuti
- **France MIN x14:** Agen, Angers, Anjou, Avignon, Bordeaux-Brienne×2, Caen, Grenoble×2, Lille, Nice, Perpignan×3, Strasbourg, Tours
- Belgium: MABRU Bruxelles, Belgium 2
- Denmark: Denmark Contact, Organic Denmark
- UK: uk fruit wholesale, scottish wholesale association members
- Vienna wholesale association members
- Firenze, Genova wholesalers Italy
- Finland teurastamo

### XLSX
- Vienna kontaktdatenverzeichnis.xls.xlsx (92 contacts, sheet=active, skip_rows=1)

### PDF (pdfplumber)
- annuaire2016-fm rungis.pdf (133 emails)
- fruits_et_legumes grossites Rungis.pdf (228 emails)

### DOC (binary scan)
- emails grossistes fruits et legumes rungis.doc (228 emails)

## Segments (after full pipeline)
- personal_close: ~13,337
- phone_only: ~13,510
- anonymous: ~10,052
- business_intl: ~7,638
- business_ro: ~7,072
- business_austria: ~106
- airbnb: 12
- school: 5
- recruitment: 1
- junk: 2

## Scoring Rules (03_score.py)
+30 business email, +20 has org, +20 starred, +15 has phone, +15 has notes
+10 has name, +10 has 2nd email, -20 no name, -30 airbnb domain
Junk threshold: score < 5

## HTML Viewer
`DATA/export/index.html` — dark theme, segment tabs, live search, score badges

## What's NOT Done Yet
1. **Run pipeline with new sources** — `python run_all.py` from CODE/ (was interrupted, last run was with old sources)
2. **enrich_anonymous.py** — extract org from notes for anonymous segment (script exists, run manually)
3. **06_enrich.py** — optional enrichment vs raspibig interjob_master (needs SSH tunnel or LAN)
4. **Napoli XLS** (`I:/BUSINESS/OIPA EXPORT 2023/ALL/PROSPECTING/ITALIA/NAPOLI/list of producers Napoli.xls`) — old .xls format, needs xlrd, 78 emails
5. **Rungis ODS** (`E:/BACKUPS/.../Grossistes fruits et legumes Rungis.ods`) — needs odfpy
6. **Hungary docx** — 0 emails found, skip
7. **FRANCAIS/FRANCE duplicates** — same files as FINLAND/FRANCE, already handled by seen_paths dedup

## Dependencies
```
pip install pdfplumber openpyxl python-docx
```

## Next Session Quick Start
```bash
cd "D:\MEMORY\CAMPAIGNS\EMAIL PERSONAL\CODE"
python run_all.py
# then open DATA/export/index.html
```
