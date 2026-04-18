import csv

fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

# Check stare values and count active
stares = {}
total = 0
caen4661_count = 0
caen4661_stares = {}

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        s = row.get('stare_inregistrare', '').strip()
        stares[s] = stares.get(s, 0) + 1
        
        caen = row.get('cod_caen', '').strip()
        if '4661' in caen:
            caen4661_count += 1
            caen4661_stares[s] = caen4661_stares.get(s, 0) + 1
        
        if total > 100000:
            break

with open(r'D:\MEMORY\DELECROIX\stare_check.txt', 'w', encoding='utf-8') as out:
    out.write(f'Total scanned: {total:,}\n')
    out.write(f'CAEN 4661 found: {caen4661_count}\n\n')
    
    out.write('All stare values:\n')
    for s, c in sorted(stares.items(), key=lambda x: -x[1]):
        out.write(f'  {repr(s)}: {c:,}\n')
    
    out.write(f'\nCAEN 4661 stare values:\n')
    for s, c in sorted(caen4661_stares.items(), key=lambda x: -x[1]):
        out.write(f'  {repr(s)}: {c:,}\n')

print('Done')
