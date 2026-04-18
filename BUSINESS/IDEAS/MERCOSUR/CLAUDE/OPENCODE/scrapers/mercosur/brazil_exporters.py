#!/usr/bin/env python3
"""
Brazilian Exporters - Unified Scraper

Main entry point that combines multiple data sources:
1. B2Brazil company profiles
2. ConnectAmericas catalog
3. ComexStat official trade data

Quick start:
    python3 brazil_exporters.py --quick        # Fast test (50 companies)
    python3 brazil_exporters.py --minerals     # Lithium/niobium focus
    python3 brazil_exporters.py --honey        # Honey exporters
    python3 brazil_exporters.py --full         # All sectors (slow)

Output: data/mercosur/brazil_exporters_YYYYMMDD.csv
"""

import sys
import csv
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Import sub-scrapers
from apex_brasil_scraper import BrazilExportersScraper, SECTORS
from connectamericas_scraper import ConnectAmericasScraper, HS_CODES

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

BASE_DIR = Path('/opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE')
OUTPUT_DIR = BASE_DIR / 'data' / 'mercosur'
LOG_DIR = BASE_DIR / 'logs'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def merge_companies(lists: List[List[Dict]]) -> List[Dict]:
    """Merge and deduplicate company lists."""
    seen = set()
    merged = []

    for company_list in lists:
        for company in company_list:
            name = company.get('name', '').lower().strip()
            if name and name not in seen:
                seen.add(name)
                merged.append(company)

    return merged


def enrich_with_sector_tags(companies: List[Dict]) -> List[Dict]:
    """Add EU-Mercosur relevance tags."""
    priority_keywords = {
        'lithium': 'critical_minerals',
        'niobium': 'critical_minerals',
        'niobio': 'critical_minerals',
        'litio': 'critical_minerals',
        'honey': 'food_quota',
        'mel': 'food_quota',
        'beef': 'food_quota',
        'carne': 'food_quota',
        'wine': 'beverages',
        'vinho': 'beverages',
        'coffee': 'commodities',
        'cafe': 'commodities',
        'soy': 'commodities',
        'soja': 'commodities'
    }

    for company in companies:
        tags = []
        text = f"{company.get('name', '')} {company.get('products', '')} {company.get('description', '')}".lower()

        for keyword, tag in priority_keywords.items():
            if keyword in text and tag not in tags:
                tags.append(tag)

        company['eu_mercosur_tags'] = ','.join(tags) if tags else ''

    return companies


def export_combined_csv(companies: List[Dict], output_file: Path) -> Path:
    """Export to unified CSV format."""
    fieldnames = [
        'name', 'sector', 'hs_codes', 'email', 'phone', 'website',
        'state', 'city', 'products', 'export_volume', 'description',
        'eu_mercosur_tags', 'country', 'source', 'scraped_at'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)

    log.info(f"Exported {len(companies)} companies to {output_file}")
    return output_file


def print_summary(companies: List[Dict]):
    """Print scraping summary."""
    total = len(companies)
    with_email = sum(1 for c in companies if c.get('email'))
    with_phone = sum(1 for c in companies if c.get('phone'))
    with_website = sum(1 for c in companies if c.get('website'))

    print("\n" + "="*50)
    print("BRAZILIAN EXPORTERS SCRAPE COMPLETE")
    print("="*50)
    print(f"Total companies: {total}")
    print(f"With email:      {with_email} ({with_email*100//max(total,1)}%)")
    print(f"With phone:      {with_phone} ({with_phone*100//max(total,1)}%)")
    print(f"With website:    {with_website} ({with_website*100//max(total,1)}%)")

    # Count by tag
    tag_counts = {}
    for c in companies:
        for tag in c.get('eu_mercosur_tags', '').split(','):
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if tag_counts:
        print("\nEU-Mercosur relevance:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
            print(f"  {tag}: {count}")

    print("="*50)


def main():
    parser = argparse.ArgumentParser(description='Brazilian Exporters Unified Scraper')
    parser.add_argument('--quick', action='store_true', help='Quick test (50 companies)')
    parser.add_argument('--minerals', action='store_true', help='Focus on critical minerals (lithium, niobium)')
    parser.add_argument('--honey', action='store_true', help='Focus on honey exporters')
    parser.add_argument('--food', action='store_true', help='Focus on food sector')
    parser.add_argument('--full', action='store_true', help='Full scrape all sectors')
    parser.add_argument('--limit', type=int, default=500, help='Max companies per source')
    parser.add_argument('--output', type=str, help='Output file path')

    args = parser.parse_args()

    all_companies = []

    # Determine what to scrape
    if args.quick:
        log.info("Quick mode: 50 companies from B2Brazil")
        scraper = BrazilExportersScraper()
        companies = scraper.scrape_sector('food', limit=50)
        all_companies.extend(companies)

    elif args.minerals:
        log.info("Minerals mode: lithium, niobium, ores")
        b2b = BrazilExportersScraper()
        ca = ConnectAmericasScraper()

        all_companies.extend(b2b.scrape_sector('minerals', limit=args.limit))
        all_companies.extend(ca.search_by_hs_code('81', limit=args.limit))  # Niobium
        all_companies.extend(ca.search_by_hs_code('26', limit=args.limit))  # Ores

    elif args.honey:
        log.info("Honey mode: HS code 0409")
        b2b = BrazilExportersScraper()
        ca = ConnectAmericasScraper()

        all_companies.extend(b2b.scrape_sector('honey', limit=args.limit))
        all_companies.extend(ca.search_by_hs_code('0409', limit=args.limit))

    elif args.food:
        log.info("Food mode: all food sectors")
        b2b = BrazilExportersScraper()
        ca = ConnectAmericasScraper()

        all_companies.extend(b2b.scrape_sector('food', limit=args.limit))
        for hs in ['02', '03', '09', '17', '22']:  # Meat, fish, coffee, sugar, beverages
            all_companies.extend(ca.search_by_hs_code(hs, limit=args.limit//5))

    elif args.full:
        log.info("Full mode: all sectors from all sources")
        b2b = BrazilExportersScraper()
        ca = ConnectAmericasScraper()

        b2b.scrape_all_sectors(limit_per_sector=args.limit)
        all_companies.extend(b2b.all_companies)

        ca.scrape_all_sectors(limit_per_sector=args.limit//len(HS_CODES))
        all_companies.extend(ca.companies)

    else:
        parser.print_help()
        print("\n\nExamples:")
        print("  python3 brazil_exporters.py --quick        # Test with 50 companies")
        print("  python3 brazil_exporters.py --minerals     # Lithium/niobium")
        print("  python3 brazil_exporters.py --honey        # Honey exporters")
        print("  python3 brazil_exporters.py --full         # Everything")
        return

    # Merge and deduplicate
    all_companies = merge_companies([all_companies])
    all_companies = enrich_with_sector_tags(all_companies)

    # Export
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = OUTPUT_DIR / f"brazil_exporters_{datetime.now():%Y%m%d_%H%M}.csv"

    export_combined_csv(all_companies, output_file)
    print_summary(all_companies)

    print(f"\nOutput: {output_file}")


if __name__ == '__main__':
    main()
