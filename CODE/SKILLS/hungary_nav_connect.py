#!/usr/bin/env python3
"""
Hungary NAV Connect - Hungarian company data connector

Connects to Hungarian data sources:
- NAV (Tax Authority) public data
- Local scraped Hungarian company data
- TEÁOR codes (Hungarian NACE)

Usage:
    python3 hungary_nav_connect.py --teaor 5610              # Restaurants
    python3 hungary_nav_connect.py --sector horeca           # Predefined sector
    python3 hungary_nav_connect.py --all-sectors             # All sectors
    python3 hungary_nav_connect.py --search "hotel budapest" # Search
    python3 hungary_nav_connect.py --list-sectors            # Show sectors
    python3 hungary_nav_connect.py --status                  # Show status

TEÁOR = Hungarian NACE = same codes as CAEN/PKD/CZ-NACE
"""

import os
import sys
import csv
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        import unicodedata
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

# Paths
DATA_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/HUNGARY")
EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/TEAOR_EXPORTS")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.hungary_nav_state.json")

# TEÁOR Sectors (same as NACE)
TEAOR_SECTORS = {
    "horeca": {
        "codes": ["5510", "5520", "5530", "5590", "5610", "5621", "5629", "5630"],
        "desc": "Hotels, Restaurants, Catering",
        "keywords": ["hotel", "etterem", "szalloda", "vendeglo", "kavehaz"]
    },
    "construction": {
        "codes": ["4110", "4120", "4211", "4212", "4221", "4291", "4311", "4312", "4321", "4322", "4329", "4331", "4332", "4391", "4399"],
        "desc": "Construction & Building",
        "keywords": ["epites", "epitoipar", "felujitas", "beruhazo"]
    },
    "manufacturing": {
        "codes": ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"],
        "desc": "Manufacturing",
        "keywords": ["gyartas", "gyar", "uzem", "termeles"]
    },
    "transport": {
        "codes": ["4910", "4920", "4931", "4932", "4941", "4942", "5210", "5221", "5222", "5224", "5229"],
        "desc": "Transport & Logistics",
        "keywords": ["szallitas", "logisztika", "fuvarozas", "raktar"]
    },
    "it_services": {
        "codes": ["6201", "6202", "6203", "6209", "6311", "6312"],
        "desc": "IT Services",
        "keywords": ["szoftver", "informatika", "IT", "programozas"]
    },
    "recruitment": {
        "codes": ["7810", "7820", "7830"],
        "desc": "Recruitment Agencies",
        "keywords": ["munkaero", "toborzas", "HR", "allaskozvetites"]
    },
    "agriculture": {
        "codes": ["0111", "0112", "0113", "0119", "0121", "0122", "0125", "0141", "0142", "0150"],
        "desc": "Agriculture",
        "keywords": ["mezogazdasag", "gazdasag", "termesztes", "allattenyesztes"]
    },
    "retail": {
        "codes": ["4711", "4719", "4721", "4722", "4729", "4741", "4751", "4759", "4771", "4772", "4773", "4774", "4775", "4778", "4779"],
        "desc": "Retail",
        "keywords": ["kiskereskedelem", "bolt", "uzlet", "aruhaz"]
    },
    "wholesale": {
        "codes": ["4611", "4612", "4619", "4621", "4622", "4631", "4632", "4639", "4641", "4645", "4649", "4690"],
        "desc": "Wholesale",
        "keywords": ["nagykereskedelem", "disztributor", "forgalmazo"]
    },
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_import": None, "sectors_imported": {}, "total_companies": 0}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def normalize_phone_hu(phone):
    """Normalize Hungarian phone number."""
    if not phone:
        return ""
    digits = re.sub(r'[^\d+]', '', str(phone))
    if digits.startswith('36') and len(digits) >= 10:
        return '+' + digits
    if digits.startswith('+36'):
        return digits
    if len(digits) == 9 and digits[0] in '123456789':
        return '+36' + digits
    if len(digits) >= 9:
        return '+36' + digits[-9:]
    return ""


def validate_email(email):
    if not email:
        return None
    email = email.lower().strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        if any(x in email for x in ['example.', 'test.', 'noreply']):
            return None
        return email
    return None


def calculate_score(row):
    """Calculate lead score."""
    score = 0
    tags = []

    email = row.get('email', '')
    if email:
        score += 10
        domain = email.split('@')[1] if '@' in email else ''
        if domain and not any(x in domain for x in ['gmail.', 'yahoo.', 'freemail.hu', 'citromail.hu', 'indamail.hu']):
            score += 15
            tags.append('corporate_email')

    if row.get('phone'):
        score += 10
        tags.append('phone')

    if row.get('website'):
        score += 10
        tags.append('website')

    if row.get('adoszam'):
        score += 10
        tags.append('adoszam')

    city = (row.get('city') or '').lower()
    major = ['budapest', 'debrecen', 'szeged', 'miskolc', 'pecs', 'gyor', 'nyiregyhaza', 'kecskemet']
    if any(c in city for c in major):
        score += 5
        tags.append('major_city')

    return score, ','.join(tags)


def load_local_data():
    """Load locally scraped Hungarian company data."""
    companies = []

    data_sources = [
        DATA_DIR / "hungary_companies.csv",
        DATA_DIR / "cegek_hu.csv",
        Path("/opt/ACTIVE/OPENDATA/DATA/AGENCIES/BY_COUNTRY/hungary_agencies.csv"),
        Path("/home/tudor/SCRAPER_DATA/HUNGARY/"),
    ]

    for source in data_sources:
        if source.is_file() and source.suffix == '.csv':
            log(f"Loading: {source}")
            try:
                with open(source, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        company = {
                            'company': row.get('company', row.get('name', row.get('cegnev', ''))),
                            'email': validate_email(row.get('email', '')),
                            'phone': normalize_phone_hu(row.get('phone', row.get('telefon', ''))),
                            'city': to_ascii(row.get('city', row.get('varos', ''))),
                            'county': to_ascii(row.get('county', row.get('megye', ''))),
                            'country': 'HU',
                            'website': row.get('website', row.get('honlap', '')),
                            'teaor': row.get('teaor', row.get('caen', row.get('nace', ''))),
                            'teaor_description': row.get('teaor_description', row.get('activity', '')),
                            'adoszam': row.get('adoszam', row.get('tax_id', '')),
                            'source': source.stem
                        }
                        if company['company'] and (company['email'] or company['phone']):
                            companies.append(company)
            except Exception as e:
                log(f"  Error: {e}")
        elif source.is_dir():
            for csv_file in source.glob("*.csv"):
                try:
                    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            company = {
                                'company': row.get('company', row.get('name', '')),
                                'email': validate_email(row.get('email', '')),
                                'phone': normalize_phone_hu(row.get('phone', '')),
                                'city': to_ascii(row.get('city', '')),
                                'county': to_ascii(row.get('county', '')),
                                'country': 'HU',
                                'website': row.get('website', ''),
                                'teaor': row.get('teaor', ''),
                                'adoszam': row.get('adoszam', ''),
                                'source': csv_file.stem
                            }
                            if company['company'] and (company['email'] or company['phone']):
                                companies.append(company)
                except:
                    pass

    log(f"Loaded {len(companies)} companies from local sources")
    return companies


def filter_by_teaor(companies, teaor_codes):
    """Filter companies by TEÁOR codes."""
    filtered = []
    for company in companies:
        teaor = str(company.get('teaor', '')).strip()
        if not teaor:
            continue
        for code in teaor_codes:
            if code.endswith('*'):
                if teaor.startswith(code[:-1]):
                    filtered.append(company)
                    break
            else:
                if teaor == code or teaor.startswith(code):
                    filtered.append(company)
                    break
    return filtered


def deduplicate(companies):
    """Deduplicate companies."""
    seen_emails = set()
    seen_names = set()
    unique = []

    for company in companies:
        email = company.get('email', '').lower()
        name_hash = hashlib.md5(to_ascii(company.get('company', '')).upper().encode()).hexdigest()[:12]

        if email and email in seen_emails:
            continue
        if name_hash in seen_names:
            continue

        if email:
            seen_emails.add(email)
        seen_names.add(name_hash)
        unique.append(company)

    return unique


def export_sector(sector_name, companies):
    """Export sector to CSV."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = EXPORT_DIR / f"hungary_{sector_name}_with_email.csv"

    fieldnames = ['company', 'email', 'phone', 'city', 'county', 'country',
                  'website', 'teaor', 'teaor_description', 'adoszam', 'score', 'tags', 'source']

    for company in companies:
        score, tags = calculate_score(company)
        company['score'] = score
        company['tags'] = tags

    companies.sort(key=lambda x: x.get('score', 0), reverse=True)

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)

    log(f"Exported {len(companies)} companies to {output_file}")
    return output_file


def import_sector(sector_name):
    """Import a predefined sector."""
    if sector_name not in TEAOR_SECTORS:
        log(f"Unknown sector: {sector_name}")
        return None

    sector = TEAOR_SECTORS[sector_name]
    log(f"=== Importing Hungary {sector_name.upper()} ===")

    all_companies = load_local_data()
    filtered = filter_by_teaor(all_companies, sector['codes'])
    log(f"Filtered by TEÁOR: {len(filtered)}")

    unique = deduplicate(filtered)
    log(f"After dedup: {len(unique)}")

    if unique:
        return export_sector(sector_name, unique)
    return None


def show_status():
    """Show connector status."""
    state = load_state()

    print("\n=== Hungary NAV Connector Status ===\n")
    print(f"Last import: {state.get('last_import', 'Never')}")

    print("\nAvailable sectors:")
    for name, sector in TEAOR_SECTORS.items():
        print(f"  {name}: {sector['desc']}")

    print("\nExported files:")
    if EXPORT_DIR.exists():
        for f in sorted(EXPORT_DIR.glob("hungary_*_with_email.csv")):
            with open(f) as fh:
                rows = sum(1 for _ in fh) - 1
            print(f"  {f.name}: {rows} rows")


def list_sectors():
    print("\n=== Hungary TEÁOR Sectors ===\n")
    for name, sector in TEAOR_SECTORS.items():
        print(f"{name}:")
        print(f"  Description: {sector['desc']}")
        print(f"  TEÁOR codes: {', '.join(sector['codes'][:5])}...")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hungary NAV Connect")
    parser.add_argument("--teaor", help="TEÁOR code(s) to import")
    parser.add_argument("--sector", help="Import predefined sector")
    parser.add_argument("--all-sectors", action="store_true", help="Import all sectors")
    parser.add_argument("--list-sectors", action="store_true", help="List sectors")
    parser.add_argument("--status", action="store_true", help="Show status")

    args = parser.parse_args()

    if args.list_sectors:
        list_sectors()
        return

    if args.status:
        show_status()
        return

    state = load_state()

    if args.all_sectors:
        for sector_name in TEAOR_SECTORS:
            import_sector(sector_name)
            state['sectors_imported'][sector_name] = datetime.now().isoformat()
    elif args.sector:
        import_sector(args.sector)
        state['sectors_imported'][args.sector] = datetime.now().isoformat()
    else:
        parser.print_help()
        return

    state['last_import'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
