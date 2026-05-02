#!/usr/bin/env python3
"""
Lawyer Search Skill
Search and query Romanian lawyers database.

Usage:
    python3 lawyers_search.py --city Bucuresti
    python3 lawyers_search.py --bar "Baroul Cluj"
    python3 lawyers_search.py --name "Popescu"
    python3 lawyers_search.py --stats
    python3 lawyers_search.py --with-email
    python3 lawyers_search.py --with-phone --city Iasi
"""

import json
import argparse
import sys

DATA_FILE = '/opt/ACTIVE/AVOCATI/data/lawyers_clean.json'


def load_lawyers():
    """Load lawyers from JSON file."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Data file not found: {DATA_FILE}")
        print("Run: python3 /opt/ACTIVE/AVOCATI/clean_lawyers.py")
        sys.exit(1)


def search_lawyers(lawyers, name=None, city=None, bar=None, with_email=False, with_phone=False):
    """Filter lawyers by criteria."""
    results = lawyers

    if name:
        name_upper = name.upper()
        results = [l for l in results if name_upper in l['name'].upper()]

    if city:
        city_upper = city.upper()
        results = [l for l in results if city_upper in l['city'].upper()]

    if bar:
        bar_upper = bar.upper()
        results = [l for l in results if bar_upper in l['bar'].upper()]

    if with_email:
        results = [l for l in results if l['email']]

    if with_phone:
        results = [l for l in results if l['phone']]

    return results


def print_stats(lawyers):
    """Print database statistics."""
    print("=" * 50)
    print("ROMANIAN LAWYERS DATABASE STATISTICS")
    print("=" * 50)
    print(f"Total lawyers: {len(lawyers)}")

    # Cities
    cities = {}
    for l in lawyers:
        city = l['city'] or 'Unknown'
        cities[city] = cities.get(city, 0) + 1

    print(f"Cities/Counties: {len(cities)}")

    # Bar associations
    bars = set(l['bar'] for l in lawyers if l['bar'])
    print(f"Bar associations: {len(bars)}")

    # Contact info
    with_email = sum(1 for l in lawyers if l['email'])
    with_phone = sum(1 for l in lawyers if l['phone'])
    print(f"With email: {with_email} ({100*with_email/len(lawyers):.1f}%)")
    print(f"With phone: {with_phone} ({100*with_phone/len(lawyers):.1f}%)")

    print("\nTop 10 cities:")
    for city, count in sorted(cities.items(), key=lambda x: -x[1])[:10]:
        pct = 100 * count / len(lawyers)
        print(f"  {city}: {count} ({pct:.1f}%)")


def print_results(lawyers, limit=20):
    """Print lawyer results."""
    for i, l in enumerate(lawyers[:limit]):
        print(f"\n{i+1}. {l['name']}")
        print(f"   City: {l['city']}")
        print(f"   Bar: {l['bar']}")
        if l['phone']:
            print(f"   Phone: {l['phone']}")
        if l['email']:
            print(f"   Email: {l['email']}")
        if l['practice_areas']:
            print(f"   Practice: {', '.join(l['practice_areas'])}")

    if len(lawyers) > limit:
        print(f"\n... and {len(lawyers) - limit} more")

    print(f"\nTotal: {len(lawyers)} lawyers")


def export_csv(lawyers, output_file):
    """Export lawyers to CSV."""
    import csv

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'city', 'bar', 'phone', 'email', 'practice_areas'])
        writer.writeheader()
        for l in lawyers:
            row = l.copy()
            row['practice_areas'] = ', '.join(l['practice_areas'])
            writer.writerow(row)

    print(f"Exported {len(lawyers)} lawyers to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Search Romanian lawyers database')
    parser.add_argument('--name', help='Search by name')
    parser.add_argument('--city', help='Filter by city')
    parser.add_argument('--bar', help='Filter by bar association')
    parser.add_argument('--with-email', action='store_true', help='Only lawyers with email')
    parser.add_argument('--with-phone', action='store_true', help='Only lawyers with phone')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--limit', type=int, default=20, help='Max results to display')
    parser.add_argument('--export', help='Export results to CSV file')
    parser.add_argument('--count', action='store_true', help='Only show count')

    args = parser.parse_args()

    lawyers = load_lawyers()

    if args.stats:
        print_stats(lawyers)
        return

    # Apply filters
    results = search_lawyers(
        lawyers,
        name=args.name,
        city=args.city,
        bar=args.bar,
        with_email=args.with_email,
        with_phone=args.with_phone
    )

    if args.export:
        export_csv(results, args.export)
    elif args.count:
        print(len(results))
    else:
        print_results(results, limit=args.limit)


if __name__ == '__main__':
    main()
