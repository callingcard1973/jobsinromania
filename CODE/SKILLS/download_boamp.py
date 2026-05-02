#!/usr/bin/env python3
"""
France BOAMP (Bulletin Officiel des Annonces des Marches Publics) Downloader

Downloads French public procurement data from:
- BOAMP Open Data (official government source)
- BOAMP OpenDataSoft API
- BeauAMP dataset (Zenodo - 2015-2023 historical data)

Output: /opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT/BOAMP/
"""

import csv
import gzip
import json
import os
import requests
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(text):
        if not text:
            return ""
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/FRANCE/BOAMP")

# BOAMP OpenDataSoft API v2.1 (WORKING)
BOAMP_BASE = "https://boamp-datadila.opendatasoft.com"
BOAMP_API = f"{BOAMP_BASE}/api/explore/v2.1/catalog/datasets/boamp/records"
BOAMP_EXPORT = f"{BOAMP_BASE}/api/explore/v2.1/catalog/datasets/boamp/exports/csv"

# Alternative BOAMP.fr API
BOAMP_FR_API = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
BOAMP_FR_EXPORT = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/exports/csv"

# BeauAMP (historical dataset 2015-2023 on Zenodo)
BEAUAMP_URL = "https://zenodo.org/records/11001277/files/BeauAMP_2015-2023.csv.gz?download=1"

# data.gouv.fr alternative (DECP - Donnees essentielles commande publique)
DATAGOUV_DECP = "https://www.data.gouv.fr/fr/datasets/r/16962018-5c31-4296-9454-5998585496d2"  # DECP JSON
DATAGOUV_BOAMP = "https://www.data.gouv.fr/fr/datasets/boamp-donnees-essentielles-de-la-commande-publique/"

# BOAMP datasets available on OpenDataSoft
BOAMP_DATASETS = {
    "main": "boamp",  # 1.6M+ records
    "piamp_preprod": "boamp_piamp_preprod",
}

# BOAMP dataset ID
BOAMP_DATASET = "boamp"


def download_file(url, output_path, chunk_size=8192):
    """Download a file with progress."""
    try:
        print(f"  Downloading: {url[:80]}...")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        total = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = (downloaded * 100) // total
                        print(f"\r    Progress: {pct}% ({downloaded//1024//1024}MB)", end="", flush=True)

        print(f"\n    Saved: {output_path} ({os.path.getsize(output_path)//1024//1024}MB)")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def query_boamp_api(dataset="boamp", limit=100, offset=0, year=None):
    """Query BOAMP OpenDataSoft API v2.1."""
    # v2.1 uses 'limit' and 'offset' instead of 'rows' and 'start'
    params = {
        "limit": limit,
        "offset": offset,
        "order_by": "datepublication DESC",
    }

    if year:
        params["where"] = f"datepublication >= '{year}-01-01' AND datepublication <= '{year}-12-31'"

    try:
        response = requests.get(BOAMP_API, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        # v2.1 returns results directly, not wrapped in 'records'
        return data.get("results", [])
    except Exception as e:
        print(f"    API Error: {e}")
        # Try alternate endpoint
        try:
            response = requests.get(BOAMP_FR_API, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e2:
            print(f"    Fallback API Error: {e2}")
            return []


def download_boamp_bulk(year=None):
    """Download BOAMP bulk data via API v2.1 export."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" BOAMP BULK EXPORT (OpenDataSoft API v2.1)")
    print("="*60)

    for name, dataset in BOAMP_DATASETS.items():
        print(f"\n  Dataset: {name}")

        # v2.1 export endpoint format
        export_url = f"{BOAMP_BASE}/api/explore/v2.1/catalog/datasets/{dataset}/exports/csv"

        # Build export params (v2.1 format)
        params = {
            "use_labels": "true",
            "delimiter": ",",
        }

        if year:
            params["where"] = f"datepublication >= '{year}-01-01' AND datepublication <= '{year}-12-31'"
            filename = f"boamp_{name}_{year}.csv"
        else:
            filename = f"boamp_{name}_all.csv"

        output_file = OUTPUT_DIR / filename

        try:
            url = f"{export_url}?{requests.compat.urlencode(params)}"
            print(f"  Exporting: {url[:80]}...")

            response = requests.get(url, timeout=600, stream=True)
            response.raise_for_status()

            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            size = os.path.getsize(output_file)
            print(f"    Saved: {output_file} ({size//1024//1024}MB)")

        except Exception as e:
            print(f"    Error: {e}")
            # Try alternate endpoint
            try:
                alt_url = f"https://www.boamp.fr/api/explore/v2.1/catalog/datasets/{dataset}/exports/csv"
                alt_url = f"{alt_url}?{requests.compat.urlencode(params)}"
                print(f"  Trying alternate: {alt_url[:80]}...")

                response = requests.get(alt_url, timeout=600, stream=True)
                response.raise_for_status()

                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                size = os.path.getsize(output_file)
                print(f"    Saved: {output_file} ({size//1024//1024}MB)")
            except Exception as e2:
                print(f"    Fallback Error: {e2}")

        time.sleep(2)

    return True


def download_beauamp():
    """Download BeauAMP historical dataset from Zenodo."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" BeauAMP HISTORICAL DATASET (2015-2023)")
    print("="*60)

    output_file = OUTPUT_DIR / "beauamp_2015_2023.csv.gz"

    print(f"\n  Source: Zenodo (doi:10.5281/zenodo.11001277)")
    print(f"  Contains: ~300,000 French procurement contracts")

    # Try direct Zenodo file download
    zenodo_urls = [
        BEAUAMP_URL,
        "https://zenodo.org/records/11001277/files/BeauAMP_2015-2023.csv.gz?download=1",
        "https://zenodo.org/api/records/11001277/files/BeauAMP_2015-2023.csv.gz/content",
    ]

    for url in zenodo_urls:
        print(f"  Trying: {url[:60]}...")
        if download_file(url, output_file):
            return True
        time.sleep(2)

    print("  WARNING: Could not download BeauAMP. Manual download may be required.")
    print(f"  Visit: https://zenodo.org/records/11001277")
    return False


def download_boamp_by_year(years):
    """Download BOAMP data for specific years."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(f" BOAMP DOWNLOAD BY YEAR: {years}")
    print("="*60)

    for year in years:
        print(f"\n  Year: {year}")
        download_boamp_bulk(year=year)

    return True


def extract_contacts():
    """Extract contacts from downloaded BOAMP data."""
    print("\n" + "="*60)
    print(" EXTRACTING CONTACTS FROM BOAMP")
    print("="*60)

    contacts = []
    csv_files = list(OUTPUT_DIR.glob("*.csv"))

    for csv_file in csv_files:
        print(f"\n  Processing: {csv_file.name}")

        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    contact = {
                        'id': row.get('id', ''),
                        'company': to_ascii(row.get('organisme', row.get('denomination', '')))[:200],
                        'address': to_ascii(row.get('adresse', ''))[:200],
                        'city': to_ascii(row.get('ville', ''))[:100],
                        'postal_code': row.get('codepostal', '')[:10],
                        'email': row.get('email', row.get('mel', ''))[:200].lower(),
                        'phone': row.get('telephone', '')[:50],
                        'website': row.get('urlprofil', row.get('url', ''))[:200],
                        'type': row.get('nature', row.get('typemarche', '')),
                        'date': row.get('datepublication', ''),
                        'cpv': row.get('codecpv', ''),
                        'value': row.get('montant', ''),
                    }

                    if contact['email'] or contact['phone']:
                        contacts.append(contact)

        except Exception as e:
            print(f"    Error: {e}")

    # Save contacts
    if contacts:
        output_file = OUTPUT_DIR / "boamp_contacts.csv"
        fieldnames = ['id', 'company', 'address', 'city', 'postal_code', 'email',
                      'phone', 'website', 'type', 'date', 'cpv', 'value']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(contacts)

        print(f"\n  Extracted: {len(contacts):,} contacts")
        print(f"  Saved: {output_file}")

    return contacts


def download_all():
    """Download all BOAMP data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"BOAMP Download Started: {datetime.now()}\n\n")

    # 1. Download BeauAMP historical (2015-2023)
    download_beauamp()

    # 2. Download current BOAMP data (2024-2025)
    download_boamp_by_year([2024, 2025])

    # 3. Extract contacts
    extract_contacts()

    with open(log_file, "a") as f:
        f.write(f"\nDownload Completed: {datetime.now()}\n")

    print("\n" + "="*60)
    print(" DOWNLOAD COMPLETE")
    print("="*60)
    print(f"\n  Output: {OUTPUT_DIR}")

    return True


def status():
    """Check download status."""
    print("\n" + "="*60)
    print(" BOAMP DOWNLOAD STATUS")
    print("="*60)

    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        print(f"\n  Directory: {OUTPUT_DIR}")
        print(f"  Files: {len([f for f in files if f.is_file()])}")
        print(f"  Size: {total_size / 1024 / 1024:.1f} MB")

        print("\n  Files:")
        for f in sorted(files):
            if f.is_file():
                size = f.stat().st_size / 1024 / 1024
                print(f"    {f.name}: {size:.1f} MB")
    else:
        print(f"\n  Directory not found: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="French BOAMP Data Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--beauamp", action="store_true", help="Download BeauAMP historical data")
    parser.add_argument("--bulk", action="store_true", help="Download BOAMP bulk export")
    parser.add_argument("--years", nargs="+", type=int, help="Download specific years")
    parser.add_argument("--extract", action="store_true", help="Extract contacts from downloaded data")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.beauamp:
        download_beauamp()
    elif args.bulk:
        download_boamp_bulk()
    elif args.years:
        download_boamp_by_year(args.years)
    elif args.extract:
        extract_contacts()
    else:
        parser.print_help()
