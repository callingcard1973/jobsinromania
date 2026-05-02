#!/usr/bin/env python3
"""
OpenTender / DIGIWHIST Data Downloader

Downloads procurement data from:
- OpenTender (opentender.eu) - 35 countries
- DIGIWHIST government transparency data
- Open Contracting Data Standard (OCDS) registry

Output: /opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT/OPENTENDER/
"""

import csv
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

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT/OPENTENDER")
OCDS_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT/OCDS")

# OCP Data Registry - TED/OpenTender bulk downloads (WORKING)
OCP_TED_BASE = "https://data.open-contracting.org/en/publication/150/download"

# OCP country-specific publications (WORKING)
OCP_COUNTRY_PUBS = {
    "eu_ted": {"pub_id": 150, "name": "TED (EU-wide)"},
    "italy": {"pub_id": 87, "name": "Italy OpenTender"},
    "netherlands": {"pub_id": 71, "name": "Netherlands OpenTender"},
    "uk": {"pub_id": 92, "name": "UK OpenTender"},
    "france": {"pub_id": 88, "name": "France OpenTender"},
    "spain": {"pub_id": 89, "name": "Spain OpenTender"},
    "germany": {"pub_id": 136, "name": "Germany BMI"},
    "poland": {"pub_id": 85, "name": "Poland OpenTender"},
}

# OCDS Data Registry sources (WORKING)
OCDS_SOURCES = {
    "uk_contracts_finder": {
        "url": "https://data.open-contracting.org/en/publication/16",
        "download": "https://data.open-contracting.org/en/publication/16/download?name=full.csv.tar.gz",
        "country": "UK"
    },
    "germany_bmi": {
        "url": "https://data.open-contracting.org/en/publication/136",
        "download": "https://data.open-contracting.org/en/publication/136/download?name=full.csv.tar.gz",
        "country": "DE"
    },
    "georgia": {
        "url": "https://data.open-contracting.org/en/publication/6",
        "download": "https://data.open-contracting.org/en/publication/6/download?name=full.csv.tar.gz",
        "country": "GE"
    },
    "colombia": {
        "url": "https://data.open-contracting.org/en/publication/3",
        "download": "https://data.open-contracting.org/en/publication/3/download?name=full.csv.tar.gz",
        "country": "CO"
    },
    "paraguay": {
        "url": "https://data.open-contracting.org/en/publication/5",
        "download": "https://data.open-contracting.org/en/publication/5/download?name=full.csv.tar.gz",
        "country": "PY"
    },
    "mexico": {
        "url": "https://data.open-contracting.org/en/publication/9",
        "download": "https://data.open-contracting.org/en/publication/9/download?name=full.csv.tar.gz",
        "country": "MX"
    },
}

# DIGIWHIST countries (govtransparency.eu)
DIGIWHIST_COUNTRIES = [
    "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES",
    "FI", "FR", "GB", "GE", "GR", "HR", "HU", "IE", "IS", "IT",
    "LT", "LU", "LV", "MT", "NL", "NO", "PL", "PT", "RO", "RS",
    "SE", "SI", "SK", "UA"
]


def download_file(url, output_path, chunk_size=8192):
    """Download a file with progress."""
    try:
        print(f"  Downloading: {url[:80]}...")
        response = requests.get(url, stream=True, timeout=60)
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
                        print(f"\r    Progress: {pct}% ({downloaded//1024}KB)", end="", flush=True)

        print(f"\n    Saved: {output_path}")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def query_opentender(country, limit=10000):
    """Query OpenTender GraphQL API for a country."""
    query = """
    query getTenders($country: String!, $first: Int!) {
        tenders(filter: {country: $country}, first: $first) {
            edges {
                node {
                    id
                    title
                    buyer {
                        name
                        address
                        city
                        country
                    }
                    lots {
                        bids {
                            bidder {
                                name
                                address
                                city
                                country
                            }
                            value
                        }
                    }
                    procedureType
                    supplyType
                    publications {
                        publicationDate
                        source
                    }
                    cpvs
                    finalPrice
                }
            }
        }
    }
    """

    try:
        response = requests.post(
            OPENTENDER_API,
            json={"query": query, "variables": {"country": country, "first": limit}},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("tenders", {}).get("edges", [])
    except Exception as e:
        print(f"    Error querying {country}: {e}")
        return []


def download_opentender_bulk():
    """Download bulk data from OCP Data Registry (OpenTender/TED)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" OCP DATA REGISTRY - TED/OPENTENDER BULK DOWNLOAD")
    print("="*60)
    print("  Source: data.open-contracting.org")
    print("  License: CC BY-NC-SA 4.0")

    # Download TED data by year (CSV format)
    years = [2023, 2024, 2025]

    for year in years:
        print(f"\n  Downloading TED {year}...")
        url = f"{OCP_TED_BASE}?name={year}.csv.tar.gz"
        output_file = OUTPUT_DIR / f"ted_ocds_{year}.csv.tar.gz"

        if not output_file.exists():
            download_file(url, output_file)
        else:
            print(f"    Skipping (exists): {output_file.name}")
        time.sleep(2)

    # Download country-specific data
    for country, info in OCP_COUNTRY_PUBS.items():
        if country == "eu_ted":
            continue  # Already downloaded above

        print(f"\n  Downloading {info['name']}...")
        pub_id = info['pub_id']
        url = f"https://data.open-contracting.org/en/publication/{pub_id}/download?name=full.csv.tar.gz"
        output_file = OUTPUT_DIR / f"ocp_{country}_full.csv.tar.gz"

        if not output_file.exists():
            download_file(url, output_file)
        else:
            print(f"    Skipping (exists): {output_file.name}")
        time.sleep(3)

    return True


def download_ocds_sources():
    """Download from OCDS Data Registry."""
    OCDS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" OCDS DATA REGISTRY DOWNLOAD")
    print("="*60)

    for name, source in OCDS_SOURCES.items():
        print(f"\n  Source: {name} ({source['country']})")

        if "download" in source and source["download"].startswith("http"):
            ext = source["download"].split(".")[-1]
            if ext == "gz":
                ext = source["download"].split(".")[-2] + ".gz"

            output_file = OCDS_DIR / f"ocds_{name}.{ext}"
            download_file(source["download"], output_file)
        else:
            print(f"    Manual download required: {source['url']}")

        time.sleep(2)

    return True


def download_digiwhist():
    """Download DIGIWHIST data from govtransparency.eu."""
    digiwhist_dir = OUTPUT_DIR / "DIGIWHIST"
    digiwhist_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" DIGIWHIST DATABASE DOWNLOAD")
    print("="*60)

    # DIGIWHIST provides CSV downloads at:
    # https://govtransparency.eu/category/databases/

    base_url = "https://opentender.eu/data/digiwhist/"

    for country in DIGIWHIST_COUNTRIES:
        print(f"\n  Country: {country}")

        url = f"{base_url}{country.lower()}_tenders.csv.gz"
        output_file = digiwhist_dir / f"{country.lower()}_tenders.csv.gz"

        download_file(url, output_file)
        time.sleep(1)

    return True


def download_all():
    """Download all OpenTender/DIGIWHIST/OCDS data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OCDS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"OpenTender Download Started: {datetime.now()}\n\n")

    # 1. Download OpenTender bulk exports
    download_opentender_bulk()

    # 2. Download DIGIWHIST data
    download_digiwhist()

    # 3. Download OCDS registry sources
    download_ocds_sources()

    with open(log_file, "a") as f:
        f.write(f"\nDownload Completed: {datetime.now()}\n")

    print("\n" + "="*60)
    print(" DOWNLOAD COMPLETE")
    print("="*60)
    print(f"\n  Output: {OUTPUT_DIR}")
    print(f"  OCDS: {OCDS_DIR}")

    return True


def status():
    """Check download status."""
    print("\n" + "="*60)
    print(" OPENTENDER DOWNLOAD STATUS")
    print("="*60)

    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.rglob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        print(f"\n  Directory: {OUTPUT_DIR}")
        print(f"  Files: {len([f for f in files if f.is_file()])}")
        print(f"  Size: {total_size / 1024 / 1024:.1f} MB")
    else:
        print(f"\n  Directory not found: {OUTPUT_DIR}")

    if OCDS_DIR.exists():
        files = list(OCDS_DIR.rglob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        print(f"\n  OCDS Directory: {OCDS_DIR}")
        print(f"  Files: {len([f for f in files if f.is_file()])}")
        print(f"  Size: {total_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenTender/DIGIWHIST Data Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--opentender", action="store_true", help="Download OpenTender bulk")
    parser.add_argument("--digiwhist", action="store_true", help="Download DIGIWHIST data")
    parser.add_argument("--ocds", action="store_true", help="Download OCDS sources")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.opentender:
        download_opentender_bulk()
    elif args.digiwhist:
        download_digiwhist()
    elif args.ocds:
        download_ocds_sources()
    else:
        parser.print_help()
