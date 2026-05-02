#!/usr/bin/env python3
"""
Bucharest + Ilfov Established Companies Extractor

Finds ALL active companies from Bucharest and Ilfov, sorted by founding date (oldest first),
with full enrichment (ANAF phones + fuzzy email matching).

Data Sources:
- ONRC (4.1M companies) - base data: CUI, name, founding date, county, status
- ANAF API (FREE) - phone + address enrichment (100 CUIs/request)
- Enrichment Index (1.1GB SQLite) - email enrichment via fuzzy matching

Usage:
    python3 buc_ilfov_established.py                    # Full run
    python3 buc_ilfov_established.py --filter-only      # Just filter ONRC (no enrichment)
    python3 buc_ilfov_established.py --skip-anaf        # Skip ANAF, do email only
    python3 buc_ilfov_established.py --limit 1000       # Limit to first N companies
    python3 buc_ilfov_established.py --status           # Show progress/stats
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import argparse
import csv
import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path

import requests

from skills_common import to_ascii

# === CONFIGURATION ===

ONRC_FILE = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC/od_firme_20260102.csv'
STATUS_FILE = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC_CACHE/od_stare_firma.csv'
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED')
STATE_FILE = OUTPUT_DIR / 'state.json'

# ANAF API
ANAF_API = 'https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva'
ANAF_BATCH_SIZE = 100
ANAF_RATE_LIMIT = 1.2  # seconds between requests

# Status codes
ACTIVE_STATUS = '1048'  # Functiune (active)

# Counties to filter
TARGET_COUNTIES = ['bucuresti', 'ilfov', 'bucureşti']

# === HELPER FUNCTIONS ===

def normalize_county(county: str) -> str:
    """Normalize county name for comparison."""
    if not county:
        return ''
    return to_ascii(county.lower().strip())


def parse_date(date_str: str) -> tuple:
    """Parse DD/MM/YYYY date to (year, month, day) tuple for sorting."""
    if not date_str:
        return (9999, 12, 31)
    try:
        parts = date_str.strip().split('/')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return (year, month, day)
    except:
        pass
    return (9999, 12, 31)


def format_date_iso(date_str: str) -> str:
    """Convert DD/MM/YYYY to YYYY-MM-DD."""
    if not date_str:
        return ''
    try:
        parts = date_str.strip().split('/')
        if len(parts) == 3:
            day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            return f"{year}-{month}-{day}"
    except:
        pass
    return date_str


def normalize_phone(phone: str) -> str:
    """Normalize phone to +40XXXXXXXXX format."""
    if not phone:
        return ''
    phone = str(phone).strip()
    digits = re.sub(r'\D', '', phone)

    if not digits:
        return ''

    # Remove country code if present
    if digits.startswith('40') and len(digits) > 10:
        digits = digits[2:]
    if digits.startswith('0040'):
        digits = digits[4:]

    # Add leading 0 if needed
    if len(digits) == 9:
        digits = '0' + digits

    # Only valid Romanian numbers
    if len(digits) == 10 and digits.startswith('0'):
        return '+40' + digits[1:]

    return ''


def load_state():
    """Load processing state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    """Save processing state."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


# === STEP 1: FILTER ONRC ===

def load_active_companies():
    """Load set of active company registration codes (COD_INMATRICULARE)."""
    print("Loading active company status codes...")
    active = set()

    with open(STATUS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f, delimiter='^')
        header = next(reader)

        for row in reader:
            if len(row) >= 2:
                reg_code, status = row[0], row[1]
                if status == ACTIVE_STATUS:
                    active.add(reg_code)

    print(f"  Found {len(active):,} active companies")
    return active


def filter_onrc(limit: int = None):
    """Filter ONRC for Bucharest + Ilfov active companies."""
    print("\n=== STEP 1: Filtering ONRC data ===")

    # Load active companies
    active_codes = load_active_companies()

    print(f"\nParsing ONRC file: {ONRC_FILE}")
    print(f"Filtering for: {', '.join(TARGET_COUNTIES)}")

    companies = []
    total = 0
    skipped_inactive = 0
    skipped_location = 0

    with open(ONRC_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f, delimiter='^')
        header = next(reader)

        # Map column indices
        col_map = {h.strip(): i for i, h in enumerate(header)}

        for row in reader:
            total += 1

            if total % 500000 == 0:
                print(f"  Processed {total:,} rows, found {len(companies):,} matches...")

            if len(row) < 8:
                continue

            # Get values
            reg_code = row[col_map.get('COD_INMATRICULARE', 2)].strip()
            county = row[col_map.get('ADR_JUDET', 7)].strip()

            # Check if active
            if reg_code not in active_codes:
                skipped_inactive += 1
                continue

            # Check county
            county_norm = normalize_county(county)
            if county_norm not in TARGET_COUNTIES:
                skipped_location += 1
                continue

            # Extract company data
            company = {
                'denumire': to_ascii(row[col_map.get('DENUMIRE', 0)]),
                'cui': row[col_map.get('CUI', 1)].strip(),
                'cod_inmatriculare': reg_code,
                'data_inmatriculare': row[col_map.get('DATA_INMATRICULARE', 3)].strip(),
                'forma_juridica': row[col_map.get('FORMA_JURIDICA', 5)].strip(),
                'judet': to_ascii(county),
                'localitate': to_ascii(row[col_map.get('ADR_LOCALITATE', 8)] if len(row) > 8 else ''),
                'strada': to_ascii(row[col_map.get('ADR_DEN_STRADA', 9)] if len(row) > 9 else ''),
                'nr_strada': row[col_map.get('ADR_NR_STRADA', 10)] if len(row) > 10 else '',
                'sector': row[col_map.get('ADR_SECTOR', 16)] if len(row) > 16 else '',
                'cod_postal': row[col_map.get('ADR_COD_POSTAL', 15)] if len(row) > 15 else '',
                'website': row[col_map.get('WEB', 18)] if len(row) > 18 else '',
            }

            companies.append(company)

            if limit and len(companies) >= limit:
                break

    print(f"\n  Total rows processed: {total:,}")
    print(f"  Skipped (inactive): {skipped_inactive:,}")
    print(f"  Skipped (wrong location): {skipped_location:,}")
    print(f"  Matched: {len(companies):,}")

    # Sort by founding date (oldest first)
    print("\nSorting by founding date (oldest first)...")
    companies.sort(key=lambda c: parse_date(c['data_inmatriculare']))

    # Show oldest companies
    print("\nOldest 10 companies:")
    for i, c in enumerate(companies[:10]):
        print(f"  {i+1}. {c['data_inmatriculare']} - {c['denumire'][:50]}")

    # Save intermediate result
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / 'buc_ilfov_active_sorted.csv'

    fieldnames = ['denumire', 'cui', 'cod_inmatriculare', 'data_inmatriculare',
                  'forma_juridica', 'judet', 'localitate', 'strada', 'nr_strada',
                  'sector', 'cod_postal', 'website']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)

    print(f"\nSaved: {output_file}")
    print(f"  Rows: {len(companies):,}")

    # Update state
    state = load_state()
    state['filter_complete'] = True
    state['filter_count'] = len(companies)
    state['filter_file'] = str(output_file)
    state['filter_time'] = datetime.now().isoformat()
    save_state(state)

    return companies, output_file


# === STEP 2: ANAF PHONE ENRICHMENT ===

def query_anaf(cuis: list) -> dict:
    """Query ANAF API for multiple CUIs (max 100)."""
    today = date.today().isoformat()
    payload = []

    for cui in cuis:
        cui_clean = re.sub(r'\D', '', str(cui))
        if cui_clean and len(cui_clean) >= 4:
            payload.append({"cui": int(cui_clean), "data": today})

    if not payload:
        return {'found': [], 'notFound': []}

    try:
        response = requests.post(
            ANAF_API,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code != 200:
            return {'error': f'HTTP {response.status_code}', 'found': [], 'notFound': []}

        return response.json()
    except Exception as e:
        return {'error': str(e), 'found': [], 'notFound': []}


def enrich_anaf(input_file: Path, resume_from: int = 0):
    """Enrich companies with ANAF phone data."""
    print("\n=== STEP 2: ANAF Phone Enrichment ===")

    # Load companies
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        companies = list(reader)
        fieldnames = list(reader.fieldnames)

    total = len(companies)
    print(f"Enriching {total:,} companies with ANAF data...")
    print(f"Rate: {ANAF_BATCH_SIZE} CUIs/request, {ANAF_RATE_LIMIT}s delay")
    print(f"Estimated time: {(total / ANAF_BATCH_SIZE) * ANAF_RATE_LIMIT / 60:.1f} minutes")

    # Add ANAF columns
    anaf_cols = ['anaf_phone', 'anaf_address', 'anaf_caen', 'anaf_status']
    for col in anaf_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    # Resume support
    if resume_from > 0:
        print(f"Resuming from row {resume_from}...")

    stats = {'total': 0, 'with_phone': 0, 'errors': 0}
    start_time = time.time()

    # Process in batches
    for i in range(resume_from, total, ANAF_BATCH_SIZE):
        batch = companies[i:i + ANAF_BATCH_SIZE]
        cuis = [c.get('cui', '') for c in batch if c.get('cui')]

        if not cuis:
            continue

        data = query_anaf(cuis)

        if data.get('error'):
            print(f"  Error at batch {i}: {data['error']}")
            stats['errors'] += 1

        # Map results by CUI
        found_map = {}
        for item in data.get('found', []):
            info = item.get('date_generale', {})
            cui = str(info.get('cui', ''))
            found_map[cui] = {
                'phone': info.get('telefon', ''),
                'address': info.get('adresa', ''),
                'caen': info.get('cod_CAEN', ''),
                'status': info.get('stare_inregistrare', ''),
            }

        # Update companies
        for c in batch:
            cui = re.sub(r'\D', '', str(c.get('cui', '')))
            if cui in found_map:
                info = found_map[cui]
                phone = normalize_phone(info['phone'])
                c['anaf_phone'] = phone
                c['anaf_address'] = to_ascii(info['address']) if info['address'] else ''
                c['anaf_caen'] = info['caen']
                c['anaf_status'] = to_ascii(info['status']) if info['status'] else ''
                if phone:
                    stats['with_phone'] += 1
            else:
                c['anaf_phone'] = ''
                c['anaf_address'] = ''
                c['anaf_caen'] = ''
                c['anaf_status'] = ''

            stats['total'] += 1

        # Progress
        elapsed = time.time() - start_time
        rate = (i + len(batch)) / elapsed if elapsed > 0 else 0
        remaining = (total - i - len(batch)) / rate if rate > 0 else 0

        if (i + len(batch)) % 5000 == 0 or i + len(batch) >= total:
            print(f"  {i + len(batch):,}/{total:,} ({100*(i+len(batch))/total:.1f}%) "
                  f"- {stats['with_phone']:,} with phone - ETA: {remaining/60:.1f}m")

        # Rate limit
        time.sleep(ANAF_RATE_LIMIT)

        # Save progress periodically
        if (i + len(batch)) % 10000 == 0:
            state = load_state()
            state['anaf_progress'] = i + len(batch)
            state['anaf_with_phone'] = stats['with_phone']
            save_state(state)

    # Save result
    output_file = OUTPUT_DIR / 'buc_ilfov_with_phones.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)

    print(f"\nANAF enrichment complete:")
    print(f"  Total: {stats['total']:,}")
    print(f"  With phone: {stats['with_phone']:,} ({100*stats['with_phone']/stats['total']:.1f}%)")
    print(f"  Errors: {stats['errors']}")
    print(f"\nSaved: {output_file}")

    # Update state
    state = load_state()
    state['anaf_complete'] = True
    state['anaf_with_phone'] = stats['with_phone']
    state['anaf_file'] = str(output_file)
    state['anaf_time'] = datetime.now().isoformat()
    save_state(state)

    return output_file, stats


# === STEP 3: EMAIL ENRICHMENT ===

def enrich_emails(input_file: Path):
    """Enrich companies with email data using universal_enrich.py."""
    print("\n=== STEP 3: Email Enrichment ===")

    output_file = OUTPUT_DIR / 'buc_ilfov_fully_enriched.csv'

    # Use universal_enrich.py
    import subprocess

    cmd = [
        '/opt/ACTIVE/INFRA/venv/bin/python3',
        '/opt/ACTIVE/INFRA/SKILLS/universal_enrich.py',
        str(input_file),
        '-o', str(output_file),
        '--name-col', 'denumire',
        '--cui-col', 'cui',
        '--auto'
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None

    print(result.stdout)

    # Update state
    state = load_state()
    state['email_complete'] = True
    state['email_file'] = str(output_file)
    state['email_time'] = datetime.now().isoformat()
    save_state(state)

    return output_file


# === STEP 4: FINAL NORMALIZATION ===

def normalize_output(input_file: Path):
    """Final normalization and cleanup."""
    print("\n=== STEP 4: Final Normalization ===")

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        companies = list(reader)
        fieldnames = list(reader.fieldnames)

    # Normalize all text fields
    for c in companies:
        for key in c:
            if isinstance(c[key], str):
                c[key] = to_ascii(c[key])

        # Format dates
        if c.get('data_inmatriculare'):
            c['data_inmatriculare'] = format_date_iso(c['data_inmatriculare'])

        # Normalize phones
        if c.get('anaf_phone'):
            c['anaf_phone'] = normalize_phone(c['anaf_phone'])
        if c.get('enrich_phone'):
            c['enrich_phone'] = normalize_phone(c['enrich_phone'])

    # Remove duplicates by CUI
    seen_cui = set()
    unique = []
    dups = 0

    for c in companies:
        cui = c.get('cui', '')
        if cui and cui in seen_cui:
            dups += 1
            continue
        if cui:
            seen_cui.add(cui)
        unique.append(c)

    print(f"  Removed {dups:,} duplicate CUIs")

    # Final output
    output_file = OUTPUT_DIR / 'oldest_companies_enriched.csv'

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(unique)

    # Stats
    with_phone = sum(1 for c in unique if c.get('anaf_phone') or c.get('enrich_phone'))
    with_email = sum(1 for c in unique if c.get('enrich_email'))

    print(f"\nFinal output: {output_file}")
    print(f"  Total companies: {len(unique):,}")
    print(f"  With phone: {with_phone:,} ({100*with_phone/len(unique):.1f}%)")
    print(f"  With email: {with_email:,} ({100*with_email/len(unique):.1f}%)")

    # Oldest companies summary
    print("\nOldest 10 companies (fully enriched):")
    for i, c in enumerate(unique[:10]):
        phone = c.get('anaf_phone') or c.get('enrich_phone') or '-'
        email = c.get('enrich_email') or '-'
        print(f"  {i+1}. {c['data_inmatriculare']} | {c['denumire'][:35]:35} | {phone}")

    # Update state
    state = load_state()
    state['complete'] = True
    state['final_file'] = str(output_file)
    state['final_count'] = len(unique)
    state['final_with_phone'] = with_phone
    state['final_with_email'] = with_email
    state['complete_time'] = datetime.now().isoformat()
    save_state(state)

    return output_file


# === MAIN ===

def show_status():
    """Show current processing status."""
    state = load_state()

    print("=== Processing Status ===\n")

    if not state:
        print("No processing started yet.")
        return

    if state.get('filter_complete'):
        print(f"Step 1 (Filter): COMPLETE")
        print(f"  Companies: {state.get('filter_count', 0):,}")
        print(f"  File: {state.get('filter_file', '-')}")
        print(f"  Time: {state.get('filter_time', '-')}")
    else:
        print("Step 1 (Filter): Not started")

    print()

    if state.get('anaf_complete'):
        print(f"Step 2 (ANAF): COMPLETE")
        print(f"  With phone: {state.get('anaf_with_phone', 0):,}")
        print(f"  File: {state.get('anaf_file', '-')}")
    elif state.get('anaf_progress'):
        print(f"Step 2 (ANAF): IN PROGRESS")
        print(f"  Progress: {state.get('anaf_progress', 0):,}")
    else:
        print("Step 2 (ANAF): Not started")

    print()

    if state.get('email_complete'):
        print(f"Step 3 (Email): COMPLETE")
        print(f"  File: {state.get('email_file', '-')}")
    else:
        print("Step 3 (Email): Not started")

    print()

    if state.get('complete'):
        print(f"Step 4 (Final): COMPLETE")
        print(f"  Total: {state.get('final_count', 0):,}")
        print(f"  With phone: {state.get('final_with_phone', 0):,}")
        print(f"  With email: {state.get('final_with_email', 0):,}")
        print(f"  Output: {state.get('final_file', '-')}")
    else:
        print("Step 4 (Final): Not started")


def main():
    parser = argparse.ArgumentParser(
        description='Bucharest + Ilfov Established Companies Extractor'
    )
    parser.add_argument('--filter-only', action='store_true',
                        help='Only filter ONRC (no enrichment)')
    parser.add_argument('--skip-anaf', action='store_true',
                        help='Skip ANAF enrichment')
    parser.add_argument('--skip-email', action='store_true',
                        help='Skip email enrichment')
    parser.add_argument('--limit', type=int,
                        help='Limit number of companies')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint')
    parser.add_argument('--status', action='store_true',
                        help='Show processing status')
    parser.add_argument('--reset', action='store_true',
                        help='Reset processing state')

    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print("State reset.")
        return 0

    start = time.time()
    print("=" * 60)
    print("BUCHAREST + ILFOV ESTABLISHED COMPANIES EXTRACTOR")
    print("=" * 60)

    state = load_state()

    # Step 1: Filter ONRC
    if not state.get('filter_complete') or not args.resume:
        companies, filtered_file = filter_onrc(limit=args.limit)
    else:
        filtered_file = Path(state['filter_file'])
        print(f"\nStep 1: Using cached filter result: {filtered_file}")

    if args.filter_only:
        print("\n--filter-only specified. Stopping after filter.")
        return 0

    # Step 2: ANAF enrichment
    if not args.skip_anaf:
        if not state.get('anaf_complete') or not args.resume:
            resume_from = state.get('anaf_progress', 0) if args.resume else 0
            anaf_file, anaf_stats = enrich_anaf(filtered_file, resume_from)
        else:
            anaf_file = Path(state['anaf_file'])
            print(f"\nStep 2: Using cached ANAF result: {anaf_file}")
    else:
        anaf_file = filtered_file
        print("\n--skip-anaf specified. Using filtered data.")

    # Step 3: Email enrichment
    if not args.skip_email:
        if not state.get('email_complete') or not args.resume:
            email_file = enrich_emails(anaf_file)
        else:
            email_file = Path(state['email_file'])
            print(f"\nStep 3: Using cached email result: {email_file}")
    else:
        email_file = anaf_file
        print("\n--skip-email specified. Using ANAF data.")

    # Step 4: Final normalization
    if email_file:
        final_file = normalize_output(email_file)

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"COMPLETE in {elapsed/60:.1f} minutes")
    print(f"Output: {OUTPUT_DIR / 'oldest_companies_enriched.csv'}")
    print(f"{'=' * 60}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
