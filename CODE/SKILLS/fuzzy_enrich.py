#!/usr/bin/env python3
"""
Fuzzy Enrichment Skill - Match company names across CSV files.

Enriches target CSV with email/phone/website from source CSVs using fuzzy matching.

Usage:
    # Enrich with ANOFM data
    python3 fuzzy_enrich.py input.csv --name-col nume_firma

    # Enrich with all sources
    python3 fuzzy_enrich.py input.csv --all-sources

    # Custom source
    python3 fuzzy_enrich.py input.csv --source source.csv --source-name company

    # Adjust threshold (default 85)
    python3 fuzzy_enrich.py input.csv --threshold 90
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from fuzzy_matcher import FuzzyMatcher, enrich_with_anofm, enrich_with_all_sources, normalize_company_name
from skills_common import to_ascii


def main():
    parser = argparse.ArgumentParser(description='Fuzzy match and enrich CSV')
    parser.add_argument('input', help='Input CSV to enrich')
    parser.add_argument('--output', '-o', help='Output path (default: input_fuzzy_enriched.csv)')
    parser.add_argument('--name-col', default='nume_firma', help='Company name column')
    parser.add_argument('--cui-col', default='cui', help='CUI column')
    parser.add_argument('--threshold', type=int, default=85, help='Match threshold (0-100)')

    # Source options
    parser.add_argument('--anofm', action='store_true', help='Enrich with ANOFM data')
    parser.add_argument('--all-sources', action='store_true', help='Enrich with ALL available sources')
    parser.add_argument('--source', help='Custom source CSV path')
    parser.add_argument('--source-name', default='company_name', help='Source company name column')
    parser.add_argument('--source-email', default='email', help='Source email column')
    parser.add_argument('--source-phone', default='phone', help='Source phone column')

    # Utils
    parser.add_argument('--normalize', action='store_true', help='Just normalize company names')
    parser.add_argument('--test', help='Test match for a company name')

    args = parser.parse_args()

    # Test mode
    if args.test:
        norm = normalize_company_name(args.test)
        print(f"Original: {args.test}")
        print(f"Normalized: {norm}")
        return

    # Normalize mode
    if args.normalize:
        import csv
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else input_path.with_suffix('.normalized.csv')

        with open(input_path, 'r', encoding='utf-8') as f_in:
            reader = csv.DictReader(f_in)
            fieldnames = list(reader.fieldnames) + ['name_normalized']

            with open(output_path, 'w', newline='', encoding='utf-8') as f_out:
                writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    row['name_normalized'] = normalize_company_name(row.get(args.name_col, ''))
                    writer.writerow(row)

        print(f"Normalized: {output_path}")
        return

    # Enrich mode
    input_path = args.input

    if args.all_sources:
        print("Enriching with ALL available sources...")
        output = enrich_with_all_sources(input_path, args.name_col, args.cui_col, args.threshold)
    elif args.anofm:
        print("Enriching with ANOFM data...")
        output = enrich_with_anofm(input_path, args.name_col, args.cui_col, args.threshold)
    elif args.source:
        print(f"Enriching with custom source: {args.source}")
        matcher = FuzzyMatcher(threshold=args.threshold)
        matcher.load_source(
            args.source,
            name_col=args.source_name,
            email_col=args.source_email,
            phone_col=args.source_phone
        )
        output = matcher.enrich(input_path, name_col=args.name_col, cui_col=args.cui_col,
                                output_path=args.output)
    else:
        # Default: ANOFM
        print("Enriching with ANOFM data (default)...")
        output = enrich_with_anofm(input_path, args.name_col, args.cui_col, args.threshold)

    print(f"\nDone: {output}")


if __name__ == '__main__':
    main()
