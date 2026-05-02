#!/usr/bin/env python3
"""
consolidate_all_agencies.py - Consolidate all agency CSVs into master file.

Collects agency data from:
- Local raspi CSVs
- Remote raspibig CSVs (via SSH)

Normalizes, deduplicates, and outputs to:
- /opt/ACTIVE/OPENDATA/DATA/AGENCIES_MASTER_ALL.csv
- /opt/ACTIVE/OPENDATA/DATA/agencies.db (SQLite)

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/consolidate_all_agencies.py
    python3 /opt/ACTIVE/INFRA/SKILLS/consolidate_all_agencies.py --dry-run
    python3 /opt/ACTIVE/INFRA/SKILLS/consolidate_all_agencies.py --local-only
"""

import os
import sys
import csv
import re
import sqlite3
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add shared code
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize
from alerting import send_telegram

# Configuration
LOCAL_OUTPUT_CSV = '/tmp/AGENCIES_MASTER_ALL.csv'
LOCAL_OUTPUT_DB = '/tmp/agencies.db'
RASPIBIG_HOST = '192.168.100.21'
RASPIBIG_OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/AGENCIES'
OUTPUT_CSV = f'{RASPIBIG_OUTPUT_DIR}/AGENCIES_MASTER_ALL.csv'
OUTPUT_DB = f'{RASPIBIG_OUTPUT_DIR}/agencies.db'
TEMP_DIR = '/tmp/agencies_consolidation'

# Column mappings: source column -> standard column
COLUMN_MAPPINGS = {
    # Company name variants
    'name': 'company_name',
    'company': 'company_name',
    'employer': 'company_name',
    'nazev': 'company_name',
    'firma': 'company_name',
    'company_name': 'company_name',
    'agency_name': 'company_name',
    'denumire': 'company_name',
    'nume': 'company_name',
    'nume_firma': 'company_name',

    # Email variants
    'email': 'email',
    'email_1': 'email',
    'email_address': 'email',
    'kontaktniosoby': 'email',
    'e-mail': 'email',
    'mail': 'email',

    # Phone variants
    'phone': 'phone',
    'phone_1': 'phone',
    'tel': 'phone',
    'telefon': 'phone',
    'telephone': 'phone',
    'mobile': 'phone',

    # Address variants
    'address': 'address',
    'adresa': 'address',
    'adresa_sediu': 'address',
    'street': 'address',
    'ulice': 'address',

    # City variants
    'city': 'city',
    'mesto': 'city',
    'oras': 'city',
    'locality': 'city',

    # Country variants
    'country': 'country',
    'stat': 'country',
    'tara': 'country',
    'zeme': 'country',

    # Website variants
    'website': 'website',
    'web': 'website',
    'url': 'website',
    'www': 'website',
    'site': 'website',

    # ID variants
    'id': 'source_id',
    'cui': 'source_id',
    'ico': 'source_id',
    'reg_number': 'source_id',
    'idno': 'source_id',
}

# Files to collect from each machine
RASPI_FILES = [
    '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/POLAND/OUTPUT/kraz_agencies_*.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND_AGENCIES/contacts/all_contacts.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/GERMANY_AGENCIES/contacts/all_contacts.csv',
    '/opt/ACTIVE/OPENDATA/DATA/RECRUITMENT_AGENCIES.csv',
    '/opt/ACTIVE/OPENDATA/DATA/MOLDOVA/agencies.csv',
    '/opt/ACTIVE/OPENDATA/DATA/FACTORY_CAMPAIGN_AGENCIES_*.csv',
    '/opt/ACTIVE/OPENDATA/DATA/DAILY/BULGARIA_AGENCIES_*.csv',
    '/opt/ACTIVE/OPENDATA/DATA/EU_EMPLOYMENT/*_agencies*.csv',
    '/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES/*agencies*.csv',
]

# Files to exclude (statistical/non-agency data, tourism)
EXCLUDE_PATTERNS = [
    'eurostat_',
    '_workers.csv',
    '_turnover.csv',
    'National_Employment_Programme',
    'National_Training_Plan',
    'TOURISM',
    'tourism',
]

RASPIBIG_FILES = [
    '/opt/ACTIVE/OPENDATA/DATA/EU_REGISTRIES/EMPLOYMENT/cz_employment_agencies.csv',
    '/opt/ACTIVE/OPENDATA/DATA/EU_REGISTRIES/EMPLOYMENT/it_campania_agencies.csv',
    '/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES/AGENCIES_MASTER_MERGED.csv',
    '/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES/all_sources_agencies.csv',
    '/opt/ACTIVE/OPENDATA/DATA/EU_EMPLOYMENT/discovery_employment_agencies_*.csv',
    '/opt/ACTIVE/OPENDATA/DATA/EU_EMPLOYMENT/es_agencies.csv',
    '/opt/ACTIVE/OPENDATA/DATA/EU_EMPLOYMENT/it_agencies_contacts.csv',
    '/opt/ACTIVE/OPENDATA/DATA/EU_EMPLOYMENT/cz_agencies_contacts.csv',
    '/opt/ACTIVE/OPENDATA/DATA/MOLDOVA/agencies.csv',
    '/opt/ACTIVE/OPENDATA/DATA/MOLDOVA/delucru_agencies.csv',
]


def normalize_email(email: str) -> str:
    """Normalize email to lowercase, trim whitespace."""
    if not email:
        return ''
    email = str(email).lower().strip()
    # Basic validation
    if '@' not in email or '.' not in email:
        return ''
    # Remove common invalid patterns
    if email in ('none', 'null', 'na', 'n/a', '-', '.', '@'):
        return ''
    return email


def normalize_phone(phone: str) -> str:
    """Normalize phone number."""
    if not phone:
        return ''
    phone = str(phone).strip()
    # Remove common invalid patterns
    if phone in ('none', 'null', 'na', 'n/a', '-', '.'):
        return ''
    # Remove non-digit characters except + at start
    cleaned = re.sub(r'[^\d+]', '', phone)
    if not cleaned or len(cleaned) < 6:
        return ''
    return cleaned


def normalize_columns(row: Dict, filename: str) -> Dict:
    """Normalize column names to standard schema."""
    result = {
        'company_name': '',
        'email': '',
        'phone': '',
        'country': '',
        'address': '',
        'city': '',
        'website': '',
        'source_id': '',
        'source_file': os.path.basename(filename),
    }

    for key, value in row.items():
        if not key or not value:
            continue
        key_lower = key.lower().strip().replace(' ', '_')
        if key_lower in COLUMN_MAPPINGS:
            std_col = COLUMN_MAPPINGS[key_lower]
            # Don't overwrite if already set
            if not result[std_col]:
                result[std_col] = str(value).strip()

    # Apply normalization
    result['company_name'] = sanitize(result['company_name'], 'company')
    result['email'] = normalize_email(result['email'])
    result['phone'] = normalize_phone(result['phone'])
    result['address'] = sanitize(result['address'], 'address')
    result['city'] = sanitize(result['city'], 'city')
    result['country'] = sanitize(result['country'], 'country')
    result['website'] = sanitize(result['website'], 'url')

    return result


def should_exclude(filepath: str) -> bool:
    """Check if file should be excluded based on patterns."""
    basename = os.path.basename(filepath)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in basename:
            return True
    return False


def collect_local_files() -> List[str]:
    """Collect all agency CSV files from local machine."""
    files = []
    for pattern in RASPI_FILES:
        if '*' in pattern:
            # Glob pattern
            from glob import glob
            found = glob(pattern)
            for f in found:
                if not should_exclude(f):
                    files.append(f)
        elif os.path.exists(pattern) and not should_exclude(pattern):
            files.append(pattern)
    return files


def collect_remote_files(host: str, patterns: List[str], temp_dir: str) -> List[str]:
    """Collect files from remote machine via SSH."""
    files = []
    for pattern in patterns:
        # Use SSH to find files
        if '*' in pattern:
            cmd = f"ssh {host} 'ls {pattern} 2>/dev/null'"
        else:
            cmd = f"ssh {host} 'test -f {pattern} && echo {pattern}'"

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            remote_files = result.stdout.strip().split('\n')
            for remote_file in remote_files:
                if not remote_file:
                    continue
                # Copy to temp directory
                local_name = os.path.basename(remote_file)
                local_path = os.path.join(temp_dir, f'raspibig_{local_name}')
                scp_cmd = f"scp -q {host}:{remote_file} {local_path}"
                scp_result = subprocess.run(scp_cmd, shell=True, capture_output=True)
                if scp_result.returncode == 0 and os.path.exists(local_path):
                    files.append(local_path)
                    print(f"  Copied: {remote_file}")
    return files


def read_csv_safely(filepath: str) -> List[Dict]:
    """Read CSV file with encoding detection and error handling."""
    rows = []
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                # Try to detect delimiter
                sample = f.read(4096)
                f.seek(0)

                # Detect delimiter
                if '\t' in sample and sample.count('\t') > sample.count(','):
                    delimiter = '\t'
                elif ';' in sample and sample.count(';') > sample.count(','):
                    delimiter = ';'
                else:
                    delimiter = ','

                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    rows.append(row)
                break
        except (UnicodeDecodeError, csv.Error):
            continue
        except Exception as e:
            print(f"  Error reading {filepath}: {e}")
            break

    return rows


def deduplicate_agencies(agencies: List[Dict]) -> List[Dict]:
    """Deduplicate agencies by email (primary) and company name (secondary)."""
    seen_emails: Set[str] = set()
    seen_names: Set[str] = set()
    unique = []

    # Sort by email (prefer rows with email)
    agencies.sort(key=lambda x: (not x['email'], not x['phone']))

    for agency in agencies:
        email = agency['email']
        name_key = agency['company_name'].lower()

        # Primary dedup by email
        if email:
            if email in seen_emails:
                continue
            seen_emails.add(email)
            unique.append(agency)
        # Secondary dedup by company name (only if no email)
        elif name_key:
            if name_key in seen_names:
                continue
            seen_names.add(name_key)
            unique.append(agency)

    return unique


def create_database(db_path: str, agencies: List[Dict]):
    """Create/update SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            country TEXT,
            address TEXT,
            city TEXT,
            website TEXT,
            source_file TEXT,
            source_id TEXT,
            scrape_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON agencies(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON agencies(country)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company ON agencies(company_name)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agency_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agency_id INTEGER,
            field_changed TEXT,
            old_value TEXT,
            new_value TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agency_id) REFERENCES agencies(id)
        )
    ''')

    # Clear existing data and insert new
    cursor.execute('DELETE FROM agencies')

    today = datetime.now().strftime('%Y-%m-%d')
    for agency in agencies:
        cursor.execute('''
            INSERT OR IGNORE INTO agencies
            (company_name, email, phone, country, address, city, website, source_file, source_id, scrape_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agency['company_name'],
            agency['email'] or None,
            agency['phone'],
            agency['country'],
            agency['address'],
            agency['city'],
            agency['website'],
            agency['source_file'],
            agency.get('source_id', ''),
            today,
        ))

    conn.commit()
    conn.close()


def write_csv(filepath: str, agencies: List[Dict]):
    """Write agencies to CSV file."""
    if not agencies:
        print("No agencies to write!")
        return

    fieldnames = ['company_name', 'email', 'phone', 'country', 'address', 'city', 'website', 'source_file']

    with open(filepath, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(agencies)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Consolidate all agency CSVs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--local-only', action='store_true', help='Skip remote files')
    parser.add_argument('--no-notify', action='store_true', help='Skip Telegram notification')
    args = parser.parse_args()

    print("="*60)
    print("AGENCY CONSOLIDATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Create temp directory
    os.makedirs(TEMP_DIR, exist_ok=True)

    all_agencies = []
    stats = {
        'local_files': 0,
        'remote_files': 0,
        'total_rows': 0,
        'unique_agencies': 0,
        'with_email': 0,
        'with_phone': 0,
    }

    # Collect local files
    print("\n[1/4] Collecting local files...")
    local_files = collect_local_files()
    stats['local_files'] = len(local_files)
    print(f"  Found {len(local_files)} local files")

    for filepath in local_files:
        rows = read_csv_safely(filepath)
        for row in rows:
            normalized = normalize_columns(row, filepath)
            if normalized['company_name'] or normalized['email']:
                all_agencies.append(normalized)
        print(f"  {os.path.basename(filepath)}: {len(rows)} rows")

    # Collect remote files
    if not args.local_only:
        print("\n[2/4] Collecting remote files from raspibig...")
        try:
            remote_files = collect_remote_files(RASPIBIG_HOST, RASPIBIG_FILES, TEMP_DIR)
            stats['remote_files'] = len(remote_files)
            print(f"  Found {len(remote_files)} remote files")

            for filepath in remote_files:
                rows = read_csv_safely(filepath)
                for row in rows:
                    normalized = normalize_columns(row, filepath)
                    if normalized['company_name'] or normalized['email']:
                        all_agencies.append(normalized)
                print(f"  {os.path.basename(filepath)}: {len(rows)} rows")
        except Exception as e:
            print(f"  Warning: Could not fetch remote files: {e}")
    else:
        print("\n[2/4] Skipping remote files (--local-only)")

    stats['total_rows'] = len(all_agencies)
    print(f"\nTotal rows before dedup: {stats['total_rows']}")

    # Deduplicate
    print("\n[3/4] Deduplicating...")
    unique_agencies = deduplicate_agencies(all_agencies)
    stats['unique_agencies'] = len(unique_agencies)
    stats['with_email'] = sum(1 for a in unique_agencies if a['email'])
    stats['with_phone'] = sum(1 for a in unique_agencies if a['phone'])

    print(f"  Unique agencies: {stats['unique_agencies']}")
    print(f"  With email: {stats['with_email']}")
    print(f"  With phone: {stats['with_phone']}")
    print(f"  Duplicates removed: {stats['total_rows'] - stats['unique_agencies']}")

    if args.dry_run:
        print("\n[DRY RUN] Would write to:")
        print(f"  CSV: {OUTPUT_CSV}")
        print(f"  DB: {OUTPUT_DB}")
        return

    # Write outputs
    print("\n[4/4] Writing outputs...")

    # Write locally first
    os.makedirs('/tmp/agencies_output', exist_ok=True)
    local_csv = '/tmp/agencies_output/AGENCIES_MASTER_ALL.csv'
    local_db = '/tmp/agencies_output/agencies.db'

    # Write CSV
    write_csv(local_csv, unique_agencies)
    print(f"  Local CSV: {local_csv}")

    # Verify ASCII
    result = subprocess.run(['file', local_csv], capture_output=True, text=True)
    print(f"  File type: {result.stdout.strip()}")

    # Write database
    create_database(local_db, unique_agencies)
    print(f"  Local DB: {local_db}")

    # Get file sizes
    csv_size = os.path.getsize(local_csv)
    db_size = os.path.getsize(local_db)

    # Copy to RASPIBIG (primary storage)
    print(f"\n  Copying to raspibig (primary)...")
    scp_csv = subprocess.run(f"scp -q {local_csv} {RASPIBIG_HOST}:{OUTPUT_CSV}", shell=True)
    scp_db = subprocess.run(f"scp -q {local_db} {RASPIBIG_HOST}:{OUTPUT_DB}", shell=True)
    if scp_csv.returncode == 0 and scp_db.returncode == 0:
        print(f"  PRIMARY: {RASPIBIG_HOST}:{OUTPUT_CSV}")
        print(f"  PRIMARY: {RASPIBIG_HOST}:{OUTPUT_DB}")
    else:
        print(f"  WARNING: Failed to copy to raspibig!")

    # Keep backup on raspi
    backup_dir = '/opt/ACTIVE/OPENDATA/DATA/BACKUP'
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy(local_csv, f"{backup_dir}/AGENCIES_MASTER_ALL.csv")
    shutil.copy(local_db, f"{backup_dir}/agencies.db")
    print(f"  BACKUP: {backup_dir}/AGENCIES_MASTER_ALL.csv")

    # Cleanup temp directory
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

    # Summary
    print("\n" + "="*60)
    print("CONSOLIDATION COMPLETE")
    print("="*60)
    print(f"Files processed: {stats['local_files']} local + {stats['remote_files']} remote")
    print(f"Total rows: {stats['total_rows']}")
    print(f"Unique agencies: {stats['unique_agencies']}")
    print(f"With email: {stats['with_email']} ({100*stats['with_email']/max(1,stats['unique_agencies']):.1f}%)")
    print(f"With phone: {stats['with_phone']} ({100*stats['with_phone']/max(1,stats['unique_agencies']):.1f}%)")
    print(f"CSV size: {csv_size/1024:.1f} KB")
    print(f"DB size: {db_size/1024:.1f} KB")
    print(f"PRIMARY: raspibig:{OUTPUT_CSV}")
    print(f"BACKUP: raspi:{backup_dir}/")

    # Send notification
    if not args.no_notify:
        try:
            msg = (
                f"Agencies Consolidated\n\n"
                f"Files: {stats['local_files']} local + {stats['remote_files']} remote\n"
                f"Unique: {stats['unique_agencies']:,}\n"
                f"Email: {stats['with_email']:,}\n"
                f"Phone: {stats['with_phone']:,}\n"
                f"Primary: raspibig:{OUTPUT_CSV}"
            )
            send_telegram(msg)
            print("\nTelegram notification sent")
        except Exception as e:
            print(f"\nTelegram notification failed: {e}")

    return stats


if __name__ == '__main__':
    main()
