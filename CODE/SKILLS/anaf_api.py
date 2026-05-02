#!/usr/bin/env python3
"""
ANAF API - Romanian Tax Authority Data

API: https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva
Rate: 100 CUIs/request, 1 req/sec
FREE, no auth required

Usage:
  python3 anaf_api.py lookup 12345678           # Single CUI lookup
  python3 anaf_api.py lookup 12345678 87654321  # Multiple CUIs
  python3 anaf_api.py enrich input.csv          # Enrich CSV with phone/address
  python3 anaf_api.py enrich input.csv --output out.csv

Returns per company:
  - telefon (phone)
  - adresa (address)
  - codPostal (postal code)
  - nrRegCom (J number)
  - cod_CAEN (activity code)
  - stare_inregistrare (status)
  - denumire (name)
  - data_inregistrare (registration date)
  - statusRO_e_Factura (e-invoice status)
  - organFiscalCompetent (tax office)
  - forma_juridica (legal form)
  - inregistrare_scop_Tva (VAT status)
  - stare_inactiv (inactive status)
"""

import sys
import csv
import json
import time
import argparse
import requests
from datetime import date
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

ANAF_API = 'https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva'
BATCH_SIZE = 100
RATE_LIMIT = 1.2


def query_anaf(cuis: list) -> dict:
    """Query ANAF API for multiple CUIs (max 100)"""
    today = date.today().isoformat()
    payload = [{"cui": int(cui), "data": today} for cui in cuis if str(cui).isdigit()]

    try:
        response = requests.post(
            ANAF_API,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code != 200:
            return {'error': f'HTTP {response.status_code}', 'found': [], 'notFound': []}

        return response.json()

    except Exception as e:
        return {'error': str(e), 'found': [], 'notFound': []}


def lookup(cuis: list) -> list:
    """Lookup company info by CUI(s)"""
    results = []

    for i in range(0, len(cuis), BATCH_SIZE):
        batch = cuis[i:i + BATCH_SIZE]
        data = query_anaf(batch)

        if data.get('error'):
            print(f"Error: {data['error']}")
            continue

        for item in data.get('found', []):
            info = item.get('date_generale', {})
            results.append({
                'cui': info.get('cui'),
                'name': info.get('denumire'),
                'phone': info.get('telefon'),
                'address': info.get('adresa'),
                'postal_code': info.get('codPostal'),
                'reg_com': info.get('nrRegCom'),
                'caen': info.get('cod_CAEN'),
                'status': info.get('stare_inregistrare'),
                'reg_date': info.get('data_inregistrare'),
                'vat_status': item.get('inregistrare_scop_Tva', {}).get('scpTVA'),
                'inactive': item.get('stare_inactiv', {}).get('statusInactivi'),
                'tax_office': info.get('organFiscalCompetent'),
                'legal_form': info.get('forma_juridica'),
            })

        if len(cuis) > BATCH_SIZE:
            time.sleep(RATE_LIMIT)

    return results


def enrich_csv(input_file: str, output_file: str = None, cui_col: str = 'cui'):
    """Enrich a CSV file with ANAF data"""
    if output_file is None:
        output_file = input_file.replace('.csv', '_anaf.csv')

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    # Add ANAF columns
    anaf_cols = ['anaf_phone', 'anaf_address', 'anaf_caen', 'anaf_status', 'anaf_vat']
    for col in anaf_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    print(f"Enriching {len(rows):,} rows...")

    # Process in batches
    stats = {'total': 0, 'with_phone': 0}

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        cuis = [r.get(cui_col, '') for r in batch if r.get(cui_col)]

        data = query_anaf(cuis)
        found_map = {}

        for item in data.get('found', []):
            info = item.get('date_generale', {})
            cui = str(info.get('cui', ''))
            found_map[cui] = {
                'phone': info.get('telefon', ''),
                'address': info.get('adresa', ''),
                'caen': info.get('cod_CAEN', ''),
                'status': info.get('stare_inregistrare', ''),
                'vat': item.get('inregistrare_scop_Tva', {}).get('scpTVA', False),
            }

        for row in batch:
            cui = str(row.get(cui_col, ''))
            if cui in found_map:
                info = found_map[cui]
                row['anaf_phone'] = to_ascii(info['phone']) if info['phone'] else ''
                row['anaf_address'] = to_ascii(info['address']) if info['address'] else ''
                row['anaf_caen'] = info['caen']
                row['anaf_status'] = to_ascii(info['status']) if info['status'] else ''
                row['anaf_vat'] = 'Y' if info['vat'] else 'N'
                if info['phone']:
                    stats['with_phone'] += 1
            else:
                row['anaf_phone'] = ''
                row['anaf_address'] = ''
                row['anaf_caen'] = ''
                row['anaf_status'] = ''
                row['anaf_vat'] = ''

            stats['total'] += 1

        print(f"  {min(i + BATCH_SIZE, len(rows)):,}/{len(rows):,}")
        time.sleep(RATE_LIMIT)

    # Save
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone: {stats['with_phone']:,}/{stats['total']:,} with phone ({stats['with_phone']/stats['total']*100:.1f}%)")
    print(f"Saved: {output_file}")

    return output_file


def main():
    parser = argparse.ArgumentParser(description='ANAF API - Romanian company data')
    subparsers = parser.add_subparsers(dest='command')

    # Lookup command
    lookup_p = subparsers.add_parser('lookup', help='Lookup CUI(s)')
    lookup_p.add_argument('cuis', nargs='+', help='CUI(s) to lookup')
    lookup_p.add_argument('--json', action='store_true', help='Output as JSON')

    # Enrich command
    enrich_p = subparsers.add_parser('enrich', help='Enrich CSV file')
    enrich_p.add_argument('input', help='Input CSV file')
    enrich_p.add_argument('--output', '-o', help='Output CSV file')
    enrich_p.add_argument('--cui-col', default='cui', help='CUI column name')

    args = parser.parse_args()

    if args.command == 'lookup':
        results = lookup(args.cuis)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            for r in results:
                print(f"\nCUI: {r['cui']}")
                print(f"  Name: {r['name']}")
                print(f"  Phone: {r['phone'] or '-'}")
                print(f"  Address: {r['address']}")
                print(f"  J-Number: {r['reg_com']}")
                print(f"  CAEN: {r['caen']}")
                print(f"  Status: {r['status']}")
                print(f"  VAT: {'Yes' if r['vat_status'] else 'No'}")

    elif args.command == 'enrich':
        enrich_csv(args.input, args.output, args.cui_col)

    else:
        parser.print_help()

    return 0


if __name__ == '__main__':
    sys.exit(main())
