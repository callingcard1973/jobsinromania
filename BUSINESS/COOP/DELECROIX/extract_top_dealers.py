import csv

# HIGH-VALUE keyword search - only truly relevant terms for Delecroix-type equipment
HIGH_VALUE_KW = {
    'RECOLTAT': ['RECOLT', 'HARVEST', 'COMBINAT', 'COMBINA '],
    'SORTARE/BENZI': ['SORTARE', 'SORTOR', 'CALIBR', 'BENZI TRANSPORT', 'CONVEYOR'],
    'HORTICULTURA': ['HORTI', 'LEGUMIC', 'SERE', 'SERA '],
    'MACHINERY IMPORT': ['UTILAJ', 'MACHINERY', 'MACHINE AGRICOL', 'ECHIPAMENT AGRIC'],
    'BRANDS DELECROIX': ['DELECROIX', 'HORTECH', 'ASA-LIFT', 'MTS-SANDEI', 'MTS SAND'],
    'BRANDS COMPETITORS': ['SIMON GEWIN', 'DOMASZ', 'KRUKOWIAK', 'ERME ', 'FERRARI CO'],
    'SPECIFIC': ['AGROMEC', 'MATRA ', 'IRICOM', 'ROMFARM'],
}

# Also search CAEN 2830 (manufacture) and specific CAEN ranges
fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

high_value = []
caen4661_active = []
caen2830_active = []
total = 0

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        
        name = row.get('denumire', '').strip()
        name_upper = name.upper()
        caen = row.get('cod_caen', '').strip()
        stare = row.get('stare_inregistrare', '').strip()
        
        # Skip dead companies
        if 'RADIERE' in stare.upper() or 'DIZOLVARE' in stare.upper():
            continue
        
        cui = row.get('cui', '').strip()
        adresa = row.get('adresa', '').strip()
        telefon = row.get('telefon', '').strip()
        
        entry = {
            'cui': cui,
            'name': name,
            'addr': adresa,
            'tel': telefon,
            'caen': caen,
            'stare': stare
        }
        
        # Collect all CAEN 4661 active
        if '4661' in caen:
            caen4661_active.append(entry)
        
        # Collect all CAEN 2830 active (manufacture agri machinery)
        if '2830' in caen:
            caen2830_active.append(entry)
        
        # Check high-value keywords
        for category, keywords in HIGH_VALUE_KW.items():
            for kw in keywords:
                if kw in name_upper:
                    entry['category'] = category
                    high_value.append(entry)
                    break
            else:
                continue
            break

print(f'Total: {total:,}')
print(f'CAEN 4661 active: {len(caen4661_active)}')
print(f'CAEN 2830 active: {len(caen2830_active)}')
print(f'High-value keyword matches: {len(high_value)}')

with open(r'D:\MEMORY\DELECROIX\distribuitori_top.txt', 'w', encoding='utf-8') as out:
    out.write(f'DISTRIBUITORI UTILAJE AGRICOLE - TOP FINDS\n')
    out.write(f'Source: ANAF (2.78M firme)\n\n')
    
    # 1. High-value keyword matches
    out.write(f'{"=" * 100}\n')
    out.write(f'HIGH-VALUE KEYWORD MATCHES ({len(high_value)} firme)\n')
    out.write(f'{"=" * 100}\n\n')
    
    for cat in HIGH_VALUE_KW.keys():
        matches = [r for r in high_value if r.get('category') == cat]
        if matches:
            out.write(f'\n--- {cat} ({len(matches)} matches) ---\n\n')
            for r in sorted(matches, key=lambda x: x['name']):
                out.write(f'  {r["name"]}\n')
                out.write(f'    CUI: {r["cui"]} | CAEN: {r["caen"]} | Tel: {r["tel"]}\n')
                out.write(f'    {r["addr"]}\n\n')
    
    # 2. All CAEN 4661 - compact with phones
    out.write(f'\n\n{"=" * 100}\n')
    out.write(f'ALL CAEN 4661 (WHOLESALE AGRI MACHINERY) - ACTIVE ({len(caen4661_active)} firme)\n')
    out.write(f'{"=" * 100}\n\n')
    
    with_phones = [r for r in caen4661_active if r['tel']]
    without_phones = [r for r in caen4661_active if not r['tel']]
    
    out.write(f'--- WITH PHONE NUMBERS ({len(with_phones)}) ---\n\n')
    for r in sorted(with_phones, key=lambda x: x['name']):
        out.write(f'{r["name"]} | {r["tel"]} | CAEN:{r["caen"]} | {r["addr"][:60]}\n')
    
    out.write(f'\n--- WITHOUT PHONE ({len(without_phones)}) ---\n\n')
    for r in sorted(without_phones, key=lambda x: x['name']):
        out.write(f'{r["name"]} | CAEN:{r["caen"]} | {r["addr"][:60]}\n')
    
    # 3. CAEN 2830 - manufacturers
    out.write(f'\n\n{"=" * 100}\n')
    out.write(f'CAEN 2830 (MANUFACTURE AGRI MACHINERY) - ACTIVE ({len(caen2830_active)} firme)\n')
    out.write(f'{"=" * 100}\n\n')
    
    for r in sorted(caen2830_active, key=lambda x: x['name']):
        out.write(f'{r["name"]} | {r["tel"]} | CAEN:{r["caen"]} | {r["addr"][:60]}\n')
    
    # 4. Cross-reference with known distributors
    out.write(f'\n\n{"=" * 100}\n')
    out.write(f'CROSS-REFERENCE: Known Delecroix partners in DB\n')
    out.write(f'{"=" * 100}\n\n')
    
    known = {
        'AGRITECH OGRADA': ['AGRITECH'],
        'EQUINTO': ['EQUINTO', 'EQINTO'],
        'MARCOSER': ['MARCOSER'],
        'GREEN GARDEN': ['GREEN GARDEN'],
        'AGRI ALIANTA': ['AGRIALIANTA', 'AGRI ALIAN'],
        'AGROMEC': ['AGROMEC'],
    }
    
    for label, kws in known.items():
        found = []
        for r in caen4661_active + caen2830_active + high_value:
            for kw in kws:
                if kw in r['name'].upper():
                    found.append(r)
                    break
        if found:
            out.write(f'\n--- {label} ({len(found)}) ---\n')
            for r in found:
                out.write(f'  {r["name"]} | CAEN:{r["caen"]} | {r["tel"]} | {r["addr"][:60]}\n')
        else:
            out.write(f'\n--- {label}: NOT FOUND in any category ---\n')

print(f'Saved to distribuitori_top.txt')
