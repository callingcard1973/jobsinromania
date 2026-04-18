import csv

TARGET_CAEN = ['4661', '2830', '4664']

f = r'D:\MEMORY\IDEAS\COOPERATIVA BUSINESS\data_working\cooperatives_full.csv'
with open(f, 'r', encoding='utf-8') as fh:
    r = csv.DictReader(fh)
    caen_cols = [h for h in r.fieldnames if 'CAEN' in h.upper()]
    
    with open(r'D:\MEMORY\DELECROIX\caen_results.txt', 'w', encoding='utf-8') as out:
        out.write(f'CAEN columns: {caen_cols}\n')
        
        found = []
        total = 0
        for row in r:
            total += 1
            for c in caen_cols:
                val = row.get(c, '').strip()
                if val:
                    for tc in TARGET_CAEN:
                        if tc in val:
                            firma = row.get('FIRMA', '')
                            judet = row.get('JUDET', '')
                            local = row.get('LOCALITATE', '')
                            ca = row.get('CIFRA_AFACERI_2018', '')
                            contact = row.get('CONTACT_FIRMA', '')
                            found.append((firma, judet, local, val, ca, contact))
                            break
        
        out.write(f'Total rows: {total}\n')
        out.write(f'Matches for CAEN {TARGET_CAEN}: {len(found)}\n\n')
        for i, m in enumerate(found[:50], 1):
            out.write(f'{i}. {m[0]} | {m[1]}, {m[2]} | CAEN:{m[3]} | CA:{m[4]} | {m[5]}\n')
        
        # Also list all unique CAEN codes
        caen_vals = set()
        fh.seek(0)
        r2 = csv.DictReader(fh)
        for row in r2:
            for c in caen_cols:
                val = row.get(c, '').strip()
                if val:
                    caen_vals.add(val)
        
        out.write(f'\n\nAll unique CAEN values ({len(caen_vals)}):\n')
        for v in sorted(caen_vals):
            out.write(f'  {v}\n')

print('Done - wrote to caen_results.txt')
