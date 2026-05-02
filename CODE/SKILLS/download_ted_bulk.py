#!/usr/bin/env python3
"""
Download TED Bulk Data - EU Procurement Notices (1993-2026).

Source: ted.europa.eu
Data: All public procurement notices across EU
Format: XML (gzip compressed)
Coverage: 1993-2026

Usage:
    python3 download_ted_bulk.py --status
    python3 download_ted_bulk.py --download 2026-1      # January 2026
    python3 download_ted_bulk.py --download 2025        # All of 2025
    python3 download_ted_bulk.py --download-daily 202600022  # Single day
    python3 download_ted_bulk.py --list-daily           # List available daily
    python3 download_ted_bulk.py --convert 2026-1       # Convert XML to CSV
"""

import argparse
import csv
import gzip
import os
import ssl
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# Output directory
BASE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_TENDERS")

# TED URLs
TED_MONTHLY_URL = "https://ted.europa.eu/packages/monthly/{year}-{month}"
TED_DAILY_URL = "https://ted.europa.eu/packages/daily/{issue}"

# Years available
YEARS_AVAILABLE = list(range(1993, 2027))


def to_ascii(text):
    """Convert text to ASCII."""
    if not text:
        return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()


def get_ssl_context():
    """Create SSL context."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def download_file(url, output_path):
    """Download file with progress."""
    ctx = get_ssl_context()

    print(f"  URL: {url}")
    print(f"  Output: {output_path}")

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })

        with urllib.request.urlopen(req, timeout=3600, context=ctx) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            content_type = resp.headers.get('Content-Type', '')

            if total:
                print(f"  Size: {total / 1024 / 1024:.1f} MB")
            print(f"  Type: {content_type}")

            downloaded = 0
            start_time = time.time()

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total:
                        pct = downloaded * 100 // total
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
                        print(f"\r  Progress: {pct}% ({downloaded/1024/1024:.1f} MB, {speed:.1f} MB/s)", end="", flush=True)

            print()
            return True

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  Not found (404)")
        else:
            print(f"  HTTP Error: {e.code}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def download_monthly(year, month):
    """Download monthly package."""
    raw_dir = BASE_DIR / "RAW" / "MONTHLY"
    raw_dir.mkdir(parents=True, exist_ok=True)

    url = TED_MONTHLY_URL.format(year=year, month=month)
    output_file = raw_dir / f"ted_{year}_{month:02d}.xml.gz"

    print(f"\n=== Downloading TED {year}-{month:02d} ===")

    if output_file.exists():
        size = output_file.stat().st_size
        print(f"  Already exists: {size / 1024 / 1024:.1f} MB")
        return True

    return download_file(url, output_file)


def download_year(year):
    """Download all months for a year."""
    print(f"\n{'='*60}")
    print(f" DOWNLOADING TED {year}")
    print(f"{'='*60}")

    results = {}
    for month in range(1, 13):
        results[month] = download_monthly(year, month)
        if not results[month]:
            # Stop if month not found (future months)
            if month > datetime.now().month and year >= datetime.now().year:
                break
        time.sleep(1)

    # Summary
    success = sum(1 for v in results.values() if v)
    print(f"\n  Downloaded: {success}/{len(results)} months")
    return success


def download_daily(issue):
    """Download daily package."""
    raw_dir = BASE_DIR / "RAW" / "DAILY"
    raw_dir.mkdir(parents=True, exist_ok=True)

    url = TED_DAILY_URL.format(issue=issue)
    output_file = raw_dir / f"ted_daily_{issue}.xml.gz"

    print(f"\n=== Downloading TED Daily {issue} ===")

    if output_file.exists():
        print(f"  Already exists")
        return True

    return download_file(url, output_file)


def list_daily_available():
    """List available daily issues."""
    print("\n=== TED Daily Issues ===")
    print("\nFormat: YYYYNNNNN (Year + OJ S issue number)")
    print("\nRecent issues (February 2026):")

    # Check recent issues
    year = 2026
    for issue in range(22, 41):
        issue_id = f"{year}000{issue:02d}"
        url = TED_DAILY_URL.format(issue=issue_id)

        try:
            ctx = get_ssl_context()
            req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                size = int(resp.headers.get('Content-Length', 0))
                print(f"  {issue_id}: Available ({size / 1024 / 1024:.1f} MB)")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  {issue_id}: Not available")
            else:
                print(f"  {issue_id}: Error {e.code}")
        except:
            print(f"  {issue_id}: Error")

        time.sleep(0.5)


def extract_notices_from_xml(xml_path, output_csv):
    """Extract key fields from TED XML to CSV."""
    print(f"\n=== Converting {xml_path.name} to CSV ===")

    # Open gzip file
    if str(xml_path).endswith('.gz'):
        f = gzip.open(xml_path, 'rt', encoding='utf-8', errors='ignore')
    else:
        f = open(xml_path, 'r', encoding='utf-8', errors='ignore')

    notices = []
    current_notice = {}

    try:
        # Parse XML iteratively (large files)
        for event, elem in ET.iterparse(f, events=['start', 'end']):
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            if event == 'end':
                # Extract common fields
                if tag == 'NOTICE_DATA':
                    # Process notice
                    if current_notice:
                        notices.append(current_notice.copy())
                        current_notice = {}
                        if len(notices) % 10000 == 0:
                            print(f"\r  Processed: {len(notices):,} notices", end="", flush=True)

                elif tag in ['NO_DOC_OJS', 'NOTICE_NUMBER']:
                    current_notice['notice_id'] = to_ascii(elem.text or '')
                elif tag in ['TI_TITLE', 'TITLE']:
                    current_notice['title'] = to_ascii(elem.text or '')[:200]
                elif tag in ['ISO_COUNTRY', 'COUNTRY']:
                    if 'country' not in current_notice:
                        current_notice['country'] = (elem.text or '').upper()[:2]
                elif tag in ['AA_NAME', 'ORGANISATION', 'OFFICIALNAME']:
                    if 'authority' not in current_notice:
                        current_notice['authority'] = to_ascii(elem.text or '')[:100]
                elif tag in ['CONTRACT_VALUE', 'VALUE']:
                    try:
                        current_notice['value'] = float(elem.text or 0)
                    except:
                        pass
                elif tag in ['DT_DATE_FOR_SUBMISSION', 'DATE_RECEIPT_TENDERS']:
                    current_notice['deadline'] = elem.text or ''
                elif tag in ['NC_CONTRACT_NATURE', 'TYPE_CONTRACT']:
                    current_notice['contract_type'] = elem.text or ''
                elif tag in ['RP_REGULATION', 'LEGAL_BASIS']:
                    current_notice['legal_basis'] = elem.text or ''
                elif tag in ['TOWN', 'CITY']:
                    if 'city' not in current_notice:
                        current_notice['city'] = to_ascii(elem.text or '')

                elem.clear()

    except ET.ParseError as e:
        print(f"\n  XML Parse error: {e}")
    finally:
        f.close()

    print(f"\r  Total notices: {len(notices):,}")

    # Write CSV
    if notices:
        fieldnames = ['notice_id', 'title', 'country', 'city', 'authority', 'value', 'contract_type', 'deadline', 'legal_basis']

        with open(output_csv, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(notices)

        print(f"  Saved: {output_csv}")
        print(f"  Rows: {len(notices):,}")

    return len(notices)


def convert_to_csv(period):
    """Convert XML files to CSV."""
    raw_dir = BASE_DIR / "RAW" / "MONTHLY"
    csv_dir = BASE_DIR / "CSV"
    csv_dir.mkdir(parents=True, exist_ok=True)

    # Parse period
    if '-' in period:
        year, month = period.split('-')
        files = [raw_dir / f"ted_{year}_{int(month):02d}.xml.gz"]
    else:
        year = period
        files = list(raw_dir.glob(f"ted_{year}_*.xml.gz"))

    total_notices = 0
    for xml_file in sorted(files):
        if xml_file.exists():
            csv_file = csv_dir / f"{xml_file.stem.replace('.xml', '')}.csv"
            notices = extract_notices_from_xml(xml_file, csv_file)
            total_notices += notices

    print(f"\n  Total converted: {total_notices:,} notices")
    return total_notices


def show_status():
    """Show download status."""
    print("\n" + "=" * 70)
    print(" TED BULK DATA - Download Status")
    print("=" * 70)

    raw_monthly = BASE_DIR / "RAW" / "MONTHLY"
    raw_daily = BASE_DIR / "RAW" / "DAILY"
    csv_dir = BASE_DIR / "CSV"

    # Monthly files
    print("\nMonthly packages:")
    if raw_monthly.exists():
        files = sorted(raw_monthly.glob("*.gz"))
        total_size = sum(f.stat().st_size for f in files)
        print(f"  Files: {len(files)}")
        print(f"  Total size: {total_size / 1024 / 1024:.1f} MB")

        # By year
        by_year = {}
        for f in files:
            year = f.name.split('_')[1]
            by_year[year] = by_year.get(year, 0) + 1

        print("  By year:")
        for year, count in sorted(by_year.items()):
            print(f"    {year}: {count} months")
    else:
        print("  No files downloaded yet")

    # Daily files
    print("\nDaily packages:")
    if raw_daily.exists():
        files = list(raw_daily.glob("*.gz"))
        print(f"  Files: {len(files)}")
    else:
        print("  No files downloaded yet")

    # CSV files
    print("\nConverted CSV:")
    if csv_dir.exists():
        files = list(csv_dir.glob("*.csv"))
        total_rows = 0
        for f in files:
            with open(f, 'r', errors='ignore') as fp:
                rows = sum(1 for _ in fp) - 1
                total_rows += rows
        print(f"  Files: {len(files)}")
        print(f"  Total rows: {total_rows:,}")
    else:
        print("  No files converted yet")

    print("\n" + "-" * 70)
    print("URLs:")
    print(f"  Monthly: {TED_MONTHLY_URL}")
    print(f"  Daily:   {TED_DAILY_URL}")
    print("-" * 70)


def main():
    parser = argparse.ArgumentParser(description="Download TED Bulk Data")
    parser.add_argument("--status", "-s", action="store_true", help="Show status")
    parser.add_argument("--download", "-d", type=str, help="Download: YYYY or YYYY-M")
    parser.add_argument("--download-daily", type=str, help="Download daily: YYYYNNNNN")
    parser.add_argument("--list-daily", action="store_true", help="List available daily issues")
    parser.add_argument("--convert", "-c", type=str, help="Convert XML to CSV: YYYY or YYYY-M")
    parser.add_argument("--all-recent", action="store_true", help="Download 2024-2026")

    args = parser.parse_args()

    # Create directories
    for subdir in ["RAW/MONTHLY", "RAW/DAILY", "CSV"]:
        (BASE_DIR / subdir).mkdir(parents=True, exist_ok=True)

    if args.status:
        show_status()
    elif args.download:
        if '-' in args.download:
            year, month = args.download.split('-')
            download_monthly(int(year), int(month))
        else:
            download_year(int(args.download))
    elif args.download_daily:
        download_daily(args.download_daily)
    elif args.list_daily:
        list_daily_available()
    elif args.convert:
        convert_to_csv(args.convert)
    elif args.all_recent:
        for year in [2024, 2025, 2026]:
            download_year(year)
    else:
        show_status()
        print("\nUsage:")
        print("  --download 2026        Download all of 2026")
        print("  --download 2026-1      Download January 2026")
        print("  --download-daily 202600022  Download daily issue")
        print("  --convert 2026         Convert to CSV")
        print("  --all-recent           Download 2024-2026")


if __name__ == "__main__":
    main()
