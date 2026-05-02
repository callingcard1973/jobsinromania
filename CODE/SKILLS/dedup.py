#!/usr/bin/env python3
"""
CSV Deduplicator - Remove duplicate rows based on key column
Runs automatically after scraper output
"""
import sys
import csv
from pathlib import Path
from collections import defaultdict

def dedupe_csv(filepath, key_column=None, inplace=False):
    """Remove duplicates from CSV based on key column."""
    filepath = Path(filepath)

    # Read
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        sample = f.read(4096)
        f.seek(0)
        delimiter = ';' if sample.count(';') > sample.count(',') else ','
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
        fieldnames = reader.fieldnames

    original_count = len(rows)

    # Auto-detect key column if not specified
    if not key_column:
        # Priority: email > id > cui > first column
        for candidate in ['email', 'Email', 'EMAIL', 'id', 'ID', 'cui', 'CUI']:
            if candidate in fieldnames:
                key_column = candidate
                break
        if not key_column:
            key_column = fieldnames[0]

    if key_column not in fieldnames:
        print(f"Error: Column '{key_column}' not found")
        print(f"Available: {', '.join(fieldnames)}")
        return 0

    # Dedupe
    seen = set()
    unique_rows = []
    duplicates = defaultdict(list)

    for i, row in enumerate(rows):
        key = row.get(key_column, '').strip().lower()
        if key and key in seen:
            duplicates[key].append(i + 1)
        else:
            if key:
                seen.add(key)
            unique_rows.append(row)

    removed = original_count - len(unique_rows)

    # Report
    print(f"Deduplication of {filepath.name} on '{key_column}':")
    print(f"  Original rows: {original_count}")
    print(f"  Unique rows: {len(unique_rows)}")
    print(f"  Duplicates removed: {removed}")

    if duplicates and removed < 20:
        print("  Duplicate keys:")
        for key, row_nums in list(duplicates.items())[:10]:
            print(f"    '{key}': rows {row_nums}")

    # Write
    if removed > 0:
        out_path = filepath if inplace else filepath.with_suffix('.deduped.csv')
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(unique_rows)
        print(f"  Output: {out_path}")

    return removed

def main():
    if len(sys.argv) < 2:
        print("Usage: dedup.py <file.csv> [--key COLUMN] [--inplace]")
        sys.exit(1)

    filepath = sys.argv[1]
    inplace = '--inplace' in sys.argv

    key_column = None
    if '--key' in sys.argv:
        idx = sys.argv.index('--key')
        if idx + 1 < len(sys.argv):
            key_column = sys.argv[idx + 1]

    dedupe_csv(filepath, key_column, inplace)

if __name__ == '__main__':
    main()
