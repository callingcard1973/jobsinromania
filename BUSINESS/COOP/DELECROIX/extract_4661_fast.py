import csv, time

# CAEN 4661 = Wholesale of agricultural machinery
# Process anaf_all_romania_full.csv but ONLY extract CAEN 4661

fpath = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv'

start = time.time()
caen4661 = []
total = 0

with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    
    # Find relevant column indices by position for speed
    print(f'Columns ({len(cols)}): {cols[:10]}...')
    
    for row in reader:
        total += 1
        
        # Quick check: scan row values for '4661' 
        row_str = str(row)
        if '4661' not in row_str:
            continue
            
        # Slower full extraction only for matches
        name_val = row.get('DENUMIRE', row.get(cols[2], row.get(cols[0], '')))
        judet_val = row.get('JUDET', row.get(cols[5] if len(cols) > 5 else '', ''))
        caen_val = ''
        for c in cols:
            v = row.get(c, '')
            if '4661' in str(v):
                caen_val = str(v)
                break
        
        if caen_val:
            caen4661.append((name_val, judet_val, caen_val))
        
        if total % 500000 == 0:
            elapsed = time.time() - start
            print(f'  {total:,} rows in {elapsed:.0f}s ({total/elapsed:.0f} rows/s), found {len(caen4661)} matches')

elapsed = time.time() - start
print(f'Done: {total:,} rows in {elapsed:.0f}s, found {len(caen4661)} CAEN 4661')

with open(r'D:\MEMORY\DELECROIX\caen4661_results.txt', 'w', encoding='utf-8') as out:
    out.write(f'CAEN 4661 - WHOLESALE AGRICULTURAL MACHINERY ({len(caen4661)} firme)\n')
    out.write(f'Source: {fpath}\n')
    out.write(f'Total scanned: {total:,}\n\n')
    
    # Group by judet
    by_judet = {}
    for name, judet, caen in caen4661:
        j = judet if judet else 'UNKNOWN'
        if j not in by_judet:
            by_judet[j] = []
        by_judet[j].append(name)
    
    out.write(f'By county ({len(by_judet)} counties):\n')
    for j in sorted(by_judet.keys()):
        out.write(f'\n  === {j} ({len(by_judet[j])} firme) ===\n')
        for name in sorted(by_judet[j]):
            out.write(f'    - {name}\n')

print('Saved to caen4661_results.txt')
