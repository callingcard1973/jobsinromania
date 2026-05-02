#!/usr/bin/env python3
"""
EU Data Downloader - Download and process EU funding/procurement data.

Downloads:
- CORDIS: EU research project organizations (with websites)
- TED: EU procurement contracts (contractors)

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_data_downloader.py --all
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_data_downloader.py --cordis
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_data_downloader.py --ted
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_data_downloader.py --ted --years 2024,2025
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import zipfile
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request
import ssl

from skills_common import to_ascii, clean_text

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT')
DB_PATH = Path('/opt/ACTIVE/OPENDATA/DATA/EU_ENRICHED/eu_data.db')

# Working URLs (verified Jan 2026)
CORDIS_URLS = {
    'horizon_europe': 'https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip',
    'horizon_2020': 'https://cordis.europa.eu/data/cordis-h2020projects-csv.zip',
    'fp7': 'https://cordis.europa.eu/data/cordis-fp7projects-csv.zip',
}

TED_URL_TEMPLATE = 'https://ted.europa.eu/en/simap/contracts-awarded-by-eu-institutions/-/downloadCan/rsjg/file/296/{year}_ALL.CSV'

# ============================================================
# DATABASE
# ============================================================

def init_db():
    """Initialize SQLite database for EU data."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Organizations from CORDIS
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cordis_orgs (
            org_id TEXT PRIMARY KEY,
            name TEXT,
            short_name TEXT,
            country TEXT,
            city TEXT,
            website TEXT,
            vat_number TEXT,
            sme INTEGER,
            activity_type TEXT,
            project_count INTEGER DEFAULT 1,
            total_funding REAL DEFAULT 0,
            last_updated TEXT
        )
    ''')

    # Contractors from TED
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ted_contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id TEXT,
            contractor_name TEXT,
            contract_title TEXT,
            contract_value REAL,
            currency TEXT,
            award_date TEXT,
            procedure_type TEXT,
            last_updated TEXT,
            UNIQUE(notice_id, contractor_name)
        )
    ''')

    # Indexes
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cordis_country ON cordis_orgs(country)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cordis_website ON cordis_orgs(website)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_ted_contractor ON ted_contractors(contractor_name)')

    conn.commit()
    return conn

# ============================================================
# DOWNLOAD UTILITIES
# ============================================================

def download_file(url: str, dest: Path, desc: str = '') -> bool:
    """Download file with progress."""
    print(f"Downloading {desc or url}...")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=300) as response:
            total = int(response.headers.get('Content-Length', 0))
            downloaded = 0

            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        print(f"\r  {pct}% ({downloaded:,}/{total:,} bytes)", end='', flush=True)

            print(f"\n  Saved: {dest} ({dest.stat().st_size:,} bytes)")
            return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

# ============================================================
# CORDIS PROCESSING
# ============================================================

def download_cordis(programmes: Optional[list] = None):
    """Download CORDIS data."""
    programmes = programmes or list(CORDIS_URLS.keys())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for prog in programmes:
        if prog not in CORDIS_URLS:
            print(f"Unknown programme: {prog}")
            continue

        url = CORDIS_URLS[prog]
        dest = OUTPUT_DIR / f'cordis_{prog}.zip'

        if download_file(url, dest, f"CORDIS {prog}"):
            downloaded.append(dest)

    return downloaded

def process_cordis(zip_paths: list):
    """Process CORDIS zip files and extract organizations."""
    conn = init_db()
    cur = conn.cursor()

    total_orgs = 0
    total_with_website = 0

    for zip_path in zip_paths:
        print(f"\nProcessing {zip_path.name}...")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Find organization.csv
                org_file = None
                for name in zf.namelist():
                    if 'organization' in name.lower() and name.endswith('.csv'):
                        org_file = name
                        break

                if not org_file:
                    print(f"  No organization.csv found in {zip_path.name}")
                    continue

                with zf.open(org_file) as f:
                    # CORDIS uses semicolon delimiter
                    content = f.read().decode('utf-8', errors='ignore')
                    reader = csv.DictReader(content.splitlines(), delimiter=';')

                    batch = []
                    for row in reader:
                        org_id = row.get('organisationID', '').strip()
                        if not org_id:
                            continue

                        website = row.get('organizationURL', '').strip()
                        funding = 0
                        try:
                            funding = float(row.get('ecContribution', 0) or 0)
                        except:
                            pass

                        batch.append((
                            org_id,
                            to_ascii(row.get('name', '')),
                            to_ascii(row.get('shortName', '')),
                            row.get('country', ''),
                            to_ascii(row.get('city', '')),
                            website if website and website.startswith('http') else None,
                            row.get('vatNumber', ''),
                            1 if row.get('SME', '').lower() == 'true' else 0,
                            row.get('activityType', ''),
                            1,  # project_count
                            funding,
                            datetime.now().isoformat()
                        ))

                        if website:
                            total_with_website += 1
                        total_orgs += 1

                        if len(batch) >= 1000:
                            cur.executemany('''
                                INSERT OR REPLACE INTO cordis_orgs
                                (org_id, name, short_name, country, city, website,
                                 vat_number, sme, activity_type, project_count, total_funding, last_updated)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', batch)
                            conn.commit()
                            batch = []

                    if batch:
                        cur.executemany('''
                            INSERT OR REPLACE INTO cordis_orgs
                            (org_id, name, short_name, country, city, website,
                             vat_number, sme, activity_type, project_count, total_funding, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', batch)
                        conn.commit()

        except Exception as e:
            print(f"  Error processing {zip_path.name}: {e}")

    conn.close()
    print(f"\nCORDIS Summary:")
    print(f"  Total organizations: {total_orgs:,}")
    print(f"  With website: {total_with_website:,}")

    return total_orgs, total_with_website

# ============================================================
# TED PROCESSING
# ============================================================

def download_ted(years: Optional[list] = None):
    """Download TED procurement data."""
    years = years or [2025, 2024, 2023]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for year in years:
        url = TED_URL_TEMPLATE.format(year=year)
        dest = OUTPUT_DIR / f'ted_{year}.csv'

        if download_file(url, dest, f"TED {year}"):
            downloaded.append(dest)

    return downloaded

def process_ted(csv_paths: list):
    """Process TED CSV files and extract contractors."""
    conn = init_db()
    cur = conn.cursor()

    total_contracts = 0
    unique_contractors = set()

    for csv_path in csv_paths:
        print(f"\nProcessing {csv_path.name}...")

        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)

                batch = []
                for row in reader:
                    contractor = row.get('Contractor awarded', '').strip()
                    if not contractor or contractor.lower() in ('not awarded', ''):
                        continue

                    notice_id = row.get('Notice publication number', '').strip()

                    # Parse value
                    value = 0
                    try:
                        val_str = row.get('Value of the tender', '').strip()
                        if val_str:
                            value = float(val_str.replace(',', ''))
                    except:
                        pass

                    batch.append((
                        notice_id,
                        to_ascii(contractor),
                        to_ascii(row.get('Title', '')),
                        value,
                        row.get('Currency', 'EUR'),
                        row.get('Publication date', ''),
                        row.get('Type of procedure', ''),
                        datetime.now().isoformat()
                    ))

                    unique_contractors.add(contractor.lower())
                    total_contracts += 1

                    if len(batch) >= 1000:
                        cur.executemany('''
                            INSERT OR IGNORE INTO ted_contractors
                            (notice_id, contractor_name, contract_title, contract_value,
                             currency, award_date, procedure_type, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', batch)
                        conn.commit()
                        batch = []

                if batch:
                    cur.executemany('''
                        INSERT OR IGNORE INTO ted_contractors
                        (notice_id, contractor_name, contract_title, contract_value,
                         currency, award_date, procedure_type, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', batch)
                    conn.commit()

        except Exception as e:
            print(f"  Error processing {csv_path.name}: {e}")

    conn.close()
    print(f"\nTED Summary:")
    print(f"  Total contracts: {total_contracts:,}")
    print(f"  Unique contractors: {len(unique_contractors):,}")

    return total_contracts, len(unique_contractors)

# ============================================================
# EXPORT
# ============================================================

def export_cordis_orgs(output_path: Optional[Path] = None, country: Optional[str] = None):
    """Export CORDIS organizations to CSV."""
    output_path = output_path or OUTPUT_DIR / 'cordis_organizations.csv'

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    query = 'SELECT * FROM cordis_orgs WHERE website IS NOT NULL'
    params = []
    if country:
        query += ' AND country = ?'
        params.append(country)
    query += ' ORDER BY total_funding DESC'

    cur.execute(query, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(zip(cols, row)))

    conn.close()
    print(f"Exported {len(rows):,} organizations to {output_path}")
    return len(rows)

def export_ted_contractors(output_path: Optional[Path] = None):
    """Export TED contractors to CSV."""
    output_path = output_path or OUTPUT_DIR / 'ted_contractors.csv'

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute('''
        SELECT contractor_name, COUNT(*) as contract_count,
               SUM(contract_value) as total_value, GROUP_CONCAT(DISTINCT currency) as currencies
        FROM ted_contractors
        GROUP BY contractor_name
        ORDER BY total_value DESC
    ''')
    rows = cur.fetchall()

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['contractor_name', 'contract_count', 'total_value', 'currencies'])
        writer.writerows(rows)

    conn.close()
    print(f"Exported {len(rows):,} contractors to {output_path}")
    return len(rows)

# ============================================================
# STATS
# ============================================================

def show_stats():
    """Show database statistics."""
    if not DB_PATH.exists():
        print("Database not found. Run with --cordis or --ted first.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    print("\n=== EU Data Statistics ===\n")

    # CORDIS stats
    cur.execute('SELECT COUNT(*), COUNT(website) FROM cordis_orgs')
    total, with_web = cur.fetchone()
    print(f"CORDIS Organizations: {total:,}")
    print(f"  With website: {with_web:,} ({with_web*100//max(total,1)}%)")

    cur.execute('SELECT country, COUNT(*) FROM cordis_orgs GROUP BY country ORDER BY COUNT(*) DESC LIMIT 10')
    print("\n  Top countries:")
    for country, cnt in cur.fetchall():
        print(f"    {country}: {cnt:,}")

    # TED stats
    cur.execute('SELECT COUNT(*), COUNT(DISTINCT contractor_name) FROM ted_contractors')
    contracts, contractors = cur.fetchone()
    print(f"\nTED Contracts: {contracts:,}")
    print(f"  Unique contractors: {contractors:,}")

    cur.execute('SELECT SUM(contract_value) FROM ted_contractors WHERE currency = "EUR"')
    total_value = cur.fetchone()[0] or 0
    print(f"  Total value (EUR): {total_value:,.0f}")

    conn.close()

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='EU Data Downloader')
    parser.add_argument('--all', action='store_true', help='Download all sources')
    parser.add_argument('--cordis', action='store_true', help='Download CORDIS data')
    parser.add_argument('--ted', action='store_true', help='Download TED procurement data')
    parser.add_argument('--years', type=str, help='TED years to download (comma-separated)')
    parser.add_argument('--export', action='store_true', help='Export to CSV')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--country', type=str, help='Filter by country code')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if not any([args.all, args.cordis, args.ted, args.export]):
        parser.print_help()
        return

    print(f"EU Data Downloader - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Download CORDIS
    if args.all or args.cordis:
        print("\n[CORDIS]")
        zips = download_cordis()
        if zips:
            process_cordis(zips)

    # Download TED
    if args.all or args.ted:
        print("\n[TED]")
        years = None
        if args.years:
            years = [int(y.strip()) for y in args.years.split(',')]
        csvs = download_ted(years)
        if csvs:
            process_ted(csvs)

    # Export
    if args.export:
        print("\n[EXPORT]")
        export_cordis_orgs(country=args.country)
        export_ted_contractors()

    # Final stats
    show_stats()

    print("\n" + "=" * 50)
    print("Done!")

if __name__ == '__main__':
    main()
