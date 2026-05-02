#!/usr/bin/env python3
"""
FIRME 2016 Enrichment Skill

Enriches the FIRME 2016 dataset (14K companies turning 10 in 2026) with contact
information from all available internal data sources.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/firme_2016_enrich.py                    # Standard enrichment
    python3 /opt/ACTIVE/INFRA/SKILLS/firme_2016_enrich.py --fuzzy            # With fuzzy matching
    python3 /opt/ACTIVE/INFRA/SKILLS/firme_2016_enrich.py --fuzzy-threshold 90
    python3 /opt/ACTIVE/INFRA/SKILLS/firme_2016_enrich.py --dry-run          # Preview only
    python3 /opt/ACTIVE/INFRA/SKILLS/firme_2016_enrich.py --stats            # Show current stats

Data Sources Used:
    Phase 1 - CUI matching:
    - ANAF all_phones (2.4M phones)
    - Romania Master/Bilant (624K phones)
    - ANOFM master
    - Website contacts
    - EU Funds contacts
    - ACHIZITII_PUBLICE

    Phase 2 - Name matching:
    - ANOFM HORECA (15K)
    - Chambers members
    - EU Funds (by name)

    Phase 3 - Fuzzy matching (optional):
    - All name sources with similarity threshold
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/SCRIPTS')

import argparse
import csv
from pathlib import Path

INPUT_FILE = '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/firme_2016_FINAL.csv'
OUTPUT_FILE = '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/firme_2016_enriched_v2.csv'


def show_stats():
    """Show current statistics."""
    print("=" * 60)
    print("FIRME 2016 - Current Statistics")
    print("=" * 60)

    for label, filepath in [("Input (FINAL)", INPUT_FILE), ("Output (v2)", OUTPUT_FILE)]:
        path = Path(filepath)
        if not path.exists():
            print(f"\n{label}: File not found")
            continue

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            rows = list(csv.DictReader(f))

        total = len(rows)
        with_phone = sum(1 for r in rows if r.get('best_phone', '').strip())
        with_email = sum(1 for r in rows if r.get('best_email', '').strip())
        no_contact = sum(1 for r in rows
                         if not r.get('best_phone', '').strip()
                         and not r.get('best_email', '').strip())
        won_contract = sum(1 for r in rows if r.get('won_public_contract', '').strip() == '1')

        print(f"\n{label}: {filepath}")
        print(f"  Total: {total:,}")
        print(f"  With phone: {with_phone:,} ({100*with_phone/total:.1f}%)")
        print(f"  With email: {with_email:,} ({100*with_email/total:.1f}%)")
        print(f"  NO CONTACT: {no_contact:,} ({100*no_contact/total:.1f}%)")
        if won_contract:
            print(f"  Won public contracts: {won_contract:,}")


def main():
    parser = argparse.ArgumentParser(description='FIRME 2016 Enrichment Skill')
    parser.add_argument('--input', '-i', default=INPUT_FILE, help='Input CSV')
    parser.add_argument('--output', '-o', default=OUTPUT_FILE, help='Output CSV')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--fuzzy', action='store_true', help='Enable fuzzy name matching')
    parser.add_argument('--fuzzy-threshold', type=int, default=85, help='Fuzzy threshold (default: 85)')
    parser.add_argument('--stats', action='store_true', help='Show current statistics')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return 0

    # Import and run enrichment
    try:
        from enrich_all_sources import enrich_companies
        enrich_companies(args.input, args.output, args.dry_run, args.fuzzy, args.fuzzy_threshold)
    except ImportError:
        # Fallback: run as subprocess
        import subprocess
        cmd = [
            '/opt/ACTIVE/INFRA/venv/bin/python3',
            '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/SCRIPTS/enrich_all_sources.py',
            '--input', args.input,
            '--output', args.output,
        ]
        if args.dry_run:
            cmd.append('--dry-run')
        if args.fuzzy:
            cmd.append('--fuzzy')
            cmd.extend(['--fuzzy-threshold', str(args.fuzzy_threshold)])

        subprocess.run(cmd)

    return 0


if __name__ == '__main__':
    sys.exit(main())
