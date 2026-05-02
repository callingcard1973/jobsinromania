#!/usr/bin/env python3
"""
Extract 20+ year old active companies from REST of Romania (excluding Bucuresti/Ilfov).
Enrich with ANAF phones + ANOFM emails.
"""
import csv
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    print("Warning: rapidfuzz not available, using exact match only")

# Files
ONRC_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DATAGOV_ALL/dateidentificare2025_csv.csv")
ANAF_PHONES_FILE = Path("/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/anaf_all/all_phones.csv")
ANOFM_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_latest.csv")
OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/REST_OF_ROMANIA")

# Config
CUTOFF_YEAR = datetime.now().year - 20  # Companies founded 2006 or earlier
EXCLUDED_COUNTIES = {'MUNICIPIUL BUCURESTI', 'ILFOV', 'MUNICIPIUL BUCURE_TI', 'BUCURESTI'}
FUZZY_THRESHOLD = 85


def to_ascii(text):
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return text
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')


def normalize_company_name(name):
    """Normalize company name for fuzzy matching."""
    if not name:
        return ""
    name = to_ascii(name.upper())
    # Remove common suffixes
    for suffix in [' SRL', ' SA', ' S.R.L.', ' S.A.', ' PFA', ' II', ' IF', ' SNC', ' SCS']:
        name = name.replace(suffix, '')
    # Remove punctuation
    name = ''.join(c if c.isalnum() or c == ' ' else '' for c in name)
    # Normalize whitespace
    return ' '.join(name.split())


def normalize_phone(phone):
    """Normalize phone number to +40... format."""
    if not phone:
        return ""
    # Extract digits only
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if len(digits) < 9:
        return ""
    # Remove leading 0 or country code
    if digits.startswith('40') and len(digits) >= 11:
        digits = digits[2:]
    if digits.startswith('0'):
        digits = digits[1:]
    if len(digits) < 9:
        return ""
    return f"+40{digits}"


def load_anaf_phones():
    """Load ANAF phones into a CUI-indexed dict."""
    print(f"Loading ANAF phones from {ANAF_PHONES_FILE}...")
    phones = {}
    with open(ANAF_PHONES_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cui = row.get('cui', '').strip()
            phone = normalize_phone(row.get('phone', ''))
            address = row.get('address', '')
            if cui and phone:
                phones[cui] = {'phone': phone, 'address': address}
    print(f"  Loaded {len(phones):,} phones")
    return phones


def load_anofm_data():
    """Load ANOFM data indexed by CUI and normalized name."""
    print(f"Loading ANOFM data from {ANOFM_FILE}...")
    by_cui = {}
    by_name = {}

    with open(ANOFM_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cui = row.get('company_org_number', '').strip()
            name = row.get('company_name', '').strip()
            email = row.get('email_1', '').strip()
            website = row.get('company_website', '').strip()

            if not email or '@' not in email:
                continue

            data = {'email': email, 'website': website, 'name': name}

            if cui:
                by_cui[cui] = data

            norm_name = normalize_company_name(name)
            if norm_name and len(norm_name) >= 5:
                by_name[norm_name] = data

    print(f"  Loaded {len(by_cui):,} by CUI, {len(by_name):,} by name")
    return by_cui, by_name


def fuzzy_match_name(name, anofm_by_name):
    """Find best fuzzy match for company name."""
    if not HAS_RAPIDFUZZ or not name:
        return None, None, 0

    norm_name = normalize_company_name(name)
    if len(norm_name) < 5:
        return None, None, 0

    # First try exact match
    if norm_name in anofm_by_name:
        return anofm_by_name[norm_name], 'exact', 100

    # Fuzzy match
    best_match = None
    best_score = 0
    best_key = None

    for anofm_name, data in anofm_by_name.items():
        score = fuzz.token_sort_ratio(norm_name, anofm_name)
        if score > best_score and score >= FUZZY_THRESHOLD:
            best_score = score
            best_match = data
            best_key = anofm_name

    if best_match:
        return best_match, 'fuzzy', best_score
    return None, None, 0


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load enrichment data
    anaf_phones = load_anaf_phones()
    anofm_by_cui, anofm_by_name = load_anofm_data()

    print(f"\nProcessing ONRC data from {ONRC_FILE}...")

    # Output files
    all_output = OUTPUT_DIR / "all_20yr_active.csv"
    contacts_output = OUTPUT_DIR / "20yr_companies_with_contacts.csv"

    stats = {
        'total': 0,
        'active': 0,
        'rest_romania': 0,
        '20yr': 0,
        'with_phone': 0,
        'with_email': 0,
        'with_both': 0,
        'cui_match': 0,
        'name_match': 0,
        'fuzzy_match': 0
    }

    companies_with_both = []

    with open(ONRC_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='^')

        for row in reader:
            stats['total'] += 1

            # Check status (active)
            stare = row.get('STARE', '')
            if stare not in ('INREGISTRAT', 'RELUARE ACTIVITATE'):
                continue
            stats['active'] += 1

            # Check county (exclude Bucuresti/Ilfov)
            judet = row.get('JUDET', '').upper()
            if any(excl in judet for excl in EXCLUDED_COUNTIES):
                continue
            stats['rest_romania'] += 1

            # Check founding date (20+ years)
            date_str = row.get('DATA_INREGISTRARE', '')
            try:
                parts = date_str.split('.')
                if len(parts) == 3:
                    year = int(parts[2])
                    if year > CUTOFF_YEAR:
                        continue
            except:
                continue
            stats['20yr'] += 1

            # Get basic info
            cui = row.get('COD_FISCAL', '').strip()
            name = to_ascii(row.get('DENUMIRE', ''))
            localitate = to_ascii(row.get('LOCALITATE', ''))
            strada = to_ascii(row.get('STRADA', ''))
            nr = to_ascii(row.get('NR', ''))

            # Enrich with ANAF phone
            phone = ''
            address = ''
            if cui in anaf_phones:
                phone = anaf_phones[cui]['phone']
                address = anaf_phones[cui]['address']

            if phone:
                stats['with_phone'] += 1

            # Enrich with ANOFM email (CUI first, then name match)
            email = ''
            website = ''
            match_type = ''
            match_score = 0

            if cui in anofm_by_cui:
                data = anofm_by_cui[cui]
                email = data['email']
                website = data.get('website', '')
                match_type = 'cui'
                stats['cui_match'] += 1
            else:
                # Try name match
                data, mtype, score = fuzzy_match_name(name, anofm_by_name)
                if data:
                    email = data['email']
                    website = data.get('website', '')
                    match_type = mtype
                    match_score = score
                    if mtype == 'exact':
                        stats['name_match'] += 1
                    else:
                        stats['fuzzy_match'] += 1

            if email:
                stats['with_email'] += 1

            # Check if has both
            if phone and email:
                stats['with_both'] += 1
                company = {
                    'denumire': name,
                    'cui': cui,
                    'founding_year': year if 'year' in dir() else '',
                    'company_age': datetime.now().year - year if 'year' in dir() else '',
                    'anaf_phone': phone,
                    'anofm_email': email,
                    'localitate': localitate,
                    'judet': to_ascii(judet),
                    'strada': f"{strada} {nr}".strip(),
                    'anofm_website': website,
                    'website': '',
                    'match_type': match_type,
                    'match_score': match_score
                }
                companies_with_both.append(company)

            if stats['total'] % 500000 == 0:
                print(f"  Processed {stats['total']:,} rows, found {stats['with_both']:,} with both...")

    # Sort by age (oldest first)
    companies_with_both.sort(key=lambda x: x.get('founding_year', 9999))

    # Write output
    print(f"\nWriting {len(companies_with_both):,} companies to {contacts_output}...")
    fieldnames = ['denumire', 'cui', 'founding_year', 'company_age', 'anaf_phone',
                  'anofm_email', 'localitate', 'judet', 'strada', 'anofm_website', 'website']

    with open(contacts_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies_with_both)

    print(f"\n=== RESULTS ===")
    print(f"Total rows processed: {stats['total']:,}")
    print(f"Active companies: {stats['active']:,}")
    print(f"Rest of Romania (excl Buc/Ilfov): {stats['rest_romania']:,}")
    print(f"20+ years old: {stats['20yr']:,}")
    print(f"With ANAF phone: {stats['with_phone']:,}")
    print(f"With ANOFM email: {stats['with_email']:,}")
    print(f"  - CUI match: {stats['cui_match']:,}")
    print(f"  - Name exact match: {stats['name_match']:,}")
    print(f"  - Fuzzy match: {stats['fuzzy_match']:,}")
    print(f"With BOTH phone + email: {stats['with_both']:,}")
    print(f"\nOutput: {contacts_output}")


if __name__ == '__main__':
    main()
