import csv

# Extract CAEN 4661 companies with proper field mapping
fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

results = []
total = 0

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    print(f'Columns: {cols[:15]}')
    # Expected: cui, denumire, adresa, telefon, fax, cod_postal, stare_inregistrare, data_inregistrare, nr_reg_com, cod_caen
    
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
        
        results.append({
            'cui': cui,
            'denumire': denumire,
            'adresa': adresa,
            'telefon': telefon,
            'stare': stare,
            'caen': caen
        })

print(f'Total: {total:,}, CAEN 4661: {len(results)}')

# Filter: only active companies
active = [r for r in results if 'FUNCŢIUNE' in r['stare'].upper() or 'FUNCTIUNE' in r['stare'].upper()]
print(f'Active (in functiune): {len(active)}')

# Sort by name
active.sort(key=lambda x: x['denumire'])

# Write results
with open(r'D:\MEMORY\DELECROIX\caen4661_distribuitori.txt', 'w', encoding='utf-8') as out:
    out.write(f'CAEN 4661 - DISTRIBUTI UTILAJE AGRICOLE DIN ROMANIA\n')
    out.write(f'Total in DB: {len(results)}, Active: {len(active)}\n')
    out.write(f'Source: anaf_all_romania_full.csv (2,778,122 firme)\n\n')
    
    for i, r in enumerate(active, 1):
        out.write(f'{i}. {r["denumire"]}\n')
        out.write(f'   CUI: {r["cui"]} | Tel: {r["telefon"]} | Stare: {r["stare"]}\n')
        out.write(f'   Adresa: {r["adresa"]}\n')
        out.write(f'   CAEN: {r["caen"]}\n\n')
    
    # Also write a compact list with just names + phones
    out.write(f'\n\n{"=" * 80}\n')
    out.write(f'COMPACT LIST (Name | Phone | Address)\n')
    out.write(f'{"=" * 80}\n\n')
    
    for r in active:
        out.write(f'{r["denumire"]} | {r["telefon"]} | {r["adresa"]}\n')

    # Search for known distributors
    out.write(f'\n\n{"=" * 80}\n')
    out.write(f'KNOWN DISTRIBUTORS CHECK\n')
    out.write(f'{"=" * 80}\n\n')
    
    known = ['AGRITECH', 'EQUINTO', 'EQINTO', 'MARCOSER', 'GREEN GARDEN', 'AGRIALIANTA', 
             'AGRI ALIANTA', 'KUBOTA', 'AGROMEC', 'MATRA', 'IRICOM', 'ROMFARM', 
             'CEREAL', 'AGRICOLA', 'AGRO', 'FARM', 'TRAKTOR', 'TRACTOR']
    
    for kw in known:
        matches = [r for r in active if kw in r['denumire'].upper()]
        if matches:
            out.write(f'\n--- {kw} ({len(matches)} matches) ---\n')
            for r in matches:
                out.write(f'  {r["denumire"]} | {r["telefon"]} | {r["adresa"]}\n')

print(f'Saved to caen4661_distribuitori.txt')
