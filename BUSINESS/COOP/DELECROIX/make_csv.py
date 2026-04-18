import csv

fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

out_csv = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_agricole.csv'

results = []
total = 0

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        caen = row.get('cod_caen', '').strip()
        
        # CAEN 4661 = wholesale agri machinery, 2830 = manufacture agri machinery
        if '4661' not in caen and '2830' not in caen:
            continue
        
        stare = row.get('stare_inregistrare', '').strip()
        if 'RADIERE' in stare.upper() or 'DIZOLVARE' in stare.upper():
            continue
        
        results.append({
            'CUI': row.get('cui', '').strip(),
            'DENUMIRE': row.get('denumire', '').strip(),
            'CAEN': caen,
            'JUDET': row.get('adresa', '').strip()[:150],
            'TELEFON': row.get('telefon', '').strip(),
            'STARE': stare
        })

# Sort by name
results.sort(key=lambda x: x['DENUMIRE'])

with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['CUI', 'DENUMIRE', 'CAEN', 'JUDET', 'TELEFON', 'STARE'])
    writer.writeheader()
    writer.writerows(results)

print(f'Total scanate: {total:,}')
print(f'Active CAEN 4661+2830: {len(results)}')
print(f'Salvat in: {out_csv}')
