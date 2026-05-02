#!/usr/bin/env python3
"""
ANOFM Employer Enricher - 8-Source Cascade

Enriches Romanian employer data with phone and email from multiple sources.

Usage:
    python3 anofm_enricher.py --file employers.csv
    python3 anofm_enricher.py --file employers.csv --max-checks 100
    python3 anofm_enricher.py --help

Sources (in order):
    1. ANAF API (phone)
    2. Domain guess (email) - DNS + multi-pattern
    3. Website scrape (email) - /contact pages
    4. Web search (phone + email) - DuckDuckGo
    5. TED winners (email) - 1.5M EU contractors
    6. Listafirme.ro (phone + email)
    7. Termene.ro (phone + email)
    8. Internal DB (phone + email)
"""

import sys
import os
import argparse
import csv
from typing import List, Dict, Tuple

# Add shared modules
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM')

def load_csv(file_path: str) -> List[Dict]:
    """Load employers from CSV file."""
    employers = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            employers.append(dict(row))
    return employers


def save_csv(employers: List[Dict], file_path: str):
    """Save employers to CSV file."""
    if not employers:
        return

    fieldnames = list(employers[0].keys())
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(employers)


def enrich_employers(employers: List[Dict], max_checks: int = 50) -> Tuple[int, int]:
    """
    Enrich employers using 8-source cascade.

    Returns:
        Tuple of (phones_found, emails_found)
    """
    # Import enrichment functions from anofm_targets
    try:
        from anofm_targets import enrich_employers_anaf
        return enrich_employers_anaf(employers, batch_size=100, enrich_email=True)
    except ImportError:
        print("[ERROR] Could not import anofm_targets module")
        print("  Expected at: /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/anofm_targets.py")
        return 0, 0


def main():
    parser = argparse.ArgumentParser(
        description='ANOFM Employer Enricher - 8-Source Cascade',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--file', '-f', required=True, help='CSV file with employers')
    parser.add_argument('--output', '-o', help='Output file (default: input_enriched.csv)')
    parser.add_argument('--max-checks', '-m', type=int, default=50, help='Max checks per source (default: 50)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"[ERROR] File not found: {args.file}")
        sys.exit(1)

    # Load employers
    print(f"Loading employers from: {args.file}")
    employers = load_csv(args.file)
    print(f"  Loaded: {len(employers)} employers")

    # Count initial coverage
    with_phone = sum(1 for e in employers if e.get('phone') or e.get('telefon'))
    with_email = sum(1 for e in employers if e.get('email'))
    print(f"  Initial: {with_phone} phones ({100*with_phone/len(employers):.1f}%), {with_email} emails ({100*with_email/len(employers):.1f}%)")

    if args.dry_run:
        print("\n[DRY RUN] Would enrich using 8-source cascade:")
        print("  1. ANAF API (phone)")
        print("  2. Domain guess (email)")
        print("  3. Website scrape (email)")
        print("  4. Web search (phone + email)")
        print("  5. TED winners (email)")
        print("  6. Listafirme.ro (phone + email)")
        print("  7. Termene.ro (phone + email)")
        print("  8. Internal DB (phone + email)")
        return

    # Enrich
    print(f"\n=== Running 8-source cascade ===")
    phones_found, emails_found = enrich_employers(employers, max_checks=args.max_checks)

    # Count final coverage
    with_phone = sum(1 for e in employers if e.get('phone') or e.get('telefon'))
    with_email = sum(1 for e in employers if e.get('email'))
    print(f"\n=== Results ===")
    print(f"  Phones found: {phones_found}")
    print(f"  Emails found: {emails_found}")
    print(f"  Final: {with_phone} phones ({100*with_phone/len(employers):.1f}%), {with_email} emails ({100*with_email/len(employers):.1f}%)")

    # Save output
    output_file = args.output or args.file.replace('.csv', '_enriched.csv')
    save_csv(employers, output_file)
    print(f"\n  Saved: {output_file}")


if __name__ == '__main__':
    main()
