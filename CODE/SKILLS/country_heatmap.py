#!/usr/bin/env python3
"""
Country Heatmap - Geographic performance analysis

Analyzes:
- Leads per country
- Sends per country
- Reply rates by country
- Best performing regions
- Language effectiveness

Usage:
    python3 country_heatmap.py                  # Full heatmap
    python3 country_heatmap.py --country PL     # Single country
    python3 country_heatmap.py --region europe  # Region analysis
    python3 country_heatmap.py --export         # Export to CSV
    python3 country_heatmap.py --telegram       # Send summary

Aggregates data from all sources.
"""

import os
import sys
import csv
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

# Paths
CAEN_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")
PKD_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/PKD_EXPORTS")
NACE_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/NACE_EXPORTS")
TEAOR_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/TEAOR_EXPORTS")
KID_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/KID_EXPORTS")
SK_NACE_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/SK_NACE_EXPORTS")
CONVERSATIONS_DB = Path("/opt/ACTIVE/OPENDATA/DATA/CONVERSATIONS/conversations.json")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")

# Country info
COUNTRIES = {
    "RO": {"name": "Romania", "region": "balkans", "language": "romanian"},
    "PL": {"name": "Poland", "region": "central_europe", "language": "polish"},
    "CZ": {"name": "Czech Republic", "region": "central_europe", "language": "czech"},
    "SK": {"name": "Slovakia", "region": "central_europe", "language": "slovak"},
    "HU": {"name": "Hungary", "region": "central_europe", "language": "hungarian"},
    "BG": {"name": "Bulgaria", "region": "balkans", "language": "bulgarian"},
    "DE": {"name": "Germany", "region": "western_europe", "language": "german"},
    "AT": {"name": "Austria", "region": "western_europe", "language": "german"},
    "NL": {"name": "Netherlands", "region": "western_europe", "language": "dutch"},
    "BE": {"name": "Belgium", "region": "western_europe", "language": "french"},
    "FR": {"name": "France", "region": "western_europe", "language": "french"},
    "ES": {"name": "Spain", "region": "southern_europe", "language": "spanish"},
    "IT": {"name": "Italy", "region": "southern_europe", "language": "italian"},
    "UK": {"name": "United Kingdom", "region": "western_europe", "language": "english"},
    "SE": {"name": "Sweden", "region": "nordic", "language": "swedish"},
    "NO": {"name": "Norway", "region": "nordic", "language": "norwegian"},
    "DK": {"name": "Denmark", "region": "nordic", "language": "danish"},
    "FI": {"name": "Finland", "region": "nordic", "language": "finnish"},
    "HR": {"name": "Croatia", "region": "balkans", "language": "croatian"},
    "SI": {"name": "Slovenia", "region": "balkans", "language": "slovenian"},
}

REGIONS = {
    "central_europe": ["PL", "CZ", "SK", "HU"],
    "balkans": ["RO", "BG", "HR", "SI"],
    "western_europe": ["DE", "AT", "NL", "BE", "FR", "UK"],
    "southern_europe": ["ES", "IT", "PT"],
    "nordic": ["SE", "NO", "DK", "FI"],
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def count_leads_by_country():
    """Count leads per country from all export directories."""
    counts = defaultdict(int)

    # Map directories to countries
    dir_country_map = {
        CAEN_EXPORT_DIR: "RO",
        PKD_EXPORT_DIR: "PL",
        NACE_EXPORT_DIR: "CZ",
        TEAOR_EXPORT_DIR: "HU",
        KID_EXPORT_DIR: "BG",
        SK_NACE_EXPORT_DIR: "SK",
    }

    for export_dir, country in dir_country_map.items():
        if export_dir.exists():
            for filepath in export_dir.glob("*_with_email.csv"):
                try:
                    with open(filepath, 'r') as f:
                        count = sum(1 for _ in f) - 1
                    counts[country] += count
                except:
                    pass

    # Also check campaign contacts for country field
    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if campaign_dir.is_dir():
            contacts_file = campaign_dir / "contacts" / "contacts.csv"
            if contacts_file.exists():
                try:
                    with open(contacts_file, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            country = row.get('country', '').upper()[:2]
                            if country in COUNTRIES:
                                counts[country] += 1
                except:
                    pass

    return dict(counts)


def count_replies_by_country():
    """Count replies per country from conversations."""
    counts = defaultdict(lambda: {'total': 0, 'interested': 0})

    if not CONVERSATIONS_DB.exists():
        return dict(counts)

    try:
        with open(CONVERSATIONS_DB) as f:
            convos = json.load(f)
    except:
        return dict(counts)

    for email_hash, convo in convos.items():
        lead_info = convo.get('lead_info', {})
        country = (lead_info.get('country', '') or '').upper()[:2]

        if country not in COUNTRIES:
            # Try to detect from email domain
            email = convo.get('email', '')
            if email:
                domain = email.split('@')[-1] if '@' in email else ''
                for code in ['pl', 'cz', 'sk', 'hu', 'bg', 'ro', 'de', 'fr']:
                    if domain.endswith(f'.{code}'):
                        country = code.upper()
                        break

        if country in COUNTRIES:
            counts[country]['total'] += len(convo.get('messages', []))
            if convo.get('status') == 'hot':
                counts[country]['interested'] += 1

    return dict(counts)


def generate_heatmap():
    """Generate country heatmap data."""
    leads = count_leads_by_country()
    replies = count_replies_by_country()

    heatmap = []

    for code, info in COUNTRIES.items():
        lead_count = leads.get(code, 0)
        reply_data = replies.get(code, {'total': 0, 'interested': 0})

        heatmap.append({
            'country_code': code,
            'country_name': info['name'],
            'region': info['region'],
            'language': info['language'],
            'leads': lead_count,
            'replies': reply_data['total'],
            'interested': reply_data['interested'],
            'reply_rate': round(reply_data['total'] / max(lead_count, 1) * 100, 2),
            'interest_rate': round(reply_data['interested'] / max(lead_count, 1) * 100, 2),
            'score': 0
        })

    # Calculate score
    for h in heatmap:
        h['score'] = min(100, int(
            h['interest_rate'] * 20 +
            h['reply_rate'] * 5 +
            (1 if h['leads'] > 1000 else 0) * 10
        ))

    # Sort by score
    heatmap.sort(key=lambda x: x['score'], reverse=True)

    return heatmap


def generate_region_summary(heatmap):
    """Generate summary by region."""
    regions = defaultdict(lambda: {'leads': 0, 'replies': 0, 'interested': 0, 'countries': 0})

    for h in heatmap:
        region = h['region']
        regions[region]['leads'] += h['leads']
        regions[region]['replies'] += h['replies']
        regions[region]['interested'] += h['interested']
        regions[region]['countries'] += 1

    # Calculate rates
    result = []
    for region, data in regions.items():
        data['region'] = region
        data['reply_rate'] = round(data['replies'] / max(data['leads'], 1) * 100, 2)
        data['interest_rate'] = round(data['interested'] / max(data['leads'], 1) * 100, 2)
        result.append(data)

    result.sort(key=lambda x: x['leads'], reverse=True)
    return result


def print_heatmap(heatmap, limit=20):
    """Print formatted heatmap."""
    print("\n" + "="*70)
    print("COUNTRY PERFORMANCE HEATMAP")
    print("="*70)

    for h in heatmap[:limit]:
        if h['leads'] == 0:
            continue

        # Heat indicator based on score
        if h['score'] >= 50:
            indicator = "🟢"
        elif h['score'] >= 25:
            indicator = "🟡"
        elif h['score'] > 0:
            indicator = "🟠"
        else:
            indicator = "⚪"

        print(f"\n{indicator} {h['country_code']} {h['country_name']} (score: {h['score']})")
        print(f"  Leads: {h['leads']:,}")
        print(f"  Replies: {h['replies']} ({h['reply_rate']}%)")
        print(f"  Interested: {h['interested']} ({h['interest_rate']}%)")
        print(f"  Region: {h['region']} | Language: {h['language']}")

    print("\n" + "="*70)


def print_region_summary(regions):
    """Print region summary."""
    print("\n📊 REGION SUMMARY\n")

    for r in regions:
        print(f"{r['region'].replace('_', ' ').title()}:")
        print(f"  Countries: {r['countries']} | Leads: {r['leads']:,}")
        print(f"  Interest rate: {r['interest_rate']}%")
        print()


def export_heatmap(heatmap, output_file=None):
    """Export heatmap to CSV."""
    output_file = output_file or Path("/opt/ACTIVE/OPENDATA/DATA/country_heatmap.csv")

    fieldnames = ['country_code', 'country_name', 'region', 'language',
                  'leads', 'replies', 'interested', 'reply_rate', 'interest_rate', 'score']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(heatmap)

    log(f"Exported to {output_file}")


def send_telegram_summary(heatmap):
    """Send summary via Telegram."""
    msg = "🗺️ COUNTRY HEATMAP\n\n"

    for h in heatmap[:8]:
        if h['leads'] == 0:
            continue
        indicator = "🟢" if h['score'] >= 50 else "🟡" if h['score'] >= 25 else "⚪"
        msg += f"{indicator} {h['country_code']}: {h['leads']:,} leads ({h['interest_rate']}% interest)\n"

    top = heatmap[0] if heatmap else None
    if top and top['leads'] > 0:
        msg += f"\n🏆 Top: {top['country_name']}"

    send_telegram(msg)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Country Heatmap")
    parser.add_argument("--country", help="Single country code")
    parser.add_argument("--region", help="Region to analyze")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    parser.add_argument("--telegram", action="store_true", help="Send via Telegram")

    args = parser.parse_args()

    heatmap = generate_heatmap()

    if args.country:
        filtered = [h for h in heatmap if h['country_code'] == args.country.upper()]
        print_heatmap(filtered)
    elif args.region:
        region_countries = REGIONS.get(args.region, [])
        filtered = [h for h in heatmap if h['country_code'] in region_countries]
        print_heatmap(filtered)
    else:
        print_heatmap(heatmap)
        regions = generate_region_summary(heatmap)
        print_region_summary(regions)

    if args.export:
        export_heatmap(heatmap)

    if args.telegram:
        send_telegram_summary(heatmap)


if __name__ == "__main__":
    main()
