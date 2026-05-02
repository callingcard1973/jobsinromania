#!/usr/bin/env python3
"""
TED Data Explorer - Search and analyze EU procurement data.

Extracts from TED XML:
- Contracting authorities (buyers)
- Contact info (email, phone, website)
- Contract values and CPV codes
- Countries, cities, sectors

Usage:
    python3 ted_explorer.py --search "construction" --country DE
    python3 ted_explorer.py --extract-contacts 2020
    python3 ted_explorer.py --stats 2020
    python3 ted_explorer.py --top-buyers 2020 --limit 50
"""

import argparse
import csv
import os
import re
import sys
import tarfile
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(text):
        if not text:
            return ""
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

# Paths
BASE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_TENDERS")
RAW_DIR = BASE_DIR / "RAW" / "MONTHLY"
OUTPUT_DIR = BASE_DIR / "EXTRACTED"
CSV_DIR = BASE_DIR / "CSV"

# CPV Categories (Common Procurement Vocabulary)
CPV_CATEGORIES = {
    '09': 'Petroleum, fuel, electricity',
    '14': 'Mining, metals',
    '15': 'Food, beverages',
    '18': 'Clothing, footwear',
    '22': 'Printed matter',
    '30': 'Office equipment, computers',
    '31': 'Electrical machinery',
    '32': 'Radio, TV, communication',
    '33': 'Medical equipment',
    '34': 'Transport equipment',
    '35': 'Security equipment',
    '37': 'Musical instruments, sports',
    '38': 'Laboratory equipment',
    '39': 'Furniture',
    '41': 'Water',
    '42': 'Industrial machinery',
    '43': 'Mining machinery',
    '44': 'Construction materials',
    '45': 'CONSTRUCTION WORKS',
    '48': 'Software packages',
    '50': 'Repair services',
    '51': 'Installation services',
    '55': 'HOTEL/RESTAURANT services',
    '60': 'TRANSPORT services',
    '63': 'Transport support',
    '64': 'Postal, telecom',
    '65': 'Utilities',
    '66': 'Financial services',
    '70': 'Real estate',
    '71': 'Architecture, engineering',
    '72': 'IT services',
    '73': 'R&D services',
    '75': 'Public admin',
    '76': 'Oil/gas services',
    '77': 'AGRICULTURE services',
    '79': 'Business services',
    '80': 'Education',
    '85': 'Health, social',
    '90': 'Sewage, waste',
    '92': 'Recreation, culture',
    '98': 'Other services',
}


def parse_ted_xml_full(xml_content):
    """Parse TED XML and extract all useful fields."""
    notice = {}

    try:
        root = ET.fromstring(xml_content)

        # Get DOC_ID from root
        notice['doc_id'] = root.get('DOC_ID', '')

        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            text = elem.text.strip() if elem.text else ''

            # Notice ID
            if tag == 'NO_DOC_OJS' and text:
                notice['notice_id'] = to_ascii(text)

            # Country
            elif tag == 'ISO_COUNTRY':
                notice['country'] = elem.get('VALUE', text).upper()[:2]

            # Title (English preferred)
            elif tag == 'ML_TI_DOC' and elem.get('LG') == 'EN':
                for child in elem:
                    if child.tag.endswith('TI_TEXT') or child.tag == 'TI_TEXT':
                        for p in child:
                            if p.text:
                                notice['title'] = to_ascii(p.text)[:500]

            # City
            elif tag == 'TOWN' and text:
                if 'city' not in notice:
                    notice['city'] = to_ascii(text)

            # Authority name
            elif tag == 'OFFICIALNAME' and text:
                if 'authority' not in notice:
                    notice['authority'] = to_ascii(text)[:200]

            # Contact info
            elif tag == 'E_MAIL' and text:
                if 'email' not in notice:
                    notice['email'] = text.lower().strip()
            elif tag == 'PHONE' and text:
                if 'phone' not in notice:
                    notice['phone'] = re.sub(r'[^\d+]', '', text)
            elif tag == 'URL_GENERAL' and text:
                if 'website' not in notice:
                    notice['website'] = text.lower().strip()

            # Value
            elif tag in ['VAL_ESTIMATED_TOTAL', 'VAL_TOTAL', 'VALUE']:
                if text and 'value' not in notice:
                    try:
                        notice['value'] = float(text.replace(',', ''))
                        notice['currency'] = elem.get('CURRENCY', 'EUR')
                    except:
                        pass

            # CPV code
            elif tag == 'CPV_CODE':
                code = elem.get('CODE', text)
                if code and 'cpv' not in notice:
                    notice['cpv'] = code[:8]
                    notice['cpv_category'] = CPV_CATEGORIES.get(code[:2], 'Other')

            # Contract type
            elif tag == 'TYPE_CONTRACT':
                ctype = elem.get('CTYPE', text)
                if ctype:
                    notice['contract_type'] = ctype

            # Authority type
            elif tag == 'AA_AUTHORITY_TYPE':
                notice['authority_type'] = elem.get('CODE', text)

            # Address
            elif tag == 'ADDRESS' and text:
                if 'address' not in notice:
                    notice['address'] = to_ascii(text)

            # Postal code
            elif tag == 'POSTAL_CODE' and text:
                notice['postal_code'] = text

    except Exception as e:
        pass

    return notice


def iterate_ted_notices(year, month=None, limit=None):
    """Iterate through TED notices for a year/month."""
    if month:
        patterns = [f"ted_{year}_{month:02d}.xml.gz"]
    else:
        patterns = [f.name for f in sorted(RAW_DIR.glob(f"ted_{year}_*.xml.gz"))]

    count = 0

    for pattern in patterns:
        monthly_file = RAW_DIR / pattern
        if not monthly_file.exists():
            continue

        try:
            with tarfile.open(monthly_file, 'r:gz') as outer_tar:
                for member in outer_tar.getmembers():
                    if not member.name.endswith('.tar.gz'):
                        continue

                    daily_file = outer_tar.extractfile(member)
                    if not daily_file:
                        continue

                    try:
                        with tarfile.open(fileobj=daily_file, mode='r:gz') as daily_tar:
                            for xml_member in daily_tar.getmembers():
                                if xml_member.name.endswith('.xml'):
                                    xml_file = daily_tar.extractfile(xml_member)
                                    if xml_file:
                                        content = xml_file.read().decode('utf-8', errors='ignore')
                                        notice = parse_ted_xml_full(content)
                                        if notice:
                                            yield notice
                                            count += 1
                                            if limit and count >= limit:
                                                return
                    except:
                        continue
        except Exception as e:
            print(f"Error reading {monthly_file}: {e}")
            continue


def extract_contacts(year, output_file=None, country=None):
    """Extract all contacts (email, phone, website) from TED data."""
    print(f"\n=== Extracting contacts from TED {year} ===\n")

    contacts = []
    seen_emails = set()

    for notice in iterate_ted_notices(year):
        email = notice.get('email', '')

        if not email or email in seen_emails:
            continue

        if country and notice.get('country') != country.upper():
            continue

        seen_emails.add(email)

        contacts.append({
            'email': email,
            'authority': notice.get('authority', ''),
            'country': notice.get('country', ''),
            'city': notice.get('city', ''),
            'phone': notice.get('phone', ''),
            'website': notice.get('website', ''),
            'cpv_category': notice.get('cpv_category', ''),
            'address': notice.get('address', ''),
            'postal_code': notice.get('postal_code', ''),
        })

        if len(contacts) % 1000 == 0:
            print(f"\r  Extracted: {len(contacts):,} unique contacts", end="", flush=True)

    print(f"\r  Total: {len(contacts):,} unique contacts")

    # Save to CSV
    if not output_file:
        output_file = CSV_DIR / f"ted_contacts_{year}.csv"

    CSV_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = ['email', 'authority', 'country', 'city', 'phone', 'website',
                  'cpv_category', 'address', 'postal_code']

    with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(contacts)

    print(f"  Saved: {output_file}")

    # Stats
    by_country = Counter(c['country'] for c in contacts)
    print(f"\n  Top countries:")
    for country, cnt in by_country.most_common(10):
        print(f"    {country}: {cnt:,}")

    return contacts


def search_notices(year, keyword, country=None, limit=100):
    """Search notices by keyword."""
    print(f"\n=== Searching TED {year} for '{keyword}' ===\n")

    keyword_lower = keyword.lower()
    results = []

    for notice in iterate_ted_notices(year, limit=limit * 10):
        if country and notice.get('country') != country.upper():
            continue

        title = notice.get('title', '').lower()
        authority = notice.get('authority', '').lower()
        category = notice.get('cpv_category', '').lower()

        if keyword_lower in title or keyword_lower in authority or keyword_lower in category:
            results.append(notice)
            if len(results) >= limit:
                break

    print(f"  Found: {len(results)} notices\n")

    for n in results[:20]:
        print(f"  {n.get('country', '??')} | {n.get('authority', 'Unknown')[:40]}")
        print(f"       {n.get('title', 'No title')[:60]}")
        if n.get('email'):
            print(f"       Email: {n['email']}")
        if n.get('value'):
            print(f"       Value: {n['value']:,.0f} {n.get('currency', 'EUR')}")
        print()

    return results


def show_stats(year):
    """Show statistics for a year."""
    print(f"\n=== TED {year} Statistics ===\n")

    total = 0
    by_country = Counter()
    by_category = Counter()
    by_type = Counter()
    total_value = 0
    with_email = 0

    for notice in iterate_ted_notices(year):
        total += 1
        by_country[notice.get('country', '??')] += 1
        by_category[notice.get('cpv_category', 'Unknown')] += 1
        by_type[notice.get('contract_type', 'Unknown')] += 1

        if notice.get('value'):
            total_value += notice['value']
        if notice.get('email'):
            with_email += 1

        if total % 10000 == 0:
            print(f"\r  Processed: {total:,}", end="", flush=True)

    print(f"\r  Total notices: {total:,}")
    print(f"  With email: {with_email:,} ({with_email*100//total if total else 0}%)")
    print(f"  Total value: {total_value/1e9:.1f}B EUR")

    print(f"\n  Top countries:")
    for country, cnt in by_country.most_common(15):
        print(f"    {country}: {cnt:,}")

    print(f"\n  Top categories:")
    for cat, cnt in by_category.most_common(10):
        print(f"    {cat[:30]}: {cnt:,}")

    print(f"\n  Contract types:")
    for t, cnt in by_type.most_common(5):
        print(f"    {t}: {cnt:,}")


def top_buyers(year, limit=50, country=None):
    """List top buyers (authorities)."""
    print(f"\n=== Top Buyers in TED {year} ===\n")

    buyers = defaultdict(lambda: {'count': 0, 'value': 0, 'email': '', 'country': ''})

    for notice in iterate_ted_notices(year):
        if country and notice.get('country') != country.upper():
            continue

        authority = notice.get('authority', '')
        if not authority:
            continue

        key = authority.lower()[:50]
        buyers[key]['count'] += 1
        buyers[key]['value'] += notice.get('value', 0)
        buyers[key]['name'] = authority
        if notice.get('email'):
            buyers[key]['email'] = notice['email']
        buyers[key]['country'] = notice.get('country', '')

    # Sort by count
    top = sorted(buyers.items(), key=lambda x: x[1]['count'], reverse=True)[:limit]

    print(f"{'Authority':<40} | {'Country':<3} | {'Notices':>8} | {'Value (M EUR)':>12} | Email")
    print("-" * 100)

    for _, b in top:
        print(f"{b['name'][:40]:<40} | {b['country']:<3} | {b['count']:>8,} | {b['value']/1e6:>12,.0f} | {b['email'][:30]}")

    return top


def show_available():
    """Show available TED data."""
    print("\n=== Available TED Data ===\n")

    if RAW_DIR.exists():
        files = sorted(RAW_DIR.glob("*.gz"))
        print(f"Raw monthly files: {len(files)}")

        by_year = Counter()
        for f in files:
            match = re.search(r'ted_(\d{4})_', f.name)
            if match:
                by_year[match.group(1)] += 1

        print("\nBy year:")
        for year in sorted(by_year.keys()):
            print(f"  {year}: {by_year[year]} months")
    else:
        print("No raw files yet")


def main():
    parser = argparse.ArgumentParser(description="TED Data Explorer")
    parser.add_argument("--extract-contacts", "-e", type=int, metavar="YEAR", help="Extract contacts for year")
    parser.add_argument("--search", "-s", type=str, help="Search keyword")
    parser.add_argument("--stats", type=int, metavar="YEAR", help="Show statistics for year")
    parser.add_argument("--top-buyers", "-t", type=int, metavar="YEAR", help="List top buyers")
    parser.add_argument("--country", "-c", type=str, help="Filter by country code (DE, FR, etc)")
    parser.add_argument("--year", "-y", type=int, help="Year for search")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Result limit")
    parser.add_argument("--output", "-o", type=str, help="Output file")
    parser.add_argument("--available", "-a", action="store_true", help="Show available data")

    args = parser.parse_args()

    if args.available:
        show_available()
    elif args.extract_contacts:
        extract_contacts(args.extract_contacts, args.output, args.country)
    elif args.search:
        year = args.year or 2024
        search_notices(year, args.search, args.country, args.limit)
    elif args.stats:
        show_stats(args.stats)
    elif args.top_buyers:
        top_buyers(args.top_buyers, args.limit, args.country)
    else:
        show_available()
        print("\nUsage:")
        print("  --extract-contacts 2024     Extract all contacts for 2024")
        print("  --search 'construction'     Search notices")
        print("  --stats 2024                Show statistics")
        print("  --top-buyers 2024           List top buyers")
        print("  --country DE                Filter by country")


if __name__ == "__main__":
    main()


def parse_ted_xml_winners(xml_content):
    """Parse TED XML and extract contract WINNERS (contractors)."""
    winners = []

    try:
        root = ET.fromstring(xml_content)
        notice_id = root.get('DOC_ID', '')

        # Get authority info first
        authority = ''
        authority_country = ''
        cpv = ''
        contract_value = 0

        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            if tag == 'OFFICIALNAME' and not authority:
                authority = to_ascii(elem.text or '')
            elif tag == 'ISO_COUNTRY':
                if not authority_country:
                    authority_country = elem.get('VALUE', '')
            elif tag == 'CPV_CODE' and not cpv:
                cpv = elem.get('CODE', '')
            elif tag == 'VAL_TOTAL' and not contract_value:
                try:
                    contract_value = float((elem.text or '0').replace(',', ''))
                except:
                    pass

        # Now find contractors
        for contractor in root.iter():
            tag = contractor.tag.split('}')[-1] if '}' in contractor.tag else contractor.tag

            if tag == 'CONTRACTOR':
                winner = {
                    'notice_id': notice_id,
                    'authority': authority[:100],
                    'authority_country': authority_country,
                    'value': contract_value,
                    'cpv': cpv,
                }

                for child in contractor.iter():
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    text = child.text.strip() if child.text else ''

                    if ctag == 'OFFICIALNAME':
                        winner['contractor'] = to_ascii(text)[:200]
                    elif ctag == 'TOWN':
                        winner['contractor_city'] = to_ascii(text)
                    elif ctag == 'COUNTRY':
                        winner['contractor_country'] = child.get('VALUE', text)
                    elif ctag == 'URL':
                        winner['contractor_website'] = text[:200]
                    elif ctag == 'ADDRESS':
                        winner['contractor_address'] = to_ascii(text)[:200]
                    elif ctag == 'E_MAIL':
                        winner['contractor_email'] = text.lower()

                if winner.get('contractor'):
                    winners.append(winner)

    except:
        pass

    return winners


def extract_winners(year, output_file=None, country=None):
    """Extract all contract WINNERS from TED data."""
    print(f"\n=== Extracting WINNERS from TED {year} ===\n")

    winners = []
    seen = set()

    for notice in iterate_ted_notices(year):
        pass  # We need raw XML, not parsed notices

    # Re-iterate with raw XML
    if month := None:
        patterns = [f.name for f in sorted(RAW_DIR.glob(f"ted_{year}_*.xml.gz"))]
    else:
        patterns = [f.name for f in sorted(RAW_DIR.glob(f"ted_{year}_*.xml.gz"))]

    for pattern in patterns:
        monthly_file = RAW_DIR / pattern
        if not monthly_file.exists():
            continue

        try:
            with tarfile.open(monthly_file, 'r:gz') as outer_tar:
                for member in outer_tar.getmembers():
                    if not member.name.endswith('.tar.gz'):
                        continue

                    daily_file = outer_tar.extractfile(member)
                    if not daily_file:
                        continue

                    try:
                        with tarfile.open(fileobj=daily_file, mode='r:gz') as daily_tar:
                            for xml_member in daily_tar.getmembers():
                                if xml_member.name.endswith('.xml'):
                                    xml_file = daily_tar.extractfile(xml_member)
                                    if xml_file:
                                        content = xml_file.read().decode('utf-8', errors='ignore')
                                        for w in parse_ted_xml_winners(content):
                                            if country and w.get('contractor_country') != country.upper():
                                                continue

                                            key = (w.get('contractor', ''), w.get('notice_id', ''))
                                            if key not in seen:
                                                seen.add(key)
                                                winners.append(w)

                                                if len(winners) % 1000 == 0:
                                                    print(f"\r  Extracted: {len(winners):,} winners", end="", flush=True)
                    except:
                        continue
        except Exception as e:
            continue

    print(f"\r  Total winners: {len(winners):,}")

    # Save CSV
    if not output_file:
        output_file = CSV_DIR / f"ted_winners_{year}.csv"

    CSV_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = ['contractor', 'contractor_city', 'contractor_country', 'contractor_website',
                  'contractor_email', 'contractor_address', 'value', 'authority',
                  'authority_country', 'cpv', 'notice_id']

    with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(winners)

    print(f"  Saved: {output_file}")

    # Stats
    by_country = Counter(w.get('contractor_country', '??') for w in winners)
    print(f"\n  Top countries:")
    for c, cnt in by_country.most_common(10):
        print(f"    {c}: {cnt:,}")

    return winners
