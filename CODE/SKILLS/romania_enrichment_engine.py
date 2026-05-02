#!/usr/bin/env python3
"""
Romania Unified Enrichment Engine

Bidirectional enrichment for all Romanian open data sources.
Matches on CUI (batch), then email, phone. Enriches ALL available fields.

Usage:
    python3 romania_enrichment_engine.py --source anofm --file scrape.csv
    python3 romania_enrichment_engine.py --source anofm --file scrape.csv --reverse
    python3 romania_enrichment_engine.py --stats
    python3 romania_enrichment_engine.py --test-match --cui 12345678

Sources: ANOFM, ONRC, ANAF, SEAP, BPI, MADR, DSVSA, LISTA_FIRME
"""

import os
import sys
import csv
import re
import argparse
import unicodedata
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor

# === CONFIG ===
DB_INTERNAL = [
    {
        'name': 'interjob_master', 'table': 'companies', 'host': 'localhost', 'user': 'tudor', 'password': 'scraper123',
        'email_cols': ['email'],
        'phone_cols': ['phone'],
        'name_col': 'name',
    },
    {
        'name': 'romania_emails', 'table': 'contacts', 'host': 'localhost', 'user': 'tudor', 'password': 'scraper123',
        'email_cols': ['email', 'email_2', 'email_3', 'hr_email'],
        'phone_cols': ['phone', 'phone_2', 'phone_3', 'mobile'],
        'name_col': 'company_name',
    },
]

# Field mappings for different sources
FIELD_MAPS = {
    'anofm': {
        'cui': ['company_org_number', 'cui', 'cif'],
        'company': ['company_name', 'employer', 'firma'],
        'email': ['email_1', 'email_2', 'email_3', 'email'],
        'phone': ['phone_1', 'phone_2', 'phone_3', 'phone'],
        'contact': ['contact_person_1', 'contact_person_2', 'contact_person', 'contact_name'],
        'city': ['city', 'company_city', 'locality'],
        'county': ['region', 'county', 'judet'],
        'address': ['company_address', 'address'],
        'website': ['company_website', 'website'],
        'sector': ['sector', 'occupation', 'caen'],
    },
    'default': {
        'cui': ['cui', 'cif', 'cod_fiscal', 'company_org_number', 'fiscal_code'],
        'company': ['company_name', 'company', 'nume', 'denumire', 'firma', 'employer', 'name'],
        'email': ['email', 'email_1', 'email_2', 'email_3', 'hr_email', 'contact_email'],
        'phone': ['phone', 'phone_1', 'phone_2', 'phone_3', 'telefon', 'tel', 'mobile'],
        'contact': ['contact_person', 'contact_name', 'contact_person_1', 'administrator'],
        'city': ['city', 'oras', 'localitate', 'municipality'],
        'county': ['county', 'judet', 'region'],
        'address': ['address', 'adresa', 'sediu'],
        'website': ['website', 'web', 'site'],
        'sector': ['sector', 'caen', 'industry', 'activitate'],
    }
}

# === NORMALIZATION ===

def to_ascii(text):
    if not text:
        return ''
    text = str(text).strip()
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

def normalize_cui(cui):
    if not cui:
        return None
    digits = re.sub(r'[^0-9]', '', str(cui))
    return digits if len(digits) >= 5 else None

def normalize_phone(phone):
    if not phone:
        return None
    digits = re.sub(r'[^0-9]', '', str(phone))
    if len(digits) < 9:
        return None
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('40') and len(digits) >= 11:
        return '+' + digits[:11]
    if digits.startswith('0') and len(digits) == 10:
        return '+4' + digits
    if len(digits) == 9:
        return '+40' + digits
    return None

def normalize_email(email):
    if not email or '@' not in str(email):
        return None
    email = str(email).strip().lower()
    if not re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email):
        return None
    if re.search(r'@(gov\.ro|edu\.ro|mil\.ro|politia|anaf|anofm)', email):
        return None
    return email

# === FIELD EXTRACTION ===

def get_field_value(row, field_type, source='default'):
    field_map = FIELD_MAPS.get(source, FIELD_MAPS['default'])
    possible_cols = field_map.get(field_type, [])
    for col in possible_cols:
        if col in row:
            val = row[col]
            if val and str(val).strip():
                return str(val).strip()
    return None

def get_all_field_values(row, field_type, source='default'):
    field_map = FIELD_MAPS.get(source, FIELD_MAPS['default'])
    possible_cols = field_map.get(field_type, [])
    values = []
    for col in possible_cols:
        if col in row:
            val = row[col]
            if val and str(val).strip():
                val = str(val).strip()
                if val not in values:
                    values.append(val)
    return values

def extract_record(row, source='default'):
    record = {
        'cui': normalize_cui(get_field_value(row, 'cui', source)),
        'company': get_field_value(row, 'company', source),
        'city': get_field_value(row, 'city', source),
        'county': get_field_value(row, 'county', source),
        'address': get_field_value(row, 'address', source),
        'website': get_field_value(row, 'website', source),
        'sector': get_field_value(row, 'sector', source),
    }
    emails = get_all_field_values(row, 'email', source)
    record['emails'] = [normalize_email(e) for e in emails if normalize_email(e)]
    phones = get_all_field_values(row, 'phone', source)
    record['phones'] = [normalize_phone(p) for p in phones if normalize_phone(p)]
    contacts = get_all_field_values(row, 'contact', source)
    record['contacts'] = [c for c in contacts if c]
    return record

# === BATCH DATABASE MATCHING ===

def get_db_connection(db_config):
    return psycopg2.connect(
        host=db_config['host'],
        dbname=db_config['name'],
        user=db_config['user'],
        password=db_config['password']
    )

def batch_match_by_cui(cui_list, db_config):
    """Batch match CUIs - returns dict {cui: row}"""
    if not cui_list:
        return {}

    conn = get_db_connection(db_config)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Clean CUIs
    clean_cuis = [c for c in cui_list if c]
    if not clean_cuis:
        conn.close()
        return {}

    # Batch query
    placeholders = ','.join(['%s'] * len(clean_cuis))
    cur.execute(f"SELECT * FROM {db_config['table']} WHERE cui IN ({placeholders})", clean_cuis)
    rows = cur.fetchall()
    conn.close()

    return {row['cui']: dict(row) for row in rows if row.get('cui')}

def find_all_matches(records):
    """Find matches for all records using batch queries."""
    # Collect all CUIs to match
    cui_to_records = defaultdict(list)
    for i, record in enumerate(records):
        if record['cui']:
            cui_to_records[record['cui']].append(i)

    all_cuis = list(cui_to_records.keys())
    print(f"  Matching {len(all_cuis)} unique CUIs...")

    # Batch match against each internal DB
    matches = {}  # record_index -> (match, db_name)

    for db in DB_INTERNAL:
        print(f"    Checking {db['name']}...")
        db_matches = batch_match_by_cui(all_cuis, db)

        for cui, match in db_matches.items():
            for record_idx in cui_to_records[cui]:
                if record_idx not in matches:
                    matches[record_idx] = (match, db['name'])

    print(f"  Found {len(matches)} matches")
    return matches

# === ENRICHMENT ===

def enrich_record(record, match, match_db):
    """Enrich record with data from match. Returns dict of enriched fields."""
    enriched = {}

    db_config = next((d for d in DB_INTERNAL if d['name'] == match_db), None)
    email_cols = db_config.get('email_cols', ['email']) if db_config else ['email']
    phone_cols = db_config.get('phone_cols', ['phone']) if db_config else ['phone']

    # Email enrichment
    if len(record['emails']) < 3:
        match_emails = []
        for col in email_cols:
            if col in match and match[col]:
                e = normalize_email(match[col])
                if e and e not in record['emails'] and e not in match_emails:
                    match_emails.append(e)

        for i, email in enumerate(match_emails):
            if len(record['emails']) + i < 3:
                slot = f'email_{len(record["emails"]) + i + 1}'
                enriched[slot] = email

    # Phone enrichment
    if len(record['phones']) < 3:
        match_phones = []
        for col in phone_cols:
            if col in match and match[col]:
                p = normalize_phone(match[col])
                if p and p not in record['phones'] and p not in match_phones:
                    match_phones.append(p)

        for i, phone in enumerate(match_phones):
            if len(record['phones']) + i < 3:
                slot = f'phone_{len(record["phones"]) + i + 1}'
                enriched[slot] = phone

    # Contact person
    if not record['contacts']:
        for col in ['contact_person', 'contact_name', 'anofm_contact_person']:
            if col in match and match[col]:
                enriched['contact_person'] = match[col]
                break

    # Single-value fields
    if not record['website'] and match.get('website'):
        enriched['website'] = match['website']
    if not record['address'] and match.get('address'):
        enriched['address'] = match['address']
    if not record['sector'] and match.get('sector'):
        enriched['sector'] = match['sector']
    if not record['county'] and match.get('county'):
        enriched['county'] = match['county']

    return enriched

def reverse_enrich_batch(records_with_matches, dry_run=False):
    """Batch update internal DBs with new data from scrape."""
    updates_by_db = defaultdict(list)  # db_name -> [(cui, updates), ...]

    for record, match, match_db in records_with_matches:
        if not record['cui'] or not record['emails']:
            continue

        db_config = next((d for d in DB_INTERNAL if d['name'] == match_db), None)
        if not db_config:
            continue

        email_cols = db_config.get('email_cols', ['email'])
        existing_emails = [match.get(col) for col in email_cols if match.get(col)]

        updates = {}
        for col in email_cols:
            if not match.get(col):
                for email in record['emails']:
                    if email not in existing_emails and col not in updates:
                        updates[col] = email
                        existing_emails.append(email)
                        break

        if updates:
            updates_by_db[match_db].append((record['cui'], updates))

    total_updated = 0
    for db_name, update_list in updates_by_db.items():
        if dry_run:
            print(f"  Would update {len(update_list)} records in {db_name}")
            continue

        db_config = next((d for d in DB_INTERNAL if d['name'] == db_name), None)
        if not db_config:
            continue

        conn = get_db_connection(db_config)
        cur = conn.cursor()

        for cui, updates in update_list:
            set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
            cur.execute(
                f"UPDATE {db_config['table']} SET {set_clause} WHERE cui = %s",
                list(updates.values()) + [cui]
            )
            if cur.rowcount > 0:
                total_updated += 1

        conn.commit()
        conn.close()
        print(f"  Updated {total_updated} records in {db_name}")

    return total_updated

# === MAIN PROCESSING ===

def process_file(filepath, source='default', dry_run=False, reverse=False):
    """Process a CSV file for enrichment."""
    print(f"\nProcessing: {filepath}")
    print(f"Source: {source}, Reverse: {reverse}, DryRun: {dry_run}")

    # Read all records
    records = []
    rows = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames.copy()
        for row in reader:
            records.append(extract_record(row, source))
            rows.append(row)

    print(f"\nTotal records: {len(records)}")

    # Stats
    with_email = sum(1 for r in records if r['emails'])
    without_email = len(records) - with_email
    print(f"With email: {with_email}, Without email: {without_email}")

    # Batch match all records
    print("\nFinding matches...")
    matches = find_all_matches(records)

    # Enrich records without email
    enriched_count = 0
    for i, (record, row) in enumerate(zip(records, rows)):
        if i in matches and not record['emails']:
            match, match_db = matches[i]
            enriched_fields = enrich_record(record, match, match_db)
            if enriched_fields:
                enriched_count += 1
                for k, v in enriched_fields.items():
                    row[k] = v

    print(f"\nEnriched {enriched_count} records with missing email")

    # Reverse enrichment
    reverse_count = 0
    if reverse:
        print("\nReverse enriching internal DBs...")
        records_with_matches = [
            (records[i], matches[i][0], matches[i][1])
            for i in matches if records[i]['emails']
        ]
        reverse_count = reverse_enrich_batch(records_with_matches, dry_run)

    # Save enriched file
    if not dry_run and enriched_count > 0:
        output_path = filepath.replace('.csv', '_enriched.csv')
        all_fields = set(fieldnames)
        for row in rows:
            all_fields.update(row.keys())

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(all_fields), extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nSaved: {output_path}")

    return {
        'total': len(records),
        'with_email': with_email,
        'without_email': without_email,
        'matched': len(matches),
        'enriched': enriched_count,
        'reverse_enriched': reverse_count,
    }

def show_stats():
    """Show enrichment statistics from internal DBs."""
    print("=== Romania Enrichment Engine Stats ===\n")
    for db in DB_INTERNAL:
        conn = get_db_connection(db)
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {db['table']}")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {db['table']} WHERE email IS NOT NULL AND email != ''")
        with_email = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {db['table']} WHERE cui IS NOT NULL AND cui != ''")
        with_cui = cur.fetchone()[0]
        conn.close()
        print(f"{db['name']}.{db['table']}:")
        print(f"  Total: {total:,}")
        print(f"  With email: {with_email:,} ({100*with_email/total:.1f}%)")
        print(f"  With CUI: {with_cui:,} ({100*with_cui/total:.1f}%)")
        print()

def test_match(cui=None, company=None, email=None):
    """Test matching for a specific CUI."""
    print(f"Testing match for CUI: {cui}")

    norm_cui = normalize_cui(cui)
    if not norm_cui:
        print("Invalid CUI")
        return

    for db in DB_INTERNAL:
        matches = batch_match_by_cui([norm_cui], db)
        if norm_cui in matches:
            match = matches[norm_cui]
            print(f"\nMATCH in {db['name']}:")
            print(f"  Company: {match.get(db['name_col']) or match.get('name') or match.get('company_name')}")
            print(f"  Email: {match.get('email')}")
            print(f"  Phone: {match.get('phone')}")
            return

    print("No match found")

def main():
    parser = argparse.ArgumentParser(description='Romania Unified Enrichment Engine')
    parser.add_argument('--source', default='default', help='Source type (anofm, onrc, default)')
    parser.add_argument('--file', help='CSV file to enrich')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--reverse', action='store_true', help='Also reverse-enrich internal DBs')
    parser.add_argument('--stats', action='store_true', help='Show enrichment stats')
    parser.add_argument('--test-match', action='store_true', help='Test matching')
    parser.add_argument('--cui', help='CUI for test match')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.test_match:
        test_match(cui=args.cui)
        return

    if args.file:
        if not os.path.exists(args.file):
            print(f"File not found: {args.file}")
            sys.exit(1)
        stats = process_file(args.file, args.source, args.dry_run, args.reverse)
        print("\n=== Summary ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    parser.print_help()

if __name__ == '__main__':
    main()
