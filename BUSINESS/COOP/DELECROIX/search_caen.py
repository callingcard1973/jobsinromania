import csv

# Search for agricultural machinery dealers in all CSV files
# CAEN 4661 = Wholesale of agricultural machinery, equipment and supplies
# CAEN 2830 = Manufacture of agricultural and forestry machinery
# CAEN 4664 = Wholesale of machinery for industry, commerce

TARGET_CAEN = ['4661', '2830', '4664', '4661Z', '2830Z', '4664Z']

print("=" * 80)
print("SEARCHING FOR AGRICULTURAL MACHINERY DEALERS IN DATABASES")
print("Target CAEN: 4661 (wholesale agri machinery), 2830 (manufacture), 4664")
print("=" * 80)

# File 1: cooperatives_full.csv
print("\n\n=== FILE: cooperatives_full.csv ===")
try:
    with open(r'D:\MEMORY\IDEAS\COOPERATIVA BUSINESS\data_working\cooperatives_full.csv', 'r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        headers = r.fieldnames
        caen_cols = [h for h in headers if 'CAEN' in h.upper()]
        print(f"CAEN columns: {caen_cols}")
        
        found = []
        for row in r:
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
                            found.append({
                                'firma': firma,
                                'judet': judet,
                                'localitate': local,
                                'caen': val,
                                'ca': ca,
                                'contact': contact
                            })
                            break
        
        print(f"\nFound {len(found)} matches:")
        for i, m in enumerate(found[:50], 1):
            print(f"{i}. {m['firma']} | {m['judet']}, {m['localitate']} | CAEN:{m['caen']} | CA:{m['ca']} | {m['contact']}")
except Exception as e:
    print(f"Error: {e}")

# File 2: master_producers_consolidated.csv
print("\n\n=== FILE: master_producers_consolidated.csv ===")
try:
    with open(r'D:\MEMORY\IDEAS\COOPERATIVA BUSINESS\data_working\master_producers_consolidated.csv', 'r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        headers = r.fieldnames
        print(f"Columns: {headers}")
        # No CAEN here, just check category
        cats = set()
        for row in r:
            cat = row.get('category', '').strip()
            if cat:
                cats.add(cat)
        print(f"Categories: {cats}")
except Exception as e:
    print(f"Error: {e}")

# Check other CSV/data files in MEMORY
import os
print("\n\n=== SEARCHING ALL CSV/JSON FILES IN MEMORY ===")
for root, dirs, files in os.walk(r'D:\MEMORY'):
    # Skip virtual envs, node_modules, __pycache__
    dirs[:] = [d for d in dirs if d not in ['.venv', 'node_modules', '__pycache__', '.git', 'venv']]
    for fname in files:
        if fname.endswith(('.csv', '.json')):
            fpath = os.path.join(root, fname)
            # Check if file has CAEN or machinery related content
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    has_caen = any(tc in content for tc in TARGET_CAEN)
                    has_machinery = any(kw in content.lower() for kw in ['utilaj', 'tractor', 'masina agric', 'combina', 'recoltat', 'agromec', 'iricom', 'matra', 'romfarm'])
                    if has_caen or has_machinery:
                        relpath = os.path.relpath(fpath, r'D:\MEMORY')
                        lines = content.count('\n')
                        reasons = []
                        if has_caen: reasons.append('HAS CAEN')
                        if has_machinery: reasons.append('HAS MACHINERY KW')
                        print(f"  {' | '.join(reasons)} | {relpath} ({lines} lines)")
            except:
                pass

# Check for ONRC/company data files
print("\n\n=== SEARCHING FOR ONRC/COMPANY DATABASE FILES ===")
for root, dirs, files in os.walk(r'D:\MEMORY'):
    dirs[:] = [d for d in dirs if d not in ['.venv', 'node_modules', '__pycache__', '.git', 'venv']]
    for fname in files:
        if any(kw in fname.lower() for kw in ['onrc', 'firma', 'company', 'caen', 'bilant', 'regis']):
            relpath = os.path.relpath(os.path.join(root, fname), r'D:\MEMORY')
            size = os.path.getsize(os.path.join(root, fname))
            print(f"  {relpath} ({size:,} bytes)")
