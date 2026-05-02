#!/usr/bin/env python3
"""
European Building & Planning Permits Downloader

Downloads construction and planning permit data from:
- Eurostat Building Permits (all EU monthly)
- EU Open Data Portal (annual statistics)
- National statistics offices
- INSPIRE Geoportal (planning data)

Output: /opt/ACTIVE/OPENDATA/DATA/EU_PERMITS/
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

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_PERMITS")
EUROSTAT_DIR = OUTPUT_DIR / "EUROSTAT"
COUNTRY_DIR = OUTPUT_DIR / "BY_COUNTRY"

# Eurostat API
EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"

# Eurostat datasets for building permits
EUROSTAT_DATASETS = {
    "STS_COBP_M": {
        "name": "Building permits - monthly data",
        "desc": "Monthly building permits by type and country",
    },
    "STS_COBP_A": {
        "name": "Building permits - annual data",
        "desc": "Annual building permits aggregates",
    },
    "PERM_CNO": {
        "name": "Construction permits by type",
        "desc": "Permits for new residential/non-residential",
    },
}

# EU Open Data datasets
EU_OPENDATA = {
    "building_permits_annual": {
        "url": "https://data.europa.eu/data/datasets/building-permits",
        "download": "https://ec.europa.eu/eurostat/databrowser-backend/api/extraction/1.0/LIVE/false/sdmx/csv/STS_COBP_A",
    },
    "construction_output": {
        "url": "https://data.europa.eu/data/datasets/construction-output",
        "download": "https://ec.europa.eu/eurostat/databrowser-backend/api/extraction/1.0/LIVE/false/sdmx/csv/STS_COPR_M",
    },
}

# National statistics offices (building permits)
NATIONAL_SOURCES = {
    "DE": {
        "name": "Destatis - Germany",
        "url": "https://www.destatis.de/DE/Themen/Branchen-Unternehmen/Bauen/_inhalt.html",
        "api": "https://www-genesis.destatis.de/genesis/online",
        "datasets": ["31111", "31121"],  # Building permits tables
    },
    "FR": {
        "name": "INSEE - France",
        "url": "https://www.insee.fr/fr/statistiques?theme=7",
        "api": "https://api.insee.fr/series/BDM/V1/data",
    },
    "UK": {
        "name": "ONS - UK",
        "url": "https://www.ons.gov.uk/businessindustryandtrade/constructionindustry/datasets/constructionoutputingreatbritain",
    },
    "NL": {
        "name": "CBS - Netherlands",
        "url": "https://opendata.cbs.nl/statline/portal.html?_la=en&_catalog=CBS",
        "api": "https://opendata.cbs.nl/ODataApi/odata/83671ENG/TypedDataSet",
    },
    "SE": {
        "name": "SCB - Sweden",
        "url": "https://www.scb.se/en/finding-statistics/statistics-by-subject-area/housing-construction-and-building/construction/new-construction-of-residential-buildings/",
        "api": "https://api.scb.se/OV0104/v1/doris/en/ssd/BO/BO0101/BO0101A/LasperM",
    },
    "DK": {
        "name": "Statistics Denmark",
        "url": "https://www.dst.dk/en/Statistik/emner/erhvervslivsliv/bygge-og-anlaegsvirksomhed",
        "api": "https://api.statbank.dk/v1/data",
    },
    "NO": {
        "name": "SSB - Norway",
        "url": "https://www.ssb.no/en/bygg-bolig-og-eiendom",
        "api": "https://data.ssb.no/api/v0/en/table/",
    },
}


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
                        print(f"\r    Progress: {pct}%", end="", flush=True)

        print(f"\n    Saved: {output_path} ({os.path.getsize(output_path)//1024} KB)")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def download_eurostat():
    """Download Eurostat building permits data."""
    EUROSTAT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" EUROSTAT BUILDING PERMITS")
    print("="*60)

    for dataset_id, info in EUROSTAT_DATASETS.items():
        print(f"\n  Dataset: {info['name']}")

        # CSV download URL
        csv_url = f"https://ec.europa.eu/eurostat/databrowser-backend/api/extraction/1.0/LIVE/false/sdmx/csv/{dataset_id}"

        output_file = EUROSTAT_DIR / f"{dataset_id.lower()}.csv"
        download_file(csv_url, output_file)

        # Also try JSON format
        json_url = f"{EUROSTAT_API}/{dataset_id}?format=JSON"
        json_file = EUROSTAT_DIR / f"{dataset_id.lower()}.json"

        try:
            response = requests.get(json_url, timeout=120)
            if response.ok:
                with open(json_file, 'w') as f:
                    json.dump(response.json(), f, indent=2)
                print(f"    Also saved: {json_file.name}")
        except:
            pass

        time.sleep(2)

    return True


def download_eu_opendata():
    """Download from EU Open Data portal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" EU OPEN DATA PORTAL")
    print("="*60)

    for name, info in EU_OPENDATA.items():
        print(f"\n  Dataset: {name}")

        if "download" in info:
            output_file = OUTPUT_DIR / f"eu_opendata_{name}.csv"
            download_file(info["download"], output_file)
        else:
            print(f"    Manual download: {info['url']}")

        time.sleep(2)

    return True


def download_germany_permits():
    """Download German building permits from Destatis."""
    de_dir = COUNTRY_DIR / "DE"
    de_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" GERMANY - DESTATIS BUILDING PERMITS")
    print("="*60)

    # Destatis provides building permit statistics
    destatis_urls = [
        # Baugenehmigungen (building permits)
        ("https://www-genesis.destatis.de/genesis/online?operation=abruftabelleDownload&levelindex=0&levelid=1708355400000&downloadname=31111-0001&format=csv",
         "destatis_baugenehmigungen_monthly.csv"),

        # By building type
        ("https://www-genesis.destatis.de/genesis/online?operation=abruftabelleDownload&levelindex=0&levelid=1708355400000&downloadname=31111-0002&format=csv",
         "destatis_baugenehmigungen_type.csv"),
    ]

    for url, filename in destatis_urls:
        print(f"\n  File: {filename}")
        output_file = de_dir / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def download_netherlands_permits():
    """Download Dutch building permits from CBS."""
    nl_dir = COUNTRY_DIR / "NL"
    nl_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" NETHERLANDS - CBS BUILDING PERMITS")
    print("="*60)

    # CBS Open Data API
    cbs_tables = [
        ("83671ENG", "building_permits_monthly"),
        ("83109ENG", "construction_costs"),
    ]

    for table_id, name in cbs_tables:
        print(f"\n  Table: {name}")

        url = f"https://opendata.cbs.nl/ODataApi/odata/{table_id}/TypedDataSet?$format=json"
        output_file = nl_dir / f"cbs_{name}.json"

        try:
            response = requests.get(url, timeout=120)
            if response.ok:
                with open(output_file, 'w') as f:
                    json.dump(response.json(), f, indent=2)
                print(f"    Saved: {output_file}")
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(2)

    return True


def download_sweden_permits():
    """Download Swedish building permits from SCB."""
    se_dir = COUNTRY_DIR / "SE"
    se_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" SWEDEN - SCB BUILDING PERMITS")
    print("="*60)

    # SCB API for building permits
    scb_queries = [
        {
            "url": "https://api.scb.se/OV0104/v1/doris/en/ssd/BO/BO0101/BO0101A/LagenhetNy662M",
            "name": "new_dwellings_monthly",
        },
    ]

    for query in scb_queries:
        print(f"\n  Query: {query['name']}")

        try:
            # Get metadata first
            response = requests.get(query["url"], timeout=60)
            if response.ok:
                output_file = se_dir / f"scb_{query['name']}_meta.json"
                with open(output_file, 'w') as f:
                    json.dump(response.json(), f, indent=2)
                print(f"    Saved: {output_file}")
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(2)

    return True


def download_denmark_permits():
    """Download Danish building permits from Statistics Denmark."""
    dk_dir = COUNTRY_DIR / "DK"
    dk_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" DENMARK - DST BUILDING PERMITS")
    print("="*60)

    # Statistics Denmark API
    dst_tables = [
        ("BYGV11", "building_permits"),
        ("BYGV01", "construction_activity"),
    ]

    for table_id, name in dst_tables:
        print(f"\n  Table: {name}")

        url = f"https://api.statbank.dk/v1/tableinfo/{table_id}?format=JSON"
        output_file = dk_dir / f"dst_{name}_meta.json"

        try:
            response = requests.get(url, timeout=60)
            if response.ok:
                with open(output_file, 'w') as f:
                    json.dump(response.json(), f, indent=2)
                print(f"    Saved: {output_file}")
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(1)

    return True


def download_norway_permits():
    """Download Norwegian building permits from SSB."""
    no_dir = COUNTRY_DIR / "NO"
    no_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" NORWAY - SSB BUILDING PERMITS")
    print("="*60)

    # SSB (Statistics Norway) API
    ssb_tables = [
        ("03723", "building_starts"),
        ("05889", "building_permits"),
    ]

    for table_id, name in ssb_tables:
        print(f"\n  Table: {name}")

        url = f"https://data.ssb.no/api/v0/en/table/{table_id}"
        output_file = no_dir / f"ssb_{name}_meta.json"

        try:
            response = requests.get(url, timeout=60)
            if response.ok:
                with open(output_file, 'w') as f:
                    json.dump(response.json(), f, indent=2)
                print(f"    Saved: {output_file}")
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(1)

    return True


def download_all():
    """Download all building permits data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EUROSTAT_DIR.mkdir(parents=True, exist_ok=True)
    COUNTRY_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"Permits Download Started: {datetime.now()}\n\n")

    # 1. Eurostat (all EU)
    download_eurostat()

    # 2. EU Open Data
    download_eu_opendata()

    # 3. National sources
    download_germany_permits()
    download_netherlands_permits()
    download_sweden_permits()
    download_denmark_permits()
    download_norway_permits()

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
    print(" PERMITS DOWNLOAD STATUS")
    print("="*60)

    total_size = 0

    if EUROSTAT_DIR.exists():
        files = list(EUROSTAT_DIR.glob("*"))
        size = sum(f.stat().st_size for f in files if f.is_file())
        total_size += size
        print(f"\n  EUROSTAT: {len([f for f in files if f.is_file()])} files, {size//1024} KB")

    if COUNTRY_DIR.exists():
        for country_dir in sorted(COUNTRY_DIR.iterdir()):
            if country_dir.is_dir():
                files = list(country_dir.glob("*"))
                size = sum(f.stat().st_size for f in files if f.is_file())
                total_size += size
                print(f"  {country_dir.name}: {len([f for f in files if f.is_file()])} files, {size//1024} KB")

    print(f"\n  Total size: {total_size//1024} KB")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="European Building Permits Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--eurostat", action="store_true", help="Download Eurostat data")
    parser.add_argument("--eu", action="store_true", help="Download EU Open Data")
    parser.add_argument("--de", action="store_true", help="Download Germany data")
    parser.add_argument("--nl", action="store_true", help="Download Netherlands data")
    parser.add_argument("--se", action="store_true", help="Download Sweden data")
    parser.add_argument("--dk", action="store_true", help="Download Denmark data")
    parser.add_argument("--no", action="store_true", help="Download Norway data")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.eurostat:
        download_eurostat()
    elif args.eu:
        download_eu_opendata()
    elif args.de:
        download_germany_permits()
    elif args.nl:
        download_netherlands_permits()
    elif args.se:
        download_sweden_permits()
    elif args.dk:
        download_denmark_permits()
    elif args.no:
        download_norway_permits()
    else:
        parser.print_help()
