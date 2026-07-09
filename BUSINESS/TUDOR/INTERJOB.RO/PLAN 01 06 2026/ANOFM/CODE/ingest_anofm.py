#!/usr/bin/env python3
"""
ANOFM Ingest - CSV to anofm_db
Imports latest CSV from scraper and inserts into anofm_db.ij_jobs

Usage:
    python3 ingest_anofm.py
    python3 ingest_anofm.py --csv /path/to/file.csv
"""

import csv
import argparse
import os
import hashlib
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print('[ERROR] psycopg2 not found. Install: pip install psycopg2-binary')
    exit(1)

DB_CONFIG = {
    'host': 'localhost',
    'database': 'anofm_db',
    'user': 'tudor',
    'password': 'tudor'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_latest_csv(csv_dir='/opt/ACTIVE/ANOFM_DATA/csv'):
    csv_files = sorted(Path(csv_dir).glob('anofm_jobs_*.csv'))
    if not csv_files:
        return None
    return max(csv_files, key=lambda p: p.stat().st_mtime)

def compute_content_hash(row):
    data = f"{row.get('job_id')}|{row.get('company_name')}|{row.get('job_title', '')}|{row.get('job_description', '')}"
    return hashlib.md5(data.encode()).hexdigest()

def ingest_csv(csv_path):
    print(f'[INFO] Ingesting: {csv_path}')
    
    conn = get_connection()
    cur = conn.cursor()
    
    seen = set()
    inserted_count = 0
    updated_count = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            job_id = row.get('job_id', '')
            company = row.get('company_name', '')
            city = row.get('city', '')
            title = row.get('job_title', '')
            
            if not job_id:
                continue
            
            # Dedup key
            dedup_key = f"{job_id}|{company}|{city}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            
            # Compute hash
            content_hash = compute_content_hash(row)
            
            # Check if exists
            cur.execute(
                'SELECT id, content_hash FROM ij_jobs WHERE source=%s AND source_job_id=%s',
                ('anofm', job_id)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update if hash changed
                if existing[1] != content_hash:
                    cur.execute('''
                        UPDATE ij_jobs SET
                            title = %s,
                            city = %s,
                            sector = %s,
                            contract_type = %s,
                            salary_min = %s,
                            salary_max = %s,
                            salary_currency = %s,
                            description = %s,
                            source_url = %s,
                            expires_at = %s,
                            content_hash = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    ''', (
                        title, city, row.get('sector', ''), row.get('contract_type', ''),
                        float(row.get('salary_min', 0) or 0), float(row.get('salary_max', 0) or 0),
                        row.get('salary_currency', ''), row.get('job_description', ''),
                        row.get('source_url', ''), row.get('expiry_date', ''), content_hash, existing[0]
                    ))
                    updated_count += 1
            else:
                # Insert new
                slug = f"{company[:200]}-{job_id[:50]}"[:500]
                
                cur.execute('''
                    INSERT INTO ij_jobs (
                        source, source_job_id, content_hash, title, slug,
                        city, sector, contract_type, salary_min, salary_max,
                        salary_currency, description, source_url, expires_at, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    'anofm', job_id, content_hash, title, slug, city, row.get('sector', ''),
                    row.get('contract_type', ''), float(row.get('salary_min', 0) or 0),
                    float(row.get('salary_max', 0) or 0), row.get('salary_currency', ''),
                    row.get('job_description', ''), row.get('source_url', ''),
                    row.get('expiry_date', ''), 'active'
                ))
                inserted_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f'[OK] Inserted: {inserted_count}, Updated: {updated_count}')
    print(f'[INFO] Total processed: {inserted_count + updated_count}')
    
    return inserted_count, updated_count

def main():
    parser = argparse.ArgumentParser(description='ANOFM CSV Ingest')
    parser.add_argument('--csv', help='CSV file to ingest (default: latest)')
    args = parser.parse_args()
    
    # Get CSV path
    if args.csv:
        csv_path = args.csv
    else:
        csv_path = get_latest_csv()
        if not csv_path:
            print('[ERROR] No CSV found')
            exit(1)
    
    # Check file exists
    if not os.path.exists(csv_path):
        print(f'[ERROR] File not found: {csv_path}')
        exit(1)
    
    # Ingest
    try:
        inserted, updated = ingest_csv(csv_path)
        print(f'[OK] Completed at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    except Exception as e:
        print(f'[ERROR] {e}')
        raise

if __name__ == '__main__':
    main()