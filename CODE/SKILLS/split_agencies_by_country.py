#!/usr/bin/env python3
"""
split_agencies_by_country.py - Split master agencies file by country.

Creates separate CSV and SQLite DB for each country in /opt/ACTIVE/OPENDATA/DATA/AGENCIES/<COUNTRY>/
on raspibig.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/split_agencies_by_country.py
"""

import os
import sys
import csv
import sqlite3
import subprocess
import shutil
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Configuration
RASPIBIG_HOST = '192.168.100.21'
RASPIBIG_OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/AGENCIES'
LOCAL_BACKUP = '/opt/ACTIVE/OPENDATA/DATA/BACKUP/AGENCIES_MASTER_ALL.csv'
LOCAL_TEMP = '/tmp/agencies_split'

# Country code mapping for folder names
COUNTRY_CODES = {
    'Poland': 'PL',
    'Germany': 'DE',
    'Czech Republic': 'CZ',
    'Czechia': 'CZ',
    'Bulgaria': 'BG',
    'Romania': 'RO',
    'RO': 'RO',
    'Moldova': 'MD',
    'Norway': 'NO',
    'Sweden': 'SE',
    'SE': 'SE',
    'Denmark': 'DK',
    'Finland': 'FI',
    'Italy': 'IT',
    'Spain': 'ES',
    'Netherlands': 'NL',
    'Belgium': 'BE',
    'United Kingdom': 'UK',
    'UK': 'UK',
    'Ireland': 'IE',
    'France': 'FR',
    'Austria': 'AT',
    'Switzerland': 'CH',
    'Portugal': 'PT',
    'Greece': 'GR',
    'Hungary': 'HU',
    'Slovakia': 'SK',
    'Slovenia': 'SI',
    'Croatia': 'HR',
    'Serbia': 'RS',
    'Ukraine': 'UA',
    'Lithuania': 'LT',
    'Latvia': 'LV',
    'Estonia': 'EE',
    'Cyprus': 'CY',
    'Malta': 'MT',
    'Luxembourg': 'LU',
    'Iceland': 'IS',
}


def get_country_code(country: str) -> str:
    """Get 2-letter country code from country name."""
    if not country:
        return 'UNKNOWN'
    country = country.strip()
    # Already a code?
    if len(country) == 2 and country.isupper():
        return country
    # Look up in mapping
    return COUNTRY_CODES.get(country, country.upper()[:2] if country else 'UNKNOWN')


def create_country_db(db_path: str, agencies: list):
    """Create SQLite database for a country."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            country TEXT,
            address TEXT,
            city TEXT,
            website TEXT,
            source_file TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON agencies(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company ON agencies(company_name)')

    for agency in agencies:
        cursor.execute('''
            INSERT INTO agencies (company_name, email, phone, country, address, city, website, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agency.get('company_name', ''),
            agency.get('email', '') or None,
            agency.get('phone', ''),
            agency.get('country', ''),
            agency.get('address', ''),
            agency.get('city', ''),
            agency.get('website', ''),
            agency.get('source_file', ''),
        ))

    conn.commit()
    conn.close()


def write_country_csv(csv_path: str, agencies: list):
    """Write CSV for a country."""
    fieldnames = ['company_name', 'email', 'phone', 'country', 'address', 'city', 'website', 'source_file']
    with open(csv_path, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(agencies)


def main():
    print("="*60)
    print("SPLIT AGENCIES BY COUNTRY")
    print("="*60)

    # Read master file from backup
    print(f"\nReading: {LOCAL_BACKUP}")
    if not os.path.exists(LOCAL_BACKUP):
        print(f"ERROR: {LOCAL_BACKUP} not found!")
        sys.exit(1)

    # Group by country
    by_country = defaultdict(list)
    total = 0

    with open(LOCAL_BACKUP, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            country = get_country_code(row.get('country', ''))
            by_country[country].append(row)
            total += 1

    print(f"Total agencies: {total}")
    print(f"Countries found: {len(by_country)}")

    # Create temp directory
    os.makedirs(LOCAL_TEMP, exist_ok=True)

    # Process each country
    print("\nCreating country files:")
    for country_code, agencies in sorted(by_country.items(), key=lambda x: -len(x[1])):
        count = len(agencies)
        print(f"  {country_code}: {count} agencies")

        country_dir = os.path.join(LOCAL_TEMP, country_code)
        os.makedirs(country_dir, exist_ok=True)

        csv_path = os.path.join(country_dir, 'agencies.csv')
        db_path = os.path.join(country_dir, 'agencies.db')

        write_country_csv(csv_path, agencies)
        create_country_db(db_path, agencies)

    # Copy to raspibig
    print(f"\nCopying to raspibig:{RASPIBIG_OUTPUT_DIR}/")

    # Create directories on raspibig
    for country_code in by_country.keys():
        subprocess.run(f"ssh {RASPIBIG_HOST} 'mkdir -p {RASPIBIG_OUTPUT_DIR}/{country_code}'", shell=True)

    # Copy files
    for country_code in by_country.keys():
        local_dir = os.path.join(LOCAL_TEMP, country_code)
        remote_dir = f"{RASPIBIG_HOST}:{RASPIBIG_OUTPUT_DIR}/{country_code}/"
        result = subprocess.run(f"scp -q {local_dir}/* {remote_dir}", shell=True)
        if result.returncode == 0:
            print(f"  {country_code}: OK")
        else:
            print(f"  {country_code}: FAILED")

    # Cleanup
    shutil.rmtree(LOCAL_TEMP, ignore_errors=True)

    # Summary
    print("\n" + "="*60)
    print("SPLIT COMPLETE")
    print("="*60)
    print(f"Countries: {len(by_country)}")
    print(f"Location: raspibig:{RASPIBIG_OUTPUT_DIR}/<COUNTRY>/")
    print("\nTop countries:")
    for country_code, agencies in sorted(by_country.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {country_code}: {len(agencies)}")


if __name__ == '__main__':
    main()
