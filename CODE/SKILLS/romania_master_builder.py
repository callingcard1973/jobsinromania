#!/usr/bin/env python3
"""
Romania Master Builder - Merge all Romanian scraper outputs into one enriched CSV.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/romania_master_builder.py              # Build master
    python3 /opt/ACTIVE/INFRA/SKILLS/romania_master_builder.py --status     # Show source status
    python3 /opt/ACTIVE/INFRA/SKILLS/romania_master_builder.py --dry-run    # Preview without saving

Pipeline:
    1. Load all Romanian scraper CSVs
    2. Normalize columns to unified schema
    3. Deduplicate by company name + email
    4. Fuzzy enrich with ALL internal sources
    5. Save to /opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER/romania_master.csv

Sources:
    - IAJOB: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB/jobs.csv
    - ANOFM: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_latest.csv
    - Pagini Aurii: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/PAGINI_AURII/pagini_aurii_contacts.csv
    - CCIB: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/CCIB/ccib_companies.csv
    - RECOM: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/RECOM/recom_administrators.csv
    - Chambers: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/CHAMBERS/chambers_members.csv
    - DSVSA: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_MASTER.csv
    - EUFUNDS: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS/eufunds_contacts.csv
"""

import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii
except ImportError:
    import unicodedata
    def to_ascii(text):
        if not text:
            return text
        normalized = unicodedata.normalize('NFKD', str(text))
        return normalized.encode('ascii', 'ignore').decode('ascii')

# Output configuration
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER')
OUTPUT_FILE = OUTPUT_DIR / 'romania_master.csv'
ENRICHED_FILE = OUTPUT_DIR / 'romania_master_enriched.csv'

# Unified schema
MASTER_COLUMNS = [
    'company',
    'email',
    'phone',
    'city',
    'county',
    'address',
    'cui',
    'website',
    'contact_person',
    'source',
    'source_date',
]

# Source configurations: path, column mappings
SOURCES = {
    'IAJOB': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB/jobs.csv',
        'columns': {
            'company': 'company',
            'email': 'contact_email',
            'phone': 'contact_phone',
            'city': 'city',
            'county': 'county',
        }
    },
    'ANOFM': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_latest.csv',
        'columns': {
            'company': 'company_name',
            'email': 'email_1',
            'phone': 'phone_1',
            'city': 'city',
            'county': 'region',
            'address': 'company_address',
            'website': 'company_website',
            'contact_person': 'contact_person_1',
        }
    },
    'PAGINI_AURII': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/PAGINI_AURII/pagini_aurii_contacts.csv',
        'columns': {
            'company': 'name',
            'email': 'email',
            'phone': 'phone',
            'address': 'address',
            'website': 'website',
        }
    },
    'CCIB': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CCIB/ccib_companies.csv',
        'columns': {
            'company': 'name',
            'email': 'email',
            'phone': 'phone_1',
            'website': 'website',
        }
    },
    'RECOM': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/RECOM/recom_administrators.csv',
        'columns': {
            'company': 'company',
            'email': 'email',
            'phone': 'phone',
            'city': 'city',
            'county': 'county',
            'cui': 'cui',
            'contact_person': 'administrator',
        }
    },
    'CHAMBERS': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CHAMBERS/chambers_members.csv',
        'columns': {
            'company': 'name',
            'email': 'email',
            'phone': 'phone',
            'county': 'county',
            'website': 'website',
        }
    },
    'DSVSA': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_MASTER.csv',
        'columns': {
            'company': 'company_name',
            'city': 'city',
            'county': 'county',
            'address': 'address',
        }
    },
    'EUFUNDS': {
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS/eufunds_contacts.csv',
        'columns': {
            'company': 'company_name',
            'email': 'email_1',
            'phone': 'phone',
            'city': 'city',
            'county': 'county',
            'cui': 'cui',
        }
    },
}


def normalize_company(name: str) -> str:
    """Normalize company name for deduplication."""
    if not name:
        return ''
    name = to_ascii(name).upper().strip()
    # Remove common suffixes
    for suffix in [' SRL', ' SA', ' S.R.L.', ' S.A.', ' S.R.L', ' PFA', ' II', ' IF']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()


def normalize_email(email: str) -> str:
    """Normalize email for deduplication."""
    if not email:
        return ''
    return email.lower().strip()


def normalize_phone(phone: str) -> str:
    """Normalize Romanian phone number."""
    if not phone:
        return ''
    # Remove non-digits
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if not digits:
        return ''
    # Format to +40...
    if digits.startswith('40') and len(digits) >= 10:
        return f'+{digits}'
    elif digits.startswith('0') and len(digits) >= 10:
        return f'+4{digits}'
    elif len(digits) >= 9:
        return f'+40{digits}'
    return phone


def load_source(name: str, config: dict) -> list:
    """Load and normalize a source CSV."""
    path = Path(config['path'])
    if not path.exists():
        return []

    rows = []
    col_map = config['columns']

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            file_date = datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d')

            for row in reader:
                new_row = {col: '' for col in MASTER_COLUMNS}
                new_row['source'] = name
                new_row['source_date'] = file_date

                for master_col, source_col in col_map.items():
                    value = row.get(source_col, '')
                    if value:
                        new_row[master_col] = to_ascii(str(value).strip())

                # Normalize phone
                if new_row.get('phone'):
                    new_row['phone'] = normalize_phone(new_row['phone'])

                # Normalize email
                if new_row.get('email'):
                    new_row['email'] = normalize_email(new_row['email'])

                # Skip rows without company name
                if not new_row.get('company'):
                    continue

                rows.append(new_row)
    except Exception as e:
        print(f"  Error loading {name}: {e}")

    return rows


def deduplicate(rows: list) -> list:
    """Deduplicate by normalized company name, keeping best record."""
    # Group by normalized company name
    groups = defaultdict(list)
    for row in rows:
        key = normalize_company(row.get('company', ''))
        if key:
            groups[key].append(row)

    # For each group, merge/select best record
    deduped = []
    for key, group in groups.items():
        if len(group) == 1:
            deduped.append(group[0])
        else:
            # Merge: take non-empty values from all records
            merged = {col: '' for col in MASTER_COLUMNS}
            sources = set()

            for record in group:
                sources.add(record.get('source', ''))
                for col in MASTER_COLUMNS:
                    if not merged[col] and record.get(col):
                        merged[col] = record[col]

            merged['source'] = ','.join(sorted(sources))
            deduped.append(merged)

    return deduped


def show_status():
    """Show status of all sources."""
    print("=== Romania Scraper Sources ===\n")

    total_rows = 0
    total_with_email = 0
    total_with_phone = 0

    for name, config in SOURCES.items():
        path = Path(config['path'])
        if path.exists():
            rows = load_source(name, config)
            with_email = sum(1 for r in rows if r.get('email'))
            with_phone = sum(1 for r in rows if r.get('phone'))
            age_days = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days

            print(f"{name:15} {len(rows):6} rows | email: {with_email:5} | phone: {with_phone:5} | {age_days}d old")
            total_rows += len(rows)
            total_with_email += with_email
            total_with_phone += with_phone
        else:
            print(f"{name:15} NOT FOUND: {config['path']}")

    print(f"\n{'TOTAL':15} {total_rows:6} rows | email: {total_with_email:5} | phone: {total_with_phone:5}")

    # Check master file
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r') as f:
            master_rows = len(f.readlines()) - 1
        age = (datetime.now() - datetime.fromtimestamp(OUTPUT_FILE.stat().st_mtime)).days
        print(f"\nMaster file: {master_rows} rows, {age}d old")
    else:
        print(f"\nMaster file: NOT BUILT")


def build_master(dry_run: bool = False):
    """Build the master CSV from all sources."""
    print("=== Building Romania Master CSV ===\n")

    all_rows = []

    # Load all sources
    for name, config in SOURCES.items():
        rows = load_source(name, config)
        print(f"Loaded {name}: {len(rows)} rows")
        all_rows.extend(rows)

    print(f"\nTotal before dedup: {len(all_rows)}")

    # Deduplicate
    deduped = deduplicate(all_rows)
    print(f"After dedup: {len(deduped)}")

    # Stats
    with_email = sum(1 for r in deduped if r.get('email'))
    with_phone = sum(1 for r in deduped if r.get('phone'))
    print(f"With email: {with_email}")
    print(f"With phone: {with_phone}")

    if dry_run:
        print("\n[DRY RUN] Not saving.")
        return

    # Save master
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\nSaved: {OUTPUT_FILE}")

    # Run fuzzy enrichment
    print("\n=== Running Fuzzy Enrichment ===")
    import subprocess
    result = subprocess.run([
        '/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/fuzzy_enrich.py',
        str(OUTPUT_FILE),
        '--name-col', 'company',
        '--all-sources',
        '--threshold', '85'
    ], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    # Send notification
    try:
        sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
        from alerting import send_telegram
        send_telegram(f"Romania Master Built\nCompanies: {len(deduped)}\nWith email: {with_email}\nWith phone: {with_phone}")
    except:
        pass


def main():
    parser = argparse.ArgumentParser(description='Build Romania master CSV from all scrapers')
    parser.add_argument('--status', action='store_true', help='Show source status')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        build_master(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
