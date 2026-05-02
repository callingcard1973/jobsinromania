#!/usr/bin/env python3
"""
TED Bulk Data Extractor and Converter.

Extracts nested TED tar.gz files and converts XML to ASCII CSV.

Structure:
  monthly.tar.gz -> daily.tar.gz -> XML files

Usage:
    python3 ted_extract_convert.py --extract 2020
    python3 ted_extract_convert.py --convert 2020
    python3 ted_extract_convert.py --all 2020
"""

import argparse
import csv
import gzip
import os
import re
import sys
import tarfile
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_TENDERS")
RAW_DIR = BASE_DIR / "RAW" / "MONTHLY"
EXTRACTED_DIR = BASE_DIR / "EXTRACTED"
CSV_DIR = BASE_DIR / "CSV"


def to_ascii(text):
    """Convert text to ASCII."""
    if not text:
        return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()


def extract_monthly(year, month=None):
    """Extract monthly tar.gz files."""
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    if month:
        patterns = [f"ted_{year}_{month:02d}.xml.gz"]
    else:
        patterns = list(RAW_DIR.glob(f"ted_{year}_*.xml.gz"))
        patterns = [p.name for p in patterns]

    total_xml = 0

    for pattern in sorted(patterns):
        monthly_file = RAW_DIR / pattern if isinstance(pattern, str) else pattern
        if not monthly_file.exists():
            monthly_file = RAW_DIR / pattern
            if not monthly_file.exists():
                print(f"  Not found: {pattern}")
                continue

        print(f"\n=== Extracting {monthly_file.name} ===")

        # Extract year-month from filename
        match = re.search(r'ted_(\d{4})_(\d{2})', monthly_file.name)
        if not match:
            continue
        y, m = match.groups()

        output_dir = EXTRACTED_DIR / f"{y}_{m}"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Open outer tar
            with tarfile.open(monthly_file, 'r:gz') as outer_tar:
                members = outer_tar.getmembers()
                print(f"  Found {len(members)} daily packages")

                for member in members:
                    if not member.name.endswith('.tar.gz'):
                        continue

                    # Extract daily tar.gz to temp
                    daily_file = outer_tar.extractfile(member)
                    if not daily_file:
                        continue

                    # Extract XML from daily tar.gz
                    try:
                        with tarfile.open(fileobj=daily_file, mode='r:gz') as daily_tar:
                            for xml_member in daily_tar.getmembers():
                                if xml_member.name.endswith('.xml'):
                                    # Extract XML
                                    xml_file = daily_tar.extractfile(xml_member)
                                    if xml_file:
                                        xml_name = Path(xml_member.name).name
                                        xml_path = output_dir / xml_name
                                        with open(xml_path, 'wb') as f:
                                            f.write(xml_file.read())
                                        total_xml += 1
                    except Exception as e:
                        print(f"    Error extracting {member.name}: {e}")
                        continue

                print(f"  Extracted to: {output_dir}")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print(f"\n  Total XML files extracted: {total_xml}")
    return total_xml


def parse_ted_xml(xml_path):
    """Parse a TED XML file and extract key fields."""
    notices = []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Handle namespaces
        ns = {'ted': 'http://publications.europa.eu/resource/schema/ted/2016/nuts'}

        notice = {}

        # Try different XML structures (TED format varies)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            text = to_ascii(elem.text) if elem.text else ''

            if tag in ['NO_DOC_OJS', 'TED_NOTICE_ID', 'DOC_ID']:
                notice['notice_id'] = text
            elif tag in ['TI_TEXT', 'TITLE_CONTRACT', 'OBJECT_CONTRACT']:
                if text and len(text) > 10:
                    notice['title'] = text[:500]
            elif tag == 'ISO_COUNTRY':
                code = elem.get('CODE', text)
                if code and len(code) == 2:
                    notice['country'] = code.upper()
            elif tag in ['OFFICIALNAME', 'ORGANISATION', 'AA_NAME']:
                if text and 'authority' not in notice:
                    notice['authority'] = text[:200]
            elif tag in ['CONTRACTOR', 'ECONOMIC_OPERATOR_NAME']:
                if text:
                    notice['contractor'] = text[:200]
            elif tag == 'VAL_TOTAL':
                try:
                    notice['value'] = float(text.replace(',', '.'))
                except:
                    pass
            elif tag in ['DT_DATE_FOR_SUBMISSION', 'DATE_RECEIPT_TENDERS']:
                notice['deadline'] = text[:20]
            elif tag in ['NC_CONTRACT_NATURE', 'TYPE_CONTRACT', 'NOTICE_TYPE']:
                notice['contract_type'] = text[:50]
            elif tag == 'TOWN':
                if text and 'city' not in notice:
                    notice['city'] = text[:100]
            elif tag in ['CPV_CODE', 'CPV_MAIN']:
                code = elem.get('CODE', text)
                if code:
                    notice['cpv'] = code[:10]

        if notice.get('notice_id') or notice.get('title'):
            notices.append(notice)

    except ET.ParseError as e:
        pass
    except Exception as e:
        pass

    return notices


def convert_to_csv(year, month=None):
    """Convert extracted XML files to CSV."""
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    if month:
        dirs = [EXTRACTED_DIR / f"{year}_{month:02d}"]
    else:
        dirs = list(EXTRACTED_DIR.glob(f"{year}_*"))

    all_notices = []

    for xml_dir in sorted(dirs):
        if not xml_dir.is_dir():
            continue

        print(f"\n=== Converting {xml_dir.name} ===")

        xml_files = list(xml_dir.glob("*.xml"))
        print(f"  Found {len(xml_files)} XML files")

        for i, xml_file in enumerate(xml_files):
            notices = parse_ted_xml(xml_file)
            all_notices.extend(notices)

            if (i + 1) % 1000 == 0:
                print(f"\r  Processed: {i+1}/{len(xml_files)} files, {len(all_notices)} notices", end="", flush=True)

        print(f"\r  Processed: {len(xml_files)} files, {len(all_notices)} notices")

    # Write CSV
    if all_notices:
        output_file = CSV_DIR / f"ted_{year}.csv"

        fieldnames = ['notice_id', 'title', 'country', 'city', 'authority',
                      'contractor', 'value', 'contract_type', 'cpv', 'deadline']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_notices)

        print(f"\n  Saved: {output_file}")
        print(f"  Total notices: {len(all_notices):,}")

        return len(all_notices)

    return 0


def show_status():
    """Show extraction status."""
    print("\n" + "=" * 60)
    print(" TED EXTRACTION STATUS")
    print("=" * 60)

    print("\nRaw files:")
    raw_files = list(RAW_DIR.glob("*.gz"))
    print(f"  Count: {len(raw_files)}")
    total_raw = sum(f.stat().st_size for f in raw_files)
    print(f"  Size: {total_raw / 1024 / 1024 / 1024:.1f} GB")

    print("\nExtracted:")
    if EXTRACTED_DIR.exists():
        for d in sorted(EXTRACTED_DIR.iterdir()):
            if d.is_dir():
                xml_count = len(list(d.glob("*.xml")))
                print(f"  {d.name}: {xml_count:,} XML files")
    else:
        print("  None yet")

    print("\nConverted CSV:")
    if CSV_DIR.exists():
        for f in sorted(CSV_DIR.glob("*.csv")):
            with open(f, 'r', errors='ignore') as fp:
                rows = sum(1 for _ in fp) - 1
            print(f"  {f.name}: {rows:,} notices")
    else:
        print("  None yet")


def main():
    parser = argparse.ArgumentParser(description="TED Bulk Data Extractor")
    parser.add_argument("--extract", "-e", type=str, help="Extract year (YYYY or YYYY-MM)")
    parser.add_argument("--convert", "-c", type=str, help="Convert year to CSV")
    parser.add_argument("--all", "-a", type=str, help="Extract and convert year")
    parser.add_argument("--status", "-s", action="store_true", help="Show status")

    args = parser.parse_args()

    # Create directories
    for d in [EXTRACTED_DIR, CSV_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if args.status:
        show_status()
    elif args.extract:
        if '-' in args.extract:
            year, month = args.extract.split('-')
            extract_monthly(int(year), int(month))
        else:
            extract_monthly(int(args.extract))
    elif args.convert:
        if '-' in args.convert:
            year, month = args.convert.split('-')
            convert_to_csv(int(year), int(month))
        else:
            convert_to_csv(int(args.convert))
    elif args.all:
        if '-' in args.all:
            year, month = args.all.split('-')
            extract_monthly(int(year), int(month))
            convert_to_csv(int(year), int(month))
        else:
            extract_monthly(int(args.all))
            convert_to_csv(int(args.all))
    else:
        show_status()
        print("\nUsage:")
        print("  --extract 2020       Extract all 2020 files")
        print("  --extract 2020-1     Extract January 2020")
        print("  --convert 2020       Convert to CSV")
        print("  --all 2020           Extract and convert")


if __name__ == "__main__":
    main()
