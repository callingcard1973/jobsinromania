import csv, re, unicodedata, sys
from pathlib import Path
from collections import defaultdict

DATA = Path(r'D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ISCIR\DATA')
ENRICHED = DATA / 'clienti_iscir_enriched.csv'
CLIENTI_PER_COUNTY = DATA / 'clienti_pe_judet'

def ascii_fold(s):
    s = s.upper()
    s = s.replace('\u021a', 'T').replace('\u0218', 'S').replace('\u0102', 'A').replace('\u00c2', 'A').replace('\u00ce', 'I')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return s

def extract_county(addr):
    if not addr:
        return ''
    m = re.search(r'JUD\.\s*([^,]+)', addr, re.IGNORECASE)
    if m:
        return ascii_fold(m.group(1).strip())
    m2 = re.search(r'JUDETUL\s*([^,]+)', addr, re.IGNORECASE)
    if m2:
        return ascii_fold(m2.group(1).strip())
    m3 = re.search(r'MUNICIPIUL\s+BUCURE.TI', addr, re.IGNORECASE)
    if m3:
        return 'BUCURESTI'
    return ''

# Read, fix county, write enriched CSV
rows = []
fixed = 0
no_extract = 0
county_added = defaultdict(int)

with open(ENRICHED, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        raw_cty = row.get('county', '').strip()
        if raw_cty:
            row['county'] = raw_cty.upper()
        else:
            cty = extract_county(row.get('anaf_address', ''))
            if cty and len(cty) > 2:
                row['county'] = cty
                fixed += 1
                county_added[cty] += 1
            else:
                no_extract += 1
        rows.append(row)

print(f'Total rows: {len(rows)}')
print(f'County fixed from ANAF: {fixed}')
print(f'Still no county: {no_extract}')
print(f'\nNew county assignments:')
for c, n in sorted(county_added.items(), key=lambda x: -x[1]):
    print(f'  {c}: {n}')

# Write updated enriched CSV
out = ENRICHED.with_name('clienti_iscir_enriched.csv')
with open(out, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f'\nSaved {out}')

# Regenerate county CSVs
CLIENTI_PER_COUNTY.mkdir(parents=True, exist_ok=True)
by_county = defaultdict(list)
for row in rows:
    cty = row.get('county', '').strip()
    if not cty:
        cty = 'FARACLASSIFICARE'
    by_county[cty.upper()].append(row)

county_file_count = 0
for cty, firms in sorted(by_county.items()):
    if cty == 'FARACLASSIFICARE':
        continue
    safe_name = cty.lower().replace(' ', '_').replace('-', '_').replace('ș', 's').replace('ț', 't')
    cty_path = CLIENTI_PER_COUNTY / f'{safe_name}.csv'
    with open(cty_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['name', 'city', 'caen', 'email', 'phone'])
        for r in firms:
            w.writerow([r.get('name', ''), r.get('city', ''), r.get('caen', ''), r.get('email', ''), r.get('phone', '')])
    county_file_count += 1

print(f'County CSV files updated: {county_file_count}')
print(f'Firms FARACLASSIFICARE: {len(by_county.get("FARACLASSIFICARE", []))}')
