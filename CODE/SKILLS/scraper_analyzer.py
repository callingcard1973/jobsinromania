#!/usr/bin/env python3
"""
Scraper Output Analyzer using LM Studio
Analyze scraper output for quality and anomalies.

Usage:
    python3 scraper_analyzer.py /opt/ACTIVE/OPENDATA/DATA/DENMARK/latest.csv
    python3 scraper_analyzer.py /path/to/file.csv --score

# [AI: Claude Code]
Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import sys
import os
import csv
import argparse
from typing import Dict, List, Optional
from collections import Counter

sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
from lmstudio_client import LMStudioClient, is_lmstudio_available


def analyze_csv(filepath: str) -> Dict:
    """Basic CSV analysis without LLM."""
    stats = {
        'path': filepath,
        'rows': 0,
        'columns': [],
        'empty_cells': 0,
        'duplicates': 0,
        'email_count': 0,
        'phone_count': 0,
        'anomalies': []
    }

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            stats['columns'] = reader.fieldnames or []

            rows = list(reader)
            stats['rows'] = len(rows)

            # Count empty cells
            for row in rows:
                for col, val in row.items():
                    if not val or val.strip() == '':
                        stats['empty_cells'] += 1
                    if col and 'email' in col.lower() and val:
                        stats['email_count'] += 1
                    if col and 'phone' in col.lower() and val:
                        stats['phone_count'] += 1

            # Check for duplicates (by first column)
            if stats['columns']:
                first_col = stats['columns'][0]
                values = [r.get(first_col) for r in rows if r.get(first_col)]
                stats['duplicates'] = len(values) - len(set(values))

            # Detect anomalies
            if stats['rows'] == 0:
                stats['anomalies'].append('Empty file')
            if stats['empty_cells'] > stats['rows'] * len(stats['columns']) * 0.3:
                stats['anomalies'].append('High empty cell ratio (>30%)')
            if stats['duplicates'] > stats['rows'] * 0.1:
                stats['anomalies'].append(f'High duplicate ratio ({stats["duplicates"]} dupes)')

    except Exception as e:
        stats['anomalies'].append(f'Error reading file: {e}')

    return stats


def score_with_llm(stats: Dict, sample_rows: List[Dict]) -> Optional[Dict]:
    """Get quality score using LLM."""
    if not is_lmstudio_available():
        return None

    # Build sample data string
    sample_str = ""
    for row in sample_rows[:3]:
        sample_str += str(dict(list(row.items())[:5])) + "\n"

    prompt = f"""Rate this data quality 1-10.

Stats:
- Rows: {stats['rows']}
- Columns: {len(stats['columns'])}
- Empty cells: {stats['empty_cells']}
- Duplicates: {stats['duplicates']}
- Emails: {stats['email_count']}
- Phones: {stats['phone_count']}

Sample:
{sample_str}

Reply with:
SCORE: [1-10]
REASON: [one sentence]"""

    client = LMStudioClient(timeout=120)
    response = client.query(prompt, temperature=0.2, max_tokens=100)

    if response:
        result = {'score': 5, 'reason': 'Unknown'}
        for line in response.split('\n'):
            if line.startswith('SCORE:'):
                try:
                    result['score'] = int(line.split(':')[1].strip().split()[0])
                except:
                    pass
            if line.startswith('REASON:'):
                result['reason'] = line.split(':', 1)[1].strip()
        return result
    return None


def main():
    parser = argparse.ArgumentParser(description='Analyze scraper output')
    parser.add_argument('filepath', help='CSV file to analyze')
    parser.add_argument('--score', action='store_true',
                        help='Get LLM quality score')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')

    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"[ERROR] File not found: {args.filepath}")
        sys.exit(1)

    # Basic analysis
    stats = analyze_csv(args.filepath)

    # LLM scoring if requested
    if args.score and is_lmstudio_available():
        with open(args.filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            sample = list(reader)[:5]
        llm_score = score_with_llm(stats, sample)
        if llm_score:
            stats['quality_score'] = llm_score['score']
            stats['quality_reason'] = llm_score['reason']

    # Output
    if args.json:
        import json
        print(json.dumps(stats, indent=2))
    else:
        print(f"File: {stats['path']}")
        print(f"Rows: {stats['rows']}")
        print(f"Columns: {len(stats['columns'])}")
        print(f"Empty cells: {stats['empty_cells']}")
        print(f"Duplicates: {stats['duplicates']}")
        print(f"Emails: {stats['email_count']}")
        print(f"Phones: {stats['phone_count']}")
        if stats['anomalies']:
            print(f"Anomalies: {', '.join(stats['anomalies'])}")
        if 'quality_score' in stats:
            print(f"Quality: {stats['quality_score']}/10 - {stats['quality_reason']}")


if __name__ == '__main__':
    main()
