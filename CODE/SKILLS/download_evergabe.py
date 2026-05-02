#!/usr/bin/env python3
"""
Germany e-Vergabe Data Downloader

Downloads German public procurement data from:
- e-Vergabe.de (federal procurement platform)
- GovData (German open data portal)
- Bund.de (federal government portal)
- BMI OCDS data (Federal Ministry of Interior)
- Destatis (Federal Statistical Office)

Output: /opt/ACTIVE/OPENDATA/DATA/GERMANY/EVERGABE/
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

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/GERMANY/EVERGABE")

# German procurement data sources
GOVDATA_API = "https://www.govdata.de/ckan/api/3/action/"

# BMI OCDS data (Open Contracting)
BMI_OCDS_BASE = "https://vergabe.govdata.de/web/rest/opendata"

# GovData datasets
GOVDATA_DATASETS = {
    "vergabe_bund": {
        "name": "Federal Procurement Data",
        "url": "https://www.govdata.de/web/guest/suchen/-/searchresult/f/tags%3AVergabe/"
    },
    "beschaffungsamt": {
        "name": "Federal Procurement Office",
        "url": "https://www.bescha.bund.de/DE/Veroeffentlichungen/veroeffentlichungen_node.html"
    },
}

# State-level procurement portals
STATE_PORTALS = {
    "bw": {
        "name": "Baden-Wurttemberg",
        "url": "https://service-bw.de/leistung/-/sbw/Ausschreibungen+fuer+Auftraege-6000142-leistung-0"
    },
    "by": {
        "name": "Bayern",
        "url": "https://www.auftraege.bayern.de/"
    },
    "nrw": {
        "name": "Nordrhein-Westfalen",
        "url": "https://www.vergabe.nrw.de/"
    },
    "he": {
        "name": "Hessen",
        "url": "https://vergabe.hessen.de/"
    },
    "sn": {
        "name": "Sachsen",
        "url": "https://www.evergabe.sachsen.de/"
    },
    "be": {
        "name": "Berlin",
        "url": "https://www.berlin.de/vergabeplattform/"
    },
}


def download_file(url, output_path, chunk_size=8192):
    """Download a file with progress."""
    try:
        print(f"  Downloading: {url[:80]}...")
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ProcurementBot/1.0)",
            "Accept": "*/*"
        }
        response = requests.get(url, stream=True, timeout=300, headers=headers)
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


def query_govdata_api(endpoint, params=None):
    """Query GovData CKAN API."""
    try:
        url = f"{GOVDATA_API}{endpoint}"
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("result", {})
    except Exception as e:
        print(f"    API Error: {e}")
        return {}


def download_bmi_ocds():
    """Download BMI OCDS data (Federal Ministry of Interior)."""
    ocds_dir = OUTPUT_DIR / "OCDS"
    ocds_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" BMI OCDS DATA DOWNLOAD")
    print("="*60)

    # BMI provides OCDS format data
    ocds_urls = [
        # CSV export
        (f"{BMI_OCDS_BASE}/1.1/csv", "bmi_ocds_releases.csv"),

        # JSON export
        (f"{BMI_OCDS_BASE}/1.1/json", "bmi_ocds_releases.json"),

        # Full dataset by year
        ("https://vergabe.govdata.de/web/rest/opendata/1.1/csv/2024", "bmi_ocds_2024.csv"),
        ("https://vergabe.govdata.de/web/rest/opendata/1.1/csv/2023", "bmi_ocds_2023.csv"),
        ("https://vergabe.govdata.de/web/rest/opendata/1.1/csv/2022", "bmi_ocds_2022.csv"),
    ]

    for url, filename in ocds_urls:
        print(f"\n  File: {filename}")
        output_file = ocds_dir / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def download_govdata():
    """Download from GovData portal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" GOVDATA DOWNLOAD")
    print("="*60)

    # Search for procurement datasets
    result = query_govdata_api("package_search", {"q": "Vergabe", "rows": 100})
    datasets = result.get("results", [])

    print(f"\n  Found {len(datasets)} procurement datasets")

    for ds in datasets[:10]:  # First 10
        name = ds.get("name", "")
        title = ds.get("title", "")
        print(f"\n  Dataset: {title[:50]}...")

        resources = ds.get("resources", [])
        for res in resources:
            fmt = res.get("format", "").lower()
            if fmt in ["csv", "json", "xml"]:
                url = res.get("url", "")
                res_name = res.get("name", name)

                # Clean filename
                filename = f"govdata_{name[:30]}_{res_name[:20]}.{fmt}".replace("/", "_")
                output_file = OUTPUT_DIR / filename

                download_file(url, output_file)
                time.sleep(1)
                break  # One file per dataset

    return True


def download_destatis():
    """Download Destatis (Federal Statistics) procurement data."""
    destatis_dir = OUTPUT_DIR / "DESTATIS"
    destatis_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" DESTATIS DOWNLOAD")
    print("="*60)

    # Destatis provides statistics on public procurement
    destatis_urls = [
        # Vergabestatistik (procurement statistics)
        ("https://www-genesis.destatis.de/genesis/online?operation=abruftabelleDownload&levelindex=0&levelid=1708355400000&downloadname=14613-0001&format=csv",
         "destatis_vergabestatistik.csv"),

        # Public contracts by type
        ("https://www-genesis.destatis.de/genesis/online?operation=abruftabelleDownload&levelindex=0&levelid=1708355400000&downloadname=14613-0002&format=csv",
         "destatis_vertragsarten.csv"),
    ]

    for url, filename in destatis_urls:
        print(f"\n  File: {filename}")
        output_file = destatis_dir / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def download_xvergabe():
    """Download XVergabe XML format data."""
    xvergabe_dir = OUTPUT_DIR / "XVERGABE"
    xvergabe_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" XVERGABE XML DOWNLOAD")
    print("="*60)

    # XVergabe is the German standard for procurement data exchange
    # Federal platform provides XVergabe exports

    xvergabe_urls = [
        # E-Vergabe platform exports
        ("https://www.evergabe-online.de/tenders/export/xml",
         "evergabe_export.xml"),
    ]

    for url, filename in xvergabe_urls:
        print(f"\n  File: {filename}")
        output_file = xvergabe_dir / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def download_bund_de():
    """Download from bund.de (federal portal)."""
    bund_dir = OUTPUT_DIR / "BUND"
    bund_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" BUND.DE DOWNLOAD")
    print("="*60)

    # Bund.de provides tender announcements
    bund_urls = [
        # RSS feed of federal tenders
        ("https://www.bund.de/SiteGlobals/Functions/RSSFeed/DE/BundDERSSFeed_ausschreibungen.xml",
         "bund_ausschreibungen.xml"),
    ]

    for url, filename in bund_urls:
        print(f"\n  File: {filename}")
        output_file = bund_dir / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def extract_contacts():
    """Extract contacts from downloaded e-Vergabe data."""
    print("\n" + "="*60)
    print(" EXTRACTING CONTACTS")
    print("="*60)

    contacts = []

    # Process CSV files
    for csv_file in OUTPUT_DIR.rglob("*.csv"):
        if "contacts" in csv_file.name:
            continue

        print(f"\n  Processing: {csv_file.name}")
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Try different delimiters (German data often uses semicolon)
                sample = f.read(1024)
                f.seek(0)

                delimiter = ';' if ';' in sample else ','
                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # German column names
                    email = row.get('email', row.get('E-Mail',
                             row.get('eMail', row.get('EMAIL', ''))))
                    phone = row.get('telefon', row.get('Telefon',
                             row.get('TELEFON', row.get('phone', ''))))
                    company = row.get('vergabestelle', row.get('Auftraggeber',
                               row.get('Organisation', row.get('name', ''))))

                    if email or phone:
                        contact = {
                            'id': row.get('id', row.get('ID', row.get('referenz', ''))),
                            'company': to_ascii(company)[:200],
                            'city': to_ascii(row.get('ort', row.get('Stadt', '')))[:100],
                            'postal_code': row.get('plz', row.get('PLZ', '')),
                            'email': (email or '').lower()[:200],
                            'phone': (phone or '')[:50],
                            'website': row.get('url', row.get('webseite', ''))[:200],
                            'type': row.get('verfahrensart', row.get('typ', '')),
                            'cpv': row.get('cpv', ''),
                            'country': 'DE',
                        }
                        contacts.append(contact)

        except Exception as e:
            print(f"    Error: {e}")

    # Process JSON files
    for json_file in OUTPUT_DIR.rglob("*.json"):
        if "contacts" in json_file.name:
            continue

        print(f"\n  Processing: {json_file.name}")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle OCDS format
            releases = data.get("releases", [data] if isinstance(data, dict) else data)
            for release in releases:
                buyer = release.get("buyer", release.get("procuringEntity", {}))
                contact_point = buyer.get("contactPoint", {})

                email = contact_point.get("email", "")
                phone = contact_point.get("telephone", "")

                if email or phone:
                    contacts.append({
                        'id': release.get("id", release.get("ocid", "")),
                        'company': to_ascii(buyer.get("name", ""))[:200],
                        'city': to_ascii(buyer.get("address", {}).get("locality", ""))[:100],
                        'postal_code': buyer.get("address", {}).get("postalCode", ""),
                        'email': email.lower()[:200],
                        'phone': phone[:50],
                        'website': contact_point.get("url", "")[:200],
                        'type': release.get("tag", [""])[0] if release.get("tag") else "",
                        'cpv': "",
                        'country': 'DE',
                    })

        except Exception as e:
            print(f"    Error: {e}")

    # Deduplicate
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
        output_file = OUTPUT_DIR / "evergabe_contacts.csv"
        fieldnames = ['id', 'company', 'city', 'postal_code', 'email', 'phone',
                      'website', 'type', 'cpv', 'country']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_contacts)

        print(f"\n  Extracted: {len(unique_contacts):,} contacts")
        print(f"  Saved: {output_file}")

    return unique_contacts


def download_all():
    """Download all e-Vergabe data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"e-Vergabe Download Started: {datetime.now()}\n\n")

    # 1. Download BMI OCDS data (most important)
    download_bmi_ocds()

    # 2. Download from GovData
    download_govdata()

    # 3. Download Destatis statistics
    download_destatis()

    # 4. Download from bund.de
    download_bund_de()

    # 5. Download XVergabe format
    download_xvergabe()

    # 6. Extract contacts
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
    print(" e-Vergabe DOWNLOAD STATUS")
    print("="*60)

    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.rglob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        print(f"\n  Directory: {OUTPUT_DIR}")
        print(f"  Files: {len([f for f in files if f.is_file()])}")
        print(f"  Size: {total_size / 1024 / 1024:.1f} MB")

        print("\n  Subdirectories:")
        for subdir in sorted(OUTPUT_DIR.iterdir()):
            if subdir.is_dir():
                subfiles = list(subdir.rglob("*"))
                subsize = sum(f.stat().st_size for f in subfiles if f.is_file())
                print(f"    {subdir.name}: {len([f for f in subfiles if f.is_file()])} files, {subsize//1024} KB")
    else:
        print(f"\n  Directory not found: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="German e-Vergabe Data Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--ocds", action="store_true", help="Download BMI OCDS data")
    parser.add_argument("--govdata", action="store_true", help="Download from GovData")
    parser.add_argument("--destatis", action="store_true", help="Download Destatis statistics")
    parser.add_argument("--bund", action="store_true", help="Download from bund.de")
    parser.add_argument("--xvergabe", action="store_true", help="Download XVergabe format")
    parser.add_argument("--extract", action="store_true", help="Extract contacts")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.ocds:
        download_bmi_ocds()
    elif args.govdata:
        download_govdata()
    elif args.destatis:
        download_destatis()
    elif args.bund:
        download_bund_de()
    elif args.xvergabe:
        download_xvergabe()
    elif args.extract:
        extract_contacts()
    else:
        parser.print_help()
