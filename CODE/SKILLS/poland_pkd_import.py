#!/usr/bin/env python3
"""
Poland PKD Company Import Skill

Imports Polish company data by PKD codes (Polish NACE equivalent).
Sources: GUS, CEIDG, KRS, local scraped data.

Usage:
    python3 poland_pkd_import.py --pkd 5610              # Restaurants
    python3 poland_pkd_import.py --pkd "55*"             # Hotels (wildcard)
    python3 poland_pkd_import.py --pkd 5510,5520,5610    # Multiple
    python3 poland_pkd_import.py --sector horeca         # Predefined sector
    python3 poland_pkd_import.py --list-sectors          # Show sectors
    python3 poland_pkd_import.py --status                # Show import status
    python3 poland_pkd_import.py --enrich                # Enrich with LLM

PKD to CAEN mapping: PKD codes = NACE Rev. 2 = same as Romanian CAEN
"""

import os
import sys
import csv
import json
import re
import time
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii, fetch_url, get_http_client
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        import unicodedata
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

    def fetch_url(url, headers=None):
        import requests
        resp = requests.get(url, headers=headers or {}, timeout=30)
        return resp.text if resp.status_code == 200 else None

# Paths
DATA_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/POLAND")
EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/PKD_EXPORTS")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.poland_pkd_state.json")
LLM_URL = "http://localhost:1234/v1/chat/completions"

# PKD Sector definitions (same as NACE/CAEN)
PKD_SECTORS = {
    "horeca": {
        "codes": ["5510", "5520", "5530", "5590", "5610", "5621", "5629", "5630"],
        "desc": "Hotels, Restaurants, Catering",
        "keywords": ["hotel", "restauracja", "bar", "kawiarnia", "catering", "pensjonat"]
    },
    "construction": {
        "codes": ["4110", "4120", "4211", "4212", "4213", "4221", "4222", "4291", "4299",
                  "4311", "4312", "4313", "4321", "4322", "4329", "4331", "4332", "4333", "4334", "4339", "4391", "4399"],
        "desc": "Construction & Building",
        "keywords": ["budowa", "konstrukcja", "remont", "budownictwo", "developer"]
    },
    "manufacturing": {
        "codes": ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"],
        "desc": "Manufacturing & Production",
        "keywords": ["produkcja", "fabryka", "zaklad", "wyrob"]
    },
    "transport": {
        "codes": ["4910", "4920", "4931", "4932", "4939", "4941", "4942", "5010", "5020", "5110", "5121", "5122",
                  "5210", "5221", "5222", "5223", "5224", "5229"],
        "desc": "Transport & Logistics",
        "keywords": ["transport", "logistyka", "spedycja", "przewoz", "magazyn"]
    },
    "it_services": {
        "codes": ["6201", "6202", "6203", "6209", "6311", "6312"],
        "desc": "IT & Software Services",
        "keywords": ["software", "IT", "programowanie", "informatyka", "technologia"]
    },
    "call_centers": {
        "codes": ["8220"],
        "desc": "Call Centers & BPO",
        "keywords": ["call center", "BPO", "outsourcing", "telemarketing"]
    },
    "recruitment": {
        "codes": ["7810", "7820", "7830"],
        "desc": "Recruitment & HR Agencies",
        "keywords": ["rekrutacja", "agencja pracy", "HR", "kadry", "zatrudnienie"]
    },
    "agriculture": {
        "codes": ["0111", "0112", "0113", "0114", "0115", "0116", "0119", "0121", "0122", "0123", "0124", "0125", "0126", "0127", "0128", "0129",
                  "0141", "0142", "0143", "0144", "0145", "0146", "0147", "0149", "0150", "0161", "0162", "0163", "0164", "0170"],
        "desc": "Agriculture & Farming",
        "keywords": ["rolnictwo", "gospodarstwo", "uprawa", "hodowla", "farma"]
    },
    "retail": {
        "codes": ["4711", "4719", "4721", "4722", "4723", "4724", "4725", "4726", "4729",
                  "4741", "4742", "4743", "4751", "4752", "4753", "4754", "4759",
                  "4761", "4762", "4763", "4764", "4765", "4771", "4772", "4773", "4774", "4775", "4776", "4777", "4778", "4779",
                  "4781", "4782", "4789", "4791", "4799"],
        "desc": "Retail Trade",
        "keywords": ["sklep", "handel", "sprzedaz", "detaliczny"]
    },
    "wholesale": {
        "codes": ["4611", "4612", "4613", "4614", "4615", "4616", "4617", "4618", "4619",
                  "4621", "4622", "4623", "4624", "4631", "4632", "4633", "4634", "4635", "4636", "4637", "4638", "4639",
                  "4641", "4642", "4643", "4644", "4645", "4646", "4647", "4648", "4649",
                  "4651", "4652", "4661", "4662", "4663", "4664", "4665", "4666", "4669",
                  "4671", "4672", "4673", "4674", "4675", "4676", "4677", "4690"],
        "desc": "Wholesale Trade",
        "keywords": ["hurt", "hurtownia", "dystrybucja", "dystrybutor"]
    },
}

# Polish voivodeships (regions)
VOIVODESHIPS = {
    "dolnoslaskie": "Lower Silesia",
    "kujawsko-pomorskie": "Kuyavia-Pomerania",
    "lubelskie": "Lublin",
    "lubuskie": "Lubusz",
    "lodzkie": "Lodz",
    "malopolskie": "Lesser Poland",
    "mazowieckie": "Masovia",
    "opolskie": "Opole",
    "podkarpackie": "Subcarpathia",
    "podlaskie": "Podlaskie",
    "pomorskie": "Pomerania",
    "slaskie": "Silesia",
    "swietokrzyskie": "Holy Cross",
    "warminsko-mazurskie": "Warmia-Masuria",
    "wielkopolskie": "Greater Poland",
    "zachodniopomorskie": "West Pomerania",
}


def log(msg):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    """Load import state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "last_import": None,
        "sectors_imported": {},
        "total_companies": 0
    }


def save_state(state):
    """Save import state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def normalize_company_name(name):
    """Normalize Polish company name."""
    if not name:
        return ""
    name = to_ascii(name.upper())
    # Remove common suffixes
    for suffix in [' SP. Z O.O.', ' SP.Z O.O.', ' SPZOO', ' SP Z O O', ' S.A.', ' SA',
                   ' SP. J.', ' SP.J.', ' S.C.', ' SC', ' SP. K.', ' SP.K.']:
        name = name.replace(suffix, '')
    return name.strip()


def normalize_phone_pl(phone):
    """Normalize Polish phone number."""
    if not phone:
        return ""
    # Remove non-digits
    digits = re.sub(r'[^\d+]', '', str(phone))
    # Handle Polish format
    if digits.startswith('48') and len(digits) >= 11:
        return '+' + digits
    if digits.startswith('+48'):
        return digits
    if len(digits) == 9 and digits[0] in '456789':
        return '+48' + digits
    if len(digits) >= 9:
        return '+48' + digits[-9:]
    return ""


def validate_email(email):
    """Validate email format."""
    if not email:
        return None
    email = email.lower().strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        # Skip common invalid patterns
        if any(x in email for x in ['example.', 'test.', 'noreply', '@localhost']):
            return None
        return email
    return None


def calculate_score(row):
    """Calculate lead score for Polish company."""
    score = 0
    tags = []

    # Has email
    email = row.get('email', '')
    if email:
        score += 10
        domain = email.split('@')[1] if '@' in email else ''
        if domain and not any(x in domain for x in ['gmail.', 'yahoo.', 'wp.pl', 'onet.pl', 'o2.pl', 'interia.pl']):
            score += 15
            tags.append('corporate_email')

    # Has phone
    if row.get('phone'):
        score += 10
        tags.append('phone')

    # Has website
    if row.get('website'):
        score += 10
        tags.append('website')

    # Has NIP (Polish tax ID)
    if row.get('nip') or row.get('cui'):
        score += 10
        tags.append('nip')

    # Major city
    city = (row.get('city') or '').lower()
    major = ['warszawa', 'krakow', 'lodz', 'wroclaw', 'poznan', 'gdansk', 'szczecin', 'bydgoszcz', 'lublin', 'katowice']
    if any(c in city for c in major):
        score += 5
        tags.append('major_city')

    return score, ','.join(tags)


def load_local_poland_data():
    """Load locally scraped Polish company data."""
    companies = []

    # Check for local Polish data files
    data_sources = [
        DATA_DIR / "poland_companies.csv",
        DATA_DIR / "firmy_pl.csv",
        Path("/opt/ACTIVE/OPENDATA/DATA/AGENCIES/BY_COUNTRY/poland_agencies.csv"),
        Path("/home/tudor/SCRAPER_DATA/POLAND/"),
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
                            'phone': normalize_phone_pl(row.get('phone', row.get('telefon', ''))),
                            'city': to_ascii(row.get('city', row.get('miasto', ''))),
                            'county': to_ascii(row.get('county', row.get('powiat', row.get('voivodeship', '')))),
                            'country': 'PL',
                            'website': row.get('website', row.get('www', '')),
                            'pkd': row.get('pkd', row.get('caen', row.get('nace', ''))),
                            'pkd_description': row.get('pkd_description', row.get('activity', '')),
                            'nip': row.get('nip', row.get('cui', '')),
                            'source': source.stem
                        }
                        if company['company'] and (company['email'] or company['phone']):
                            companies.append(company)
            except Exception as e:
                log(f"  Error loading {source}: {e}")
        elif source.is_dir():
            for csv_file in source.glob("*.csv"):
                log(f"Loading: {csv_file}")
                try:
                    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            company = {
                                'company': row.get('company', row.get('name', row.get('firma', ''))),
                                'email': validate_email(row.get('email', '')),
                                'phone': normalize_phone_pl(row.get('phone', row.get('telefon', ''))),
                                'city': to_ascii(row.get('city', row.get('miasto', ''))),
                                'county': to_ascii(row.get('county', row.get('powiat', ''))),
                                'country': 'PL',
                                'website': row.get('website', row.get('www', '')),
                                'pkd': row.get('pkd', row.get('caen', '')),
                                'pkd_description': row.get('pkd_description', ''),
                                'nip': row.get('nip', ''),
                                'source': csv_file.stem
                            }
                            if company['company'] and (company['email'] or company['phone']):
                                companies.append(company)
                except Exception as e:
                    log(f"  Error: {e}")

    log(f"Loaded {len(companies)} companies from local sources")
    return companies


def filter_by_pkd(companies, pkd_codes):
    """Filter companies by PKD codes."""
    filtered = []

    for company in companies:
        pkd = str(company.get('pkd', '')).strip()
        if not pkd:
            continue

        for code in pkd_codes:
            if code.endswith('*'):
                # Wildcard match
                prefix = code[:-1]
                if pkd.startswith(prefix):
                    filtered.append(company)
                    break
            else:
                # Exact match
                if pkd == code or pkd.startswith(code):
                    filtered.append(company)
                    break

    return filtered


def filter_by_keywords(companies, keywords):
    """Filter companies by keywords in name/activity."""
    if not keywords:
        return companies

    filtered = []
    for company in companies:
        name = (company.get('company', '') + ' ' + company.get('pkd_description', '')).lower()
        if any(kw.lower() in name for kw in keywords):
            filtered.append(company)

    return filtered


def deduplicate(companies):
    """Deduplicate by email and normalized name."""
    seen_emails = set()
    seen_names = set()
    unique = []

    for company in companies:
        email = company.get('email', '').lower()
        name_hash = hashlib.md5(normalize_company_name(company.get('company', '')).encode()).hexdigest()[:12]

        if email and email in seen_emails:
            continue
        if name_hash in seen_names:
            continue

        if email:
            seen_emails.add(email)
        seen_names.add(name_hash)
        unique.append(company)

    return unique


def export_sector(sector_name, companies, with_score=True):
    """Export sector to CSV."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = EXPORT_DIR / f"poland_{sector_name}_with_email.csv"

    fieldnames = [
        'company', 'email', 'phone', 'city', 'county', 'country',
        'website', 'pkd', 'pkd_description', 'nip', 'score', 'tags', 'source'
    ]

    # Add scores
    for company in companies:
        score, tags = calculate_score(company)
        company['score'] = score
        company['tags'] = tags

    # Sort by score
    companies.sort(key=lambda x: x.get('score', 0), reverse=True)

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)

    log(f"Exported {len(companies)} companies to {output_file}")
    return output_file


def enrich_with_llm(companies, limit=50):
    """Enrich companies using local LLM."""
    import requests

    enriched = 0

    for company in companies[:limit]:
        if company.get('pkd_description'):
            continue

        pkd = company.get('pkd', '')
        name = company.get('company', '')

        if not pkd and not name:
            continue

        prompt = f"""Given this Polish company:
Name: {name}
PKD code: {pkd}

Provide a brief English description of their likely business activity (max 10 words).
Only output the description, nothing else."""

        try:
            response = requests.post(
                LLM_URL,
                json={
                    "model": "llama-3.2-3b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.3
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                desc = result['choices'][0]['message']['content'].strip()
                company['pkd_description'] = to_ascii(desc)[:100]
                enriched += 1

        except Exception as e:
            pass

        time.sleep(0.2)

    log(f"Enriched {enriched} companies with LLM")
    return companies


def import_sector(sector_name, enrich=False):
    """Import a predefined sector."""
    if sector_name not in PKD_SECTORS:
        log(f"Unknown sector: {sector_name}")
        return None

    sector = PKD_SECTORS[sector_name]
    log(f"=== Importing Poland {sector_name.upper()} ===")
    log(f"PKD codes: {', '.join(sector['codes'][:5])}...")

    # Load all local data
    all_companies = load_local_poland_data()

    # Filter by PKD codes
    filtered = filter_by_pkd(all_companies, sector['codes'])
    log(f"Filtered by PKD: {len(filtered)}")

    # Also filter by keywords if not enough
    if len(filtered) < 50:
        keyword_filtered = filter_by_keywords(all_companies, sector['keywords'])
        filtered.extend(keyword_filtered)
        log(f"Added keyword matches: {len(keyword_filtered)}")

    # Deduplicate
    unique = deduplicate(filtered)
    log(f"After dedup: {len(unique)}")

    # Enrich with LLM if requested
    if enrich:
        unique = enrich_with_llm(unique)

    # Export
    if unique:
        output_file = export_sector(sector_name, unique)
        return output_file

    return None


def import_by_pkd(pkd_codes, output_name=None, enrich=False):
    """Import by specific PKD codes."""
    log(f"=== Importing Poland PKD: {pkd_codes} ===")

    # Parse codes
    if isinstance(pkd_codes, str):
        codes = [c.strip() for c in pkd_codes.split(',')]
    else:
        codes = pkd_codes

    # Load all local data
    all_companies = load_local_poland_data()

    # Filter by PKD codes
    filtered = filter_by_pkd(all_companies, codes)
    log(f"Filtered by PKD: {len(filtered)}")

    # Deduplicate
    unique = deduplicate(filtered)
    log(f"After dedup: {len(unique)}")

    # Enrich with LLM if requested
    if enrich:
        unique = enrich_with_llm(unique)

    # Export
    if unique:
        name = output_name or f"pkd_{'_'.join(codes[:3])}"
        output_file = export_sector(name, unique)
        return output_file

    return None


def show_status():
    """Show import status."""
    state = load_state()

    print("\n=== Poland PKD Import Status ===\n")
    print(f"Last import: {state.get('last_import', 'Never')}")
    print(f"Total companies tracked: {state.get('total_companies', 0)}")

    print("\nAvailable sectors:")
    for name, sector in PKD_SECTORS.items():
        print(f"  {name}: {sector['desc']} ({len(sector['codes'])} codes)")

    print("\nExported files:")
    if EXPORT_DIR.exists():
        for f in sorted(EXPORT_DIR.glob("poland_*_with_email.csv")):
            with open(f) as fh:
                rows = sum(1 for _ in fh) - 1
            print(f"  {f.name}: {rows} rows")

    print("\nLocal data sources:")
    for source in [DATA_DIR, Path("/home/tudor/SCRAPER_DATA/POLAND/")]:
        if source.exists():
            if source.is_dir():
                csv_count = len(list(source.glob("*.csv")))
                print(f"  {source}: {csv_count} CSV files")
            else:
                print(f"  {source}: exists")


def list_sectors():
    """List available sectors."""
    print("\n=== Available Poland PKD Sectors ===\n")
    for name, sector in PKD_SECTORS.items():
        print(f"{name}:")
        print(f"  Description: {sector['desc']}")
        print(f"  PKD codes: {', '.join(sector['codes'][:5])}...")
        print(f"  Keywords: {', '.join(sector['keywords'][:5])}")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Poland PKD Company Import")
    parser.add_argument("--pkd", help="PKD code(s) to import (comma-separated, wildcard with *)")
    parser.add_argument("--sector", help="Import predefined sector")
    parser.add_argument("--all-sectors", action="store_true", help="Import all sectors")
    parser.add_argument("--enrich", action="store_true", help="Enrich with local LLM")
    parser.add_argument("--list-sectors", action="store_true", help="List available sectors")
    parser.add_argument("--status", action="store_true", help="Show import status")
    parser.add_argument("--output", help="Output name for PKD import")

    args = parser.parse_args()

    if args.list_sectors:
        list_sectors()
        return

    if args.status:
        show_status()
        return

    state = load_state()

    if args.all_sectors:
        for sector_name in PKD_SECTORS:
            import_sector(sector_name, args.enrich)
            state['sectors_imported'][sector_name] = datetime.now().isoformat()
    elif args.sector:
        import_sector(args.sector, args.enrich)
        state['sectors_imported'][args.sector] = datetime.now().isoformat()
    elif args.pkd:
        import_by_pkd(args.pkd, args.output, args.enrich)
    else:
        parser.print_help()
        return

    state['last_import'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
