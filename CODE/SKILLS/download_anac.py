#!/usr/bin/env python3
"""
Italy ANAC (Autorita Nazionale Anticorruzione) Data Downloader

Downloads Italian public procurement data from:
- ANAC Open Data Portal (dati.anticorruzione.it)
- ANAC OCDS API (contracts >40K EUR)
- Italian government transparency data

Output: /opt/ACTIVE/OPENDATA/DATA/ITALY/ANAC/
"""

import csv
import gzip
import json
import os
import requests
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(text):
        if not text:
            return ""
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ITALY/ANAC")

# ANAC Open Data endpoints (UPDATED 2026)
ANAC_BASE = "https://dati.anticorruzione.it"
ANAC_API = f"{ANAC_BASE}/api/3/action/"

# Alternative ANAC endpoints (try multiple)
ANAC_OPENDATA = f"{ANAC_BASE}/opendata"
ANAC_DOWNLOAD = f"{ANAC_BASE}/superset/explore_json"

# ANAC datasets - direct download URLs
ANAC_DATASETS = {
    "stazioni_appaltanti": {
        "name": "Contracting Authorities",
        "urls": [
            f"{ANAC_BASE}/opendata/dataset/stazioni-appaltanti",
            f"{ANAC_BASE}/superset/explore_json/?datasource_type=table&datasource_id=1",
        ],
        "format": "csv"
    },
    "partecipanti": {
        "name": "Participants",
        "urls": [
            f"{ANAC_BASE}/opendata/dataset/partecipanti",
        ],
        "format": "csv"
    },
    "lavorazioni": {
        "name": "Works/Processing",
        "urls": [
            f"{ANAC_BASE}/opendata/dataset/lavorazioni",
        ],
        "format": "csv"
    },
    "cup": {
        "name": "CUP (Project Codes)",
        "urls": [
            f"{ANAC_BASE}/opendata/opendata/dataset/cup",
        ],
        "format": "csv"
    },
}

# ANAC OCDS bulk download URLs (monthly releases)
ANAC_OCDS_BASE = "https://dati.anticorruzione.it/opendata/ocds"

# OCP Data Registry - Italy ANAC (alternative source)
OCP_ITALY = "https://data.open-contracting.org/en/publication/87"
OCP_ITALY_DOWNLOAD = "https://data.open-contracting.org/en/publication/87/download?name=full.csv.tar.gz"


def download_file(url, output_path, chunk_size=8192):
    """Download a file with progress."""
    try:
        print(f"  Downloading: {url[:80]}...")
        response = requests.get(url, stream=True, timeout=300, allow_redirects=True)
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


def query_anac_api(endpoint):
    """Query ANAC CKAN API."""
    try:
        url = f"{ANAC_API}{endpoint}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("result", {})
    except Exception as e:
        print(f"    API Error: {e}")
        return {}


def get_dataset_resources(dataset_name):
    """Get resources (files) for a dataset."""
    result = query_anac_api(f"package_show?id={dataset_name}")
    return result.get("resources", [])


def download_anac_datasets():
    """Download main ANAC datasets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" ANAC DATASETS DOWNLOAD")
    print("="*60)

    # Try OCP Data Registry first (most reliable)
    print("\n  Trying OCP Data Registry (Italy ANAC)...")
    ocp_file = OUTPUT_DIR / "anac_ocp_full.csv.tar.gz"
    if not ocp_file.exists():
        if download_file(OCP_ITALY_DOWNLOAD, ocp_file):
            print("    OCP download successful!")
    else:
        print(f"    Skipping (exists): {ocp_file.name}")

    # Known direct download URLs for bulk data (multiple URL variants to try)
    direct_urls = [
        # Contracts by year - try multiple URL patterns
        ([
            "https://dati.anticorruzione.it/opendata/download/dataset/contratti/2024_contratti.csv.gz",
            "https://dati.anticorruzione.it/superset/explore_json/?datasource_type=table&slice_id=contratti_2024",
        ], "contratti_2024.csv.gz"),
        ([
            "https://dati.anticorruzione.it/opendata/download/dataset/contratti/2023_contratti.csv.gz",
        ], "contratti_2023.csv.gz"),
        ([
            "https://dati.anticorruzione.it/opendata/download/dataset/contratti/2022_contratti.csv.gz",
        ], "contratti_2022.csv.gz"),

        # Economic operators
        ([
            "https://dati.anticorruzione.it/opendata/download/dataset/operatori_economici/operatori_economici.csv.gz",
            "https://dati.anticorruzione.it/opendata/dataset/operatori-economici/download",
        ], "operatori_economici.csv.gz"),

        # Contracting authorities
        ([
            "https://dati.anticorruzione.it/opendata/download/dataset/stazioni_appaltanti/stazioni_appaltanti.csv.gz",
            "https://dati.anticorruzione.it/opendata/dataset/stazioni-appaltanti/download",
        ], "stazioni_appaltanti.csv.gz"),

        # Contract awards
        ([
            "https://dati.anticorruzione.it/opendata/download/dataset/aggiudicazioni/aggiudicazioni.csv.gz",
        ], "aggiudicazioni.csv.gz"),
    ]

    for urls, filename in direct_urls:
        print(f"\n  File: {filename}")
        output_file = OUTPUT_DIR / filename

        if output_file.exists():
            print(f"    Skipping (exists): {filename}")
            continue

        success = False
        for url in urls:
            if download_file(url, output_file):
                success = True
                break
            time.sleep(1)

        if not success:
            print(f"    WARNING: Could not download {filename}")

        time.sleep(2)

    return True


def download_anac_ocds():
    """Download ANAC OCDS format data."""
    ocds_dir = OUTPUT_DIR / "OCDS"
    ocds_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" ANAC OCDS DATA DOWNLOAD")
    print("="*60)

    # OCDS releases by year
    for year in range(2020, 2026):
        print(f"\n  Year: {year}")

        for month in range(1, 13):
            filename = f"ocds_releases_{year}_{month:02d}.json.gz"
            url = f"{ANAC_OCDS_BASE}/{year}/{filename}"
            output_file = ocds_dir / filename

            if output_file.exists():
                print(f"    Skipping (exists): {filename}")
                continue

            download_file(url, output_file)
            time.sleep(1)

    return True


def download_via_api():
    """Download data via ANAC CKAN API."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" ANAC API DOWNLOAD")
    print("="*60)

    # List available datasets
    datasets = query_anac_api("package_list")

    if isinstance(datasets, list):
        print(f"\n  Available datasets: {len(datasets)}")

        for ds_name in datasets[:10]:  # First 10
            print(f"\n  Dataset: {ds_name}")
            resources = get_dataset_resources(ds_name)

            for res in resources:
                if res.get("format", "").lower() in ["csv", "json"]:
                    url = res.get("url", "")
                    name = res.get("name", ds_name)
                    fmt = res.get("format", "csv").lower()

                    output_file = OUTPUT_DIR / f"{name}.{fmt}"
                    download_file(url, output_file)
                    time.sleep(2)

    return True


def extract_contacts():
    """Extract contacts from downloaded ANAC data."""
    print("\n" + "="*60)
    print(" EXTRACTING CONTACTS FROM ANAC")
    print("="*60)

    contacts = []

    # Process stazioni_appaltanti (contracting authorities)
    sa_file = OUTPUT_DIR / "stazioni_appaltanti.csv.gz"
    if sa_file.exists():
        print(f"\n  Processing: {sa_file.name}")
        try:
            with gzip.open(sa_file, 'rt', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter=';')

                for row in reader:
                    contact = {
                        'id': row.get('cf_sa', ''),
                        'company': to_ascii(row.get('denominazione', ''))[:200],
                        'type': 'contracting_authority',
                        'address': to_ascii(row.get('indirizzo', ''))[:200],
                        'city': to_ascii(row.get('comune', ''))[:100],
                        'postal_code': row.get('cap', '')[:10],
                        'province': row.get('provincia', ''),
                        'region': row.get('regione', ''),
                        'email': row.get('email', row.get('pec', ''))[:200].lower(),
                        'phone': row.get('telefono', '')[:50],
                        'website': row.get('sito_web', '')[:200],
                        'country': 'IT',
                    }

                    if contact['email'] or contact['phone']:
                        contacts.append(contact)

        except Exception as e:
            print(f"    Error: {e}")

    # Process operatori_economici (economic operators)
    op_file = OUTPUT_DIR / "operatori_economici.csv.gz"
    if op_file.exists():
        print(f"\n  Processing: {op_file.name}")
        try:
            with gzip.open(op_file, 'rt', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter=';')

                for row in reader:
                    contact = {
                        'id': row.get('cf_operatore', row.get('piva', '')),
                        'company': to_ascii(row.get('ragione_sociale', row.get('denominazione', '')))[:200],
                        'type': 'economic_operator',
                        'address': to_ascii(row.get('indirizzo', ''))[:200],
                        'city': to_ascii(row.get('comune', ''))[:100],
                        'postal_code': row.get('cap', '')[:10],
                        'province': row.get('provincia', ''),
                        'email': row.get('email', row.get('pec', ''))[:200].lower(),
                        'phone': row.get('telefono', '')[:50],
                        'website': row.get('sito_web', '')[:200],
                        'country': 'IT',
                    }

                    if contact['email'] or contact['phone']:
                        contacts.append(contact)

        except Exception as e:
            print(f"    Error: {e}")

    # Save contacts
    if contacts:
        output_file = OUTPUT_DIR / "anac_contacts.csv"
        fieldnames = ['id', 'company', 'type', 'address', 'city', 'postal_code',
                      'province', 'region', 'email', 'phone', 'website', 'country']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(contacts)

        print(f"\n  Extracted: {len(contacts):,} contacts")
        print(f"  Saved: {output_file}")

    return contacts


def download_all():
    """Download all ANAC data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"ANAC Download Started: {datetime.now()}\n\n")

    # 1. Download main datasets
    download_anac_datasets()

    # 2. Download OCDS data
    download_anac_ocds()

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
    print(" ANAC DOWNLOAD STATUS")
    print("="*60)

    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.rglob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        print(f"\n  Directory: {OUTPUT_DIR}")
        print(f"  Files: {len([f for f in files if f.is_file()])}")
        print(f"  Size: {total_size / 1024 / 1024:.1f} MB")

        print("\n  Files:")
        for f in sorted(OUTPUT_DIR.glob("*")):
            if f.is_file():
                size = f.stat().st_size / 1024 / 1024
                print(f"    {f.name}: {size:.1f} MB")
    else:
        print(f"\n  Directory not found: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Italian ANAC Data Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--datasets", action="store_true", help="Download main datasets")
    parser.add_argument("--ocds", action="store_true", help="Download OCDS data")
    parser.add_argument("--api", action="store_true", help="Download via API")
    parser.add_argument("--extract", action="store_true", help="Extract contacts")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.datasets:
        download_anac_datasets()
    elif args.ocds:
        download_anac_ocds()
    elif args.api:
        download_via_api()
    elif args.extract:
        extract_contacts()
    else:
        parser.print_help()
