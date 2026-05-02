#!/usr/bin/env python3
"""
Country Data Downloader - Downloads business data country by country.

Downloads: companies, agencies, hotels, restaurants, tenders, employers
Sources: CKAN portals, EU portal, direct government APIs

All output is ASCII-only.

Usage:
    python3 country_data_downloader.py SI           # Slovenia
    python3 country_data_downloader.py SI PT BG     # Multiple
    python3 country_data_downloader.py --all        # All countries
    python3 country_data_downloader.py --status     # Status
"""

import argparse
import csv
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

# Country download sources
COUNTRY_SOURCES = {
    "SI": {
        "name": "Slovenia",
        "sources": [
            # Business register
            {
                "name": "Poslovni register (Business Register)",
                "url": "https://podatki.gov.si/dataset/9ee1a9aa-c224-4995-b2ad-3760d7af0748/resource/beb70929-3d0d-41c6-9af2-25d525d906d3/download/opsiprs.csv",
                "type": "companies",
                "encoding": "utf-16-le",
            },
        ],
        "ckan": "https://podatki.gov.si/api/3/action/",
        "search_terms": ["turisticne agencije", "gostinstvo", "hoteli"],
    },
    "PT": {
        "name": "Portugal",
        "ckan": "https://dados.gov.pt/api/3/action/",
        "search_terms": ["empresas", "turismo", "hotelaria", "restaurantes"],
    },
    "BG": {
        "name": "Bulgaria",
        "eu_search": ["bulgaria business register", "bulgaria hotels", "bulgaria tourism"],
    },
    "HR": {
        "name": "Croatia",
        "eu_search": ["croatia business", "croatia tourism agencies"],
    },
    "SK": {
        "name": "Slovakia",
        "ckan": "https://data.gov.sk/api/3/action/",
        "search_terms": ["firmy", "hotely", "restauracie"],
    },
    "HU": {
        "name": "Hungary",
        "ckan": "https://data.gov.hu/api/3/action/",
        "search_terms": ["cegek", "szallodak", "etterem"],
    },
    "PL": {
        "name": "Poland",
        "eu_search": ["poland companies register", "poland hotels", "poland tourism"],
    },
    "CZ": {
        "name": "Czech",
        "eu_search": ["czech companies", "czech hotels", "czech tourism"],
    },
    "RO": {
        "name": "Romania",
        "sources": [
            # ANAF - handled separately
        ],
        "eu_search": ["romania ANAF", "romania companies", "romania tourism"],
    },
    "EE": {
        "name": "Estonia",
        "ckan": "https://opendata.riik.ee/api/3/action/",
        "search_terms": ["ettevotted", "turism", "hotellid"],
    },
    "LV": {
        "name": "Latvia",
        "ckan": "https://data.gov.lv/api/3/action/",
        "search_terms": ["uznemumi", "viesnicas", "turisma"],
    },
    "LT": {
        "name": "Lithuania",
        "ckan": "https://data.gov.lt/api/3/action/",
        "search_terms": ["imones", "viesbuciu", "turizmo"],
    },
    "GR": {
        "name": "Greece",
        "eu_search": ["greece companies", "greece hotels", "greece tourism"],
    },
    "MT": {
        "name": "Malta",
        "eu_search": ["malta companies", "malta hotels", "malta tourism"],
    },
    "RS": {
        "name": "Serbia",
        "sources": [
            {
                "name": "APR Serbia Business Register",
                "url": "https://data.gov.rs/sr/datasets/r/apr-registar-privrednih-subjekata/",
                "type": "companies",
            },
        ],
        "eu_search": ["serbia companies", "serbia business register", "serbia hotels", "serbia tourism agencies"],
    },
    "BA": {
        "name": "Bosnia",
        "eu_search": ["bosnia companies", "bosnia business register", "bosnia hotels", "bosnia tourism"],
    },
    "AT": {
        "name": "Austria",
        "eu_search": ["austria companies register", "austria hotels CSV"],
    },
    "DE": {
        "name": "Germany",
        "eu_search": ["germany companies", "germany hotels register"],
    },
    "IT": {
        "name": "Italy",
        "eu_search": ["italy companies register CSV", "italy hotels", "italy tourism agencies"],
    },
    "ES": {
        "name": "Spain",
        "eu_search": ["spain companies register", "spain hotels", "spain tourism"],
    },
    "FR": {
        "name": "France",
        "eu_search": ["france companies SIRENE", "france hotels", "france tourism"],
    },
}


# =============================================================================
# Utilities
# =============================================================================

def to_ascii(text: str) -> str:
    """Convert to ASCII."""
    if not text:
        return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()


def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def download_file(url: str, output_path: Path, max_retries: int = 5) -> bool:
    """Download with retries and progress."""
    ctx = get_ssl_context()

    for attempt in range(max_retries):
        try:
            print(f"    Attempt {attempt + 1}/{max_retries}")
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': '*/*'
            })

            with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
                total = resp.headers.get('Content-Length')
                if total:
                    total = int(total)
                    print(f"    Size: {total / 1024 / 1024:.1f} MB")

                downloaded = 0
                with open(output_path, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            print(f"\r    Progress: {downloaded * 100 // total}%", end="", flush=True)
                print()
                return True

        except Exception as e:
            print(f"    Error: {e}")
            if attempt < max_retries - 1:
                wait = 5 * (2 ** attempt)
                print(f"    Retry in {wait}s...")
                time.sleep(wait)

    return False


def convert_to_ascii(input_path: Path, output_path: Path) -> int:
    """Convert to ASCII CSV."""
    # Detect encoding
    with open(input_path, 'rb') as f:
        header = f.read(4)

    if header.startswith(b'\xff\xfe'):
        encoding = 'utf-16-le'
    elif header.startswith(b'\xfe\xff'):
        encoding = 'utf-16-be'
    elif header.startswith(b'\xef\xbb\xbf'):
        encoding = 'utf-8-sig'
    else:
        encoding = 'utf-8'

    print(f"    Encoding: {encoding}")

    rows = []
    with open(input_path, 'r', encoding=encoding, errors='ignore') as f:
        content = f.read().lstrip('\ufeff')
        for line in content.splitlines():
            # Parse CSV line
            reader = csv.reader([line])
            for row in reader:
                rows.append([to_ascii(cell) for cell in row])

    with open(output_path, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return len(rows)


def fetch_json(url: str) -> Optional[Dict]:
    """Fetch JSON."""
    try:
        ctx = get_ssl_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except:
        return None


def search_ckan(api_url: str, query: str) -> List[str]:
    """Search CKAN for CSV URLs."""
    url = f"{api_url}package_search?q={urllib.parse.quote(query)}&rows=20"
    data = fetch_json(url)

    if not data or not data.get('success'):
        return []

    urls = []
    for ds in data.get('result', {}).get('results', []):
        for res in ds.get('resources', []):
            fmt = str(res.get('format', '')).upper()
            if fmt in ['CSV', 'TEXT/CSV']:
                u = res.get('url')
                if u:
                    urls.append(u)
    return urls


def search_eu_portal(query: str) -> List[str]:
    """Search EU portal for CSV URLs."""
    encoded = urllib.parse.quote(query)
    url = f"https://data.europa.eu/api/hub/search/search?q={encoded}&filter=dataset&limit=20"

    data = fetch_json(url)
    if not data:
        return []

    urls = []
    for ds in data.get('result', {}).get('results', []):
        for d in ds.get('distributions', []):
            dl = d.get('downloadUrl') or d.get('accessUrl')
            if dl and '.csv' in dl.lower():
                urls.append(dl)
    return urls


# =============================================================================
# Main Downloader
# =============================================================================

def download_country(country_code: str) -> Dict:
    """Download all data for a country."""
    if country_code not in COUNTRY_SOURCES:
        return {"success": False, "error": f"Unknown country: {country_code}"}

    config = COUNTRY_SOURCES[country_code]
    country_name = config["name"]

    print(f"\n{'='*60}")
    print(f" Downloading: {country_name} ({country_code})")
    print(f"{'='*60}")

    # Setup directories
    country_dir = BASE_DIR / country_name.upper()
    for subdir in ["RAW", "COMPANIES", "AGENCIES", "JOBS", "EMPLOYERS"]:
        (country_dir / subdir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    all_urls = []
    results = {"success": True, "country": country_code, "files": [], "total_rows": 0}

    # 1. Direct sources
    for source in config.get("sources", []):
        print(f"\n  Source: {source['name']}")
        all_urls.append((source["url"], source.get("type", "companies"), source.get("encoding")))

    # 2. CKAN search
    if config.get("ckan"):
        print(f"\n  Searching CKAN: {config['ckan']}")
        for term in config.get("search_terms", []):
            print(f"    Term: {term}")
            urls = search_ckan(config["ckan"], term)
            for u in urls:
                all_urls.append((u, "companies", None))
            print(f"    Found: {len(urls)} URLs")

    # 3. EU portal search
    if config.get("eu_search"):
        print(f"\n  Searching EU portal...")
        for term in config["eu_search"]:
            print(f"    Term: {term}")
            urls = search_eu_portal(term)
            for u in urls:
                all_urls.append((u, "companies", None))
            print(f"    Found: {len(urls)} URLs")

    # Deduplicate
    seen = set()
    unique_urls = []
    for item in all_urls:
        if item[0] not in seen:
            seen.add(item[0])
            unique_urls.append(item)

    print(f"\n  Total unique URLs: {len(unique_urls)}")

    if not unique_urls:
        results["success"] = False
        results["error"] = "No download URLs found"
        return results

    # Download each URL
    for i, (url, dtype, encoding) in enumerate(unique_urls[:15]):  # Max 15 files
        print(f"\n  [{i+1}/{min(len(unique_urls), 15)}] Downloading...")
        print(f"    URL: {url[:60]}...")

        raw_file = country_dir / "RAW" / f"{dtype}_{timestamp}_{i}.csv"

        if not download_file(url, raw_file):
            print("    FAILED")
            continue

        size = raw_file.stat().st_size
        if size < 100:
            print("    Too small, skipping")
            raw_file.unlink()
            continue

        print(f"    Downloaded: {size / 1024:.1f} KB")

        # Convert to ASCII
        output_dir = country_dir / dtype.upper()
        if not output_dir.exists():
            output_dir = country_dir / "COMPANIES"

        output_file = output_dir / f"{dtype}_{timestamp}_{i}.csv"

        try:
            rows = convert_to_ascii(raw_file, output_file)
            print(f"    Rows: {rows:,}")
            print(f"    Saved: {output_file.name}")
            results["files"].append(str(output_file))
            results["total_rows"] += rows
        except Exception as e:
            print(f"    Conversion error: {e}")

    # Log
    log_file = country_dir / "download_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | {results['total_rows']} rows | {len(results['files'])} files\n")

    print(f"\n{'='*60}")
    print(f" DONE: {country_name} - {results['total_rows']:,} rows")
    print(f"{'='*60}")

    return results


def show_status():
    """Show download status."""
    print("\n" + "="*70)
    print(" Country Data Download Status")
    print("="*70)

    for code in sorted(COUNTRY_SOURCES.keys()):
        config = COUNTRY_SOURCES[code]
        country_dir = BASE_DIR / config["name"].upper()

        total = 0
        files = 0
        latest = None

        for subdir in ["COMPANIES", "AGENCIES", "JOBS", "EMPLOYERS"]:
            d = country_dir / subdir
            if d.exists():
                for f in d.glob("*.csv"):
                    files += 1
                    if f.stat().st_size > 0:
                        with open(f, 'r', errors='ignore') as fp:
                            total += sum(1 for _ in fp)
                        if not latest or f.stat().st_mtime > latest.stat().st_mtime:
                            latest = f

        if files > 0:
            date = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d") if latest else "?"
            print(f"{code:3} | {config['name']:15} | {total:>10,} rows | {files:>3} files | {date}")
        else:
            print(f"{code:3} | {config['name']:15} | {'No data':>10}")

    print("="*70)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Country Data Downloader")
    parser.add_argument("countries", nargs="*", help="Country codes (SI, PT, BG...)")
    parser.add_argument("--all", "-a", action="store_true", help="Download all")
    parser.add_argument("--status", "-s", action="store_true", help="Show status")
    parser.add_argument("--list", "-l", action="store_true", help="List countries")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.list:
        print("\nAvailable countries:")
        for code, config in sorted(COUNTRY_SOURCES.items()):
            print(f"  {code}: {config['name']}")
    elif args.all:
        for code in COUNTRY_SOURCES.keys():
            download_country(code)
            time.sleep(3)
    elif args.countries:
        for code in args.countries:
            download_country(code.upper())
            time.sleep(2)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
