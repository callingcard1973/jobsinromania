#!/usr/bin/env python3
"""
Afterschool Bucuresti - Data Collection and Management Skill

Collects contact data for afterschool programs in Bucharest for email outreach.

Sources:
- Google Maps (via SerpAPI)
- Firme.info (CAEN codes for education)
- ISMB (Inspectoratul Scolar Bucuresti)
- Manual CSV imports

Usage:
    python3 afterschool_bucuresti.py --scrape [--limit N]    # Scrape all sources
    python3 afterschool_bucuresti.py --scrape-maps           # Google Maps only
    python3 afterschool_bucuresti.py --scrape-firme          # Firme.info only
    python3 afterschool_bucuresti.py --import FILE           # Import CSV
    python3 afterschool_bucuresti.py --list                  # List all entries
    python3 afterschool_bucuresti.py --stats                 # Show statistics
    python3 afterschool_bucuresti.py --export [FILE]         # Export for campaigns
    python3 afterschool_bucuresti.py --enrich                # Fuzzy match enrichment
    python3 afterschool_bucuresti.py --dedup                 # Remove duplicates
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import re
import argparse
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

from skills_common import to_ascii, sanitize, fetch_url
from phone_utils import normalize_phone_ro, extract_phones_ro

# === CONSTANTS ===

DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EDUCATION/AFTERSCHOOL_BUCURESTI')
MASTER_FILE = DATA_DIR / 'afterschool_bucuresti.csv'
IMPORTS_DIR = DATA_DIR / 'imports'
LOGS_DIR = DATA_DIR / 'logs'

# CSV Schema
COLUMNS = ['id', 'name', 'type', 'address', 'sector', 'phone', 'email', 'website', 'source', 'scraped_date']

# Sectors in Bucharest
SECTORS = ['Sector 1', 'Sector 2', 'Sector 3', 'Sector 4', 'Sector 5', 'Sector 6']

# CAEN codes for education
EDUCATION_CAEN = [
    '8510',  # Invatamant prescolar
    '8520',  # Invatamant primar
    '8531',  # Invatamant secundar general
    '8559',  # Alte forme de invatamant n.c.a.
]

# Rate limiting
REQUEST_DELAY = 5  # seconds between requests


# === UTILITIES ===

def ensure_dirs():
    """Create necessary directories."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def generate_id(name: str, address: str) -> str:
    """Generate unique ID from name and address."""
    key = f"{to_ascii(name).lower()}_{to_ascii(address).lower()}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def detect_sector(address: str) -> str:
    """Extract sector from address string."""
    if not address:
        return ''
    address_lower = address.lower()
    for i in range(1, 7):
        patterns = [f'sector {i}', f'sectorul {i}', f's{i}', f'sect.{i}', f'sect {i}']
        for p in patterns:
            if p in address_lower:
                return f'Sector {i}'
    return ''


def extract_email(text: str) -> str:
    """Extract email from text."""
    if not text:
        return ''
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return match.group(0).lower() if match else ''


def extract_website(text: str) -> str:
    """Extract website URL from text."""
    if not text:
        return ''
    # Already a URL
    if text.startswith('http'):
        return text.split()[0]
    match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    if match:
        domain = match.group(1)
        if not domain.endswith(('.com', '.ro', '.eu', '.org', '.net', '.info')):
            return ''
        return f'https://{domain}'
    return ''


def load_master() -> List[Dict]:
    """Load master CSV file."""
    if not MASTER_FILE.exists():
        return []

    entries = []
    with open(MASTER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(row)
    return entries


def save_master(entries: List[Dict]):
    """Save entries to master CSV."""
    ensure_dirs()
    with open(MASTER_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for entry in entries:
            # Ensure all columns exist
            row = {col: entry.get(col, '') for col in COLUMNS}
            writer.writerow(row)


def normalize_entry(entry: Dict) -> Dict:
    """Normalize an entry to standard format."""
    normalized = {
        'id': entry.get('id', ''),
        'name': to_ascii(entry.get('name', '')).strip(),
        'type': entry.get('type', 'private'),
        'address': to_ascii(entry.get('address', '')).strip(),
        'sector': entry.get('sector', ''),
        'phone': '',
        'email': entry.get('email', '').lower().strip(),
        'website': entry.get('website', '').strip(),
        'source': entry.get('source', 'manual'),
        'scraped_date': entry.get('scraped_date', datetime.now().strftime('%Y-%m-%d')),
    }

    # Normalize phone
    phone = entry.get('phone', '')
    if phone:
        normalized_phone = normalize_phone_ro(phone)
        normalized['phone'] = normalized_phone or to_ascii(phone)

    # Auto-detect sector if missing
    if not normalized['sector']:
        normalized['sector'] = detect_sector(normalized['address'])

    # Generate ID if missing
    if not normalized['id']:
        normalized['id'] = generate_id(normalized['name'], normalized['address'])

    return normalized


# === SCRAPERS ===

def scrape_google_maps(limit: int = 100) -> List[Dict]:
    """
    Scrape afterschool data from Google Maps via SerpAPI.

    Requires SERPAPI_KEY in environment.
    """
    api_key = os.getenv('SERPAPI_KEY')
    if not api_key:
        print("  [WARN] SERPAPI_KEY not set, skipping Google Maps scraper")
        print("  Set it with: export SERPAPI_KEY=your_key")
        return []

    entries = []
    queries = [
        'afterschool bucuresti',
        'after school bucuresti',
        'after-school bucuresti',
    ]

    # Add sector-specific queries
    for sector in range(1, 7):
        queries.append(f'afterschool sector {sector} bucuresti')

    try:
        import requests
    except ImportError:
        print("  [ERROR] requests module not available")
        return []

    seen_ids = set()

    for query in queries:
        if len(entries) >= limit:
            break

        print(f"  Searching: {query}")

        try:
            params = {
                'engine': 'google_maps',
                'q': query,
                'type': 'search',
                'll': '@44.4268,26.1025,12z',  # Bucharest center
                'api_key': api_key,
            }

            response = requests.get('https://serpapi.com/search', params=params, timeout=30)
            data = response.json()

            results = data.get('local_results', [])
            print(f"    Found {len(results)} results")

            for result in results:
                if len(entries) >= limit:
                    break

                name = result.get('title', '')
                address = result.get('address', '')

                # Skip if already seen
                entry_id = generate_id(name, address)
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)

                # Extract phone from result
                phone = result.get('phone', '')

                # Extract website
                website = result.get('website', '')

                entry = normalize_entry({
                    'id': entry_id,
                    'name': name,
                    'type': 'private',
                    'address': address,
                    'phone': phone,
                    'website': website,
                    'source': 'google_maps',
                })

                entries.append(entry)

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"    [ERROR] {e}")
            continue

    return entries


def scrape_firme_info(limit: int = 100) -> List[Dict]:
    """
    Scrape education companies from firme.info.

    Searches for CAEN codes related to education in Bucharest.
    """
    entries = []
    seen_ids = set()

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("  [ERROR] requests or bs4 not available")
        return []

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }

    # Search URLs for education companies in Bucharest
    search_urls = [
        'https://www.firme.info/caen-8510-invatamant-prescolar/bucuresti/',
        'https://www.firme.info/caen-8520-invatamant-primar/bucuresti/',
        'https://www.firme.info/caen-8559-alte-forme-de-invatamant-n-c-a/bucuresti/',
    ]

    for url in search_urls:
        if len(entries) >= limit:
            break

        print(f"  Fetching: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find company listings
            company_links = soup.select('a[href*="/firme/"]')

            for link in company_links[:20]:  # Limit per page
                if len(entries) >= limit:
                    break

                name = link.get_text(strip=True)
                if not name or len(name) < 3:
                    continue

                # Skip if obviously not an afterschool
                name_lower = name.lower()
                if not any(kw in name_lower for kw in ['after', 'school', 'scoala', 'educatie', 'copii', 'kids']):
                    # Still include if it has education CAEN
                    pass

                entry_id = generate_id(name, 'bucuresti')
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)

                entry = normalize_entry({
                    'id': entry_id,
                    'name': name,
                    'type': 'private',
                    'address': 'Bucuresti',
                    'source': 'firme_info',
                })

                entries.append(entry)

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"    [ERROR] {e}")
            continue

    return entries


def scrape_listafirme(limit: int = 100) -> List[Dict]:
    """
    Scrape from listafirme.ro for afterschool/education businesses.
    """
    entries = []
    seen_ids = set()

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("  [ERROR] requests or bs4 not available")
        return []

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }

    search_terms = ['afterschool', 'after+school', 'educatie+copii']

    for term in search_terms:
        if len(entries) >= limit:
            break

        url = f'https://www.listafirme.ro/search.asp?what={term}&where=bucuresti'
        print(f"  Searching: {term}")

        try:
            response = requests.get(url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find company entries
            company_divs = soup.select('div.company-info, div.firma')

            for div in company_divs[:20]:
                if len(entries) >= limit:
                    break

                name_elem = div.select_one('h2, h3, .company-name')
                if not name_elem:
                    continue

                name = name_elem.get_text(strip=True)
                if not name:
                    continue

                entry_id = generate_id(name, 'bucuresti')
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)

                # Try to extract more details
                address = ''
                phone = ''
                addr_elem = div.select_one('.address, .adresa')
                if addr_elem:
                    address = addr_elem.get_text(strip=True)

                phone_elem = div.select_one('.phone, .telefon')
                if phone_elem:
                    phone = phone_elem.get_text(strip=True)

                entry = normalize_entry({
                    'id': entry_id,
                    'name': name,
                    'type': 'private',
                    'address': address or 'Bucuresti',
                    'phone': phone,
                    'source': 'listafirme',
                })

                entries.append(entry)

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"    [ERROR] {e}")
            continue

    return entries


# === IMPORT ===

def import_csv(filepath: str) -> List[Dict]:
    """
    Import afterschool data from external CSV.

    Flexible column mapping:
    - name/nume/denumire -> name
    - address/adresa -> address
    - phone/telefon -> phone
    - email/mail -> email
    - website/site/url -> website
    """
    entries = []

    column_map = {
        'name': ['name', 'nume', 'denumire', 'firma', 'afterschool'],
        'address': ['address', 'adresa', 'sediu', 'locatie'],
        'phone': ['phone', 'telefon', 'tel', 'mobil'],
        'email': ['email', 'mail', 'e-mail'],
        'website': ['website', 'site', 'url', 'web'],
        'type': ['type', 'tip', 'categorie'],
        'sector': ['sector', 'sectorul'],
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = [h.lower().strip() for h in reader.fieldnames]

            # Build mapping
            field_map = {}
            for target, sources in column_map.items():
                for source in sources:
                    if source in headers:
                        field_map[target] = reader.fieldnames[headers.index(source)]
                        break

            if 'name' not in field_map:
                print(f"  [ERROR] No name column found in {filepath}")
                return []

            # Read and normalize
            f.seek(0)
            reader = csv.DictReader(f)

            for row in reader:
                entry_data = {}
                for target, source in field_map.items():
                    entry_data[target] = row.get(source, '')

                if not entry_data.get('name'):
                    continue

                entry_data['source'] = f'import:{Path(filepath).name}'
                entry = normalize_entry(entry_data)
                entries.append(entry)

        # Copy imported file to imports dir
        import_path = IMPORTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(filepath).name}"
        import shutil
        shutil.copy2(filepath, import_path)
        print(f"  Imported file saved to: {import_path}")

    except Exception as e:
        print(f"  [ERROR] Failed to import {filepath}: {e}")

    return entries


# === DEDUPLICATION ===

def deduplicate(entries: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Remove duplicate entries based on name similarity and address.

    Returns: (deduplicated_entries, removed_count)
    """
    if not entries:
        return [], 0

    try:
        from rapidfuzz import fuzz
    except ImportError:
        # Simple dedup by ID
        seen = {}
        for e in entries:
            if e['id'] not in seen:
                seen[e['id']] = e
        return list(seen.values()), len(entries) - len(seen)

    # Group by normalized name prefix (first 10 chars)
    groups = {}
    for entry in entries:
        key = to_ascii(entry['name'])[:10].lower()
        if key not in groups:
            groups[key] = []
        groups[key].append(entry)

    unique = []
    removed = 0

    for key, group in groups.items():
        if len(group) == 1:
            unique.append(group[0])
            continue

        # Sort by completeness (more data = better)
        def completeness(e):
            score = 0
            if e.get('phone'): score += 2
            if e.get('email'): score += 2
            if e.get('website'): score += 1
            if e.get('address'): score += 1
            return score

        group.sort(key=completeness, reverse=True)

        kept = []
        for entry in group:
            is_dup = False
            for existing in kept:
                name_sim = fuzz.ratio(entry['name'].lower(), existing['name'].lower())
                if name_sim > 85:
                    # Merge data from duplicate into existing
                    if entry.get('phone') and not existing.get('phone'):
                        existing['phone'] = entry['phone']
                    if entry.get('email') and not existing.get('email'):
                        existing['email'] = entry['email']
                    if entry.get('website') and not existing.get('website'):
                        existing['website'] = entry['website']
                    is_dup = True
                    removed += 1
                    break

            if not is_dup:
                kept.append(entry)

        unique.extend(kept)

    return unique, removed


# === ENRICHMENT ===

def enrich_with_internal(entries: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Enrich entries using fuzzy matching against ANOFM/MASTER_ALL.

    Returns: (enriched_entries, matches_found)
    """
    try:
        from fuzzy_matcher import FuzzyMatcher
    except ImportError:
        print("  [WARN] fuzzy_matcher not available, skipping enrichment")
        return entries, 0

    # Source files to match against
    sources = [
        ('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_master.csv', 'company_name', 'email', 'phone'),
        ('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER_ALL.csv', 'company', 'email', 'phone'),
    ]

    matches = 0

    for source_path, name_col, email_col, phone_col in sources:
        if not Path(source_path).exists():
            continue

        print(f"  Matching against: {Path(source_path).name}")

        try:
            matcher = FuzzyMatcher()
            matcher.load_source(source_path, name_col=name_col,
                               email_col=email_col, phone_col=phone_col)

            for entry in entries:
                if entry.get('email') and entry.get('phone'):
                    continue  # Already complete

                match = matcher.find_match(entry['name'])
                if match:
                    if not entry.get('email') and match.get('email'):
                        entry['email'] = match['email']
                        matches += 1
                    if not entry.get('phone') and match.get('phone'):
                        phone = normalize_phone_ro(match['phone'])
                        if phone:
                            entry['phone'] = phone
                            matches += 1
        except Exception as e:
            print(f"    [ERROR] {e}")

    return entries, matches


# === COMMANDS ===

def cmd_scrape(args):
    """Run scrapers and collect data."""
    print("\n=== AFTERSCHOOL BUCURESTI - SCRAPING ===\n")

    existing = load_master()
    existing_ids = {e['id'] for e in existing}
    print(f"Existing entries: {len(existing)}")

    new_entries = []

    # Google Maps
    if not args.source or args.source == 'maps':
        print("\n[1/3] Google Maps scraper...")
        maps_entries = scrape_google_maps(limit=args.limit)
        for e in maps_entries:
            if e['id'] not in existing_ids:
                new_entries.append(e)
                existing_ids.add(e['id'])
        print(f"  Found {len(maps_entries)} entries, {len([e for e in maps_entries if e['id'] not in existing_ids])} new")

    # Firme.info
    if not args.source or args.source == 'firme':
        print("\n[2/3] Firme.info scraper...")
        firme_entries = scrape_firme_info(limit=args.limit)
        for e in firme_entries:
            if e['id'] not in existing_ids:
                new_entries.append(e)
                existing_ids.add(e['id'])
        print(f"  Found {len(firme_entries)} entries")

    # Listafirme
    if not args.source or args.source == 'listafirme':
        print("\n[3/3] Listafirme.ro scraper...")
        lista_entries = scrape_listafirme(limit=args.limit)
        for e in lista_entries:
            if e['id'] not in existing_ids:
                new_entries.append(e)
                existing_ids.add(e['id'])
        print(f"  Found {len(lista_entries)} entries")

    # Merge and save
    if new_entries:
        all_entries = existing + new_entries
        all_entries, removed = deduplicate(all_entries)
        save_master(all_entries)
        print(f"\n=== RESULT ===")
        print(f"New entries: {len(new_entries)}")
        print(f"Duplicates removed: {removed}")
        print(f"Total: {len(all_entries)}")
    else:
        print("\nNo new entries found")


def cmd_import(args):
    """Import CSV file."""
    print(f"\n=== IMPORTING: {args.file} ===\n")

    if not Path(args.file).exists():
        print(f"[ERROR] File not found: {args.file}")
        return

    imported = import_csv(args.file)
    print(f"Parsed {len(imported)} entries from file")

    if not imported:
        return

    existing = load_master()
    existing_ids = {e['id'] for e in existing}

    new_entries = [e for e in imported if e['id'] not in existing_ids]
    print(f"New entries: {len(new_entries)}")

    if new_entries:
        all_entries = existing + new_entries
        all_entries, removed = deduplicate(all_entries)
        save_master(all_entries)
        print(f"Saved {len(all_entries)} total entries")


def cmd_list(args):
    """List all entries."""
    entries = load_master()

    if not entries:
        print("No entries found")
        return

    # Filter by sector if specified
    if args.sector:
        entries = [e for e in entries if args.sector.lower() in e.get('sector', '').lower()]

    # Filter by type
    if args.type:
        entries = [e for e in entries if e.get('type', '') == args.type]

    print(f"\n=== AFTERSCHOOL LIST ({len(entries)} entries) ===\n")

    for i, e in enumerate(entries[:args.limit or 50], 1):
        print(f"{i}. {e['name'][:40]}")
        print(f"   Type: {e.get('type', '-')}, Sector: {e.get('sector', '-')}")
        print(f"   Phone: {e.get('phone', '-')}, Email: {e.get('email', '-')}")
        if e.get('website'):
            print(f"   Website: {e.get('website')}")
        print()


def cmd_stats(args):
    """Show statistics."""
    entries = load_master()

    print("\n=== AFTERSCHOOL BUCURESTI - STATISTICS ===\n")

    if not entries:
        print("No entries in database")
        print(f"Master file: {MASTER_FILE}")
        return

    print(f"Total entries: {len(entries)}")
    print()

    # By type
    types = Counter(e.get('type', 'unknown') for e in entries)
    print("By Type:")
    for t, count in types.most_common():
        print(f"  {t}: {count}")
    print()

    # By sector
    sectors = Counter(e.get('sector', 'Unknown') or 'Unknown' for e in entries)
    print("By Sector:")
    for s, count in sorted(sectors.items()):
        print(f"  {s}: {count}")
    print()

    # Data completeness
    with_phone = sum(1 for e in entries if e.get('phone'))
    with_email = sum(1 for e in entries if e.get('email'))
    with_website = sum(1 for e in entries if e.get('website'))

    print("Data Completeness:")
    print(f"  With phone: {with_phone} ({100*with_phone/len(entries):.1f}%)")
    print(f"  With email: {with_email} ({100*with_email/len(entries):.1f}%)")
    print(f"  With website: {with_website} ({100*with_website/len(entries):.1f}%)")
    print()

    # Campaign ready (has email)
    campaign_ready = [e for e in entries if e.get('email')]
    print(f"Campaign Ready (with email): {len(campaign_ready)}")

    # By source
    sources = Counter(e.get('source', 'unknown') for e in entries)
    print("\nBy Source:")
    for s, count in sources.most_common():
        print(f"  {s}: {count}")


def cmd_export(args):
    """Export for email campaigns."""
    entries = load_master()

    if not entries:
        print("No entries to export")
        return

    # Filter to entries with email
    if not args.all:
        entries = [e for e in entries if e.get('email')]

    if not entries:
        print("No entries with email addresses")
        return

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = DATA_DIR / f"export_{datetime.now().strftime('%Y%m%d')}.csv"

    # Campaign-compatible columns
    export_cols = ['email', 'name', 'phone', 'address', 'sector', 'website']

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=export_cols)
        writer.writeheader()

        for e in entries:
            row = {col: to_ascii(e.get(col, '')) for col in export_cols}
            writer.writerow(row)

    print(f"\n=== EXPORT COMPLETE ===")
    print(f"Exported {len(entries)} entries to: {output_path}")
    print(f"Columns: {', '.join(export_cols)}")


def cmd_enrich(args):
    """Enrich data with fuzzy matching."""
    print("\n=== ENRICHING DATA ===\n")

    entries = load_master()
    if not entries:
        print("No entries to enrich")
        return

    before_phone = sum(1 for e in entries if e.get('phone'))
    before_email = sum(1 for e in entries if e.get('email'))

    entries, matches = enrich_with_internal(entries)

    after_phone = sum(1 for e in entries if e.get('phone'))
    after_email = sum(1 for e in entries if e.get('email'))

    save_master(entries)

    print(f"\n=== ENRICHMENT RESULT ===")
    print(f"Phone: {before_phone} -> {after_phone} (+{after_phone - before_phone})")
    print(f"Email: {before_email} -> {after_email} (+{after_email - before_email})")


def cmd_dedup(args):
    """Remove duplicates."""
    print("\n=== DEDUPLICATING ===\n")

    entries = load_master()
    if not entries:
        print("No entries to deduplicate")
        return

    before = len(entries)
    entries, removed = deduplicate(entries)
    save_master(entries)

    print(f"Before: {before}")
    print(f"After: {len(entries)}")
    print(f"Removed: {removed} duplicates")


# === MAIN ===

def main():
    parser = argparse.ArgumentParser(
        description='Afterschool Bucuresti - Data Collection Skill',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --scrape              # Scrape all sources
  %(prog)s --scrape --source maps --limit 50
  %(prog)s --import data.csv     # Import CSV file
  %(prog)s --list --sector 1     # List entries from Sector 1
  %(prog)s --stats               # Show statistics
  %(prog)s --export              # Export for campaigns
  %(prog)s --enrich              # Fuzzy match enrichment
        """
    )

    parser.add_argument('--scrape', action='store_true', help='Run scrapers')
    parser.add_argument('--source', choices=['maps', 'firme', 'listafirme'], help='Scrape specific source')
    parser.add_argument('--import', dest='file', help='Import CSV file')
    parser.add_argument('--list', action='store_true', help='List all entries')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--export', action='store_true', help='Export for campaigns')
    parser.add_argument('--enrich', action='store_true', help='Fuzzy match enrichment')
    parser.add_argument('--dedup', action='store_true', help='Remove duplicates')

    # Filters
    parser.add_argument('--sector', help='Filter by sector (1-6)')
    parser.add_argument('--type', choices=['private', 'public'], help='Filter by type')
    parser.add_argument('--limit', type=int, default=100, help='Limit results')
    parser.add_argument('--output', '-o', help='Output file for export')
    parser.add_argument('--all', action='store_true', help='Export all, not just with email')

    args = parser.parse_args()

    ensure_dirs()

    if args.scrape:
        cmd_scrape(args)
    elif args.file:
        cmd_import(args)
    elif args.list:
        cmd_list(args)
    elif args.stats:
        cmd_stats(args)
    elif args.export:
        cmd_export(args)
    elif args.enrich:
        cmd_enrich(args)
    elif args.dedup:
        cmd_dedup(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
