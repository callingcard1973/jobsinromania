#!/usr/bin/env python3
"""Convert ANOFM 16-col daily format to 50-col master format."""
import csv
import sys
from pathlib import Path

MASTER_COLS = [
    'company_name', 'company_normalized', 'company_address', 'company_city',
    'company_postal_code', 'company_website', 'company_org_number',
    'contact_person_1', 'contact_person_2', 'email_1', 'email_2', 'email_3',
    'phone_1', 'phone_2', 'phone_3', 'contact_title', 'job_title', 'job_id',
    'job_description', 'occupation', 'sector', 'location', 'city', 'region',
    'municipality', 'country', 'country_name', 'employment_type', 'contract_type',
    'working_hours', 'positions_available', 'start_date', 'application_deadline',
    'salary', 'salary_min', 'salary_max', 'salary_currency', 'source_url',
    'application_url', 'posting_date', 'expiry_date', 'source', 'official_job_board',
    'scrape_server', 'scrape_method', 'scrape_timestamp', 'scrape_date',
    'raw_source_file', 'batch_id', 'fingerprint'
]

# Map 16-col to 50-col
COL_MAP = {
    'job_id': 'job_id',
    'title': 'job_title',
    'employer': 'company_name',
    'contact_person': 'contact_person_1',
    'emails': 'email_1',
    'phones': 'phone_1',
    'positions_count': 'positions_available',
    'location': 'location',
    'contract_type': 'contract_type',
    'salary_min': 'salary_min',
    'salary_max': 'salary_max',
    'description': 'job_description',
    'job_expiry_date': 'expiry_date',
    'employer_tax_code': 'company_org_number',
    'scraped_by': 'scrape_server',
    'scraped_at': 'scrape_timestamp',
}

def convert_row(row):
    new_row = {col: '' for col in MASTER_COLS}
    new_row['country'] = 'RO'
    new_row['country_name'] = 'Romania'
    new_row['source'] = 'ANOFM'
    
    for old_col, new_col in COL_MAP.items():
        if old_col in row:
            new_row[new_col] = row[old_col]
    
    # Split multiple emails/phones
    if row.get('emails'):
        emails = row['emails'].split(';')
        for i, e in enumerate(emails[:3]):
            new_row[f'email_{i+1}'] = e.strip()
    
    if row.get('phones'):
        phones = row['phones'].split(';')
        for i, p in enumerate(phones[:3]):
            new_row[f'phone_{i+1}'] = p.strip()
    
    return new_row

def convert_file(infile, outfile=None):
    if outfile is None:
        outfile = infile.replace('.csv', '_50col.csv')
    
    with open(infile, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [convert_row(r) for r in reader]
    
    with open(outfile, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_COLS)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f'{infile}: {len(rows)} rows -> {outfile}')
    return outfile

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 anofm_format_converter.py <file.csv> [output.csv]')
        sys.exit(1)
    
    infile = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) > 2 else None
    convert_file(infile, outfile)
