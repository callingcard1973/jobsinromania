import csv

# CAEN 4661 = Wholesale of agricultural machinery, equipment and supplies
# CAEN 2830 = Manufacture of agricultural and forestry machinery  
# Also search for agri keywords in company names

AGRI_NAME_KEYWORDS = ['utilaj', 'tractor', 'agricol', 'agro', 'recoltat', 'combina', 'cerec', 'semen', 'legum', 'horticol', 'agromec', 'matra', 'iricom', 'romfarm', 'farm', 'green garden', 'agritech']

# First check the ANAF file - it has 2.7M rows
fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

print(f'Reading: {fpath}')

# Get header first
with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    print(f'Columns: {cols}')
    
# Find column names
# We need: CAEN, company name, judet, telefon/email

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    
    caen4661 = []
    caen2830 = []
    agri_names = []
    total = 0
    
    for row in reader:
        total += 1
        if total % 500000 == 0:
            print(f'  Scanned {total:,} rows...')
        
        # Get CAEN
        caen_val = ''
        for c in cols:
            if 'caen' in c.lower():
                caen_val = row.get(c, '').strip()
                break
        
        # Get company name
        name_val = ''
        for c in cols:
            if any(kw in c.lower() for kw in ['firma', 'denumire', 'name', 'company', 'nume']):
                name_val = row.get(c, '').strip()
                break
        if not name_val:
            # Try first column
            name_val = row.get(cols[0], '').strip()
        
        # Get judet
        judet_val = ''
        for c in cols:
            if 'judet' in c.lower() or 'county' in c.lower():
                judet_val = row.get(c, '').strip()
                break
        
        # Get contact
        contact_val = ''
        for c in cols:
            if any(kw in c.lower() for kw in ['telefon', 'phone', 'email', 'contact']):
                val = row.get(c, '').strip()
                if val:
                    contact_val += val + ' '
        
        # Check CAEN 4661
        if '4661' in caen_val:
            caen4661.append((name_val, judet_val, caen_val, contact_val.strip()))
        
        # Check CAEN 2830
        if '2830' in caen_val:
            caen2830.append((name_val, judet_val, caen_val, contact_val.strip()))
        
        # Check agri keywords in name
        name_lower = name_val.lower()
        for kw in AGRI_NAME_KEYWORDS:
            if kw in name_lower:
                agri_names.append((name_val, judet_val, caen_val, contact_val.strip()))
                break
    
    print(f'\nTotal rows scanned: {total:,}')
    print(f'CAEN 4661 (wholesale agri machinery): {len(caen4661)}')
    print(f'CAEN 2830 (manufacture agri machinery): {len(caen2830)}')
    print(f'Agri name keywords: {len(agri_names)}')
    
    # Write results
    with open(r'D:\MEMORY\DELECROIX\distribuitori_agri_db.txt', 'w', encoding='utf-8') as out:
        out.write(f'DISTRIBUITORI UTILAJE AGRICOLE DIN BAZA ANAF\n')
        out.write(f'Total firme scanate: {total:,}\n')
        out.write(f'Data sursa: {fpath}\n\n')
        
        out.write(f'=' * 80 + '\n')
        out.write(f'CAEN 4661 - WHOLESALE AGRICULTURAL MACHINERY ({len(caen4661)} firme)\n')
        out.write(f'=' * 80 + '\n\n')
        for i, (name, judet, caen, contact) in enumerate(sorted(caen4661, key=lambda x: x[1]), 1):
            out.write(f'{i}. {name} | {judet} | CAEN:{caen} | {contact}\n')
        
        out.write(f'\n\n{"=" * 80}\n')
        out.write(f'CAEN 2830 - MANUFACTURE AGRICULTURAL MACHINERY ({len(caen2830)} firme)\n')
        out.write(f'{"=" * 80}\n\n')
        for i, (name, judet, caen, contact) in enumerate(sorted(caen2830, key=lambda x: x[1]), 1):
            out.write(f'{i}. {name} | {judet} | CAEN:{caen} | {contact}\n')
        
        out.write(f'\n\n{"=" * 80}\n')
        out.write(f'AGRI NAME KEYWORDS ({len(agri_names)} firme)\n')
        out.write(f'Keywords: {AGRI_NAME_KEYWORDS}\n')
        out.write(f'{"=" * 80}\n\n')
        for i, (name, judet, caen, contact) in enumerate(sorted(agri_names, key=lambda x: x[1]), 1):
            out.write(f'{i}. {name} | {judet} | CAEN:{caen} | {contact}\n')

print(f'\nResults saved to distribuitori_agri_db.txt')
