import csv

fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

all_4661 = []
total = 0

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        caen = row.get('cod_caen', '').strip()
        if '4661' not in caen:
            continue
        
        cui = row.get('cui', '').strip()
        denumire = row.get('denumire', '').strip()
        adresa = row.get('adresa', '').strip()
        telefon = row.get('telefon', '').strip()
        stare = row.get('stare_inregistrare', '').strip()
        
        # Determine if active
        is_active = 'INREGISTRAT' in stare.upper() or 'RELUARE' in stare.upper()
        is_dead = 'RADIERE' in stare.upper() or 'DIZOLVARE' in stare.upper()
        is_suspended = 'SUSPENDARE' in stare.upper()
        
        status = 'ACTIVE' if is_active else ('SUSPENDED' if is_suspended else 'DEAD')
        
        all_4661.append({
            'cui': cui,
            'name': denumire,
            'addr': adresa,
            'tel': telefon,
            'stare': stare,
            'status': status,
            'caen': caen
        })

active = [r for r in all_4661 if r['status'] == 'ACTIVE']
suspended = [r for r in all_4661 if r['status'] == 'SUSPENDED']
dead = [r for r in all_4661 if r['status'] == 'DEAD']

print(f'Total CAEN 4661: {len(all_4661)}')
print(f'Active: {len(active)}')
print(f'Suspended: {len(suspended)}')
print(f'Dead: {len(dead)}')

# Sort active by name
active.sort(key=lambda x: x['name'])

with open(r'D:\MEMORY\DELECROIX\caen4661_distribuitori.txt', 'w', encoding='utf-8') as out:
    out.write(f'CAEN 4661 - DISTRIBUTI UTILAJE AGRICOLE ROMANIA\n')
    out.write(f'Total: {len(all_4661)} | Active: {len(active)} | Suspended: {len(suspended)} | Dead: {len(dead)}\n')
    out.write(f'Source: ANAF (2,778,122 firme)\n')
    out.write(f'{"=" * 100}\n\n')
    
    for i, r in enumerate(active, 1):
        out.write(f'{i}. {r["name"]}\n')
        out.write(f'   CUI: {r["cui"]} | Tel: {r["tel"]} | {r["status"]}\n')
        out.write(f'   Addr: {r["addr"]}\n\n')
    
    # Keyword search in names
    out.write(f'\n{"=" * 100}\n')
    out.write(f'KEYWORD SEARCH IN ACTIVE COMPANIES\n')
    out.write(f'{"=" * 100}\n\n')
    
    keywords = {
        'TRACTOR/UTILAJ': ['TRACTOR', 'UTILAJ', 'MASI', 'MASIN'],
        'AGROMEC/MATRA': ['AGROMEC', 'MATRA', 'IRICOM', 'ROMFARM'],
        'GREEN/AGRI': ['GREEN', 'AGRI', 'FARM', 'HORTI'],
        'DEALER BRANDS': ['KUBOTA', 'JOHN DEERE', 'NEW HOLLAND', 'CLAAS', 'FENDT', 'MASSEY', 'CASE', 'VALTRA', 'DEUTZ', 'SAME', 'LANDINI', 'ZETOR', 'MTZ'],
        'RECOLT/HARVEST': ['RECOLT', 'HARVEST', 'COMBIN', 'CEREAL'],
        'LEO/LIV': ['LEGUM', 'FRUCT', 'PRODUS'],
        'ECHIP/EQUIP': ['ECHIP', 'EQUIP', 'TEHN', 'TECH'],
    }
    
    for label, kws in keywords.items():
        matches = [r for r in active if any(kw in r['name'].upper() for kw in kws)]
        if matches:
            out.write(f'\n--- {label} ({len(matches)}) ---\n')
            for r in matches:
                out.write(f'  {r["name"]} | {r["tel"]} | {r["addr"][:80]}\n')
    
    # Also search in dead/suspended for known names
    out.write(f'\n\n{"=" * 100}\n')
    out.write(f'KNOWN DISTRIBUTORS CHECK (all statuses)\n')
    out.write(f'{"=" * 100}\n\n')
    
    known = ['AGRITECH', 'EQUINTO', 'EQINTO', 'MARCOSER', 'GREEN GARDEN', 
             'AGRIALIANTA', 'AGRI ALIANTA', 'AGRIALIANTA']
    
    for kw in known:
        matches = [r for r in all_4661 if kw in r['name'].upper()]
        if matches:
            out.write(f'\n--- {kw} ({len(matches)}) ---\n')
            for r in matches:
                out.write(f'  [{r["status"]}] {r["name"]} | {r["tel"]} | {r["addr"][:80]}\n')

print(f'Saved to caen4661_distribuitori.txt ({len(active)} active companies)')
