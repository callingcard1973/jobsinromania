#!/usr/bin/env python3
"""
Agency Splitter - Separate agencies by country

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/agency_splitter.py                    # Split to /opt/ACTIVE/OPENDATA/DATA/AGENCIES/BY_COUNTRY/
    python3 /opt/ACTIVE/INFRA/SKILLS/agency_splitter.py --input file.csv   # Custom input
    python3 /opt/ACTIVE/INFRA/SKILLS/agency_splitter.py --output /path/    # Custom output dir
    python3 /opt/ACTIVE/INFRA/SKILLS/agency_splitter.py --stats            # Show stats only
    python3 /opt/ACTIVE/INFRA/SKILLS/agency_splitter.py --dry-run          # Preview without writing
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import os
import argparse
from collections import defaultdict, Counter
from skills_common import to_ascii

# Country code normalization
COUNTRY_CODES = {
    'SE': 'Sweden',
    'NO': 'Norway',
    'DK': 'Denmark',
    'FI': 'Finland',
    'DE': 'Germany',
    'DEU': 'Germany',
    'NL': 'Netherlands',
    'BE': 'Belgium',
    'AT': 'Austria',
    'CH': 'Switzerland',
    'FR': 'France',
    'IT': 'Italy',
    'ES': 'Spain',
    'PT': 'Portugal',
    'PL': 'Poland',
    'CZ': 'Czech Republic',
    'SK': 'Slovakia',
    'HU': 'Hungary',
    'RO': 'Romania',
    'BG': 'Bulgaria',
    'HR': 'Croatia',
    'HRV': 'Croatia',
    'SI': 'Slovenia',
    'RS': 'Serbia',
    'MD': 'Moldova',
    'UA': 'Ukraine',
    'LT': 'Lithuania',
    'LV': 'Latvia',
    'EE': 'Estonia',
    'IE': 'Ireland',
    'UK': 'United Kingdom',
    'GB': 'United Kingdom',
    'LU': 'Luxembourg',
    'GR': 'Greece',
    'CY': 'Cyprus',
    'MT': 'Malta',
    'IS': 'Iceland',
    'US': 'United States',
    'CA': 'Canada',
    'BR': 'Brazil',
}

# Source file to country mapping
SOURCE_TO_COUNTRY = {
    'kraz': 'Poland',
    'cz_agencies': 'Czech Republic',
    'czech': 'Czech Republic',
    'bulgaria': 'Bulgaria',
    'bg_': 'Bulgaria',
    'romania': 'Romania',
    'ro_': 'Romania',
    'it_': 'Italy',
    'italy': 'Italy',
    'german': 'Germany',
    'de_': 'Germany',
    'sweden': 'Sweden',
    'se_': 'Sweden',
    'norway': 'Norway',
    'no_': 'Norway',
    'denmark': 'Denmark',
    'dk_': 'Denmark',
    'finland': 'Finland',
    'fi_': 'Finland',
    'uk_': 'United Kingdom',
    'british': 'United Kingdom',
    'ireland': 'Ireland',
    'ie_': 'Ireland',
    'poland': 'Poland',
    'pl_': 'Poland',
    'netherlands': 'Netherlands',
    'nl_': 'Netherlands',
    'dutch': 'Netherlands',
    'belgium': 'Belgium',
    'be_': 'Belgium',
    'france': 'France',
    'fr_': 'France',
    'spain': 'Spain',
    'es_': 'Spain',
    'austria': 'Austria',
    'at_': 'Austria',
    'switzerland': 'Switzerland',
    'ch_': 'Switzerland',
    'hungary': 'Hungary',
    'hu_': 'Hungary',
    'slovakia': 'Slovakia',
    'sk_': 'Slovakia',
    'croatia': 'Croatia',
    'hr_': 'Croatia',
    'slovenia': 'Slovenia',
    'si_': 'Slovenia',
    'serbia': 'Serbia',
    'rs_': 'Serbia',
    'moldova': 'Moldova',
    'md_': 'Moldova',
    'ukraine': 'Ukraine',
    'ua_': 'Ukraine',
    'lithuania': 'Lithuania',
    'lt_': 'Lithuania',
    'latvia': 'Latvia',
    'lv_': 'Latvia',
    'estonia': 'Estonia',
    'ee_': 'Estonia',
    'greece': 'Greece',
    'gr_': 'Greece',
    'portugal': 'Portugal',
    'pt_': 'Portugal',
    'iceland': 'Iceland',
    'is_': 'Iceland',
    'malta': 'Malta',
    'mt_': 'Malta',
    'cyprus': 'Cyprus',
    'cy_': 'Cyprus',
    'luxembourg': 'Luxembourg',
    'lu_': 'Luxembourg',
}

# Polish voivodeships (regions) - detect Polish addresses
POLISH_VOIVODESHIPS = [
    'mazowieckie', 'slaskie', 'wielkopolskie', 'malopolskie', 'dolnoslaskie',
    'lodzkie', 'pomorskie', 'lubelskie', 'podkarpackie', 'kujawsko-pomorskie',
    'zachodniopomorskie', 'warminsko-mazurskie', 'swietokrzyskie', 'opolskie',
    'podlaskie', 'lubuskie', 'warszawa', 'krakow', 'wroclaw', 'poznan', 'gdansk',
    'szczecin', 'lodz', 'katowice', 'lublin', 'bialystok'
]

# Romanian company suffixes
ROMANIAN_PATTERNS = ['s.r.l', 'srl', ' sa ', ' s.a.', 'pfa', 'ii ', 'i.i.']

# Spanish city/region patterns
SPANISH_PATTERNS = [
    'madrid', 'barcelona', 'valencia', 'sevilla', 'zaragoza', 'malaga', 'murcia',
    'palma', 'bilbao', 'alicante', 'cordoba', 'valladolid', 'vigo', 'gijon',
    'cataluna', 'andalucia', 'castilla', 'galicia', 'aragon', 'asturias',
    'extremadura', 'cantabria', 'navarra', 'rioja', 'euskadi', 'espana'
]

# Email domain to country
EMAIL_DOMAINS = {
    '.pl': 'Poland',
    '.cz': 'Czech Republic',
    '.sk': 'Slovakia',
    '.ro': 'Romania',
    '.bg': 'Bulgaria',
    '.hu': 'Hungary',
    '.de': 'Germany',
    '.at': 'Austria',
    '.ch': 'Switzerland',
    '.nl': 'Netherlands',
    '.be': 'Belgium',
    '.fr': 'France',
    '.it': 'Italy',
    '.es': 'Spain',
    '.pt': 'Portugal',
    '.dk': 'Denmark',
    '.se': 'Sweden',
    '.no': 'Norway',
    '.fi': 'Finland',
    '.ie': 'Ireland',
    '.uk': 'United Kingdom',
    '.co.uk': 'United Kingdom',
    '.gr': 'Greece',
    '.hr': 'Croatia',
    '.si': 'Slovenia',
    '.rs': 'Serbia',
    '.ua': 'Ukraine',
    '.md': 'Moldova',
    '.lt': 'Lithuania',
    '.lv': 'Latvia',
    '.ee': 'Estonia',
}


def normalize_country(country_value):
    """Normalize country name from code or variant."""
    if not country_value:
        return None

    country = country_value.strip()

    # Check if it's a code
    upper = country.upper()
    if upper in COUNTRY_CODES:
        return COUNTRY_CODES[upper]

    # Check if it's already a valid country name
    valid_countries = set(COUNTRY_CODES.values())
    if country in valid_countries:
        return country

    # Title case normalization
    titled = country.title()
    if titled in valid_countries:
        return titled

    # Handle "United Kingdom" variants
    if 'kingdom' in country.lower():
        return 'United Kingdom'

    # Handle obvious typos/variants
    if '@' in country or '.' in country:
        return None  # Email accidentally in country field

    if country.lower() in ('bucuresti', 'bucharest'):
        return 'Romania'

    return country if len(country) > 2 else None


def infer_country_from_source(source_file):
    """Infer country from source filename."""
    if not source_file:
        return None

    source_lower = source_file.lower()

    for pattern, country in SOURCE_TO_COUNTRY.items():
        if pattern in source_lower:
            return country

    return None


def infer_from_email(email):
    """Infer country from email domain."""
    if not email:
        return None
    email_lower = email.lower()
    for domain, country in EMAIL_DOMAINS.items():
        if email_lower.endswith(domain):
            return country
    return None


def infer_from_address(address):
    """Infer country from address patterns."""
    if not address:
        return None
    addr_lower = address.lower()

    # Check for Polish voivodeships or "ul." (street in Polish)
    if 'ul.' in addr_lower or 'ul ' in addr_lower:
        return 'Poland'
    for voivodeship in POLISH_VOIVODESHIPS:
        if voivodeship in addr_lower:
            return 'Poland'

    # Check for Spanish patterns
    for pattern in SPANISH_PATTERNS:
        if pattern in addr_lower:
            return 'Spain'

    return None


def infer_from_company_name(name):
    """Infer country from company name patterns."""
    if not name:
        return None
    name_lower = name.lower()

    # Romanian company suffixes
    for pattern in ROMANIAN_PATTERNS:
        if pattern in name_lower:
            return 'Romania'

    # Polish company suffixes
    if ' sp. z o.o' in name_lower or 'spolka z' in name_lower or ' sp.z' in name_lower:
        return 'Poland'

    # German company suffixes
    if ' gmbh' in name_lower or ' ag ' in name_lower:
        return 'Germany'

    # Spanish company suffixes
    if ' s.l.' in name_lower or ' s.l ' in name_lower:
        return 'Spain'

    return None


def get_country(row):
    """Get country for a row, trying multiple methods."""
    # 1. Try explicit country field
    country = normalize_country(row.get('country', ''))
    if country:
        return country

    # 2. Try to infer from source file
    source = row.get('source_file', '')
    country = infer_country_from_source(source)
    if country:
        return country

    # 3. Try to infer from address patterns
    address = row.get('address', '')
    country = infer_from_address(address)
    if country:
        return country

    # 4. Try to infer from company name
    name = row.get('company_name', '')
    country = infer_from_company_name(name)
    if country:
        return country

    # 5. Try to infer from email domain
    email = row.get('email', '')
    country = infer_from_email(email)
    if country:
        return country

    return 'Unknown'


def split_agencies(input_file, output_dir, dry_run=False):
    """Split agencies CSV by country."""

    # Read all data
    agencies_by_country = defaultdict(list)
    total = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            total += 1
            country = get_country(row)

            # Clean row - convert to ASCII
            clean_row = {}
            for k, v in row.items():
                clean_row[k] = to_ascii(str(v)) if v else ''

            # Update country field with resolved value
            clean_row['country'] = country

            agencies_by_country[country].append(clean_row)

    # Print stats
    print(f"\n=== AGENCY SPLIT RESULTS ===")
    print(f"Total agencies: {total:,}")
    print(f"Countries found: {len(agencies_by_country)}")
    print()

    # Sort by count descending
    sorted_countries = sorted(agencies_by_country.items(), key=lambda x: -len(x[1]))

    for country, agencies in sorted_countries:
        print(f"  {country}: {len(agencies):,}")

    if dry_run:
        print("\n[DRY RUN - no files written]")
        return agencies_by_country

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Write separate files
    print(f"\nWriting to: {output_dir}")

    for country, agencies in sorted_countries:
        # Create safe filename
        safe_name = country.lower().replace(' ', '_').replace('-', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
        filename = f"agencies_{safe_name}.csv"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(agencies)

        print(f"  {filename}: {len(agencies):,} agencies")

    # Write summary
    summary_path = os.path.join(output_dir, 'SUMMARY.txt')
    with open(summary_path, 'w') as f:
        f.write(f"Agency Split Summary\n")
        f.write(f"{'='*40}\n")
        f.write(f"Source: {input_file}\n")
        f.write(f"Total: {total:,} agencies\n")
        f.write(f"Countries: {len(agencies_by_country)}\n\n")
        for country, agencies in sorted_countries:
            f.write(f"{country}: {len(agencies):,}\n")

    print(f"\nSummary written to: {summary_path}")

    return agencies_by_country


def show_stats(input_file):
    """Show statistics without splitting."""
    countries = Counter()
    sources = Counter()

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            country = get_country(row)
            countries[country] += 1
            sources[row.get('source_file', 'unknown')] += 1

    print("=== COUNTRIES (after inference) ===")
    for c, count in countries.most_common():
        print(f"  {c}: {count:,}")

    print("\n=== SOURCE FILES ===")
    for s, count in sources.most_common(15):
        print(f"  {s}: {count:,}")


def main():
    parser = argparse.ArgumentParser(description='Split agencies by country')
    parser.add_argument('--input', '-i',
                        default='/opt/ACTIVE/OPENDATA/DATA/AGENCIES/AGENCIES_MASTER_ALL.csv',
                        help='Input CSV file')
    parser.add_argument('--output', '-o',
                        default='/opt/ACTIVE/OPENDATA/DATA/AGENCIES/BY_COUNTRY',
                        help='Output directory')
    parser.add_argument('--stats', action='store_true',
                        help='Show stats only')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without writing files')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    if args.stats:
        show_stats(args.input)
    else:
        split_agencies(args.input, args.output, args.dry_run)


if __name__ == '__main__':
    main()
