#!/usr/bin/env python3
"""
National Bureau of Statistics of China (NBS) API Scraper

Downloads trade and economic statistics from data.stats.gov.cn
FREE API - no authentication required.

Data available:
- Import/Export by country
- Trade by commodity (HS codes)
- GDP, industrial output
- Regional statistics

Usage:
    python3 nbs_china_api.py --dataset exports --years 2020-2024
    python3 nbs_china_api.py --dataset imports --format csv
    python3 nbs_china_api.py --list-datasets
"""

import argparse
import csv
import json
import requests
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path('/opt/ACTIVE/IDEAS/CHINA')
OUTPUT_DIR = BASE_DIR / 'data' / 'nbs'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# NBS API endpoints
NBS_BASE = 'https://data.stats.gov.cn'
NBS_API = f'{NBS_BASE}/english/easyquery.htm'

# Dataset codes (discovered from NBS website)
DATASETS = {
    # Trade data
    'exports_total': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0E01'},
    'imports_total': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0E02'},
    'exports_by_country': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0E0301'},
    'imports_by_country': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0E0302'},
    'exports_by_commodity': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0E0501'},
    'imports_by_commodity': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0E0502'},

    # Economic indicators
    'gdp': {'dbcode': 'hgjd', 'wdcode': 'zb', 'id': 'A0101'},
    'industrial_output': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0201'},
    'cpi': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0901'},

    # Foreign investment
    'fdi': {'dbcode': 'hgyd', 'wdcode': 'zb', 'id': 'A0F01'},
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
    'Accept': 'application/json',
    'Referer': NBS_BASE,
}


def to_ascii(text):
    """Convert to ASCII."""
    if not text:
        return ''
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


def fetch_nbs_data(dataset_key, start_year=2020, end_year=2024):
    """Fetch data from NBS API."""
    if dataset_key not in DATASETS:
        print(f'[ERR] Unknown dataset: {dataset_key}')
        print(f'Available: {", ".join(DATASETS.keys())}')
        return None

    ds = DATASETS[dataset_key]

    # Build time range
    if 'hgyd' in ds['dbcode']:  # Monthly data
        time_range = f'{start_year}01-{end_year}12'
    else:  # Quarterly/annual
        time_range = f'{start_year}-{end_year}'

    params = {
        'm': 'QueryData',
        'dbcode': ds['dbcode'],
        'rowcode': 'sj',
        'colcode': ds['wdcode'],
        'wds': json.dumps([]),
        'dfwds': json.dumps([{'wdcode': ds['wdcode'], 'valuecode': ds['id']}]),
        'k1': int(datetime.now().timestamp() * 1000),
    }

    print(f'[NBS] Fetching {dataset_key} for {start_year}-{end_year}...')

    try:
        resp = requests.get(NBS_API, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        data = resp.json()

        if 'returndata' not in data:
            print(f'[WARN] No data returned')
            return None

        return data['returndata']

    except Exception as e:
        print(f'[ERR] API request failed: {e}')
        return None


def parse_nbs_response(data, dataset_key):
    """Parse NBS API response into records."""
    records = []

    if not data or 'datanodes' not in data:
        return records

    for node in data['datanodes']:
        try:
            record = {
                'dataset': dataset_key,
                'period': '',
                'indicator': '',
                'value': '',
                'unit': '',
            }

            # Extract period (time)
            for wd in node.get('wds', []):
                if wd.get('wdcode') == 'sj':
                    record['period'] = wd.get('valuecode', '')
                elif wd.get('wdcode') == 'zb':
                    record['indicator'] = to_ascii(wd.get('cname', ''))

            # Extract value
            data_info = node.get('data', {})
            record['value'] = data_info.get('data', '')
            record['unit'] = to_ascii(data_info.get('cdata', ''))

            if record['period'] and record['value']:
                records.append(record)

        except Exception as e:
            continue

    return records


def fetch_trade_partners():
    """Fetch list of China's trade partners with trade volumes."""
    print('[NBS] Fetching trade partner data...')

    # This requires different API call structure
    params = {
        'm': 'getTree',
        'dbcode': 'hgyd',
        'wdcode': 'reg',
        'id': 'zb.A0E03',
    }

    try:
        resp = requests.get(NBS_API, params=params, headers=HEADERS, timeout=30)
        data = resp.json()

        partners = []
        for item in data:
            if 'id' in item and 'name' in item:
                partners.append({
                    'code': item['id'],
                    'country': to_ascii(item.get('name', '')),
                    'pid': item.get('pid', ''),
                })

        return partners

    except Exception as e:
        print(f'[ERR] Failed to fetch partners: {e}')
        return []


def save_csv(records, filename):
    """Save records to CSV."""
    if not records:
        print('[WARN] No records to save')
        return None

    output_file = OUTPUT_DIR / filename

    fieldnames = list(records[0].keys())

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f'[SAVED] {len(records)} records to {output_file}')
    return output_file


def save_json(data, filename):
    """Save raw data to JSON."""
    output_file = OUTPUT_DIR / filename

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'[SAVED] {output_file}')
    return output_file


def list_datasets():
    """Print available datasets."""
    print('\n=== AVAILABLE NBS DATASETS ===\n')

    categories = {
        'Trade': ['exports_total', 'imports_total', 'exports_by_country',
                  'imports_by_country', 'exports_by_commodity', 'imports_by_commodity'],
        'Economy': ['gdp', 'industrial_output', 'cpi'],
        'Investment': ['fdi'],
    }

    for cat, datasets in categories.items():
        print(f'{cat}:')
        for ds in datasets:
            print(f'  - {ds}')
        print()


def main():
    parser = argparse.ArgumentParser(description='Fetch China NBS statistics')
    parser.add_argument('--dataset', '-d', help='Dataset to fetch')
    parser.add_argument('--start-year', '-s', type=int, default=2020)
    parser.add_argument('--end-year', '-e', type=int, default=2024)
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='csv')
    parser.add_argument('--list-datasets', '-l', action='store_true')
    parser.add_argument('--trade-partners', '-p', action='store_true',
                        help='Fetch list of trade partners')
    parser.add_argument('--all-trade', '-a', action='store_true',
                        help='Fetch all trade datasets')

    args = parser.parse_args()

    if args.list_datasets:
        list_datasets()
        return

    if args.trade_partners:
        partners = fetch_trade_partners()
        if partners:
            save_csv(partners, 'trade_partners.csv')
        return

    if args.all_trade:
        trade_datasets = ['exports_total', 'imports_total',
                          'exports_by_country', 'imports_by_country']
        all_records = []

        for ds in trade_datasets:
            data = fetch_nbs_data(ds, args.start_year, args.end_year)
            if data:
                records = parse_nbs_response(data, ds)
                all_records.extend(records)

        if all_records:
            filename = f'china_trade_{args.start_year}_{args.end_year}.csv'
            save_csv(all_records, filename)
        return

    if not args.dataset:
        print('Usage: python3 nbs_china_api.py --dataset <name>')
        print('       python3 nbs_china_api.py --list-datasets')
        return

    # Fetch single dataset
    data = fetch_nbs_data(args.dataset, args.start_year, args.end_year)

    if data:
        timestamp = datetime.now().strftime('%Y%m%d')

        if args.format == 'json':
            save_json(data, f'{args.dataset}_{timestamp}.json')
        else:
            records = parse_nbs_response(data, args.dataset)
            save_csv(records, f'{args.dataset}_{timestamp}.csv')


if __name__ == '__main__':
    main()
