#!/usr/bin/env python3
"""
Netherlands TenderNed Data Downloader

Downloads Dutch public procurement data from:
- TenderNed API (tenderned.nl)
- Dutch Open Data Portal (data.overheid.nl)
- PIANOo (government procurement expertise center)

Output: /opt/ACTIVE/OPENDATA/DATA/NETHERLANDS/TENDERNED/
"""

import csv
import json
import os
import requests
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
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

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/NETHERLANDS/TENDERNED")

# TenderNed API endpoints (public webservice)
TENDERNED_API = "https://www.tenderned.nl/papi/tenderned-rs-tns/v2"
TENDERNED_SEARCH = f"{TENDERNED_API}/publicaties"

# TenderNed datasets page
TENDERNED_DATASETS = "https://www.tenderned.nl/cms/nl/aanbesteden-in-cijfers/datasets-aanbestedingen"

# Dutch Open Data
OPENDATA_NL = "https://data.overheid.nl"
OPENDATA_NL_API = "https://data.overheid.nl/data/api/3/action"

# OCP Data Registry - Netherlands (reliable fallback)
OCP_NL = "https://data.open-contracting.org/en/publication/71"
OCP_NL_DOWNLOAD = "https://data.open-contracting.org/en/publication/71/download?name=full.csv.tar.gz"

# Dataset URLs
DATASETS = {
    "aanbestedingskalender": {
        "name": "Tender Calendar",
        "url": "https://data.overheid.nl/data/dataset/aanbestedingskalender-rijksoverheid",
        "format": "csv"
    },
    "contracten_rijk": {
        "name": "Government Contracts",
        "url": "https://data.overheid.nl/data/dataset/contractenregister-rijksoverheid",
        "format": "csv"
    },
    "tenderned_notices": {
        "name": "TenderNed Notices",
        "url": "https://data.overheid.nl/en/dataset/aankondigingen-van-overheidsopdrachten---tenderned",
        "format": "xml"
    }
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
                        print(f"\r    Progress: {pct}% ({downloaded//1024}KB)", end="", flush=True)

        print(f"\n    Saved: {output_path} ({os.path.getsize(output_path)//1024}KB)")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def query_tenderned_api(params=None, limit=100, offset=0):
    """Query TenderNed API for tender notices."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    default_params = {
        "pageSize": limit,
        "pageNumber": offset // limit + 1,
    }

    if params:
        default_params.update(params)

    try:
        response = requests.get(
            TENDERNED_SEARCH,
            headers=headers,
            params=default_params,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"    API Error: {e}")
        return {}


def download_tenderned_via_api(days_back=365, max_records=10000):
    """Download tender notices via TenderNed API."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" TenderNed API DOWNLOAD")
    print("="*60)

    records = []
    offset = 0
    page_size = 100

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    params = {
        "datumVanaf": start_date.strftime("%Y-%m-%d"),
        "datumTot": end_date.strftime("%Y-%m-%d"),
    }

    while len(records) < max_records:
        print(f"\r  Fetching records {offset} - {offset + page_size}...", end="", flush=True)

        data = query_tenderned_api(params=params, limit=page_size, offset=offset)

        if not data:
            break

        items = data.get("publicaties", data.get("items", []))
        if not items:
            break

        for item in items:
            record = {
                'id': item.get('publicatieId', item.get('id', '')),
                'title': to_ascii(item.get('titel', item.get('title', '')))[:300],
                'type': item.get('soort', item.get('type', '')),
                'procedure': item.get('procedure', ''),
                'cpv': item.get('cpvCode', item.get('cpv', '')),
                'deadline': item.get('sluitingsdatum', item.get('deadline', '')),
                'publication_date': item.get('publicatiedatum', item.get('publishDate', '')),
                'authority': to_ascii(item.get('aanbestedendeDienst', {}).get('naam', ''))[:200],
                'authority_city': to_ascii(item.get('aanbestedendeDienst', {}).get('plaats', ''))[:100],
                'email': item.get('contactpersoon', {}).get('email', '')[:200].lower(),
                'phone': item.get('contactpersoon', {}).get('telefoon', '')[:50],
                'website': item.get('url', item.get('link', ''))[:200],
                'value': item.get('waarde', {}).get('bedrag', ''),
                'currency': item.get('waarde', {}).get('valuta', 'EUR'),
            }
            records.append(record)

        offset += page_size
        time.sleep(0.5)  # Rate limit

        if len(items) < page_size:
            break

    print(f"\n  Total records: {len(records)}")

    # Save to CSV
    if records:
        output_file = OUTPUT_DIR / f"tenderned_notices_{datetime.now().strftime('%Y%m%d')}.csv"
        fieldnames = ['id', 'title', 'type', 'procedure', 'cpv', 'deadline',
                      'publication_date', 'authority', 'authority_city', 'email',
                      'phone', 'website', 'value', 'currency']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        print(f"  Saved: {output_file}")

    return records


def download_opendata_nl():
    """Download from Dutch Open Data portal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" DUTCH OPEN DATA DOWNLOAD")
    print("="*60)

    # Direct download URLs for government procurement data
    downloads = [
        # Aanbestedingskalender (tender calendar)
        ("https://data.overheid.nl/sites/default/files/dataset/aanbestedingskalender.csv",
         "aanbestedingskalender.csv"),

        # Contracten register
        ("https://data.overheid.nl/sites/default/files/dataset/contractenregister.csv",
         "contractenregister_rijk.csv"),

        # CBS procurement statistics
        ("https://opendata.cbs.nl/CsvDownload/csv/84899NED.csv",
         "cbs_aanbestedingen_stats.csv"),
    ]

    for url, filename in downloads:
        print(f"\n  File: {filename}")
        output_file = OUTPUT_DIR / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def download_pianoo():
    """Download PIANOo procurement data."""
    pianoo_dir = OUTPUT_DIR / "PIANOo"
    pianoo_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" PIANOo DATA DOWNLOAD")
    print("="*60)

    # PIANOo provides procurement expertise and data
    pianoo_urls = [
        ("https://www.pianoo.nl/sites/default/files/documents/drempelwaarden.csv",
         "drempelwaarden.csv"),  # Threshold values
    ]

    for url, filename in pianoo_urls:
        print(f"\n  File: {filename}")
        output_file = pianoo_dir / filename
        download_file(url, output_file)
        time.sleep(1)

    return True


def extract_contacts():
    """Extract contacts from downloaded TenderNed data."""
    print("\n" + "="*60)
    print(" EXTRACTING CONTACTS")
    print("="*60)

    contacts = []

    # Process all CSV files
    for csv_file in OUTPUT_DIR.glob("*.csv"):
        if "contacts" in csv_file.name:
            continue

        print(f"\n  Processing: {csv_file.name}")
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Try multiple column name variants
                    email = row.get('email', row.get('Email', row.get('e-mail', '')))
                    phone = row.get('phone', row.get('telefoon', row.get('Telefoon', '')))
                    company = row.get('authority', row.get('organisatie', row.get('naam', '')))

                    if email or phone:
                        contact = {
                            'id': row.get('id', row.get('ID', '')),
                            'company': to_ascii(company)[:200],
                            'city': to_ascii(row.get('city', row.get('plaats', '')))[:100],
                            'email': email[:200].lower() if email else '',
                            'phone': phone[:50] if phone else '',
                            'website': row.get('website', row.get('url', ''))[:200],
                            'type': row.get('type', row.get('soort', '')),
                            'country': 'NL',
                        }
                        contacts.append(contact)

        except Exception as e:
            print(f"    Error: {e}")

    # Deduplicate by email
    seen_emails = set()
    unique_contacts = []
    for c in contacts:
        if c['email'] and c['email'] not in seen_emails:
            seen_emails.add(c['email'])
            unique_contacts.append(c)
        elif not c['email']:
            unique_contacts.append(c)

    # Save contacts
    if unique_contacts:
        output_file = OUTPUT_DIR / "tenderned_contacts.csv"
        fieldnames = ['id', 'company', 'city', 'email', 'phone', 'website', 'type', 'country']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_contacts)

        print(f"\n  Extracted: {len(unique_contacts):,} contacts")
        print(f"  Saved: {output_file}")

    return unique_contacts


def download_ocp_netherlands():
    """Download Netherlands data from OCP Data Registry (most reliable)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" OCP DATA REGISTRY - NETHERLANDS")
    print("="*60)

    ocp_file = OUTPUT_DIR / "netherlands_ocp_full.csv.tar.gz"
    if not ocp_file.exists():
        print(f"\n  Downloading from OCP Data Registry...")
        if download_file(OCP_NL_DOWNLOAD, ocp_file):
            print("    OCP download successful!")
            return True
    else:
        print(f"    Skipping (exists): {ocp_file.name}")
        return True

    return False


def download_all():
    """Download all TenderNed data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"TenderNed Download Started: {datetime.now()}\n\n")

    # 1. Download from OCP Registry (most reliable)
    download_ocp_netherlands()

    # 2. Download via TenderNed API (may require auth)
    download_tenderned_via_api()

    # 3. Download from Open Data portal
    download_opendata_nl()

    # 4. Download PIANOo data
    download_pianoo()

    # 5. Extract contacts
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
    print(" TenderNed DOWNLOAD STATUS")
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
                size = f.stat().st_size / 1024
                print(f"    {f.name}: {size:.1f} KB")
    else:
        print(f"\n  Directory not found: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Netherlands TenderNed Data Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--api", action="store_true", help="Download via TenderNed API")
    parser.add_argument("--opendata", action="store_true", help="Download from Open Data portal")
    parser.add_argument("--pianoo", action="store_true", help="Download PIANOo data")
    parser.add_argument("--extract", action="store_true", help="Extract contacts")
    parser.add_argument("--days", type=int, default=365, help="Days back for API query")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.api:
        download_tenderned_via_api(days_back=args.days)
    elif args.opendata:
        download_opendata_nl()
    elif args.pianoo:
        download_pianoo()
    elif args.extract:
        extract_contacts()
    else:
        parser.print_help()
