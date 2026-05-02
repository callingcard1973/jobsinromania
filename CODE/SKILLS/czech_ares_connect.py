#!/usr/bin/env python3
"""
Czech ARES Company Registry Connector

Connects to Czech ARES (Administrative Register of Economic Subjects) API
to fetch company data by CZ-NACE codes.

API: https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/
Docs: https://ares.gov.cz/swagger-ui/

Usage:
    python3 czech_ares_connect.py --nace 5610              # Restaurants
    python3 czech_ares_connect.py --nace "55*"             # Hotels (wildcard)
    python3 czech_ares_connect.py --sector horeca          # Predefined sector
    python3 czech_ares_connect.py --ico 12345678           # Single company by ICO
    python3 czech_ares_connect.py --search "hotel praha"   # Search by name
    python3 czech_ares_connect.py --list-sectors           # Show sectors
    python3 czech_ares_connect.py --status                 # Show status
    python3 czech_ares_connect.py --enrich                 # Enrich with local LLM

CZ-NACE = NACE Rev. 2 = same as Romanian CAEN and Polish PKD
"""

import os
import sys
import csv
import json
import re
import time
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

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
DATA_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CZECH")
EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/NACE_EXPORTS")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.czech_ares_state.json")
LLM_URL = "http://localhost:1234/v1/chat/completions"

# ARES API
ARES_BASE = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest"
ARES_SEARCH = f"{ARES_BASE}/ekonomicke-subjekty/vyhledat"
ARES_DETAIL = f"{ARES_BASE}/ekonomicke-subjekty"

# CZ-NACE Sector definitions (same as NACE/CAEN/PKD)
CZ_NACE_SECTORS = {
    "horeca": {
        "codes": ["5510", "5520", "5530", "5590", "5610", "5621", "5629", "5630"],
        "desc": "Hotels, Restaurants, Catering",
        "keywords": ["hotel", "restaurace", "bar", "kavarna", "catering", "penzion"]
    },
    "construction": {
        "codes": ["4110", "4120", "4211", "4212", "4213", "4221", "4222", "4291", "4299",
                  "4311", "4312", "4313", "4321", "4322", "4329", "4331", "4332", "4333", "4334", "4339", "4391", "4399"],
        "desc": "Construction & Building",
        "keywords": ["stavba", "konstrukce", "stavebni", "developer", "rekonstrukce"]
    },
    "manufacturing": {
        "codes": ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"],
        "desc": "Manufacturing & Production",
        "keywords": ["vyroba", "tovarna", "zavod", "produkcni"]
    },
    "transport": {
        "codes": ["4910", "4920", "4931", "4932", "4939", "4941", "4942", "5010", "5020", "5110", "5121", "5122",
                  "5210", "5221", "5222", "5223", "5224", "5229"],
        "desc": "Transport & Logistics",
        "keywords": ["doprava", "logistika", "spedice", "preprava", "sklad"]
    },
    "it_services": {
        "codes": ["6201", "6202", "6203", "6209", "6311", "6312"],
        "desc": "IT & Software Services",
        "keywords": ["software", "IT", "programovani", "informatika", "technologie"]
    },
    "call_centers": {
        "codes": ["8220"],
        "desc": "Call Centers & BPO",
        "keywords": ["call centrum", "BPO", "outsourcing", "telemarketing"]
    },
    "recruitment": {
        "codes": ["7810", "7820", "7830"],
        "desc": "Recruitment & HR Agencies",
        "keywords": ["agentura prace", "personalni", "HR", "nabor", "zamestnani"]
    },
    "agriculture": {
        "codes": ["0111", "0112", "0113", "0114", "0115", "0116", "0119", "0121", "0122", "0123", "0124", "0125"],
        "desc": "Agriculture & Farming",
        "keywords": ["zemedelstvi", "farma", "pestovani", "chov"]
    },
    "retail": {
        "codes": ["4711", "4719", "4721", "4722", "4723", "4724", "4725", "4726", "4729",
                  "4741", "4742", "4743", "4751", "4752", "4759", "4761", "4771", "4772", "4773", "4774", "4775", "4776", "4777", "4778", "4779"],
        "desc": "Retail Trade",
        "keywords": ["obchod", "prodej", "maloobchod", "prodejna"]
    },
    "wholesale": {
        "codes": ["4611", "4612", "4613", "4614", "4615", "4616", "4617", "4618", "4619",
                  "4621", "4622", "4623", "4624", "4631", "4632", "4633", "4634", "4635", "4636", "4637", "4638", "4639",
                  "4641", "4642", "4643", "4644", "4645", "4646", "4647", "4648", "4649", "4651", "4652", "4690"],
        "desc": "Wholesale Trade",
        "keywords": ["velkoobchod", "distribuce", "distributor"]
    },
}

# Czech regions
CZ_REGIONS = {
    "CZ010": "Praha",
    "CZ020": "Stredocesky",
    "CZ031": "Jihocesky",
    "CZ032": "Plzensky",
    "CZ041": "Karlovarsky",
    "CZ042": "Ustecky",
    "CZ051": "Liberecky",
    "CZ052": "Kralovehradecky",
    "CZ053": "Pardubicky",
    "CZ063": "Vysocina",
    "CZ064": "Jihomoravsky",
    "CZ071": "Olomoucky",
    "CZ072": "Zlinsky",
    "CZ080": "Moravskoslezsky",
}


def log(msg):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    """Load connector state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "last_fetch": None,
        "sectors_fetched": {},
        "total_companies": 0,
        "api_calls": 0
    }


def save_state(state):
    """Save connector state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def normalize_phone_cz(phone):
    """Normalize Czech phone number."""
    if not phone:
        return ""
    digits = re.sub(r'[^\d+]', '', str(phone))
    if digits.startswith('420') and len(digits) >= 12:
        return '+' + digits
    if digits.startswith('+420'):
        return digits
    if len(digits) == 9 and digits[0] in '234567':
        return '+420' + digits
    if len(digits) >= 9:
        return '+420' + digits[-9:]
    return ""


def validate_email(email):
    """Validate email format."""
    if not email:
        return None
    email = email.lower().strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        if any(x in email for x in ['example.', 'test.', 'noreply', '@localhost']):
            return None
        return email
    return None


def calculate_score(row):
    """Calculate lead score for Czech company."""
    score = 0
    tags = []

    email = row.get('email', '')
    if email:
        score += 10
        domain = email.split('@')[1] if '@' in email else ''
        if domain and not any(x in domain for x in ['gmail.', 'yahoo.', 'seznam.cz', 'email.cz', 'centrum.cz']):
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
    major = ['praha', 'brno', 'ostrava', 'plzen', 'liberec', 'olomouc', 'ceske budejovice', 'hradec kralove', 'pardubice', 'zlin']
    if any(c in city for c in major):
        score += 5
        tags.append('major_city')

    return score, ','.join(tags)


def fetch_ares_by_ico(ico):
    """Fetch single company from ARES by ICO (company ID)."""
    url = f"{ARES_DETAIL}/{ico}"
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; CompanyBot/1.0)'
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        log(f"ARES API error: {e}")

    return None


def fetch_ares_search(query, max_results=100):
    """Search ARES by company name."""
    url = ARES_SEARCH
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; CompanyBot/1.0)'
    }

    payload = {
        "obchodniJmeno": query,
        "pocet": min(max_results, 1000),
        "razeni": ["obchodniJmeno"],
        "start": 0
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('ekonomickeSubjekty', [])
    except Exception as e:
        log(f"ARES search error: {e}")

    return []


def fetch_ares_by_nace(nace_codes, region=None, max_results=500):
    """Fetch companies from ARES by CZ-NACE codes."""
    url = ARES_SEARCH
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; CompanyBot/1.0)'
    }

    companies = []

    for nace in nace_codes:
        if nace.endswith('*'):
            # ARES doesn't support wildcard, need to expand
            continue

        payload = {
            "czNace": [nace],
            "pocet": min(max_results, 1000),
            "razeni": ["obchodniJmeno"],
            "start": 0
        }

        if region:
            payload["sidlo"] = {"nuts": [region]}

        try:
            log(f"  Fetching NACE {nace}...")
            resp = requests.post(url, headers=headers, json=payload, timeout=60)

            if resp.status_code == 200:
                data = resp.json()
                results = data.get('ekonomickeSubjekty', [])
                companies.extend(results)
                log(f"    Found {len(results)} companies")

                # Rate limit
                time.sleep(1)
            else:
                log(f"    API returned {resp.status_code}")

        except Exception as e:
            log(f"    Error: {e}")

    return companies


def parse_ares_company(ares_data):
    """Parse ARES API response into standard format."""
    if not ares_data:
        return None

    company = {
        'company': to_ascii(ares_data.get('obchodniJmeno', '')),
        'ico': ares_data.get('ico', ''),
        'dic': ares_data.get('dic', ''),
        'email': '',
        'phone': '',
        'website': '',
        'city': '',
        'county': '',
        'country': 'CZ',
        'nace': '',
        'nace_description': '',
        'source': 'ares_api'
    }

    # Address
    sidlo = ares_data.get('sidlo', {})
    if sidlo:
        company['city'] = to_ascii(sidlo.get('nazevObce', ''))
        company['county'] = to_ascii(sidlo.get('nazevOkresu', ''))
        company['address'] = to_ascii(sidlo.get('textovaAdresa', ''))

    # NACE codes
    cinnosti = ares_data.get('czNace', [])
    if cinnosti:
        company['nace'] = cinnosti[0] if isinstance(cinnosti[0], str) else ''

    # Legal form
    forma = ares_data.get('pravniForma', {})
    if forma:
        company['legal_form'] = to_ascii(forma.get('nazev', ''))

    return company


def load_local_czech_data():
    """Load locally scraped Czech company data."""
    companies = []

    data_sources = [
        DATA_DIR / "czech_companies.csv",
        DATA_DIR / "firmy_cz.csv",
        Path("/opt/ACTIVE/OPENDATA/DATA/AGENCIES/BY_COUNTRY/czech_agencies.csv"),
        Path("/home/tudor/SCRAPER_DATA/CZECH/"),
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
                            'phone': normalize_phone_cz(row.get('phone', row.get('telefon', ''))),
                            'city': to_ascii(row.get('city', row.get('mesto', ''))),
                            'county': to_ascii(row.get('county', row.get('kraj', ''))),
                            'country': 'CZ',
                            'website': row.get('website', row.get('www', '')),
                            'ico': row.get('ico', row.get('cui', '')),
                            'nace': row.get('nace', row.get('caen', '')),
                            'nace_description': row.get('nace_description', row.get('activity', '')),
                            'source': source.stem
                        }
                        if company['company'] and (company['email'] or company['phone'] or company['ico']):
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
                                'company': row.get('company', row.get('name', '')),
                                'email': validate_email(row.get('email', '')),
                                'phone': normalize_phone_cz(row.get('phone', '')),
                                'city': to_ascii(row.get('city', '')),
                                'county': to_ascii(row.get('county', '')),
                                'country': 'CZ',
                                'website': row.get('website', ''),
                                'ico': row.get('ico', ''),
                                'nace': row.get('nace', ''),
                                'nace_description': row.get('nace_description', ''),
                                'source': csv_file.stem
                            }
                            if company['company'] and (company['email'] or company['phone']):
                                companies.append(company)
                except Exception as e:
                    log(f"  Error: {e}")

    log(f"Loaded {len(companies)} companies from local sources")
    return companies


def filter_by_nace(companies, nace_codes):
    """Filter companies by CZ-NACE codes."""
    filtered = []

    for company in companies:
        nace = str(company.get('nace', '')).strip()
        if not nace:
            continue

        for code in nace_codes:
            if code.endswith('*'):
                prefix = code[:-1]
                if nace.startswith(prefix):
                    filtered.append(company)
                    break
            else:
                if nace == code or nace.startswith(code):
                    filtered.append(company)
                    break

    return filtered


def deduplicate(companies):
    """Deduplicate by ICO, email, and name."""
    seen_ico = set()
    seen_emails = set()
    seen_names = set()
    unique = []

    for company in companies:
        ico = company.get('ico', '')
        email = company.get('email', '').lower()
        name_hash = hashlib.md5(to_ascii(company.get('company', '')).upper().encode()).hexdigest()[:12]

        if ico and ico in seen_ico:
            continue
        if email and email in seen_emails:
            continue
        if name_hash in seen_names:
            continue

        if ico:
            seen_ico.add(ico)
        if email:
            seen_emails.add(email)
        seen_names.add(name_hash)
        unique.append(company)

    return unique


def enrich_with_llm(companies, limit=50):
    """Enrich companies using local LLM."""
    enriched = 0

    for company in companies[:limit]:
        if company.get('nace_description'):
            continue

        nace = company.get('nace', '')
        name = company.get('company', '')

        if not nace and not name:
            continue

        prompt = f"""Given this Czech company:
Name: {name}
CZ-NACE code: {nace}

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
                company['nace_description'] = to_ascii(desc)[:100]
                enriched += 1

        except Exception:
            pass

        time.sleep(0.2)

    log(f"Enriched {enriched} companies with LLM")
    return companies


def export_sector(sector_name, companies, with_score=True):
    """Export sector to CSV."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = EXPORT_DIR / f"czech_{sector_name}_with_email.csv"

    fieldnames = [
        'company', 'email', 'phone', 'city', 'county', 'country',
        'website', 'ico', 'nace', 'nace_description', 'score', 'tags', 'source'
    ]

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


def import_sector(sector_name, use_api=False, enrich=False):
    """Import a predefined sector."""
    if sector_name not in CZ_NACE_SECTORS:
        log(f"Unknown sector: {sector_name}")
        return None

    sector = CZ_NACE_SECTORS[sector_name]
    log(f"=== Importing Czech {sector_name.upper()} ===")
    log(f"CZ-NACE codes: {', '.join(sector['codes'][:5])}...")

    all_companies = []

    # Load local data first
    local_companies = load_local_czech_data()
    filtered = filter_by_nace(local_companies, sector['codes'])
    all_companies.extend(filtered)
    log(f"From local: {len(filtered)}")

    # Optionally fetch from ARES API
    if use_api:
        api_companies = fetch_ares_by_nace(sector['codes'][:5], max_results=200)
        for ares_data in api_companies:
            parsed = parse_ares_company(ares_data)
            if parsed:
                all_companies.append(parsed)
        log(f"From ARES API: {len(api_companies)}")

    # Deduplicate
    unique = deduplicate(all_companies)
    log(f"After dedup: {len(unique)}")

    # Enrich with LLM if requested
    if enrich:
        unique = enrich_with_llm(unique)

    # Export
    if unique:
        output_file = export_sector(sector_name, unique)
        return output_file

    return None


def show_status():
    """Show connector status."""
    state = load_state()

    print("\n=== Czech ARES Connector Status ===\n")
    print(f"Last fetch: {state.get('last_fetch', 'Never')}")
    print(f"API calls made: {state.get('api_calls', 0)}")
    print(f"Total companies: {state.get('total_companies', 0)}")

    print("\nAvailable sectors:")
    for name, sector in CZ_NACE_SECTORS.items():
        print(f"  {name}: {sector['desc']} ({len(sector['codes'])} codes)")

    print("\nExported files:")
    if EXPORT_DIR.exists():
        for f in sorted(EXPORT_DIR.glob("czech_*_with_email.csv")):
            with open(f) as fh:
                rows = sum(1 for _ in fh) - 1
            print(f"  {f.name}: {rows} rows")

    print("\nLocal data sources:")
    for source in [DATA_DIR, Path("/home/tudor/SCRAPER_DATA/CZECH/")]:
        if source.exists():
            if source.is_dir():
                csv_count = len(list(source.glob("*.csv")))
                print(f"  {source}: {csv_count} CSV files")


def list_sectors():
    """List available sectors."""
    print("\n=== Available Czech CZ-NACE Sectors ===\n")
    for name, sector in CZ_NACE_SECTORS.items():
        print(f"{name}:")
        print(f"  Description: {sector['desc']}")
        print(f"  NACE codes: {', '.join(sector['codes'][:5])}...")
        print(f"  Keywords: {', '.join(sector['keywords'][:5])}")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Czech ARES Company Connector")
    parser.add_argument("--nace", help="CZ-NACE code(s) to import (comma-separated)")
    parser.add_argument("--sector", help="Import predefined sector")
    parser.add_argument("--all-sectors", action="store_true", help="Import all sectors")
    parser.add_argument("--ico", help="Fetch single company by ICO")
    parser.add_argument("--search", help="Search by company name")
    parser.add_argument("--api", action="store_true", help="Use ARES API (slower, more data)")
    parser.add_argument("--enrich", action="store_true", help="Enrich with local LLM")
    parser.add_argument("--list-sectors", action="store_true", help="List available sectors")
    parser.add_argument("--status", action="store_true", help="Show connector status")

    args = parser.parse_args()

    if args.list_sectors:
        list_sectors()
        return

    if args.status:
        show_status()
        return

    if args.ico:
        log(f"Fetching company ICO: {args.ico}")
        data = fetch_ares_by_ico(args.ico)
        if data:
            company = parse_ares_company(data)
            print(json.dumps(company, indent=2, ensure_ascii=False))
        else:
            print("Company not found")
        return

    if args.search:
        log(f"Searching: {args.search}")
        results = fetch_ares_search(args.search, max_results=20)
        for r in results:
            company = parse_ares_company(r)
            if company:
                print(f"{company['ico']}: {company['company']} ({company['city']})")
        return

    state = load_state()

    if args.all_sectors:
        for sector_name in CZ_NACE_SECTORS:
            import_sector(sector_name, args.api, args.enrich)
            state['sectors_fetched'][sector_name] = datetime.now().isoformat()
    elif args.sector:
        import_sector(args.sector, args.api, args.enrich)
        state['sectors_fetched'][args.sector] = datetime.now().isoformat()
    else:
        parser.print_help()
        return

    state['last_fetch'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
