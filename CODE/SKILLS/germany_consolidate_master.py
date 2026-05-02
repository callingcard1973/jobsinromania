#!/usr/bin/env python3
"""Consolidate ALL Germany contact sources into GERMANY_ULTIMATE_MASTER.csv.
Deduplicates by email, merges officer names from cross-reference.
Output: /opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/GERMANY_ULTIMATE_MASTER.csv"""

import csv
import os
import re
from collections import defaultdict

OUTPUT = '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/GERMANY_ULTIMATE_MASTER.csv'

SOURCES = [
    {
        'name': 'Enriched Master',
        'path': '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/Germany_ENRICHED_MASTER.csv',
        'email_col': 'email',
        'company_col': 'company',
        'phone_col': None,
        'website_col': 'website',
        'city_col': 'city',
    },
    {
        'name': 'EURES Agencies',
        'path': '/opt/ACTIVE/OPENDATA/DATA/EURES_AGENCIES/germany_agencies.csv',
        'email_col': 'email',
        'company_col': 'company_name',
        'phone_col': 'phone',
        'website_col': 'website',
        'city_col': None,
    },
    {
        'name': 'All Sources Agencies',
        'path': '/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES/all_sources_agencies.csv',
        'email_col': 'email',
        'company_col': 'company',
        'phone_col': 'phone',
        'website_col': None,
        'city_col': 'city',
    },
    {
        'name': 'Merged Master',
        'path': '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/Germany_MERGED_MASTER.csv',
        'email_col': 'email_1',
        'company_col': 'company_name',
        'phone_col': 'phone_1',
        'website_col': 'company_website',
        'city_col': 'company_city',
    },
    {
        'name': 'Xing Companies',
        'path': '/mnt/usb/CSV_20251207/germany_xing.csv',
        'email_col': 'email',
        'company_col': 'company_name',
        'phone_col': 'phone',
        'website_col': 'website',
        'city_col': None,
        'contact_col': 'contact_person',
    },
    {
        'name': 'Gelbe Seiten',
        'path': '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/gelbe_seiten_all.csv',
        'email_col': 'email',
        'company_col': 'company_name',
        'phone_col': 'phone',
        'website_col': 'website',
        'city_col': 'city',
    },
    {
        'name': 'SCRAPER Contacts',
        'path': '/opt/ACTIVE/OPENDATA/DATA/SCRAPER_CONTACTS/OTHER/Germany_contacts_50.csv',
        'email_col': 'email_1',
        'company_col': 'company_name',
        'phone_col': 'phone_1',
        'website_col': 'company_website',
        'city_col': 'company_city',
        'contact_col': 'contact_person_1',
    },
    {
        'name': 'Old Agencies',
        'path': '/opt/ACTIVE/OPENDATA/DATA/AGENCIES/BY_COUNTRY/agencies_germany.csv',
        'email_col': 'email',
        'company_col': 'company_name',
        'phone_col': 'phone',
        'website_col': 'website',
        'city_col': 'city',
    },
]

# Officer data from cross-reference
OFFICERS_FILE = '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/bundesagentur_with_officers.csv'

def normalize_email(email):
    if not email:
        return ''
    return email.lower().strip()

def normalize_company(name):
    if not name:
        return ''
    return name.lower().strip()

def main():
    # Load officer data for company name lookup
    print("Loading officer data from cross-reference...")
    officers_by_company = {}  # normalized company name -> officer info
    if os.path.exists(OFFICERS_FILE):
        with open(OFFICERS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = normalize_company(row.get('company_name', ''))
                if name and row.get('officer_1_name'):
                    officers_by_company[name] = {
                        'officer_name': row.get('officer_1_name', ''),
                        'officer_position': row.get('officer_1_position', ''),
                        'officer_firstname': row.get('officer_1_firstname', ''),
                        'officer_lastname': row.get('officer_1_lastname', ''),
                        'federal_state': row.get('or_federal_state', ''),
                    }
        print(f"  Loaded officers for {len(officers_by_company)} companies")

    # Collect all contacts
    contacts = {}  # email -> best record
    no_email = []  # companies without email (for enrichment queue)

    for source in SOURCES:
        path = source['path']
        if not os.path.exists(path):
            print(f"  SKIP {source['name']}: {path} not found")
            continue

        count = 0
        new = 0
        csv.field_size_limit(10 * 1024 * 1024)

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    count += 1
                    email = normalize_email(row.get(source['email_col'], ''))
                    company = row.get(source['company_col'], '').strip()
                    phone = row.get(source.get('phone_col', ''), '').strip() if source.get('phone_col') else ''
                    website = row.get(source.get('website_col', ''), '').strip() if source.get('website_col') else ''
                    city = row.get(source.get('city_col', ''), '').strip() if source.get('city_col') else ''
                    contact = row.get(source.get('contact_col', ''), '').strip() if source.get('contact_col') else ''

                    if not email or '@' not in email:
                        if company:
                            no_email.append(company)
                        continue

                    if email not in contacts:
                        contacts[email] = {
                            'email': email,
                            'company_name': company,
                            'phone': phone,
                            'website': website,
                            'city': city,
                            'contact_person': contact,
                            'officer_name': '',
                            'officer_firstname': '',
                            'officer_lastname': '',
                            'officer_position': '',
                            'federal_state': '',
                            'sources': source['name'],
                            'country': 'Germany'
                        }
                        new += 1
                    else:
                        existing = contacts[email]
                        # Update missing fields
                        if company and not existing['company_name']:
                            existing['company_name'] = company
                        if phone and not existing['phone']:
                            existing['phone'] = phone
                        if website and not existing['website']:
                            existing['website'] = website
                        if city and not existing['city']:
                            existing['city'] = city
                        if contact and not existing['contact_person']:
                            existing['contact_person'] = contact
                        if source['name'] not in existing['sources']:
                            existing['sources'] += f", {source['name']}"

            print(f"  {source['name']}: {count} rows, {new} new unique emails")
        except Exception as e:
            print(f"  ERROR {source['name']}: {e}")

    # Enrich with officer data
    print("\nMatching officer data...")
    officer_matches = 0
    for email, record in contacts.items():
        norm_name = normalize_company(record['company_name'])
        if norm_name in officers_by_company:
            off = officers_by_company[norm_name]
            record['officer_name'] = off['officer_name']
            record['officer_firstname'] = off['officer_firstname']
            record['officer_lastname'] = off['officer_lastname']
            record['officer_position'] = off['officer_position']
            if not record['federal_state']:
                record['federal_state'] = off['federal_state']
            officer_matches += 1
    print(f"  Officer data added to {officer_matches} contacts")

    # Write output
    fields = ['email', 'company_name', 'phone', 'website', 'city', 'federal_state',
              'contact_person', 'officer_name', 'officer_firstname', 'officer_lastname',
              'officer_position', 'country', 'sources']

    # Sort by number of sources (most data-rich first)
    sorted_contacts = sorted(contacts.values(),
                             key=lambda x: (-len(x['sources'].split(',')), x['company_name']))

    with open(OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for record in sorted_contacts:
            writer.writerow(record)

    # Stats
    total = len(sorted_contacts)
    with_phone = sum(1 for c in sorted_contacts if c['phone'])
    with_website = sum(1 for c in sorted_contacts if c['website'])
    with_officer = sum(1 for c in sorted_contacts if c['officer_name'])
    with_contact = sum(1 for c in sorted_contacts if c['contact_person'])
    multi_source = sum(1 for c in sorted_contacts if ',' in c['sources'])

    print(f"\n{'='*60}")
    print(f"GERMANY ULTIMATE MASTER")
    print(f"{'='*60}")
    print(f"Total unique emails:     {total}")
    print(f"With phone:              {with_phone} ({with_phone*100/total:.0f}%)")
    print(f"With website:            {with_website} ({with_website*100/total:.0f}%)")
    print(f"With officer/director:   {with_officer} ({with_officer*100/total:.0f}%)")
    print(f"With contact person:     {with_contact} ({with_contact*100/total:.0f}%)")
    print(f"Multi-source (verified): {multi_source} ({multi_source*100/total:.0f}%)")
    print(f"\nCompanies without email (enrichment queue): {len(set(no_email))}")
    print(f"Output: {OUTPUT}")

if __name__ == '__main__':
    main()
