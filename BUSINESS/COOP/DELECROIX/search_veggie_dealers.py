import csv

# Search for companies that might be specifically focused on vegetable/small-scale farming equipment
# Not just tractors for cereal farmers

VEG_KEYWORDS = [
    'LEGUM', 'FRUCT', 'HORTI', 'SERĂ', 'SERA', 'SOLARI', 'PICURARE', 'IRRIGA',
    'RECOLT', 'SORTARE', 'CALIBR', 'AMBAL', 'PACK', 'PRODUS MONTAN',
    'BANDĂ', 'BANDA', 'CONVEYOR', 'TRANSPORT', 'BENZI',
    'DELECROIX', 'SIMON', 'DOMASZ', 'KRUKOWIAK', 'MTS', 'SANDEI',
    'HORTECH', 'ASA-LIFT', 'ERME', 'FERRARI',
    'MARCOSER', 'EQUINTO', 'EQINTO', 'AGRIALIANTA', 'AGRI ALIAN'
]

fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

results = []
total = 0

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        
        # Check ALL rows, not just CAEN 4661
        name = row.get('denumire', '').upper()
        caen = row.get('cod_caen', '').strip()
        stare = row.get('stare_inregistrare', '').strip()
        
        # Must be active
        if 'RADIERE' in stare.upper() or 'DIZOLVARE' in stare.upper():
            continue
        
        # Check keywords in name
        matched = []
        for kw in VEG_KEYWORDS:
            if kw in name:
                matched.append(kw)
        
        if not matched:
            continue
        
        cui = row.get('cui', '').strip()
        adresa = row.get('adresa', '').strip()
        telefon = row.get('telefon', '').strip()
        
        results.append({
            'cui': cui,
            'name': row.get('denumire', '').strip(),
            'addr': adresa,
            'tel': telefon,
            'caen': caen,
            'keywords': matched
        })

print(f'Total scanned: {total:,}')
print(f'Matches: {len(results)}')

with open(r'D:\MEMORY\DELECROIX\veggie_dealers.txt', 'w', encoding='utf-8') as out:
    out.write(f'DEALERS WITH VEGETABLE/HORTICULTURE KEYWORDS\n')
    out.write(f'Total matches: {len(results)}\n')
    out.write(f'Keywords searched: {VEG_KEYWORDS}\n')
    out.write(f'{"=" * 100}\n\n')
    
    # Group by keyword
    for kw in VEG_KEYWORDS:
        matches = [r for r in results if kw in r['keywords']]
        if matches:
            out.write(f'\n--- {kw} ({len(matches)} matches) ---\n')
            for r in matches:
                out.write(f'  {r["name"]} | CAEN:{r["caen"]} | {r["tel"]} | {r["addr"][:80]}\n')
    
    out.write(f'\n\n{"=" * 100}\n')
    out.write(f'ALL MATCHES SORTED BY NAME\n')
    out.write(f'{"=" * 100}\n\n')
    
    for r in sorted(results, key=lambda x: x['name']):
        out.write(f'{r["name"]}\n')
        out.write(f'  CUI: {r["cui"]} | CAEN: {r["caen"]} | Tel: {r["tel"]}\n')
        out.write(f'  Keywords: {", ".join(r["keywords"])}\n')
        out.write(f'  Addr: {r["addr"]}\n\n')

print('Saved to veggie_dealers.txt')
