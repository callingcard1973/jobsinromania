#!/usr/bin/env python3
"""
CCIB Chamber of Commerce Bucharest - Skill wrapper

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/ccib_scraper.py              # Scrape all
    python3 /opt/ACTIVE/INFRA/SKILLS/ccib_scraper.py --stats      # Show stats
    python3 /opt/ACTIVE/INFRA/SKILLS/ccib_scraper.py --letter A   # Single letter
"""

import subprocess
import sys
import csv
from pathlib import Path

SCRAPER = '/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/ccib_scraper.py'
OUTPUT = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CCIB/ccib_companies.csv')
PYTHON = '/opt/ACTIVE/INFRA/venv/bin/python3'


def show_stats():
    """Show CCIB data stats."""
    if not OUTPUT.exists():
        print("No CCIB data. Run: python3 /opt/ACTIVE/INFRA/SKILLS/ccib_scraper.py")
        return

    with open(OUTPUT, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    print(f"=== CCIB Companies ===")
    print(f"Total: {len(rows)}")
    print(f"With phone: {sum(1 for r in rows if r.get('phone_1'))}")
    print(f"With email: {sum(1 for r in rows if r.get('email'))}")
    print(f"With website: {sum(1 for r in rows if r.get('website'))}")
    print(f"Output: {OUTPUT}")


def run_scraper(letter=None):
    """Run the CCIB scraper."""
    cmd = [PYTHON, SCRAPER]
    if letter:
        cmd.extend(['--letter', letter])

    result = subprocess.run(cmd, capture_output=False)

    # Deduplicate after scraping
    if OUTPUT.exists():
        dedupe()

    return result.returncode


def dedupe():
    """Remove duplicate companies."""
    if not OUTPUT.exists():
        return

    seen = set()
    unique = []

    with open(OUTPUT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            key = row.get('name', '').strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(row)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(unique)

    print(f"Deduplicated: {len(unique)} unique companies")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--stats', action='store_true', help='Show stats')
    p.add_argument('--letter', help='Scrape single letter')
    p.add_argument('--dedupe', action='store_true', help='Dedupe existing file')
    args = p.parse_args()

    if args.stats:
        show_stats()
    elif args.dedupe:
        dedupe()
    else:
        run_scraper(args.letter)
