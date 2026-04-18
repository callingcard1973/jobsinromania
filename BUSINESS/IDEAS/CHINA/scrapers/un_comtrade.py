#!/usr/bin/env python3
"""
UN Comtrade API - China Trade Data

Free API for international trade statistics.
100,000 records/query limit for free users.

Data available:
- China exports by partner country
- China imports by partner country
- Trade by HS commodity code
- Historical data from 1992+

Usage:
    python3 un_comtrade.py --exports --year 2023
    python3 un_comtrade.py --imports --partner Germany
    python3 un_comtrade.py --commodity 8471 --year 2023  # Computers
    python3 un_comtrade.py --top-exports 20
"""

import argparse
import csv
import json
import requests
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path('/opt/ACTIVE/IDEAS/CHINA')
OUTPUT_DIR = BASE_DIR / 'data' / 'comtrade'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# UN Comtrade API
# NOTE: Free tier requires registration at https://comtradedeveloper.un.org/
# Get API key and set: export COMTRADE_API_KEY=your_key
COMTRADE_API = 'https://comtradeapi.un.org/data/v1/get/C/A'  # Commodities/Annual
COMTRADE_PREVIEW = 'https://comtradeapi.un.org/public/v1/preview/C/A'

# China reporter code
CHINA_CODE = '156'

# Common partner codes
PARTNER_CODES = {
    'USA': '842',
    'Germany': '276',
    'Japan': '392',
    'South Korea': '410',
    'UK': '826',
    'France': '251',
    'Netherlands': '528',
    'Italy': '381',
    'Russia': '643',
    'India': '699',
    'Australia': '036',
    'Brazil': '076',
    'World': '0',
}

# HS codes for major export categories
HS_CODES = {
    'electronics': '85',      # Electrical machinery
    'machinery': '84',        # Machinery/mechanical appliances
    'textiles': '61-62',      # Apparel
    'furniture': '94',        # Furniture
    'plastics': '39',         # Plastics
    'vehicles': '87',         # Vehicles
    'steel': '72-73',         # Iron and steel
    'toys': '95',             # Toys and games
    'footwear': '64',         # Footwear
    'computers': '8471',      # Computers (specific)
    'phones': '8517',         # Phones (specific)
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; ChinaDataScraper/1.0)',
    'Accept': 'application/json',
}


def to_ascii(text):
    """Convert to ASCII."""
    if not text:
        return ''
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


def fetch_comtrade(reporter='156', partner='0', flow='X', year='2023',
                   commodity='TOTAL', freq='A'):
    """
    Fetch data from UN Comtrade API.

    Args:
        reporter: Reporter country code (156 = China)
        partner: Partner country code (0 = World)
        flow: X = exports, M = imports
        year: Year (YYYY) or range (2020-2023)
        commodity: HS code or TOTAL
        freq: A = annual, M = monthly
    """
    params = {
        'reporterCode': reporter,
        'partnerCode': partner,
        'flowCode': flow,
        'period': year,
        'cmdCode': commodity,
        'freq': freq,
        'clCode': 'HS',          # HS classification
        'includeDesc': 'true',
    }

    print(f'[COMTRADE] Fetching {flow}ports for {year}...')

    try:
        # Try preview endpoint first (no auth needed)
        resp = requests.get(COMTRADE_API, params=params, headers=HEADERS, timeout=60)

        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', [])
        else:
            print(f'[WARN] Status {resp.status_code}: {resp.text[:200]}')
            return []

    except Exception as e:
        print(f'[ERR] API request failed: {e}')
        return []


def fetch_top_partners(flow='X', year='2023', limit=50):
    """Fetch China's top trading partners."""
    records = fetch_comtrade(
        reporter=CHINA_CODE,
        partner='0',  # Will get breakdown
        flow=flow,
        year=year,
        commodity='TOTAL'
    )

    # Sort by trade value
    records.sort(key=lambda x: float(x.get('primaryValue', 0) or 0), reverse=True)

    return records[:limit]


def fetch_top_commodities(flow='X', year='2023', partner='0', limit=50):
    """Fetch China's top traded commodities."""
    records = fetch_comtrade(
        reporter=CHINA_CODE,
        partner=partner,
        flow=flow,
        year=year,
        commodity='AG2'  # 2-digit HS codes
    )

    # Sort by trade value
    records.sort(key=lambda x: float(x.get('primaryValue', 0) or 0), reverse=True)

    return records[:limit]


def parse_records(raw_records):
    """Parse Comtrade records into clean format."""
    records = []

    for r in raw_records:
        try:
            record = {
                'year': r.get('period', ''),
                'flow': 'Export' if r.get('flowCode') == 'X' else 'Import',
                'partner_code': r.get('partnerCode', ''),
                'partner': to_ascii(r.get('partnerDesc', '')),
                'commodity_code': r.get('cmdCode', ''),
                'commodity': to_ascii(r.get('cmdDesc', ''))[:100],
                'value_usd': r.get('primaryValue', ''),
                'qty': r.get('qty', ''),
                'qty_unit': to_ascii(r.get('qtyUnitAbbr', '')),
                'net_weight_kg': r.get('netWgt', ''),
            }
            records.append(record)
        except Exception:
            continue

    return records


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


def main():
    parser = argparse.ArgumentParser(description='Fetch China trade data from UN Comtrade')
    parser.add_argument('--exports', '-e', action='store_true', help='Fetch export data')
    parser.add_argument('--imports', '-i', action='store_true', help='Fetch import data')
    parser.add_argument('--year', '-y', default='2023', help='Year (YYYY)')
    parser.add_argument('--partner', '-p', help='Partner country name')
    parser.add_argument('--commodity', '-c', help='HS code or category name')
    parser.add_argument('--top-exports', type=int, help='Get top N export partners')
    parser.add_argument('--top-imports', type=int, help='Get top N import partners')
    parser.add_argument('--top-commodities', type=int, help='Get top N commodities')
    parser.add_argument('--all-summary', '-a', action='store_true',
                        help='Fetch summary of all trade')

    args = parser.parse_args()

    timestamp = datetime.now().strftime('%Y%m%d')

    # Determine flow direction
    flow = 'X'  # Default exports
    if args.imports:
        flow = 'M'

    # Get partner code
    partner_code = '0'  # World
    if args.partner:
        partner_code = PARTNER_CODES.get(args.partner, args.partner)

    # Get commodity code
    commodity = 'TOTAL'
    if args.commodity:
        commodity = HS_CODES.get(args.commodity, args.commodity)

    # Execute queries
    if args.top_exports:
        raw = fetch_top_partners('X', args.year, args.top_exports)
        records = parse_records(raw)
        save_csv(records, f'china_top_export_partners_{args.year}.csv')

    elif args.top_imports:
        raw = fetch_top_partners('M', args.year, args.top_imports)
        records = parse_records(raw)
        save_csv(records, f'china_top_import_partners_{args.year}.csv')

    elif args.top_commodities:
        raw = fetch_top_commodities(flow, args.year, partner_code, args.top_commodities)
        records = parse_records(raw)
        flow_name = 'export' if flow == 'X' else 'import'
        save_csv(records, f'china_top_{flow_name}_commodities_{args.year}.csv')

    elif args.all_summary:
        all_records = []

        # Exports to world
        print('\n=== EXPORTS ===')
        raw = fetch_comtrade(CHINA_CODE, '0', 'X', args.year, 'TOTAL')
        all_records.extend(parse_records(raw))
        time.sleep(1)

        # Imports from world
        print('\n=== IMPORTS ===')
        raw = fetch_comtrade(CHINA_CODE, '0', 'M', args.year, 'TOTAL')
        all_records.extend(parse_records(raw))

        save_csv(all_records, f'china_trade_summary_{args.year}.csv')

    else:
        # Custom query
        raw = fetch_comtrade(CHINA_CODE, partner_code, flow, args.year, commodity)
        records = parse_records(raw)

        flow_name = 'exports' if flow == 'X' else 'imports'
        save_csv(records, f'china_{flow_name}_{timestamp}.csv')

    print('\n=== DONE ===')
    print(f'Output directory: {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
