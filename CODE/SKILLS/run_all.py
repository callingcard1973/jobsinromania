#!/usr/bin/env python3
"""
Run EU Suppliers scrapers for all or selected countries.

Usage:
    python run_all.py --list              # List datasets from all countries
    python run_all.py --download          # Download from all countries
    python run_all.py --country POLAND    # Single country
    python run_all.py --countries "POLAND,GERMANY,FRANCE"  # Multiple
"""

import argparse
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path("/opt/ACTIVE/OPENDATA/SANDBOX/EU_SUPPLIERS")
PYTHON = "/opt/ACTIVE/INFRA/venv/bin/python3"

COUNTRIES = [
    "AUSTRIA", "BELGIUM", "BULGARIA", "CROATIA", "CYPRUS", "CZECH",
    "DENMARK", "ESTONIA", "FINLAND", "FRANCE", "GERMANY", "GREECE",
    "HUNGARY", "IRELAND", "ITALY", "LATVIA", "LITHUANIA", "LUXEMBOURG",
    "MALTA", "NETHERLANDS", "NORWAY", "POLAND", "PORTUGAL", "ROMANIA",
    "SERBIA", "SLOVAKIA", "SLOVENIA", "SPAIN", "SWEDEN", "SWITZERLAND", "UK"
]


def run_scraper(country: str, action: str) -> bool:
    """Run scraper for a country."""
    country_dir = BASE_DIR / country
    scraper = country_dir / f"{country.lower()}_scraper.py"

    if not scraper.exists():
        print(f"[SKIP] {country}: No scraper found")
        return False

    cmd = [PYTHON, str(scraper), f"--{action}"]
    print(f"\n{'='*60}")
    print(f"Running: {country} --{action}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, capture_output=False, timeout=300)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {country}")
        return False
    except Exception as e:
        print(f"[ERROR] {country}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Run EU Suppliers scrapers')
    parser.add_argument('--list', action='store_true', help='List datasets')
    parser.add_argument('--download', action='store_true', help='Download data')
    parser.add_argument('--country', type=str, help='Single country')
    parser.add_argument('--countries', type=str, help='Comma-separated countries')

    args = parser.parse_args()
    action = 'download' if args.download else 'list'

    # Determine which countries to process
    if args.country:
        countries = [args.country.upper()]
    elif args.countries:
        countries = [c.strip().upper() for c in args.countries.split(',')]
    else:
        countries = COUNTRIES

    # Validate countries
    invalid = [c for c in countries if c not in COUNTRIES]
    if invalid:
        print(f"Invalid countries: {invalid}")
        print(f"Valid: {', '.join(COUNTRIES)}")
        sys.exit(1)

    # Run scrapers
    results = {"success": [], "failed": [], "skipped": []}

    for country in countries:
        if run_scraper(country, action):
            results["success"].append(country)
        else:
            results["failed"].append(country)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Success: {len(results['success'])} - {', '.join(results['success'][:5])}...")
    print(f"Failed:  {len(results['failed'])} - {', '.join(results['failed'])}")


if __name__ == '__main__':
    main()
