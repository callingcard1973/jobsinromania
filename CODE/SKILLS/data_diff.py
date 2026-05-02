#!/usr/bin/env python3
"""
Data Diff - Compare two CSV files and show differences
Usage: python3 data_diff.py <file1.csv> <file2.csv> [--key column] [--output diff.csv]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

# ============================================================
# CSV COMPARISON
# ============================================================

def read_csv(filepath: str) -> Tuple[List[str], List[Dict]]:
    """Read CSV and return headers and rows as dicts"""
    rows = []
    headers = []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    return headers, rows

def find_key_column(headers: List[str]) -> Optional[str]:
    """Auto-detect the best key column"""
    # Priority order
    priority = ['email', 'id', 'url', 'link', 'phone', 'name', 'title']

    headers_lower = {h.lower(): h for h in headers}

    for key in priority:
        for h_lower, h_orig in headers_lower.items():
            if key in h_lower:
                return h_orig

    # Fall back to first column
    return headers[0] if headers else None

def get_row_key(row: Dict, key_column: str) -> str:
    """Get the key value for a row"""
    return str(row.get(key_column, '')).strip().lower()

def get_row_hash(row: Dict, exclude_cols: Set[str] = None) -> str:
    """Get a hash of row values for comparison"""
    exclude = exclude_cols or set()
    values = [str(row.get(k, '')) for k in sorted(row.keys()) if k not in exclude]
    return '|'.join(values)

def compare_csvs(file1: str, file2: str, key_column: str = None) -> Dict:
    """Compare two CSV files"""
    result = {
        'file1': file1,
        'file2': file2,
        'file1_name': Path(file1).name,
        'file2_name': Path(file2).name,
        'key_column': None,
        'file1_rows': 0,
        'file2_rows': 0,
        'added': [],      # In file2 but not file1
        'removed': [],    # In file1 but not file2
        'modified': [],   # Same key but different values
        'unchanged': 0,
        'headers_added': [],
        'headers_removed': [],
        'summary': {},
    }

    # Read files
    headers1, rows1 = read_csv(file1)
    headers2, rows2 = read_csv(file2)

    result['file1_rows'] = len(rows1)
    result['file2_rows'] = len(rows2)

    # Compare headers
    set1, set2 = set(headers1), set(headers2)
    result['headers_added'] = list(set2 - set1)
    result['headers_removed'] = list(set1 - set2)

    # Determine key column
    if not key_column:
        key_column = find_key_column(headers1)
    result['key_column'] = key_column

    if not key_column:
        result['error'] = 'Could not determine key column'
        return result

    # Index rows by key
    index1 = {}
    for row in rows1:
        key = get_row_key(row, key_column)
        if key:
            index1[key] = row

    index2 = {}
    for row in rows2:
        key = get_row_key(row, key_column)
        if key:
            index2[key] = row

    keys1 = set(index1.keys())
    keys2 = set(index2.keys())

    # Find additions (in file2 but not file1)
    for key in keys2 - keys1:
        result['added'].append(index2[key])

    # Find removals (in file1 but not file2)
    for key in keys1 - keys2:
        result['removed'].append(index1[key])

    # Find modifications (same key, different values)
    common_keys = keys1 & keys2
    for key in common_keys:
        row1 = index1[key]
        row2 = index2[key]

        # Compare values (exclude key column from comparison)
        hash1 = get_row_hash(row1, {key_column})
        hash2 = get_row_hash(row2, {key_column})

        if hash1 != hash2:
            # Find which columns changed
            changes = {}
            all_cols = set(row1.keys()) | set(row2.keys())
            for col in all_cols:
                v1 = str(row1.get(col, '')).strip()
                v2 = str(row2.get(col, '')).strip()
                if v1 != v2:
                    changes[col] = {'old': v1, 'new': v2}

            result['modified'].append({
                'key': key,
                'changes': changes,
                'old': row1,
                'new': row2,
            })
        else:
            result['unchanged'] += 1

    # Summary
    result['summary'] = {
        'added': len(result['added']),
        'removed': len(result['removed']),
        'modified': len(result['modified']),
        'unchanged': result['unchanged'],
        'total_changes': len(result['added']) + len(result['removed']) + len(result['modified']),
    }

    return result

def export_diff(result: Dict, output_path: str, diff_type: str = 'all'):
    """Export diff results to CSV"""
    rows = []

    if diff_type in ['all', 'added']:
        for row in result['added']:
            row['_diff_type'] = 'ADDED'
            rows.append(row)

    if diff_type in ['all', 'removed']:
        for row in result['removed']:
            row['_diff_type'] = 'REMOVED'
            rows.append(row)

    if diff_type in ['all', 'modified']:
        for mod in result['modified']:
            row = mod['new'].copy()
            row['_diff_type'] = 'MODIFIED'
            row['_changes'] = ', '.join(mod['changes'].keys())
            rows.append(row)

    if rows:
        # Get all fieldnames
        fieldnames = ['_diff_type']
        for row in rows:
            for k in row.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return len(rows)

# ============================================================
# OUTPUT
# ============================================================

def print_diff(result: Dict, show_details: bool = False, limit: int = 10):
    """Print diff results"""
    print(f"\n{'='*70}")
    print(f"DATA DIFF")
    print(f"{'='*70}\n")

    print(f"FILE 1: {result['file1_name']} ({result['file1_rows']} rows)")
    print(f"FILE 2: {result['file2_name']} ({result['file2_rows']} rows)")
    print(f"KEY:    {result['key_column']}")

    if result.get('headers_added'):
        print(f"\nNEW COLUMNS: {', '.join(result['headers_added'])}")
    if result.get('headers_removed'):
        print(f"REMOVED COLUMNS: {', '.join(result['headers_removed'])}")

    print(f"\n{'-'*70}")
    print(f"SUMMARY:")
    s = result['summary']
    print(f"  Added:     {s['added']:5} rows (in file2, not in file1)")
    print(f"  Removed:   {s['removed']:5} rows (in file1, not in file2)")
    print(f"  Modified:  {s['modified']:5} rows (same key, different values)")
    print(f"  Unchanged: {s['unchanged']:5} rows")
    print(f"  ---")
    print(f"  Total changes: {s['total_changes']}")

    # Show change percentage
    if result['file1_rows'] > 0:
        change_pct = s['total_changes'] * 100 / result['file1_rows']
        print(f"  Change rate: {change_pct:.1f}%")

    if show_details or limit > 0:
        if result['added']:
            print(f"\n{'-'*70}")
            print(f"ADDED ({len(result['added'])} rows):")
            for row in result['added'][:limit]:
                key_val = row.get(result['key_column'], 'N/A')
                print(f"  + {key_val}")
            if len(result['added']) > limit:
                print(f"  ... and {len(result['added']) - limit} more")

        if result['removed']:
            print(f"\n{'-'*70}")
            print(f"REMOVED ({len(result['removed'])} rows):")
            for row in result['removed'][:limit]:
                key_val = row.get(result['key_column'], 'N/A')
                print(f"  - {key_val}")
            if len(result['removed']) > limit:
                print(f"  ... and {len(result['removed']) - limit} more")

        if result['modified']:
            print(f"\n{'-'*70}")
            print(f"MODIFIED ({len(result['modified'])} rows):")
            for mod in result['modified'][:limit]:
                print(f"  ~ {mod['key']}")
                for col, change in list(mod['changes'].items())[:3]:
                    old_val = change['old'][:30] if change['old'] else '(empty)'
                    new_val = change['new'][:30] if change['new'] else '(empty)'
                    print(f"      {col}: '{old_val}' -> '{new_val}'")
            if len(result['modified']) > limit:
                print(f"  ... and {len(result['modified']) - limit} more")

    print(f"\n{'='*70}\n")

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if len(args) < 2 or '-h' in args or '--help' in args:
        print(f"""
{'='*60}
DATA DIFF - Compare CSV files
{'='*60}

Usage: data_diff.py <file1.csv> <file2.csv> [options]

Options:
  --key COLUMN     Column to use as unique key (auto-detected if not specified)
  --output FILE    Export differences to CSV
  --json           Output as JSON
  --details        Show all differences (not just first 10)
  --limit N        Number of examples to show (default: 10)

Examples:
  data_diff.py old_data.csv new_data.csv
  data_diff.py contacts_v1.csv contacts_v2.csv --key email
  data_diff.py before.csv after.csv --output changes.csv
""")
        return

    file1 = args[0]
    file2 = args[1]

    # Parse options
    key_column = None
    output_file = None
    as_json = '--json' in args
    show_details = '--details' in args
    limit = 10

    for i, arg in enumerate(args):
        if arg == '--key' and i + 1 < len(args):
            key_column = args[i + 1]
        elif arg == '--output' and i + 1 < len(args):
            output_file = args[i + 1]
        elif arg == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])

    # Validate files
    if not os.path.exists(file1):
        print(f"Error: File not found: {file1}")
        return
    if not os.path.exists(file2):
        print(f"Error: File not found: {file2}")
        return

    # Compare
    result = compare_csvs(file1, file2, key_column)

    if result.get('error'):
        print(f"Error: {result['error']}")
        return

    # Output
    if as_json:
        # Remove large data for JSON output
        output = {k: v for k, v in result.items() if k not in ['added', 'removed', 'modified']}
        output['added_count'] = len(result['added'])
        output['removed_count'] = len(result['removed'])
        output['modified_count'] = len(result['modified'])
        output['added_sample'] = result['added'][:5]
        output['removed_sample'] = result['removed'][:5]
        print(json.dumps(output, indent=2))
    else:
        print_diff(result, show_details, limit)

    # Export if requested
    if output_file:
        count = export_diff(result, output_file)
        print(f"Exported {count} changes to {output_file}")

if __name__ == '__main__':
    main()
