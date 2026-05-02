#!/usr/bin/env python3
"""
URL Fixer Skill - Fix and validate website URLs in CSV files.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/url_fixer.py --fix "www.example.ro"
    python3 /opt/ACTIVE/INFRA/SKILLS/url_fixer.py --test "#"
    python3 /opt/ACTIVE/INFRA/SKILLS/url_fixer.py --extract-onrc
    python3 /opt/ACTIVE/INFRA/SKILLS/url_fixer.py --csv input.csv -o output.csv

Examples:
    # Fix single URL
    python3 /opt/ACTIVE/INFRA/SKILLS/url_fixer.py --fix "arakisprodcom.go.ro: www.arakis.go.ro"

    # Extract valid URLs from ONRC
    python3 /opt/ACTIVE/INFRA/SKILLS/url_fixer.py --extract-onrc

    # Fix URLs in any CSV
    python3 /opt/ACTIVE/INFRA/SKILLS/url_fixer.py --csv data.csv -o fixed.csv --column website
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from url_utils import (
    fix_url, normalize_url, is_valid_url,
    validate_urls, extract_urls_from_field, URLFixer
)
from pathlib import Path


def extract_onrc_urls():
    """Extract valid URLs from ONRC database."""
    onrc_file = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC/onrc_firme_clean.csv')
    output_file = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC/valid_urls.csv')

    if not onrc_file.exists():
        print(f"Error: ONRC file not found: {onrc_file}")
        return

    print(f"Extracting valid URLs from ONRC...")
    print(f"Input: {onrc_file}")

    fixer = URLFixer()
    stats = fixer.extract_valid_urls(
        str(onrc_file),
        str(output_file),
        url_column='WEB',
        id_column='CUI',
        delimiter='^'
    )

    print(f"\nStats:")
    print(f"  Total records: {stats['total']:,}")
    print(f"  Valid URLs: {stats['valid']:,}")
    print(f"  Garbage URLs: {stats['garbage']:,}")
    print(f"\nOutput: {output_file}")


def main():
    import argparse

    p = argparse.ArgumentParser(description='URL Fixer Skill')
    p.add_argument('--fix', metavar='URL', help='Fix single URL')
    p.add_argument('--test', metavar='URL', help='Test if URL is valid')
    p.add_argument('--extract-onrc', action='store_true', help='Extract valid URLs from ONRC')
    p.add_argument('--csv', metavar='FILE', help='Fix URLs in CSV file')
    p.add_argument('--output', '-o', metavar='FILE', help='Output file')
    p.add_argument('--column', '-c', default='WEB', help='URL column name')
    p.add_argument('--delimiter', '-d', default=',', help='CSV delimiter')
    args = p.parse_args()

    if args.fix:
        result = fix_url(args.fix)
        print(f"Input:  {args.fix}")
        print(f"Output: {result or 'INVALID'}")

    elif args.test:
        valid = is_valid_url(args.test)
        normalized = normalize_url(args.test) if valid else None
        print(f"URL: {args.test}")
        print(f"Valid: {valid}")
        if normalized:
            print(f"Normalized: {normalized}")

    elif args.extract_onrc:
        extract_onrc_urls()

    elif args.csv:
        if not args.output:
            print("Error: --output required for --csv")
            sys.exit(1)
        fixer = URLFixer()
        stats = fixer.fix_csv(args.csv, args.output, args.column, args.delimiter)
        print(f"Stats: {stats}")
        print(f"Output: {args.output}")

    else:
        p.print_help()


if __name__ == '__main__':
    main()
