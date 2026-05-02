#!/usr/bin/env python3
"""
SOC to COR Mapper - Bridge UK SOC codes to Romania COR codes via ISCO-08

The mapping chain: UK SOC 2010 → ISCO-08 → Romania COR

Usage:
    python3 soc_cor_mapper.py lookup 8211           # SOC code → COR codes
    python3 soc_cor_mapper.py isco 8211             # ISCO code → COR codes
    python3 soc_cor_mapper.py title "Care Worker"  # Search by title
    python3 soc_cor_mapper.py cor 532103           # COR → SOC reverse lookup
    python3 soc_cor_mapper.py convert input.csv    # Bulk CSV conversion
    python3 soc_cor_mapper.py stats                # Show statistics
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

import os
import csv
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Data paths
DATA_DIR = Path('/opt/ACTIVE/INFRA/SKILLS/data/occupation_codes')
SOC_ISCO_FILE = DATA_DIR / 'soc_isco_mapping.csv'
COR_FILE = DATA_DIR / 'cor_romania.csv'

# Lazy-loaded data caches
_soc_to_isco: Dict[str, dict] = {}
_isco_to_soc: Dict[str, List[dict]] = {}
_cor_codes: Dict[str, dict] = {}
_isco_to_cor: Dict[str, List[dict]] = {}


def load_data():
    """Load all mapping data into memory"""
    global _soc_to_isco, _isco_to_soc, _cor_codes, _isco_to_cor

    if _soc_to_isco:  # Already loaded
        return

    # Load SOC → ISCO mapping
    if SOC_ISCO_FILE.exists():
        with open(SOC_ISCO_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                soc = row['soc2010']
                isco = row['isco08']
                entry = {
                    'soc': soc,
                    'soc_title': row['soc_title'],
                    'isco': isco,
                    'isco_title': row['isco_title']
                }
                _soc_to_isco[soc] = entry

                if isco not in _isco_to_soc:
                    _isco_to_soc[isco] = []
                _isco_to_soc[isco].append(entry)

    # Load COR codes
    if COR_FILE.exists():
        with open(COR_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cor = row['cor_code']
                isco = row['isco08']
                entry = {
                    'cor': cor,
                    'occupation_ro': row['occupation_ro'],
                    'isco': isco
                }
                _cor_codes[cor] = entry

                if isco not in _isco_to_cor:
                    _isco_to_cor[isco] = []
                _isco_to_cor[isco].append(entry)


def soc_to_cor(soc_code: str) -> List[dict]:
    """
    Convert UK SOC code to Romania COR codes.

    Returns list of matching COR entries with details.
    """
    load_data()

    # Clean the SOC code
    soc = str(soc_code).strip().replace('.', '')

    # Look up SOC → ISCO
    if soc not in _soc_to_isco:
        return []

    soc_entry = _soc_to_isco[soc]
    isco = soc_entry['isco']

    # Look up ISCO → COR
    cor_entries = _isco_to_cor.get(isco, [])

    # Add SOC context to results
    results = []
    for cor in cor_entries:
        results.append({
            'soc': soc,
            'soc_title': soc_entry['soc_title'],
            'isco': isco,
            'isco_title': soc_entry['isco_title'],
            'cor': cor['cor'],
            'occupation_ro': cor['occupation_ro']
        })

    return results


def isco_to_cor(isco_code: str) -> List[dict]:
    """
    Convert ISCO-08 code to Romania COR codes.
    """
    load_data()

    isco = str(isco_code).strip().zfill(4)
    return _isco_to_cor.get(isco, [])


def cor_to_soc(cor_code: str) -> List[dict]:
    """
    Reverse lookup: COR code to UK SOC codes.
    """
    load_data()

    cor = str(cor_code).strip()
    if cor not in _cor_codes:
        return []

    cor_entry = _cor_codes[cor]
    isco = cor_entry['isco']

    # Look up ISCO → SOC (reverse)
    soc_entries = _isco_to_soc.get(isco, [])

    results = []
    for soc in soc_entries:
        results.append({
            'cor': cor,
            'occupation_ro': cor_entry['occupation_ro'],
            'isco': isco,
            'soc': soc['soc'],
            'soc_title': soc['soc_title']
        })

    return results


def search_by_title(query: str, source: str = 'all') -> List[dict]:
    """
    Search for occupations by title.

    Args:
        query: Search term (case insensitive)
        source: 'soc', 'cor', or 'all'

    Returns:
        List of matching entries
    """
    load_data()

    query_lower = query.lower()
    query_ascii = to_ascii(query).lower()
    results = []

    if source in ('soc', 'all'):
        for soc, entry in _soc_to_isco.items():
            if query_lower in entry['soc_title'].lower():
                # Get COR matches
                cor_matches = soc_to_cor(soc)
                results.append({
                    'source': 'SOC',
                    'code': soc,
                    'title': entry['soc_title'],
                    'isco': entry['isco'],
                    'cor_count': len(cor_matches),
                    'cor_codes': [c['cor'] for c in cor_matches[:5]]
                })

    if source in ('cor', 'all'):
        for cor, entry in _cor_codes.items():
            title_ascii = to_ascii(entry['occupation_ro']).lower()
            if query_ascii in title_ascii or query_lower in entry['occupation_ro'].lower():
                # Get SOC matches (reverse)
                soc_matches = cor_to_soc(cor)
                results.append({
                    'source': 'COR',
                    'code': cor,
                    'title': entry['occupation_ro'],
                    'isco': entry['isco'],
                    'soc_count': len(soc_matches),
                    'soc_codes': [s['soc'] for s in soc_matches[:5]]
                })

    return results[:50]  # Limit results


def convert_csv(input_file: str, output_file: str = None, soc_column: str = 'soc_code') -> Tuple[int, int]:
    """
    Convert a CSV with SOC codes to include COR codes.

    Returns:
        Tuple of (total rows, matched rows)
    """
    load_data()

    if not output_file:
        base = Path(input_file).stem
        output_file = f"{base}_with_cor.csv"

    total = 0
    matched = 0

    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['isco08', 'cor_codes', 'cor_titles']

        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                total += 1
                soc = row.get(soc_column, '')

                cor_results = soc_to_cor(soc) if soc else []

                if cor_results:
                    matched += 1
                    row['isco08'] = cor_results[0]['isco']
                    row['cor_codes'] = ';'.join([c['cor'] for c in cor_results[:10]])
                    row['cor_titles'] = ';'.join([to_ascii(c['occupation_ro'])[:30] for c in cor_results[:5]])
                else:
                    row['isco08'] = ''
                    row['cor_codes'] = ''
                    row['cor_titles'] = ''

                writer.writerow(row)

    print(f"Converted: {output_file}")
    print(f"Total rows: {total}, Matched: {matched} ({matched*100/total:.1f}%)")
    return total, matched


def get_stats() -> dict:
    """Get statistics about loaded data."""
    load_data()

    return {
        'soc_codes': len(_soc_to_isco),
        'isco_codes': len(_isco_to_soc),
        'cor_codes': len(_cor_codes),
        'isco_to_cor_mappings': sum(len(v) for v in _isco_to_cor.values())
    }


def print_results(results: List[dict], format_type: str = 'table'):
    """Pretty print results"""
    if not results:
        print("No matches found")
        return

    print(f"\nFound {len(results)} matches:\n")

    for r in results[:20]:
        if 'soc' in r and 'cor' in r:
            # Full SOC → COR result or COR → SOC reverse
            if 'isco_title' in r:
                print(f"SOC {r['soc']}: {r['soc_title'][:40]}")
                print(f"  → ISCO {r['isco']}: {r['isco_title'][:40]}")
                print(f"  → COR {r['cor']}: {to_ascii(r['occupation_ro'])[:40]}")
            else:
                # Reverse lookup (COR → SOC)
                print(f"COR {r['cor']}: {to_ascii(r['occupation_ro'])[:40]}")
                print(f"  → ISCO {r['isco']}")
                print(f"  → SOC {r['soc']}: {r['soc_title'][:40]}")
            print()
        elif 'source' in r:
            # Search result
            print(f"[{r['source']}] {r['code']}: {r['title'][:50]}")
            if r.get('cor_codes'):
                print(f"  COR: {', '.join(r['cor_codes'])}")
            if r.get('soc_codes'):
                print(f"  SOC: {', '.join(r['soc_codes'])}")
            print()
        else:
            # Simple result
            for key, val in r.items():
                print(f"  {key}: {val}")
            print()


# ============================================================
# COMMON UK VISA SOC CODES (for quick reference)
# ============================================================

COMMON_UK_SOC = {
    # Healthcare
    '2231': 'Nurses',
    '6145': 'Care workers and home carers',
    '6146': 'Senior care workers',

    # Construction
    '5315': 'Carpenters and joiners',
    '5319': 'Construction trades n.e.c.',
    '5241': 'Electricians',
    '5314': 'Plumbers, heating engineers',
    '5321': 'Plasterers',
    '5322': 'Floorers and wall tilers',
    '5323': 'Painters and decorators',

    # Transport
    '8211': 'Large goods vehicle drivers',
    '8212': 'Van drivers',
    '8214': 'Taxi and cab drivers',

    # Hospitality
    '5434': 'Chefs',
    '9272': 'Kitchen and catering assistants',
    '9273': 'Waiters and waitresses',

    # Manufacturing
    '8125': 'Metal working machine operatives',
    '8111': 'Food, drink and tobacco process operatives',
    '8121': 'Paper and wood machine operatives',

    # Warehouse
    '9134': 'Packers, bottlers, canners and fillers',
    '9260': 'Elementary storage occupations',
}


def main():
    parser = argparse.ArgumentParser(description='UK SOC to Romania COR mapper')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # lookup command
    lookup_parser = subparsers.add_parser('lookup', help='Look up SOC code')
    lookup_parser.add_argument('soc', help='UK SOC code (e.g., 8211)')

    # isco command
    isco_parser = subparsers.add_parser('isco', help='Look up ISCO code')
    isco_parser.add_argument('code', help='ISCO-08 code (e.g., 8332)')

    # cor command (reverse lookup)
    cor_parser = subparsers.add_parser('cor', help='Reverse lookup COR to SOC')
    cor_parser.add_argument('code', help='Romania COR code (e.g., 532103)')

    # title command
    title_parser = subparsers.add_parser('title', help='Search by job title')
    title_parser.add_argument('query', help='Search term')
    title_parser.add_argument('--source', choices=['soc', 'cor', 'all'], default='all')

    # convert command
    convert_parser = subparsers.add_parser('convert', help='Convert CSV with SOC codes')
    convert_parser.add_argument('input', help='Input CSV file')
    convert_parser.add_argument('--output', '-o', help='Output CSV file')
    convert_parser.add_argument('--soc-column', default='soc_code', help='Column name with SOC codes')

    # stats command
    subparsers.add_parser('stats', help='Show statistics')

    # common command
    subparsers.add_parser('common', help='Show common UK visa SOC codes')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\n=== Quick Examples ===")
        print("  python3 soc_cor_mapper.py lookup 8211    # HGV drivers")
        print("  python3 soc_cor_mapper.py lookup 6145    # Care workers")
        print("  python3 soc_cor_mapper.py title nurse")
        print("  python3 soc_cor_mapper.py common         # UK visa codes")
        return

    if args.command == 'lookup':
        results = soc_to_cor(args.soc)
        print_results(results)

    elif args.command == 'isco':
        results = isco_to_cor(args.code)
        print(f"\nISCO {args.code} → {len(results)} COR codes:\n")
        for r in results[:20]:
            print(f"  {r['cor']}: {to_ascii(r['occupation_ro'])[:50]}")

    elif args.command == 'cor':
        results = cor_to_soc(args.code)
        print_results(results)

    elif args.command == 'title':
        results = search_by_title(args.query, args.source)
        print_results(results)

    elif args.command == 'convert':
        convert_csv(args.input, args.output, args.soc_column)

    elif args.command == 'stats':
        stats = get_stats()
        print("\n=== Occupation Code Statistics ===")
        print(f"UK SOC codes:        {stats['soc_codes']}")
        print(f"ISCO-08 categories:  {stats['isco_codes']}")
        print(f"Romania COR codes:   {stats['cor_codes']}")
        print(f"ISCO→COR mappings:   {stats['isco_to_cor_mappings']}")

    elif args.command == 'common':
        print("\n=== Common UK Visa SOC Codes ===\n")
        for soc, title in sorted(COMMON_UK_SOC.items()):
            results = soc_to_cor(soc)
            cor_count = len(results)
            cor_example = results[0]['cor'] if results else 'N/A'
            print(f"SOC {soc}: {title[:35]:35} → {cor_count} COR codes (e.g., {cor_example})")


if __name__ == '__main__':
    main()
