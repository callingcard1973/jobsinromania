#!/usr/bin/env python3
"""
ROMANIA COMPANIES SKILL
=======================
Master database of Romanian companies with financial data, phones, addresses.

Data Sources:
- BILANT (data.gov.ro) - revenue, employees, profit (2023-2024)
- ONRC (data.gov.ro) - company name, J code, address, founding date
- ANAF API - phone numbers (free, 100 CUI/request)
- SITUR - licensed HoReCa establishments

Usage:
    python3 romania_companies.py --download          # Download all raw data
    python3 romania_companies.py --build             # Build master database
    python3 romania_companies.py --stats             # Show statistics
    python3 romania_companies.py --filter-horeca     # Extract HoReCa only
    python3 romania_companies.py --segment           # Create targeting segments
    python3 romania_companies.py --lookup CUI        # Lookup single company
    python3 romania_companies.py --enrich FILE.csv   # Enrich CSV with financial data
"""

import os
import sys
import csv
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# === PATHS ===
DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA')
BILANT_DIR = DATA_DIR / 'BILANT'
MASTER_FILE = BILANT_DIR / 'romania_companies_master.csv'
BILANT_FILE = BILANT_DIR / 'bilant_master.csv'
ONRC_FILE = DATA_DIR / 'ONRC/od_firme_20260102.csv'
ANAF_PHONES = DATA_DIR / 'FIRME_ROMANIA/DATA/anaf_all/all_phones.csv'

# === DATA SOURCES ===
BILANT_SOURCES = {
    'uu_2024': 'https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/25098618-f6a5-4610-8c7f-c0bdb801635f/download/web_uu_an2024.txt',
    'bl_2024': 'https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/f89140dc-20dd-494f-912a-d1a482188885/download/web_bl_bs_sl_an2024.txt',
    'uu_2023': 'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/ee5b6665-c096-4582-ada7-cc51a62c3c40/download/web_uu_an2023.txt',
    'bl_2023': 'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/8c914899-cf2a-494c-9d3b-7f9f7faa47a3/download/web_bl_bs_sl_an2023.txt',
    'ong_2023': 'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/137f73ef-e1e4-466e-b1ab-1912c9be7c83/download/web_ong_an2023.txt',
}

ONRC_SOURCE = 'https://data.gov.ro/dataset/date-de-identificare-platitori/resource/latest'

# === HORECA CAEN CODES ===
HORECA_CAEN = {'5510', '5520', '5530', '5590', '5610', '5621', '5629', '5630'}

# === COLUMN DEFINITIONS ===
"""
Bilant columns (I1-I20):
- I1: Active imobilizate (fixed assets)
- I2: Active circulante (current assets)
- I13: Cifra de afaceri neta (net revenue)
- I16: Profit brut
- I17: Pierdere bruta
- I18: Profit net
- I19: Pierdere neta
- I20: Numar mediu de salariati (average employees)

ONRC columns (^ delimiter):
DENUMIRE^CUI^COD_INMATRICULARE^DATA_INMATRICULARE^EUID^FORMA_JURIDICA^
ADR_TARA^ADR_JUDET^ADR_LOCALITATE^ADR_DEN_STRADA^ADR_NR_STRADA^
ADR_BLOC^ADR_SCARA^ADR_ETAJ^ADR_APARTAMENT^ADR_COD_POSTAL^ADR_SECTOR
"""

def download_file(url, output_path, desc=''):
    """Download file with progress"""
    print(f"Downloading {desc or output_path.name}...")
    try:
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        total = int(resp.headers.get('content-length', 0))

        with open(output_path, 'wb') as f:
            downloaded = 0
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  {pct}% ({downloaded:,} bytes)", end='')
        print()
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def download_all():
    """Download all raw data sources"""
    print("=" * 70)
    print("DOWNLOADING ALL DATA SOURCES")
    print("=" * 70)

    BILANT_DIR.mkdir(parents=True, exist_ok=True)

    # Download bilant files
    for source_id, url in BILANT_SOURCES.items():
        output = BILANT_DIR / f'raw_{source_id}.txt'
        if not output.exists():
            download_file(url, output, source_id)
        else:
            print(f"Cached: {output.name}")

    print("\nDownload complete!")

def parse_bilant_file(filepath):
    """Parse bilant TXT file, yield standardized rows"""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 22:
                continue
            try:
                cui = row[0].strip()
                if not cui.isdigit():
                    continue

                yield {
                    'cui': cui,
                    'caen': row[1].strip(),
                    'cifra_afaceri': int(row[14]) if row[14].strip() else 0,
                    'nr_angajati': int(row[21]) if row[21].strip() else 0,
                    'profit_net': int(row[19]) if row[19].strip() else 0,
                    'pierdere_net': int(row[20]) if row[20].strip() else 0,
                    'active_imobilizate': int(row[2]) if row[2].strip() else 0,
                    'active_circulante': int(row[3]) if row[3].strip() else 0
                }
            except (ValueError, IndexError):
                continue

def load_bilant():
    """Load bilant data into dict by CUI"""
    print("Loading bilant data...")
    data = {}

    # Process files in order (2024 first to prefer newer data)
    for source_id in ['uu_2024', 'bl_2024', 'uu_2023', 'bl_2023', 'ong_2023']:
        filepath = BILANT_DIR / f'raw_{source_id}.txt'
        if not filepath.exists():
            continue

        count = 0
        for row in parse_bilant_file(filepath):
            cui = row['cui']
            # Keep newer/higher revenue data
            if cui not in data or row['cifra_afaceri'] > data[cui]['cifra_afaceri']:
                data[cui] = row
            count += 1
        print(f"  {source_id}: {count:,} records")

    print(f"  Total: {len(data):,} companies")
    return data

def load_onrc():
    """Load ONRC data (name, J code, address, founding date)"""
    print("Loading ONRC registry...")
    data = {}

    if not ONRC_FILE.exists():
        print(f"  ERROR: {ONRC_FILE} not found")
        return data

    with open(ONRC_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter='^')
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 10:
                continue
            cui = row[1].strip()
            if not cui.isdigit():
                continue

            # Parse founding date
            data_inm = row[3] if len(row) > 3 else ''
            founding_year = None
            if data_inm:
                try:
                    parts = data_inm.split('/')
                    if len(parts) == 3:
                        founding_year = int(parts[2])
                except:
                    pass

            # Build address
            judet = row[7] if len(row) > 7 else ''
            localitate = row[8] if len(row) > 8 else ''
            strada = row[9] if len(row) > 9 else ''
            nr = row[10] if len(row) > 10 else ''
            sector = row[16] if len(row) > 16 else ''

            addr_parts = [localitate]
            if sector:
                addr_parts.append(f"Sector {sector}")
            if strada:
                addr_parts.append(strada)
            if nr:
                addr_parts.append(f"nr. {nr}")

            data[cui] = {
                'nume_firma': to_ascii(row[0][:100]),
                'cod_j': row[2] if len(row) > 2 else '',
                'judet': to_ascii(judet),
                'localitate': to_ascii(localitate),
                'sector': sector,
                'adresa': to_ascii(', '.join(p for p in addr_parts if p))[:150],
                'founding_year': founding_year,
                'data_inmatriculare': data_inm
            }

    print(f"  Loaded {len(data):,} companies")
    return data

def load_phones():
    """Load ANAF phone numbers"""
    print("Loading ANAF phones...")
    data = {}

    if not ANAF_PHONES.exists():
        print(f"  ANAF phones not found, skipping")
        return data

    with open(ANAF_PHONES, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cui = row.get('cui', '').strip()
            phone = row.get('phone', '').strip()
            if cui and phone:
                data[cui] = phone

    print(f"  Loaded {len(data):,} phones")
    return data

def build_master():
    """Build master database by joining all sources"""
    print("=" * 70)
    print("BUILDING MASTER DATABASE")
    print("=" * 70)

    bilant = load_bilant()
    onrc = load_onrc()
    phones = load_phones()

    print("\nJoining data sources...")
    master = {}
    current_year = datetime.now().year

    for cui in bilant:
        if cui not in onrc:
            continue

        b = bilant[cui]
        o = onrc[cui]

        # Calculate age and revenue per employee
        years_old = None
        if o.get('founding_year'):
            years_old = current_year - o['founding_year']

        rev_per_emp = 0
        if b['nr_angajati'] > 0:
            rev_per_emp = b['cifra_afaceri'] / b['nr_angajati']

        master[cui] = {
            'cui': cui,
            'nume_firma': o['nume_firma'],
            'caen': b['caen'],
            'cifra_afaceri': b['cifra_afaceri'],
            'nr_angajati': b['nr_angajati'],
            'profit_net': b['profit_net'] - b['pierdere_net'],
            'cod_j': o['cod_j'],
            'judet': o['judet'],
            'localitate': o['localitate'],
            'sector': o.get('sector', ''),
            'adresa': o['adresa'],
            'telefon': phones.get(cui, ''),
            'founding_year': o.get('founding_year') or '',
            'years_old': years_old or '',
            'rev_per_employee': int(rev_per_emp),
            'is_horeca': '1' if b['caen'][:4] in HORECA_CAEN else '0'
        }

    print(f"  Joined {len(master):,} companies")

    # Write master file
    BILANT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'cui', 'nume_firma', 'caen', 'cifra_afaceri', 'nr_angajati',
        'profit_net', 'cod_j', 'judet', 'localitate', 'sector', 'adresa',
        'telefon', 'founding_year', 'years_old', 'rev_per_employee', 'is_horeca'
    ]

    with open(MASTER_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cui in sorted(master.keys(), key=lambda x: int(x)):
            writer.writerow(master[cui])

    print(f"\nWritten: {MASTER_FILE}")
    return master

def show_stats():
    """Show database statistics"""
    print("=" * 70)
    print("ROMANIA COMPANIES DATABASE - STATISTICS")
    print("=" * 70)

    if not MASTER_FILE.exists():
        print("Master file not found. Run --build first.")
        return

    total = 0
    with_phone = 0
    with_revenue = 0
    with_employees = 0
    horeca = 0
    by_judet = defaultdict(int)

    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row['telefon']:
                with_phone += 1
            if int(row['cifra_afaceri'] or 0) > 0:
                with_revenue += 1
            if int(row['nr_angajati'] or 0) > 0:
                with_employees += 1
            if row['is_horeca'] == '1':
                horeca += 1
            by_judet[row['judet']] += 1

    print(f"Total companies:      {total:,}")
    print(f"With phone:           {with_phone:,} ({with_phone*100//total}%)")
    print(f"With revenue > 0:     {with_revenue:,}")
    print(f"With employees > 0:   {with_employees:,}")
    print(f"HoReCa (CAEN 55-56):  {horeca:,}")

    print("\nTop 10 judete:")
    for judet, count in sorted(by_judet.items(), key=lambda x: -x[1])[:10]:
        print(f"  {judet:20} {count:,}")

def filter_horeca():
    """Extract HoReCa businesses only"""
    print("Filtering HoReCa businesses...")

    if not MASTER_FILE.exists():
        print("Master file not found. Run --build first.")
        return

    output = BILANT_DIR / 'horeca_all.csv'
    count = 0

    with open(MASTER_FILE, 'r', encoding='utf-8') as fin:
        reader = csv.DictReader(fin)
        with open(output, 'w', newline='', encoding='utf-8') as fout:
            writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                if row['is_horeca'] == '1' and int(row['cifra_afaceri'] or 0) > 0:
                    writer.writerow(row)
                    count += 1

    print(f"Written {count:,} HoReCa companies to {output}")

def create_segments():
    """Create targeting segments"""
    print("=" * 70)
    print("CREATING TARGETING SEGMENTS")
    print("=" * 70)

    if not MASTER_FILE.exists():
        print("Master file not found. Run --build first.")
        return

    MIN_REV_PER_EMP = 200000  # RON (~40K EUR)

    segments = {
        'lunch': [],      # 1-19 employees, quality businesses
        'party': [],      # 20-50 employees, anniversary 8-12 years
        'large': [],      # 50+ employees
        'bucuresti': []   # All Bucuresti businesses
    }

    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            emp = int(row['nr_angajati'] or 0)
            rev_per_emp = int(row['rev_per_employee'] or 0)
            years = int(row['years_old']) if row['years_old'] else 0
            judet = row['judet']

            # Bucuresti filter
            if judet == 'Bucuresti':
                segments['bucuresti'].append(row)

            # Quality filter
            if rev_per_emp < MIN_REV_PER_EMP:
                continue

            if 1 <= emp <= 19:
                segments['lunch'].append(row)
            if 20 <= emp <= 50 and 8 <= years <= 12:
                segments['party'].append(row)
            if emp >= 50:
                segments['large'].append(row)

    # Write segments
    for name, data in segments.items():
        output = BILANT_DIR / f'segment_{name}.csv'
        with open(output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted(data, key=lambda x: -int(x['cifra_afaceri'] or 0)):
                writer.writerow(row)
        print(f"  {name}: {len(data):,} companies -> {output}")

def lookup_company(cui):
    """Lookup single company by CUI"""
    if not MASTER_FILE.exists():
        print("Master file not found. Run --build first.")
        return

    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['cui'] == cui:
                print(f"\nCompany: {row['nume_firma']}")
                print(f"CUI: {row['cui']}")
                print(f"Cod J: {row['cod_j']}")
                print(f"CAEN: {row['caen']}")
                print(f"Revenue: {int(row['cifra_afaceri']):,} RON")
                print(f"Employees: {row['nr_angajati']}")
                print(f"Phone: {row['telefon'] or 'N/A'}")
                print(f"Address: {row['adresa']}")
                print(f"Founded: {row['founding_year']}")
                return

    print(f"Company with CUI {cui} not found")

def enrich_csv(input_file, cui_col='cui'):
    """Enrich CSV with financial data"""
    print(f"Enriching {input_file}...")

    if not MASTER_FILE.exists():
        print("Master file not found. Run --build first.")
        return

    # Load master data
    master = {}
    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            master[row['cui']] = row

    # Process input file
    input_path = Path(input_file)
    output_path = input_path.with_suffix('.enriched.csv')

    enriched = 0
    total = 0

    with open(input_path, 'r', encoding='utf-8') as fin:
        reader = csv.DictReader(fin)
        new_fields = ['cifra_afaceri', 'nr_angajati', 'telefon', 'adresa']
        fieldnames = reader.fieldnames + [f for f in new_fields if f not in reader.fieldnames]

        with open(output_path, 'w', newline='', encoding='utf-8') as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                total += 1
                cui = row.get(cui_col, '').strip()
                if cui in master:
                    m = master[cui]
                    row['cifra_afaceri'] = m['cifra_afaceri']
                    row['nr_angajati'] = m['nr_angajati']
                    row['telefon'] = row.get('telefon') or m['telefon']
                    row['adresa'] = row.get('adresa') or m['adresa']
                    enriched += 1
                writer.writerow(row)

    print(f"Enriched {enriched}/{total} companies")
    print(f"Output: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Romania Companies Database')
    parser.add_argument('--download', action='store_true', help='Download all raw data')
    parser.add_argument('--build', action='store_true', help='Build master database')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--filter-horeca', action='store_true', help='Extract HoReCa only')
    parser.add_argument('--segment', action='store_true', help='Create targeting segments')
    parser.add_argument('--lookup', metavar='CUI', help='Lookup company by CUI')
    parser.add_argument('--enrich', metavar='FILE', help='Enrich CSV with financial data')
    parser.add_argument('--cui-col', default='cui', help='CUI column name for --enrich')

    args = parser.parse_args()

    if args.download:
        download_all()
    elif args.build:
        build_master()
    elif args.stats:
        show_stats()
    elif args.filter_horeca:
        filter_horeca()
    elif args.segment:
        create_segments()
    elif args.lookup:
        lookup_company(args.lookup)
    elif args.enrich:
        enrich_csv(args.enrich, args.cui_col)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
