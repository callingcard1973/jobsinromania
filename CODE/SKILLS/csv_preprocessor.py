#!/usr/bin/env python3
"""
CSV Pre-processor - Runs automatically on new CSVs
Outputs summary to /tmp/claude_context/csv_summaries/
"""
import sys
import os
import csv
import json
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

SUMMARY_DIR = Path('/tmp/claude_context/csv_summaries')
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

def get_file_hash(filepath):
    """Get MD5 hash of file for change detection."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()[:8]

def analyze_csv(filepath):
    """Analyze CSV and return summary dict."""
    filepath = Path(filepath)
    if not filepath.exists():
        return {'error': f'File not found: {filepath}'}

    summary = {
        'file': str(filepath),
        'name': filepath.name,
        'size_bytes': filepath.stat().st_size,
        'modified': datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
        'hash': get_file_hash(filepath),
        'analyzed_at': datetime.now().isoformat()
    }

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            # Detect delimiter
            sample = f.read(4096)
            f.seek(0)

            if sample.count(';') > sample.count(','):
                delimiter = ';'
            else:
                delimiter = ','

            reader = csv.DictReader(f, delimiter=delimiter)
            rows = list(reader)

            summary['delimiter'] = delimiter
            summary['columns'] = reader.fieldnames or []
            summary['row_count'] = len(rows)

            # Column stats
            col_stats = {}
            for col in summary['columns']:
                values = [r.get(col, '') for r in rows]
                non_empty = [v for v in values if v and v.strip()]
                col_stats[col] = {
                    'filled': len(non_empty),
                    'empty': len(values) - len(non_empty),
                    'fill_rate': round(len(non_empty) / max(len(values), 1) * 100, 1)
                }
            summary['column_stats'] = col_stats

            # Detect email column
            email_cols = [c for c in summary['columns'] if 'email' in c.lower() or 'mail' in c.lower()]
            if email_cols:
                summary['email_column'] = email_cols[0]
                emails = [r.get(email_cols[0], '') for r in rows if r.get(email_cols[0], '')]
                summary['unique_emails'] = len(set(emails))
                summary['duplicate_emails'] = len(emails) - len(set(emails))

            # Quick quality flags
            summary['flags'] = []
            if summary['row_count'] == 0:
                summary['flags'].append('EMPTY_FILE')
            if any(cs['fill_rate'] < 50 for cs in col_stats.values()):
                summary['flags'].append('LOW_FILL_RATE')
            if summary.get('duplicate_emails', 0) > 0:
                summary['flags'].append('HAS_DUPLICATES')

    except Exception as e:
        summary['error'] = str(e)

    return summary

def save_summary(filepath, summary):
    """Save summary to cache."""
    name = Path(filepath).stem
    hash_part = summary.get('hash', 'unknown')[:8]
    out_file = SUMMARY_DIR / f"{name}_{hash_part}.json"

    with open(out_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return out_file

def main():
    if len(sys.argv) < 2:
        print("Usage: csv_preprocessor.py <file.csv> [--json]")
        sys.exit(1)

    filepath = sys.argv[1]
    json_output = '--json' in sys.argv

    summary = analyze_csv(filepath)
    out_file = save_summary(filepath, summary)

    if json_output:
        print(json.dumps(summary, indent=2))
    else:
        print(f"File: {summary['name']}")
        print(f"Rows: {summary.get('row_count', 'N/A')}")
        print(f"Columns: {len(summary.get('columns', []))}")
        if summary.get('flags'):
            print(f"Flags: {', '.join(summary['flags'])}")
        print(f"Summary: {out_file}")

if __name__ == '__main__':
    main()
