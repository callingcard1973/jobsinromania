#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
EU Subsidy Database Skill - Query EU grant/subsidy recipients.

Provides access to 673K+ companies that received EU funding (warm leads with budget).

Usage:
    python3 eu_subsidy.py                          # Show status
    python3 eu_subsidy.py --scrape                 # Full scrape (all 27 countries)
    python3 eu_subsidy.py --scrape --country DE    # Single country
    python3 eu_subsidy.py --search "automotive"    # Search by industry
    python3 eu_subsidy.py --top 100                # Show top 100 by funding
    python3 eu_subsidy.py --export DE              # Export country to CSV

Data sources:
- Kohesio: https://kohesio.ec.europa.eu (1.7M projects, 673K beneficiaries)

See /opt/CLAUDE.md for shared code rules.
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from skills_common import to_ascii
from eu_utils import EU_COUNTRIES, SCHEMA_50, normalize_eu_company

# Paths
DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EU_SUBSIDY')
SCRAPER_PATH = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EU_SUBSIDY/kohesio_scraper.py')


def show_status():
    """Show current database status."""
    print("=" * 70)
    print("EU SUBSIDY DATABASE STATUS")
    print("=" * 70)
    print()

    stats_file = DATA_DIR / 'kohesio_stats.json'
    if stats_file.exists():
        with open(stats_file) as f:
            stats = json.load(f)
        print(f"Last updated:        {stats.get('last_run', 'Never')}")
        print(f"Countries scraped:   {stats.get('countries', 0)} / {len(EU_COUNTRIES)}")
        print(f"Total beneficiaries: {stats.get('total_beneficiaries', 0):,}")
        print(f"With email:          {stats.get('with_email', 0):,}")
        if stats.get('total_eu_funding_eur'):
            print(f"Total EU funding:    EUR {stats.get('total_eu_funding_eur', 0):,.0f}")
    else:
        print("No data scraped yet.")
        print()
        print("Run: python3 eu_subsidy.py --scrape")
        return

    print()
    print("Per-country data:")
    print("-" * 70)
    print(f"{'Country':<20} {'Code':<6} {'Beneficiaries':>15} {'File Size':>12}")
    print("-" * 70)

    total_records = 0
    for code, name in sorted(EU_COUNTRIES.items(), key=lambda x: x[1]):
        file_path = DATA_DIR / f"{code}_{name.lower().replace(' ', '_')}_beneficiaries.csv"
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    rows = sum(1 for _ in f) - 1
                size = file_path.stat().st_size
                size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
                print(f"{name:<20} {code:<6} {rows:>15,} {size_str:>12}")
                total_records += rows
            except Exception:
                print(f"{name:<20} {code:<6} {'Error':>15}")
        else:
            print(f"{name:<20} {code:<6} {'Not scraped':>15}")

    print("-" * 70)
    print(f"{'TOTAL':<20} {'':<6} {total_records:>15,}")


def run_scrape(country: str = None, test: bool = False):
    """Run the Kohesio scraper."""
    cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', str(SCRAPER_PATH)]

    if country:
        cmd.extend(['--country', country.upper()])
    elif test:
        cmd.append('--test')

    print(f"Running: {' '.join(cmd)}")
    print()
    subprocess.run(cmd)


def search_beneficiaries(query: str, limit: int = 50) -> List[Dict]:
    """Search beneficiaries by name or industry."""
    results = []
    query_lower = query.lower()

    # Search across all country files
    for file_path in DATA_DIR.glob('*_beneficiaries.csv'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('company_name', '').lower()
                    industry = row.get('company_industry', '').lower()

                    if query_lower in name or query_lower in industry:
                        results.append(row)

                        if len(results) >= limit:
                            break

        except Exception:
            continue

        if len(results) >= limit:
            break

    return results


def show_search_results(query: str, limit: int = 50):
    """Display search results."""
    print(f"Searching for: '{query}'...")
    print()

    results = search_beneficiaries(query, limit)

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} results:")
    print("-" * 90)
    print(f"{'Company':<40} {'Country':<4} {'Website':<30} {'Industry':<15}")
    print("-" * 90)

    for row in results:
        name = row.get('company_name', '')[:38]
        country = row.get('location_country', '')
        website = row.get('company_website', '')[:28]
        industry = row.get('company_industry', '')[:13]
        print(f"{name:<40} {country:<4} {website:<30} {industry:<15}")


def show_top_beneficiaries(limit: int = 100):
    """Show top beneficiaries by funding amount."""
    beneficiaries = []

    for file_path in DATA_DIR.glob('*_beneficiaries.csv'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Extract budget from extra_1
                    budget_str = row.get('extra_1', '')
                    if budget_str.startswith('Budget:'):
                        try:
                            budget = float(budget_str.replace('Budget:', ''))
                            beneficiaries.append({
                                'name': row.get('company_name', ''),
                                'country': row.get('location_country', ''),
                                'budget': budget,
                                'website': row.get('company_website', ''),
                            })
                        except ValueError:
                            pass
        except Exception:
            continue

    # Sort by budget (descending)
    beneficiaries.sort(key=lambda x: x['budget'], reverse=True)
    beneficiaries = beneficiaries[:limit]

    if not beneficiaries:
        print("No beneficiaries with budget data found.")
        return

    print(f"Top {len(beneficiaries)} beneficiaries by EU funding:")
    print("-" * 90)
    print(f"{'#':<4} {'Company':<40} {'Country':<4} {'Budget (EUR)':>15} {'Website':<25}")
    print("-" * 90)

    for i, b in enumerate(beneficiaries, 1):
        name = b['name'][:38]
        website = b['website'][:23]
        print(f"{i:<4} {name:<40} {b['country']:<4} {b['budget']:>15,.0f} {website:<25}")


def export_country(country_code: str, output_path: str = None):
    """Export country data to a clean CSV."""
    country_code = country_code.upper()
    country_name = EU_COUNTRIES.get(country_code, country_code).lower().replace(' ', '_')

    input_file = DATA_DIR / f"{country_code}_{country_name}_beneficiaries.csv"

    if not input_file.exists():
        print(f"No data for {country_code}. Run --scrape first.")
        return

    if not output_path:
        output_path = f"{country_code}_beneficiaries_export_{datetime.now().strftime('%Y%m%d')}.csv"

    # Copy with clean headers
    with open(input_file, 'r', encoding='utf-8') as fin:
        with open(output_path, 'w', newline='', encoding='utf-8') as fout:
            reader = csv.DictReader(fin)
            # Export only useful columns
            export_cols = ['company_name', 'company_id', 'company_website', 'location_country']
            writer = csv.DictWriter(fout, fieldnames=export_cols, extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            for row in reader:
                writer.writerow(row)

    print(f"Exported to: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='EU Subsidy Database Skill')
    parser.add_argument('--scrape', action='store_true', help='Run Kohesio scraper')
    parser.add_argument('--country', type=str, help='Country code (DE, FR, etc.)')
    parser.add_argument('--test', action='store_true', help='Test mode (3 countries)')
    parser.add_argument('--search', type=str, help='Search beneficiaries')
    parser.add_argument('--top', type=int, help='Show top N by funding')
    parser.add_argument('--export', type=str, help='Export country to CSV')
    parser.add_argument('--output', type=str, help='Output file path')

    args = parser.parse_args()

    if args.scrape:
        run_scrape(country=args.country, test=args.test)
    elif args.search:
        show_search_results(args.search)
    elif args.top:
        show_top_beneficiaries(args.top)
    elif args.export:
        export_country(args.export, args.output)
    else:
        show_status()


if __name__ == '__main__':
    main()
