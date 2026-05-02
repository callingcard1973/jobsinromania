#!/usr/bin/env python3
"""
Slovakia Company Connect - Slovak company data connector

Sources:
- Local scraped Slovak company data
- SK-NACE codes (Slovak NACE)
- Slovak business directories

Usage:
    python3 slovakia_connect.py --nace 5610          # Restaurants
    python3 slovakia_connect.py --sector horeca      # Predefined sector
    python3 slovakia_connect.py --all-sectors        # All sectors
    python3 slovakia_connect.py --list-sectors       # Show sectors
    python3 slovakia_connect.py --status             # Show status

SK-NACE = same codes as CAEN/PKD/CZ-NACE
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
DATA_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/SLOVAKIA")
EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/SK_NACE_EXPORTS")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.slovakia_state.json")

# SK-NACE Sectors
SK_NACE_SECTORS = {
    "horeca": {
        "codes": ["5510", "5520", "5530", "5590", "5610", "5621", "5629", "5630"],
        "desc": "Hotels, Restaurants, Catering",
        "keywords": ["hotel", "restauracia", "penzion", "kaviaren"]
    },
    "construction": {
        "codes": ["4110", "4120", "4211", "4221", "4291", "4311", "4312", "4321", "4322", "4329", "4331", "4391", "4399"],
        "desc": "Construction",
        "keywords": ["stavebnictvo", "stavba", "rekonstrukcia"]
    },
    "manufacturing": {
        "codes": ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"],
        "desc": "Manufacturing",
        "keywords": ["vyroba", "fabrika", "zavod"]
    },
    "transport": {
        "codes": ["4910", "4920", "4931", "4941", "4942", "5210", "5221", "5224", "5229"],
        "desc": "Transport & Logistics",
        "keywords": ["doprava", "logistika", "preprava", "sklad"]
    },
    "it_services": {
        "codes": ["6201", "6202", "6203", "6209", "6311", "6312"],
        "desc": "IT Services",
        "keywords": ["softver", "IT", "programovanie", "informatika"]
    },
    "recruitment": {
        "codes": ["7810", "7820", "7830"],
        "desc": "Recruitment Agencies",
        "keywords": ["agentura prace", "nabor", "HR", "zamestnanie"]
    },
    "agriculture": {
        "codes": ["0111", "0112", "0113", "0119", "0121", "0122", "0141", "0142", "0150"],
        "desc": "Agriculture",
        "keywords": ["polnohospodarstvo", "farma", "pestovanie"]
    },
    "retail": {
        "codes": ["4711", "4719", "4721", "4722", "4729", "4741", "4751", "4771", "4772", "4773", "4778", "4779"],
        "desc": "Retail",
        "keywords": ["obchod", "predaj", "maloobchod"]
    },
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_import": None, "sectors_imported": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def normalize_phone_sk(phone):
    """Normalize Slovak phone number."""
    if not phone:
        return ""
    digits = re.sub(r'[^\d+]', '', str(phone))
    if digits.startswith('421') and len(digits) >= 10:
        return '+' + digits
    if digits.startswith('+421'):
        return digits
    if len(digits) == 9 and digits[0] in '29':
        return '+421' + digits
    if len(digits) >= 9:
        return '+421' + digits[-9:]
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
    score = 0
    tags = []

    email = row.get('email', '')
    if email:
        score += 10
        domain = email.split('@')[1] if '@' in email else ''
        if domain and not any(x in domain for x in ['gmail.', 'yahoo.', 'azet.sk', 'post.sk', 'centrum.sk']):
            score += 15
            tags.append('corporate_email')

    if row.get('phone'):
        score += 10
        tags.append('phone')

    if row.get('website'):
        score += 10
        tags.append('website')

    if row.get('ico'):
        score += 10
        tags.append('ico')

    city = (row.get('city') or '').lower()
    major = ['bratislava', 'kosice', 'presov', 'zilina', 'banska bystrica', 'nitra', 'trnava', 'trencin']
    if any(c in city for c in major):
        score += 5
        tags.append('major_city')

    return score, ','.join(tags)


def load_local_data():
    """Load Slovak company data."""
    companies = []

    data_sources = [
        DATA_DIR / "slovakia_companies.csv",
        DATA_DIR / "firmy_sk.csv",
        Path("/opt/ACTIVE/OPENDATA/DATA/AGENCIES/BY_COUNTRY/slovakia_agencies.csv"),
        Path("/home/tudor/SCRAPER_DATA/SLOVAKIA/"),
    ]

    for source in data_sources:
        if source.is_file() and source.suffix == '.csv':
            log(f"Loading: {source}")
            try:
                with open(source, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        company = {
                            'company': row.get('company', row.get('name', row.get('firma', ''))),
                            'email': validate_email(row.get('email', '')),
                            'phone': normalize_phone_sk(row.get('phone', row.get('telefon', ''))),
                            'city': to_ascii(row.get('city', row.get('mesto', ''))),
                            'county': to_ascii(row.get('county', row.get('kraj', ''))),
                            'country': 'SK',
                            'website': row.get('website', ''),
                            'nace': row.get('nace', row.get('caen', '')),
                            'nace_description': row.get('nace_description', row.get('activity', '')),
                            'ico': row.get('ico', ''),
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
                                'phone': normalize_phone_sk(row.get('phone', '')),
                                'city': to_ascii(row.get('city', '')),
                                'country': 'SK',
                                'website': row.get('website', ''),
                                'nace': row.get('nace', ''),
                                'ico': row.get('ico', ''),
                                'source': csv_file.stem
                            }
                            if company['company'] and (company['email'] or company['phone']):
                                companies.append(company)
                except:
                    pass

    log(f"Loaded {len(companies)} companies")
    return companies


def filter_by_nace(companies, nace_codes):
    filtered = []
    for company in companies:
        nace = str(company.get('nace', '')).strip()
        if not nace:
            continue
        for code in nace_codes:
            if code.endswith('*'):
                if nace.startswith(code[:-1]):
                    filtered.append(company)
                    break
            else:
                if nace == code or nace.startswith(code):
                    filtered.append(company)
                    break
    return filtered


def deduplicate(companies):
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
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = EXPORT_DIR / f"slovakia_{sector_name}_with_email.csv"

    fieldnames = ['company', 'email', 'phone', 'city', 'county', 'country',
                  'website', 'nace', 'nace_description', 'ico', 'score', 'tags', 'source']

    for company in companies:
        score, tags = calculate_score(company)
        company['score'] = score
        company['tags'] = tags

    companies.sort(key=lambda x: x.get('score', 0), reverse=True)

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)

    log(f"Exported {len(companies)} to {output_file}")
    return output_file


def import_sector(sector_name):
    if sector_name not in SK_NACE_SECTORS:
        log(f"Unknown sector: {sector_name}")
        return None

    sector = SK_NACE_SECTORS[sector_name]
    log(f"=== Importing Slovakia {sector_name.upper()} ===")

    all_companies = load_local_data()
    filtered = filter_by_nace(all_companies, sector['codes'])
    log(f"Filtered by NACE: {len(filtered)}")

    unique = deduplicate(filtered)
    log(f"After dedup: {len(unique)}")

    if unique:
        return export_sector(sector_name, unique)
    return None


def show_status():
    state = load_state()
    print("\n=== Slovakia Connect Status ===\n")
    print(f"Last import: {state.get('last_import', 'Never')}")

    print("\nAvailable sectors:")
    for name, sector in SK_NACE_SECTORS.items():
        print(f"  {name}: {sector['desc']}")

    print("\nExported files:")
    if EXPORT_DIR.exists():
        for f in sorted(EXPORT_DIR.glob("slovakia_*_with_email.csv")):
            with open(f) as fh:
                rows = sum(1 for _ in fh) - 1
            print(f"  {f.name}: {rows} rows")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Slovakia Connect")
    parser.add_argument("--nace", help="NACE code(s)")
    parser.add_argument("--sector", help="Sector name")
    parser.add_argument("--all-sectors", action="store_true")
    parser.add_argument("--list-sectors", action="store_true")
    parser.add_argument("--status", action="store_true")

    args = parser.parse_args()

    if args.list_sectors:
        print("\n=== Slovakia SK-NACE Sectors ===\n")
        for name, sector in SK_NACE_SECTORS.items():
            print(f"{name}: {sector['desc']}")
        return

    if args.status:
        show_status()
        return

    state = load_state()

    if args.all_sectors:
        for sector_name in SK_NACE_SECTORS:
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
