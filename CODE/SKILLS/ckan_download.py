#!/usr/bin/env python3
"""
CKAN Download Skill - Robust downloader for European open data portals.

Downloads company registries from CKAN portals with:
- Automatic retries with exponential backoff
- UTF-16/UTF-8 detection and conversion
- ASCII normalization (removes diacritics)
- Verification and logging

Usage:
    python3 ckan_download.py --portal SI              # Download Slovenia
    python3 ckan_download.py --portal PT              # Download Portugal
    python3 ckan_download.py --all                    # Download all portals
    python3 ckan_download.py --status                 # Check download status
"""

import argparse
import csv
import hashlib
import os
import ssl
import sys
import time
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA")

# Known direct CSV URLs for company registries
PORTAL_DOWNLOADS = {
    "SI": {
        "name": "Slovenia - Poslovni register",
        "country": "SLOVENIA",
        "urls": [
            "https://podatki.gov.si/dataset/9ee1a9aa-c224-4995-b2ad-3760d7af0748/resource/beb70929-3d0d-41c6-9af2-25d525d906d3/download/opsiprs.csv",
        ],
        "encoding": "utf-16-le",
    },
    "PT": {
        "name": "Portugal - Empresas",
        "country": "PORTUGAL",
        "urls": [],  # Need to discover via CKAN API
        "api_url": "https://dados.gov.pt/api/3/action/",
        "search_terms": ["empresas", "sociedades"],
    },
    "SK": {
        "name": "Slovakia - Obchodny register",
        "country": "SLOVAKIA",
        "urls": [],
        "api_url": "https://data.gov.sk/api/3/action/",
        "search_terms": ["firmy", "obchodny-register"],
    },
    "EE": {
        "name": "Estonia - Ariregister",
        "country": "ESTONIA",
        "urls": [],
        "api_url": "https://opendata.riik.ee/api/3/action/",
        "search_terms": ["ettevotted", "ariregister"],
    },
    "LV": {
        "name": "Latvia - Uznemumi",
        "country": "LATVIA",
        "urls": [],
        "api_url": "https://data.gov.lv/api/3/action/",
        "search_terms": ["uznemumi", "komersanti"],
    },
    "LT": {
        "name": "Lithuania - Imones",
        "country": "LITHUANIA",
        "urls": [],
        "api_url": "https://data.gov.lt/api/3/action/",
        "search_terms": ["imones", "juridiniai"],
    },
    "HU": {
        "name": "Hungary - Cegek",
        "country": "HUNGARY",
        "urls": [],
        "api_url": "https://data.gov.hu/api/3/action/",
        "search_terms": ["cegek", "vallalkozasok"],
    },
    "GR": {
        "name": "Greece - Epicheiriseis",
        "country": "GREECE",
        "urls": [],
        "api_url": "https://data.gov.gr/api/3/action/",
        "search_terms": ["epicheiriseis", "companies"],
    },
}


# =============================================================================
# Utility Functions
# =============================================================================

def to_ascii(text: str) -> str:
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return text
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')


def get_ssl_context():
    """Create permissive SSL context."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def download_file(url: str, output_path: Path, max_retries: int = 5) -> bool:
    """Download file with retries and progress."""
    ctx = get_ssl_context()

    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
            }

            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=300, context=ctx) as response:
                total_size = response.headers.get('Content-Length')
                if total_size:
                    total_size = int(total_size)
                    print(f"  Size: {total_size / 1024 / 1024:.1f} MB")

                chunk_size = 65536
                downloaded = 0

                with open(output_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size:
                            pct = (downloaded / total_size) * 100
                            print(f"\r  Progress: {pct:.0f}%", end="", flush=True)

                print()
                return True

        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                print(f"  Retry in {wait}s...")
                time.sleep(wait)

    return False


def detect_encoding(filepath: Path) -> str:
    """Detect file encoding."""
    with open(filepath, 'rb') as f:
        header = f.read(4)

    if header.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    elif header.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    elif header.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    else:
        return 'utf-8'


def convert_to_ascii_csv(input_path: Path, output_path: Path, source_encoding: str = None) -> Tuple[int, List[str]]:
    """Convert CSV to ASCII format."""
    if not source_encoding:
        source_encoding = detect_encoding(input_path)

    print(f"  Encoding: {source_encoding}")

    # Read with detected encoding
    rows = []
    headers = []

    with open(input_path, 'r', encoding=source_encoding, errors='ignore') as f:
        # Skip BOM if present
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]

        reader = csv.reader(content.splitlines())
        for i, row in enumerate(reader):
            ascii_row = [to_ascii(cell.strip()) for cell in row]
            if i == 0:
                headers = ascii_row
            rows.append(ascii_row)

    # Write ASCII
    with open(output_path, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return len(rows), headers


def get_file_hash(filepath: Path) -> str:
    """Calculate MD5 hash."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# =============================================================================
# CKAN API Functions
# =============================================================================

def ckan_search(api_url: str, query: str) -> List[Dict]:
    """Search CKAN for datasets."""
    import json

    url = f"{api_url}package_search?q={query}&rows=50"

    try:
        ctx = get_ssl_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data.get('success'):
            return data.get('result', {}).get('results', [])
    except Exception as e:
        print(f"  CKAN search error: {e}")

    return []


def find_csv_resources(api_url: str, search_terms: List[str]) -> List[str]:
    """Find CSV download URLs from CKAN."""
    csv_urls = []

    for term in search_terms:
        print(f"  Searching: {term}")
        datasets = ckan_search(api_url, term)

        for ds in datasets:
            for resource in ds.get('resources', []):
                fmt = resource.get('format', '').upper()
                if fmt in ['CSV', 'TEXT/CSV']:
                    url = resource.get('url')
                    if url and url not in csv_urls:
                        csv_urls.append(url)
                        print(f"    Found: {resource.get('name', 'unnamed')}")

    return csv_urls


# =============================================================================
# Main Download Functions
# =============================================================================

def download_portal(portal_code: str, force: bool = False) -> Dict:
    """Download data from a single portal."""
    if portal_code not in PORTAL_DOWNLOADS:
        return {"success": False, "error": f"Unknown portal: {portal_code}"}

    config = PORTAL_DOWNLOADS[portal_code]
    country = config["country"]

    print(f"\n{'='*60}")
    print(f"Downloading: {config['name']}")
    print(f"{'='*60}")

    # Setup directories
    country_dir = BASE_DIR / country
    raw_dir = country_dir / "RAW"
    companies_dir = country_dir / "COMPANIES"

    for d in [raw_dir, companies_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Get URLs
    urls = config.get("urls", [])

    # If no direct URLs, search CKAN
    if not urls and config.get("api_url"):
        print("Searching CKAN for CSV resources...")
        urls = find_csv_resources(config["api_url"], config.get("search_terms", []))

    if not urls:
        return {"success": False, "error": "No CSV URLs found"}

    results = {
        "success": True,
        "portal": portal_code,
        "country": country,
        "files": [],
        "total_rows": 0,
    }

    timestamp = datetime.now().strftime("%Y%m%d")

    for i, url in enumerate(urls):
        print(f"\nDownloading file {i+1}/{len(urls)}...")
        print(f"  URL: {url[:80]}...")

        # Download to RAW
        raw_file = raw_dir / f"download_{timestamp}_{i}.csv"

        if not download_file(url, raw_file):
            print("  FAILED to download")
            continue

        # Check file size
        size_mb = raw_file.stat().st_size / 1024 / 1024
        print(f"  Downloaded: {size_mb:.1f} MB")

        if size_mb < 0.001:
            print("  SKIPPED: File too small")
            raw_file.unlink()
            continue

        # Convert to ASCII
        print("  Converting to ASCII...")
        output_file = companies_dir / f"companies_{timestamp}_{i}.csv"

        try:
            encoding = config.get("encoding")
            row_count, headers = convert_to_ascii_csv(raw_file, output_file, encoding)

            print(f"  Rows: {row_count:,}")
            print(f"  Columns: {len(headers)}")
            print(f"  Output: {output_file.name}")

            results["files"].append({
                "path": str(output_file),
                "rows": row_count,
                "columns": headers[:5],
            })
            results["total_rows"] += row_count

        except Exception as e:
            print(f"  Conversion error: {e}")

    # Log
    log_file = country_dir / "download_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | {portal_code} | {results['total_rows']} rows | {len(results['files'])} files\n")

    print(f"\n{'='*60}")
    print(f"COMPLETE: {results['total_rows']:,} total rows in {len(results['files'])} files")
    print(f"{'='*60}")

    return results


def download_all_portals() -> Dict:
    """Download from all configured portals."""
    results = {}

    for portal_code in PORTAL_DOWNLOADS.keys():
        try:
            results[portal_code] = download_portal(portal_code)
        except Exception as e:
            results[portal_code] = {"success": False, "error": str(e)}

        # Small delay between portals
        time.sleep(2)

    return results


def show_status():
    """Show download status for all portals."""
    print("\n" + "="*70)
    print("CKAN Download Status")
    print("="*70)

    for code, config in PORTAL_DOWNLOADS.items():
        country = config["country"]
        country_dir = BASE_DIR / country / "COMPANIES"

        if country_dir.exists():
            files = list(country_dir.glob("*.csv"))
            total_rows = 0
            latest = None

            for f in files:
                if f.stat().st_size > 0:
                    with open(f, 'r', errors='ignore') as fp:
                        total_rows += sum(1 for _ in fp)
                    if not latest or f.stat().st_mtime > latest.stat().st_mtime:
                        latest = f

            if files:
                latest_date = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d")
                print(f"{code:4} | {config['name'][:35]:35} | {total_rows:>10,} rows | {latest_date}")
            else:
                print(f"{code:4} | {config['name'][:35]:35} | {'No data':>10}")
        else:
            print(f"{code:4} | {config['name'][:35]:35} | {'Not downloaded':>10}")

    print("="*70)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="CKAN Download Skill")
    parser.add_argument("--portal", "-p", help="Portal code (SI, PT, SK, etc.)")
    parser.add_argument("--all", "-a", action="store_true", help="Download all portals")
    parser.add_argument("--status", "-s", action="store_true", help="Show status")
    parser.add_argument("--force", "-f", action="store_true", help="Force re-download")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.all:
        results = download_all_portals()
        print("\n=== Summary ===")
        for code, r in results.items():
            status = "OK" if r.get("success") else "FAILED"
            rows = r.get("total_rows", 0)
            print(f"{code}: {status} ({rows:,} rows)")
    elif args.portal:
        result = download_portal(args.portal.upper(), args.force)
        if not result.get("success"):
            print(f"ERROR: {result.get('error')}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
