#!/usr/bin/env python3
"""
EU Data Internal Enrichment

Enriches EU data (CORDIS, TED, Kohesio) with contact info from internal sources.
NO external website scraping - only matches against local databases.

Internal Sources:
- MASTER_ALL.csv: 65K employer records with emails
- ANOFM: 18K Romanian companies with emails/phones
- ONRC: 2.5M Romanian companies (for CUI matching)

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_internal_enrichment.py --all
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_internal_enrichment.py --source cordis
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_internal_enrichment.py --source kohesio --country RO
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_internal_enrichment.py --stats
    python3 /opt/ACTIVE/INFRA/SKILLS/eu_internal_enrichment.py --export
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import re
import csv
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Set, Tuple
from collections import defaultdict

from skills_common import to_ascii

# ============================================================
# CONFIGURATION
# ============================================================

# Internal data sources
MASTER_ALL = Path('/opt/ACTIVE/OPENDATA/DATA/MASTER_ALL.csv')
ANOFM_CSV = Path('/opt/ACTIVE/OPENDATA/DATA/ANOFM/anofm_merged_all.csv')
ONRC_CSV = Path('/opt/ACTIVE/OPENDATA/DATA/ONRC/onrc_firme_clean.csv')

# EU data
EU_DB = Path('/opt/ACTIVE/OPENDATA/DATA/EU_ENRICHED/eu_data.db')
KOHESIO_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EU_SUBSIDY')

# Output
ENRICHMENT_DB = Path('/opt/ACTIVE/OPENDATA/DATA/EU_ENRICHED/internal_enrichment.db')
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT')

# ============================================================
# NAME NORMALIZATION
# ============================================================

def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ''

    # Convert to ASCII lowercase
    name = to_ascii(name).lower().strip()

    # Remove common suffixes
    suffixes = [
        r'\s+(s\.?r\.?l\.?|s\.?a\.?|s\.?c\.?s\.?|ltd\.?|gmbh|ag|bv|nv|ab|as|oy|a/s)',
        r'\s+(limited|inc\.?|corp\.?|llc|plc|co\.?|company)',
        r'\s+(srl|sa|spa|sarl|eurl|sas|snc)',
    ]
    for suffix in suffixes:
        name = re.sub(suffix + r'$', '', name, flags=re.IGNORECASE)

    # Remove punctuation and extra spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    name = ' '.join(name.split())

    return name

def extract_cui(text: str) -> Optional[str]:
    """Extract Romanian CUI/tax code."""
    if not text:
        return None

    # Clean and extract digits
    text = str(text).strip()

    # RO prefix
    if text.upper().startswith('RO'):
        text = text[2:]

    # Extract numeric CUI (6-10 digits)
    match = re.search(r'\b(\d{6,10})\b', text)
    if match:
        return match.group(1)

    return None

# ============================================================
# INTERNAL DATA LOADERS
# ============================================================

def load_master_all() -> Dict[str, dict]:
    """Load MASTER_ALL.csv - company name -> contact info."""
    if not MASTER_ALL.exists():
        print(f"  Warning: {MASTER_ALL} not found")
        return {}

    contacts = {}
    with open(MASTER_ALL, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Get company name
            company = row.get('employer', '') or row.get('employer_normalized', '')
            if not company:
                continue

            norm_name = normalize_company_name(company)
            if not norm_name or len(norm_name) < 3:
                continue

            # Get emails
            emails = []
            for col in ['email1', 'email2', 'email3']:
                email = row.get(col, '').strip().lower()
                if email and '@' in email:
                    emails.append(email)

            if emails and norm_name not in contacts:
                contacts[norm_name] = {
                    'emails': emails,
                    'source': 'MASTER_ALL',
                    'country': row.get('country', ''),
                }

    print(f"  Loaded MASTER_ALL: {len(contacts):,} companies with emails")
    return contacts

def load_anofm() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Load ANOFM data - returns (name_index, cui_index)."""
    if not ANOFM_CSV.exists():
        print(f"  Warning: {ANOFM_CSV} not found")
        return {}, {}

    name_index = {}
    cui_index = {}

    with open(ANOFM_CSV, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get('company_name', '') or row.get('company_normalized', '')
            if not company:
                continue

            # Get emails
            emails = []
            for col in ['email_1', 'email_2', 'email_3']:
                email = row.get(col, '').strip().lower()
                if email and '@' in email:
                    emails.append(email)

            # Get phones
            phones = []
            for col in ['phone_1', 'phone_2']:
                phone = row.get(col, '').strip()
                if phone and len(phone) >= 9:
                    phones.append(phone)

            if not emails:
                continue

            info = {
                'emails': emails,
                'phones': phones,
                'website': row.get('company_website', ''),
                'source': 'ANOFM',
                'country': 'RO',
            }

            # Index by name
            norm_name = normalize_company_name(company)
            if norm_name and len(norm_name) >= 3:
                name_index[norm_name] = info

            # Index by CUI
            cui = extract_cui(row.get('company_org_number', ''))
            if cui:
                cui_index[cui] = info

    print(f"  Loaded ANOFM: {len(name_index):,} by name, {len(cui_index):,} by CUI")
    return name_index, cui_index

def load_onrc() -> Dict[str, dict]:
    """Load ONRC - CUI -> company info (for cross-referencing)."""
    if not ONRC_CSV.exists():
        print(f"  Warning: {ONRC_CSV} not found")
        return {}

    cui_index = {}

    with open(ONRC_CSV, 'r', encoding='utf-8', errors='ignore') as f:
        # ONRC uses ^ delimiter
        reader = csv.DictReader(f, delimiter='^')
        for row in reader:
            cui = row.get('CUI', '').strip()
            if not cui:
                continue

            website = row.get('WEB', '').strip()
            if not website:
                continue

            cui_index[cui] = {
                'name': row.get('DENUMIRE', ''),
                'website': website,
                'city': row.get('ADR_LOCALITATE', ''),
                'source': 'ONRC',
            }

    print(f"  Loaded ONRC: {len(cui_index):,} companies with websites")
    return cui_index

# ============================================================
# DATABASE
# ============================================================

def init_db():
    """Initialize enrichment database."""
    ENRICHMENT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ENRICHMENT_DB))
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS enriched_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT,
            source_id TEXT,
            company_name TEXT,
            normalized_name TEXT,
            country TEXT,
            cui TEXT,
            email TEXT,
            phone TEXT,
            website TEXT,
            match_source TEXT,
            match_type TEXT,
            enriched_date TEXT,
            UNIQUE(source_type, source_id)
        )
    ''')

    cur.execute('CREATE INDEX IF NOT EXISTS idx_source ON enriched_companies(source_type)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_country ON enriched_companies(country)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_email ON enriched_companies(email)')

    conn.commit()
    return conn

# ============================================================
# ENRICHMENT LOGIC
# ============================================================

def enrich_cordis(master: dict, anofm_name: dict, anofm_cui: dict) -> int:
    """Enrich CORDIS organizations."""
    if not EU_DB.exists():
        print("  EU database not found - run eu_data_downloader.py first")
        return 0

    conn = init_db()
    cur = conn.cursor()

    eu_conn = sqlite3.connect(str(EU_DB))
    eu_cur = eu_conn.cursor()

    eu_cur.execute('SELECT org_id, name, country, vat_number FROM cordis_orgs')
    orgs = eu_cur.fetchall()

    matched = 0
    for org_id, name, country, vat in orgs:
        norm_name = normalize_company_name(name)
        cui = extract_cui(vat) if country == 'RO' else None

        # Try matching
        match_info = None
        match_type = None

        # 1. CUI match (Romania)
        if cui and cui in anofm_cui:
            match_info = anofm_cui[cui]
            match_type = 'cui_exact'
        # 2. Name match in ANOFM
        elif norm_name in anofm_name:
            match_info = anofm_name[norm_name]
            match_type = 'name_exact'
        # 3. Name match in MASTER_ALL
        elif norm_name in master:
            match_info = master[norm_name]
            match_type = 'name_exact'

        if match_info and match_info.get('emails'):
            try:
                cur.execute('''
                    INSERT OR REPLACE INTO enriched_companies
                    (source_type, source_id, company_name, normalized_name, country,
                     cui, email, phone, website, match_source, match_type, enriched_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'cordis', org_id, to_ascii(name), norm_name, country,
                    cui, ';'.join(match_info['emails'][:3]),
                    ';'.join(match_info.get('phones', [])[:2]),
                    match_info.get('website', ''),
                    match_info['source'], match_type, datetime.now().isoformat()
                ))
                matched += 1
            except:
                pass

    conn.commit()
    conn.close()
    eu_conn.close()

    return matched

def enrich_ted(master: dict, anofm_name: dict) -> int:
    """Enrich TED contractors."""
    if not EU_DB.exists():
        return 0

    conn = init_db()
    cur = conn.cursor()

    eu_conn = sqlite3.connect(str(EU_DB))
    eu_cur = eu_conn.cursor()

    eu_cur.execute('SELECT DISTINCT contractor_name FROM ted_contractors')
    contractors = eu_cur.fetchall()

    matched = 0
    for (name,) in contractors:
        norm_name = normalize_company_name(name)

        match_info = None
        match_type = None

        if norm_name in anofm_name:
            match_info = anofm_name[norm_name]
            match_type = 'name_exact'
        elif norm_name in master:
            match_info = master[norm_name]
            match_type = 'name_exact'

        if match_info and match_info.get('emails'):
            try:
                cur.execute('''
                    INSERT OR REPLACE INTO enriched_companies
                    (source_type, source_id, company_name, normalized_name, country,
                     email, phone, website, match_source, match_type, enriched_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'ted', norm_name, to_ascii(name), norm_name,
                    match_info.get('country', ''),
                    ';'.join(match_info['emails'][:3]),
                    ';'.join(match_info.get('phones', [])[:2]),
                    match_info.get('website', ''),
                    match_info['source'], match_type, datetime.now().isoformat()
                ))
                matched += 1
            except:
                pass

    conn.commit()
    conn.close()
    eu_conn.close()

    return matched

def enrich_kohesio(master: dict, anofm_name: dict, anofm_cui: dict, country: Optional[str] = None) -> int:
    """Enrich Kohesio beneficiaries."""
    kohesio_file = KOHESIO_DIR / 'EU_KOHESIO_LATEST.csv'
    if not kohesio_file.exists():
        print("  Kohesio file not found")
        return 0

    conn = init_db()
    cur = conn.cursor()

    matched = 0
    with open(kohesio_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            co = row.get('location_country', '')
            if country and co != country:
                continue

            name = row.get('company_name', '')
            company_id = row.get('company_id', '')
            if not name or not company_id:
                continue

            norm_name = normalize_company_name(name)

            match_info = None
            match_type = None

            # Name matching
            if norm_name in anofm_name:
                match_info = anofm_name[norm_name]
                match_type = 'name_exact'
            elif norm_name in master:
                match_info = master[norm_name]
                match_type = 'name_exact'

            if match_info and match_info.get('emails'):
                batch.append((
                    'kohesio', company_id, to_ascii(name), norm_name, co,
                    None, ';'.join(match_info['emails'][:3]),
                    ';'.join(match_info.get('phones', [])[:2]),
                    match_info.get('website', ''),
                    match_info['source'], match_type, datetime.now().isoformat()
                ))
                matched += 1

                if len(batch) >= 1000:
                    cur.executemany('''
                        INSERT OR REPLACE INTO enriched_companies
                        (source_type, source_id, company_name, normalized_name, country,
                         cui, email, phone, website, match_source, match_type, enriched_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', batch)
                    conn.commit()
                    batch = []

        if batch:
            cur.executemany('''
                INSERT OR REPLACE INTO enriched_companies
                (source_type, source_id, company_name, normalized_name, country,
                 cui, email, phone, website, match_source, match_type, enriched_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            conn.commit()

    conn.close()
    return matched

# ============================================================
# STATS & EXPORT
# ============================================================

def show_stats():
    """Show enrichment statistics."""
    if not ENRICHMENT_DB.exists():
        print("No enrichment data yet. Run with --all first.")
        return

    conn = sqlite3.connect(str(ENRICHMENT_DB))
    cur = conn.cursor()

    print("\n=== INTERNAL ENRICHMENT STATISTICS ===\n")

    # Total
    cur.execute('SELECT COUNT(*), COUNT(DISTINCT email) FROM enriched_companies')
    total, unique_emails = cur.fetchone()
    print(f"Total enriched: {total:,}")
    print(f"Unique emails: {unique_emails:,}")

    # By source type
    print("\nBy EU data source:")
    cur.execute('''
        SELECT source_type, COUNT(*), COUNT(DISTINCT email)
        FROM enriched_companies GROUP BY source_type ORDER BY COUNT(*) DESC
    ''')
    for src, cnt, emails in cur.fetchall():
        print(f"  {src}: {cnt:,} records, {emails:,} emails")

    # By match source
    print("\nBy internal data source:")
    cur.execute('''
        SELECT match_source, COUNT(*)
        FROM enriched_companies GROUP BY match_source ORDER BY COUNT(*) DESC
    ''')
    for src, cnt in cur.fetchall():
        print(f"  {src}: {cnt:,}")

    # By country
    print("\nTop countries:")
    cur.execute('''
        SELECT country, COUNT(*), COUNT(DISTINCT email)
        FROM enriched_companies WHERE country != ''
        GROUP BY country ORDER BY COUNT(*) DESC LIMIT 10
    ''')
    for co, cnt, emails in cur.fetchall():
        print(f"  {co}: {cnt:,} records, {emails:,} emails")

    conn.close()

def export_enriched(output_path: Optional[Path] = None):
    """Export enriched data to CSV."""
    if not ENRICHMENT_DB.exists():
        print("No enrichment data to export")
        return

    output_path = output_path or OUTPUT_DIR / 'eu_enriched_contacts.csv'
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(ENRICHMENT_DB))
    cur = conn.cursor()

    cur.execute('SELECT * FROM enriched_companies ORDER BY source_type, country')
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(zip(cols, row)))

    conn.close()
    print(f"Exported {len(rows):,} enriched contacts to {output_path}")

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='EU Data Internal Enrichment')
    parser.add_argument('--all', action='store_true', help='Enrich all sources')
    parser.add_argument('--source', choices=['cordis', 'ted', 'kohesio'], help='Enrich specific source')
    parser.add_argument('--country', type=str, help='Filter Kohesio by country')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--export', action='store_true', help='Export to CSV')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.export:
        export_enriched()
        return

    if not any([args.all, args.source]):
        parser.print_help()
        return

    print(f"EU Internal Enrichment - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Load internal data
    print("\nLoading internal data sources...")
    master = load_master_all()
    anofm_name, anofm_cui = load_anofm()

    total_matched = 0

    # Enrich sources
    if args.all or args.source == 'cordis':
        print("\nEnriching CORDIS organizations...")
        matched = enrich_cordis(master, anofm_name, anofm_cui)
        print(f"  Matched: {matched:,}")
        total_matched += matched

    if args.all or args.source == 'ted':
        print("\nEnriching TED contractors...")
        matched = enrich_ted(master, anofm_name)
        print(f"  Matched: {matched:,}")
        total_matched += matched

    if args.all or args.source == 'kohesio':
        print("\nEnriching Kohesio beneficiaries...")
        matched = enrich_kohesio(master, anofm_name, anofm_cui, args.country)
        print(f"  Matched: {matched:,}")
        total_matched += matched

    print("\n" + "=" * 50)
    print(f"Total matched: {total_matched:,}")

    # Show stats
    show_stats()

if __name__ == '__main__':
    main()
