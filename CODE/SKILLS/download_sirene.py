#!/usr/bin/env python3
"""
Download France SIRENE - French company database.

Source: data.gouv.fr
Data: ~35M establishments, ~25M legal units
Format: CSV (ZIP) or Parquet
License: Open License 2.0

Usage:
    python3 download_sirene.py --status
    python3 download_sirene.py --download all
    python3 download_sirene.py --download establishments
    python3 download_sirene.py --download units
    python3 download_sirene.py --convert  # Convert to ASCII CSV
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
import zipfile
from datetime import datetime
from pathlib import Path

# Output directory
BASE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/FRANCE")

# SIRENE datasets on data.gouv.fr
DATASETS = {
    "establishments": {
        "name": "StockEtablissement",
        "description": "All French establishments (35M+)",
        "url": "https://www.data.gouv.fr/fr/datasets/r/0651fb76-bcf3-4f6a-a38d-bc04fa708576",
        "size_mb": 2600,
        "format": "zip",
    },
    "units": {
        "name": "StockUniteLegale",
        "description": "Legal units/companies (25M+)",
        "url": "https://www.data.gouv.fr/fr/datasets/r/825f4199-cadd-486c-ac46-a65a8ea1a047",
        "size_mb": 897,
        "format": "zip",
    },
    "establishments_history": {
        "name": "StockEtablissementHistorique",
        "description": "Historical establishment changes",
        "url": "https://www.data.gouv.fr/fr/datasets/r/88fbb6b4-0320-443e-b739-b4376a012c32",
        "size_mb": 1100,
        "format": "zip",
    },
    "units_history": {
        "name": "StockUniteLegaleHistorique",
        "description": "Historical legal unit changes",
        "url": "https://www.data.gouv.fr/fr/datasets/r/0835cd60-2c2a-497b-bc64-404de704ce89",
        "size_mb": 1100,
        "format": "zip",
    },
    "duplicates": {
        "name": "StockDoublons",
        "description": "Duplicate records",
        "url": "https://www.data.gouv.fr/fr/datasets/r/d8c31348-8630-4918-b6d1-5dd689b05f29",
        "size_mb": 1,
        "format": "zip",
    },
}


def to_ascii(text):
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()


def get_ssl_context():
    """Create SSL context that accepts all certificates."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def download_file(url, output_path, expected_mb=0):
    """Download file with progress indicator."""
    ctx = get_ssl_context()

    print(f"  Downloading to: {output_path}")
    if expected_mb:
        print(f"  Expected size: ~{expected_mb} MB")

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })

        with urllib.request.urlopen(req, timeout=3600, context=ctx) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            if total:
                print(f"  Actual size: {total / 1024 / 1024:.1f} MB")

            downloaded = 0
            start_time = time.time()

            with open(output_path, 'wb') as f:
                while True:
                    chunk = resp.read(1024 * 1024)  # 1MB chunks
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

    except Exception as e:
        print(f"\n  Error: {e}")
        return False


def extract_zip(zip_path, output_dir):
    """Extract ZIP file."""
    print(f"  Extracting: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                print(f"    - {name}")
            zf.extractall(output_dir)
        return True
    except Exception as e:
        print(f"  Extract error: {e}")
        return False


def convert_to_ascii(input_path, output_path, limit=0):
    """Convert CSV to ASCII format."""
    print(f"  Converting to ASCII: {input_path.name}")

    # Detect encoding
    with open(input_path, 'rb') as f:
        header = f.read(4)

    if header.startswith(b'\xff\xfe'):
        encoding = 'utf-16-le'
    elif header.startswith(b'\xef\xbb\xbf'):
        encoding = 'utf-8-sig'
    else:
        encoding = 'utf-8'

    print(f"    Encoding: {encoding}")

    rows = 0
    with open(input_path, 'r', encoding=encoding, errors='ignore') as f:
        reader = csv.reader(f)
        with open(output_path, 'w', newline='', encoding='ascii', errors='ignore') as out:
            writer = csv.writer(out)
            for row in reader:
                writer.writerow([to_ascii(cell) for cell in row])
                rows += 1
                if rows % 1000000 == 0:
                    print(f"\r    Processed: {rows:,} rows", end="", flush=True)
                if limit and rows >= limit:
                    break

    print(f"\r    Total: {rows:,} rows")
    return rows


def show_status():
    """Show download status."""
    print("\n" + "=" * 70)
    print(" FRANCE SIRENE - Download Status")
    print("=" * 70)

    raw_dir = BASE_DIR / "RAW"
    companies_dir = BASE_DIR / "COMPANIES"

    print(f"\nOutput directory: {BASE_DIR}")
    print(f"RAW directory: {raw_dir}")
    print(f"COMPANIES directory: {companies_dir}")

    print("\n" + "-" * 70)
    print(f"{'Dataset':<25} | {'Size MB':>8} | {'Status':<20}")
    print("-" * 70)

    for key, ds in DATASETS.items():
        zip_file = raw_dir / f"{ds['name']}.zip"
        csv_files = list((companies_dir).glob(f"{ds['name']}*.csv")) if companies_dir.exists() else []

        if csv_files:
            status = f"Converted ({len(csv_files)} files)"
        elif zip_file.exists():
            status = f"Downloaded ({zip_file.stat().st_size / 1024 / 1024:.0f} MB)"
        else:
            status = "Not downloaded"

        print(f"{ds['name']:<25} | {ds['size_mb']:>8} | {status:<20}")

    print("-" * 70)

    # Show row counts
    if companies_dir.exists():
        print("\nConverted files:")
        for f in sorted(companies_dir.glob("*.csv")):
            with open(f, 'r', errors='ignore') as fp:
                rows = sum(1 for _ in fp)
            print(f"  {f.name}: {rows:,} rows")


def download_dataset(key):
    """Download a specific dataset."""
    if key not in DATASETS:
        print(f"Unknown dataset: {key}")
        print(f"Available: {', '.join(DATASETS.keys())}")
        return False

    ds = DATASETS[key]
    raw_dir = BASE_DIR / "RAW"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Downloading: {ds['name']} ===")
    print(f"Description: {ds['description']}")
    print(f"URL: {ds['url'][:60]}...")

    output_file = raw_dir / f"{ds['name']}.zip"

    if output_file.exists():
        print(f"  Already exists: {output_file}")
        return True

    return download_file(ds['url'], output_file, ds['size_mb'])


def download_all():
    """Download all datasets."""
    print("\n" + "=" * 70)
    print(" DOWNLOADING ALL SIRENE DATASETS")
    print("=" * 70)
    print(f" Started: {datetime.now().isoformat()}")
    print(f" Total size: ~5.7 GB")
    print("=" * 70)

    results = {}
    for key in DATASETS:
        results[key] = download_dataset(key)
        time.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print(" DOWNLOAD SUMMARY")
    print("=" * 70)
    for key, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {DATASETS[key]['name']}: {status}")

    return all(results.values())


def extract_all():
    """Extract all downloaded ZIP files."""
    raw_dir = BASE_DIR / "RAW"

    print("\n=== Extracting all ZIP files ===")

    for key, ds in DATASETS.items():
        zip_file = raw_dir / f"{ds['name']}.zip"
        if zip_file.exists():
            extract_zip(zip_file, raw_dir)


def convert_all(limit=0):
    """Convert all CSVs to ASCII."""
    raw_dir = BASE_DIR / "RAW"
    companies_dir = BASE_DIR / "COMPANIES"
    companies_dir.mkdir(parents=True, exist_ok=True)

    print("\n=== Converting to ASCII ===")

    timestamp = datetime.now().strftime("%Y%m%d")

    for csv_file in raw_dir.glob("*.csv"):
        output_file = companies_dir / f"{csv_file.stem}_{timestamp}.csv"
        if not output_file.exists():
            rows = convert_to_ascii(csv_file, output_file, limit)
            print(f"  Saved: {output_file.name} ({rows:,} rows)")

    # Log
    log_file = BASE_DIR / "download_log.txt"
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | converted\n")


def main():
    parser = argparse.ArgumentParser(description="Download France SIRENE data")
    parser.add_argument("--status", "-s", action="store_true", help="Show status")
    parser.add_argument("--download", "-d", choices=list(DATASETS.keys()) + ["all"], help="Download dataset")
    parser.add_argument("--extract", "-e", action="store_true", help="Extract ZIP files")
    parser.add_argument("--convert", "-c", action="store_true", help="Convert to ASCII")
    parser.add_argument("--limit", type=int, default=0, help="Limit rows for conversion")

    args = parser.parse_args()

    # Create directories
    for subdir in ["RAW", "COMPANIES"]:
        (BASE_DIR / subdir).mkdir(parents=True, exist_ok=True)

    if args.status:
        show_status()
    elif args.download:
        if args.download == "all":
            download_all()
        else:
            download_dataset(args.download)
    elif args.extract:
        extract_all()
    elif args.convert:
        convert_all(args.limit)
    else:
        show_status()
        print("\nUsage:")
        print("  --download all        Download all datasets (~5.7 GB)")
        print("  --download units      Download legal units only (~900 MB)")
        print("  --extract             Extract ZIP files")
        print("  --convert             Convert to ASCII CSV")


if __name__ == "__main__":
    main()
