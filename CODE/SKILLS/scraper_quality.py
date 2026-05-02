#!/usr/bin/env python3
"""
Scraper Quality Checker - Validate scraper output
Usage: python3 scraper_quality.py /path/to/output.csv
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import csv, re
from collections import Counter
from pathlib import Path

def analyze(csv_path):
    print(f"\n{'='*60}\nSCRAPER QUALITY CHECK: {Path(csv_path).name}\n{'='*60}\n")
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        rows = list(csv.DictReader(f))
    
    total = len(rows)
    cols = list(rows[0].keys()) if rows else []
    print(f"Rows: {total} | Columns: {len(cols)}")
    print(f"Fields: {', '.join(cols[:10])}{'...' if len(cols)>10 else ''}\n")
    
    # Missing values per column
    print("MISSING VALUES:")
    for col in cols[:15]:
        empty = sum(1 for r in rows if not r.get(col,'').strip())
        if empty > 0:
            print(f"  {col}: {empty} ({empty*100//total}%)")
    
    # Email validation
    email_cols = [c for c in cols if 'email' in c.lower()]
    for ec in email_cols:
        emails = [r.get(ec,'').strip().lower() for r in rows if r.get(ec,'').strip()]
        valid = [e for e in emails if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e)]
        invalid = len(emails) - len(valid)
        dupes = len(emails) - len(set(emails))
        print(f"\n{ec.upper()}: {len(emails)} total | {len(valid)} valid | {invalid} invalid | {dupes} dupes")
    
    # Phone validation
    phone_cols = [c for c in cols if 'phone' in c.lower() or 'tel' in c.lower()]
    for pc in phone_cols:
        phones = [r.get(pc,'').strip() for r in rows if r.get(pc,'').strip()]
        short = [p for p in phones if len(re.sub(r'\D','',p)) < 8]
        print(f"\n{pc.upper()}: {len(phones)} total | {len(short)} too short")
    
    # URL validation
    url_cols = [c for c in cols if 'url' in c.lower() or 'website' in c.lower() or 'link' in c.lower()]
    for uc in url_cols:
        urls = [r.get(uc,'').strip() for r in rows if r.get(uc,'').strip()]
        invalid_urls = [u for u in urls if not u.startswith(('http://','https://','www.'))]
        print(f"\n{uc.upper()}: {len(urls)} total | {len(invalid_urls)} invalid format")
    
    # Duplicate rows check
    row_hashes = [hash(tuple(r.values())) for r in rows]
    dupe_rows = len(row_hashes) - len(set(row_hashes))
    print(f"\nDUPLICATE ROWS: {dupe_rows}")
    
    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    analyze(sys.argv[1]) if len(sys.argv)>1 else print("Usage: scraper_quality.py <csv>")
