#!/usr/bin/env python3
"""
EU Data Scraper - Unified scraper for European open data portals.

Scrapes company/business data from:
- data.europa.eu (EU-wide portal)
- National CKAN portals (SI, PT, SK, EE, LV, LT, HU, GR)
- Direct government APIs

All output is ASCII-only, saved to /opt/ACTIVE/OPENDATA/DATA/<COUNTRY>/

Usage:
    python3 eu_data_scraper.py --country SI          # Slovenia
    python3 eu_data_scraper.py --country BG          # Bulgaria
    python3 eu_data_scraper.py --all                 # All countries
    python3 eu_data_scraper.py --status              # Show status
    python3 eu_data_scraper.py --search "companies"  # Search EU portal
"""

import argparse
import csv
import hashlib
import json
import os
import ssl
import sys
import time
import unicodedata
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA")

# EU Data Portal API
EU_PORTAL_API = "https://data.europa.eu/api/hub/search/search"

# Country configurations
COUNTRIES = {
    "SI": {
        "name": "Slovenia",
        "ckan_url": "https://podatki.gov.si/api/3/action/",
        "direct_urls": [
            "https://podatki.gov.si/dataset/9ee1a9aa-c224-4995-b2ad-3760d7af0748/resource/beb70929-3d0d-41c6-9af2-25d525d906d3/download/opsiprs.csv",
        ],
        "search_terms": ["podjetja", "prs", "register"],
        "encoding": "utf-16-le",
    },
    "BG": {
        "name": "Bulgaria",
        "search_terms": ["bulgaria business register", "bulgarian companies"],
        "eu_search": True,
    },
    "HR": {
        "name": "Croatia",
        "search_terms": ["croatia business", "croatian register"],
        "eu_search": True,
    },
    "SK": {
        "name": "Slovakia",
        "ckan_url": "https://data.gov.sk/api/3/action/",
        "search_terms": ["firmy", "obchodny register"],
    },
    "HU": {
        "name": "Hungary",
        "ckan_url": "https://data.gov.hu/api/3/action/",
        "search_terms": ["cegek", "vallalkozasok"],
    },
    "PL": {
        "name": "Poland",
        "search_terms": ["poland companies", "polish business"],
        "eu_search": True,
    },
    "CZ": {
        "name": "Czech",
        "search_terms": ["czech companies", "ceske firmy"],
        "eu_search": True,
    },
    "RO": {
        "name": "Romania",
        "search_terms": ["romania companies", "romanian firms"],
        "eu_search": True,
    },
    "EE": {
        "name": "Estonia",
        "ckan_url": "https://opendata.riik.ee/api/3/action/",
        "search_terms": ["ettevotted", "ariregister"],
    },
    "LV": {
        "name": "Latvia",
        "ckan_url": "https://data.gov.lv/api/3/action/",
        "search_terms": ["uznemumi", "komersanti"],
    },
    "LT": {
        "name": "Lithuania",
        "ckan_url": "https://data.gov.lt/api/3/action/",
        "search_terms": ["imones", "juridiniai"],
    },
    "PT": {
        "name": "Portugal",
        "ckan_url": "https://dados.gov.pt/api/3/action/",
        "search_terms": ["empresas", "sociedades"],
    },
    "GR": {
        "name": "Greece",
        "search_terms": ["greece companies", "greek business"],
        "eu_search": True,
    },
    "MT": {
        "name": "Malta",
        "search_terms": ["malta companies", "maltese business"],
        "eu_search": True,
    },
}


# =============================================================================
# Utilities
# =============================================================================

def to_ascii(text: str) -> str:
    """Convert to ASCII, removing diacritics."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii').strip()


def get_ssl_context():
    """Permissive SSL context."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_json(url: str, timeout: int = 30) -> Optional[Dict]:
    """Fetch JSON from URL."""
    try:
        ctx = get_ssl_context()
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (EU Data Scraper)',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  Fetch error: {e}")
        return None


def download_file(url: str, output_path: Path, max_retries: int = 3) -> bool:
    """Download with retries."""
    ctx = get_ssl_context()

    for attempt in range(max_retries):
        try:
            print(f"  Download attempt {attempt + 1}/{max_retries}")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
                with open(output_path, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                return True

        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))

    return False


def convert_to_ascii_csv(input_path: Path, output_path: Path) -> int:
    """Convert CSV to ASCII."""
    # Detect encoding
    with open(input_path, 'rb') as f:
        header = f.read(4)

    if header.startswith(b'\xff\xfe'):
        encoding = 'utf-16-le'
    elif header.startswith(b'\xfe\xff'):
        encoding = 'utf-16-be'
    else:
        encoding = 'utf-8'

    print(f"  Encoding: {encoding}")

    rows = []
    with open(input_path, 'r', encoding=encoding, errors='ignore') as f:
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]

        reader = csv.reader(content.splitlines())
        for row in reader:
            rows.append([to_ascii(cell) for cell in row])

    with open(output_path, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return len(rows)


# =============================================================================
# EU Portal Search
# =============================================================================

def search_eu_portal(query: str, limit: int = 50) -> List[Dict]:
    """Search EU data portal for datasets."""
    encoded_query = urllib.parse.quote(query)
    url = f"{EU_PORTAL_API}?q={encoded_query}&filter=dataset&limit={limit}"

    print(f"  Searching EU portal: {query}")
    data = fetch_json(url)

    if not data:
        return []

    results = []
    for ds in data.get('result', {}).get('results', []):
        title = ds.get('title', {})
        if isinstance(title, dict):
            title = title.get('en') or list(title.values())[0] if title else ''

        # Extract CSV URLs
        csv_urls = []
        for dist in ds.get('distributions', []):
            fmt = str(dist.get('format', {}).get('id', '')).lower()
            if 'csv' in fmt:
                url = dist.get('downloadUrl') or dist.get('accessUrl')
                if url:
                    csv_urls.append(url)

        if csv_urls:
            results.append({
                'title': to_ascii(title),
                'id': ds.get('id'),
                'csv_urls': csv_urls,
            })

    return results


# =============================================================================
# CKAN Search
# =============================================================================

def search_ckan(api_url: str, query: str) -> List[Dict]:
    """Search CKAN portal."""
    url = f"{api_url}package_search?q={urllib.parse.quote(query)}&rows=50"

    print(f"  Searching CKAN: {query}")
    data = fetch_json(url)

    if not data or not data.get('success'):
        return []

    results = []
    for ds in data.get('result', {}).get('results', []):
        csv_urls = []
        for res in ds.get('resources', []):
            fmt = str(res.get('format', '')).upper()
            if fmt in ['CSV', 'TEXT/CSV']:
                url = res.get('url')
                if url:
                    csv_urls.append(url)

        if csv_urls:
            results.append({
                'title': to_ascii(ds.get('title', '')),
                'id': ds.get('id'),
                'csv_urls': csv_urls,
            })

    return results


# =============================================================================
# Country Scraper
# =============================================================================

def scrape_country(country_code: str) -> Dict:
    """Scrape data for a country."""
    if country_code not in COUNTRIES:
        return {"success": False, "error": f"Unknown country: {country_code}"}

    config = COUNTRIES[country_code]
    country_name = config["name"]

    print(f"\n{'='*60}")
    print(f"Scraping: {country_name} ({country_code})")
    print(f"{'='*60}")

    # Setup directories
    country_dir = BASE_DIR / country_name.upper()
    raw_dir = country_dir / "RAW"
    companies_dir = country_dir / "COMPANIES"

    for d in [raw_dir, companies_dir]:
        d.mkdir(parents=True, exist_ok=True)

    csv_urls = []
    timestamp = datetime.now().strftime("%Y%m%d")

    # 1. Direct URLs
    if config.get("direct_urls"):
        print("\nUsing direct URLs...")
        csv_urls.extend(config["direct_urls"])

    # 2. CKAN search
    if config.get("ckan_url"):
        print("\nSearching CKAN portal...")
        for term in config.get("search_terms", []):
            results = search_ckan(config["ckan_url"], term)
            for r in results:
                csv_urls.extend(r.get("csv_urls", []))

    # 3. EU portal search
    if config.get("eu_search"):
        print("\nSearching EU portal...")
        for term in config.get("search_terms", []):
            results = search_eu_portal(term)
            for r in results:
                csv_urls.extend(r.get("csv_urls", []))

    # Deduplicate
    csv_urls = list(set(csv_urls))
    print(f"\nFound {len(csv_urls)} unique CSV URLs")

    if not csv_urls:
        return {"success": False, "error": "No CSV URLs found", "country": country_code}

    # Download and convert
    total_rows = 0
    files_saved = []

    for i, url in enumerate(csv_urls[:10]):  # Limit to 10 files
        print(f"\n[{i+1}/{min(len(csv_urls), 10)}] {url[:60]}...")

        raw_file = raw_dir / f"download_{timestamp}_{i}.csv"

        if not download_file(url, raw_file):
            continue

        size_mb = raw_file.stat().st_size / 1024 / 1024
        print(f"  Size: {size_mb:.1f} MB")

        if size_mb < 0.001:
            raw_file.unlink()
            continue

        # Convert to ASCII
        output_file = companies_dir / f"companies_{timestamp}_{i}.csv"
        try:
            rows = convert_to_ascii_csv(raw_file, output_file)
            print(f"  Rows: {rows:,}")
            total_rows += rows
            files_saved.append(str(output_file))
        except Exception as e:
            print(f"  Conversion error: {e}")

    # Log
    log_file = country_dir / "scrape_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | {total_rows} rows | {len(files_saved)} files\n")

    print(f"\n{'='*60}")
    print(f"DONE: {country_name} - {total_rows:,} rows in {len(files_saved)} files")
    print(f"{'='*60}")

    return {
        "success": True,
        "country": country_code,
        "total_rows": total_rows,
        "files": files_saved,
    }


def scrape_all() -> Dict:
    """Scrape all countries."""
    results = {}
    for code in COUNTRIES.keys():
        try:
            results[code] = scrape_country(code)
        except Exception as e:
            results[code] = {"success": False, "error": str(e)}
        time.sleep(2)
    return results


def show_status():
    """Show scraping status."""
    print("\n" + "="*70)
    print("EU Data Scraper Status")
    print("="*70)

    for code, config in COUNTRIES.items():
        country_dir = BASE_DIR / config["name"].upper() / "COMPANIES"

        if country_dir.exists():
            files = list(country_dir.glob("*.csv"))
            total_rows = 0

            for f in files:
                if f.stat().st_size > 0:
                    with open(f, 'r', errors='ignore') as fp:
                        total_rows += sum(1 for _ in fp)

            if files:
                latest = max(files, key=lambda x: x.stat().st_mtime)
                latest_date = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d")
                print(f"{code:4} | {config['name']:15} | {total_rows:>10,} rows | {latest_date}")
            else:
                print(f"{code:4} | {config['name']:15} | {'No data':>10}")
        else:
            print(f"{code:4} | {config['name']:15} | {'Not scraped':>10}")

    print("="*70)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="EU Data Scraper")
    parser.add_argument("--country", "-c", help="Country code (SI, BG, HR, etc.)")
    parser.add_argument("--all", "-a", action="store_true", help="Scrape all countries")
    parser.add_argument("--status", "-s", action="store_true", help="Show status")
    parser.add_argument("--search", help="Search EU portal")
    parser.add_argument("--list", "-l", action="store_true", help="List countries")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.list:
        print("\nAvailable countries:")
        for code, config in COUNTRIES.items():
            print(f"  {code}: {config['name']}")
    elif args.search:
        results = search_eu_portal(args.search)
        print(f"\nFound {len(results)} datasets with CSV:")
        for r in results[:20]:
            print(f"  {r['title'][:50]}")
            print(f"    {r['csv_urls'][0][:60]}...")
    elif args.all:
        results = scrape_all()
        print("\n=== Summary ===")
        for code, r in results.items():
            status = "OK" if r.get("success") else "FAILED"
            rows = r.get("total_rows", 0)
            print(f"{code}: {status} ({rows:,} rows)")
    elif args.country:
        result = scrape_country(args.country.upper())
        if not result.get("success"):
            print(f"ERROR: {result.get('error')}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
