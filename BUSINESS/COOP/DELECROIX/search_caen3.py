import os, csv

TARGET_CAEN = ['4661', '2830', '4664', '461', '462', '463', '466']
AGRI_KEYWORDS = ['utilaj', 'tractor', 'agricol', 'recoltat', 'combina', 'agromec', 'matra', 'cereal', 'semin', 'legum', 'horticol']

found_files = []

for root, dirs, files in os.walk(r'D:\MEMORY'):
    dirs[:] = [d for d in dirs if d not in ['.venv', 'node_modules', '__pycache__', '.git', 'venv', 'lib', 'Scripts', 'Include']]
    for fname in files:
        if fname.endswith('.csv'):
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    header_line = f.readline()
                    header_lower = header_line.lower()
                    
                    # Must have CAEN or FIRMA column
                    has_caen_col = 'caen' in header_lower
                    has_firma_col = any(kw in header_lower for kw in ['firma', 'company', 'name', 'denumire', 'cui'])
                    
                    if not (has_caen_col or has_firma_col):
                        continue
                    
                    # Now check if any row has target CAEN or agri keywords
                    f.seek(0)
                    reader = csv.DictReader(f)
                    cols = reader.fieldnames
                    if not cols:
                        continue
                    
                    caen_cols = [c for c in cols if 'caen' in c.lower()]
                    name_cols = [c for c in cols if any(kw in c.lower() for kw in ['firma', 'company', 'name', 'denumire'])]
                    contact_cols = [c for c in cols if any(kw in c.lower() for kw in ['contact', 'email', 'telefon', 'phone', 'mail'])]
                    judet_cols = [c for c in cols if 'judet' in c.lower() or 'county' in c.lower()]
                    
                    count = 0
                    matches = []
                    for row in reader:
                        count += 1
                        # Check CAEN
                        for cc in caen_cols:
                            val = row.get(cc, '').strip()
                            if val:
                                for tc in TARGET_CAEN:
                                    if tc in val:
                                        name = ' | '.join(row.get(c, '') for c in name_cols[:2])
                                        judet = ' | '.join(row.get(c, '') for c in judet_cols)
                                        matches.append(f'CAEN:{val} - {name} ({judet})')
                                        break
                    
                    if matches:
                        rel = os.path.relpath(fpath, r'D:\MEMORY')
                        found_files.append((rel, count, len(matches), matches[:20]))
                    
            except Exception as e:
                pass

with open(r'D:\MEMORY\DELECROIX\caen_agri_results.txt', 'w', encoding='utf-8') as out:
    out.write(f'Files with CAEN {TARGET_CAEN}: {len(found_files)}\n\n')
    for rel, total, match_count, matches in sorted(found_files, key=lambda x: -x[2]):
        out.write(f'=== {rel} ({total} rows, {match_count} matches) ===\n')
        for m in matches:
            out.write(f'  {m}\n')
        out.write('\n')

print(f'Found {len(found_files)} files with matching CAEN codes')
print(f'Results in caen_agri_results.txt')
