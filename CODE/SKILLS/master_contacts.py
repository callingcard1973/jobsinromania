#!/usr/bin/env python3
"""
Master Contact Analyzer - Scan ALL CSVs on raspibig and raspi
Usage: python3 master_contacts.py [--full]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import subprocess
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

def find_csvs_local():
    """Find all CSVs on raspibig"""
    paths = [
        '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE',
        '/opt/ACTIVE/EMAIL/CAMPAIGNS',
        '/mnt/hdd/SCRAPER_DATA',
        '/opt/ACTIVE/OPENDATA/DATA'
    ]
    csvs = []
    for p in paths:
        try:
            result = subprocess.run(['find', p, '-name', '*.csv', '-type', 'f'], 
                                    capture_output=True, text=True, timeout=60)
            csvs.extend(result.stdout.strip().split('\n'))
        except: pass
    return [c for c in csvs if c and c.endswith('.csv')]

def find_csvs_remote():
    """Find all CSVs on raspi via SSH"""
    paths = ['/opt/ACTIVE/EMAIL/CAMPAIGNS', '/opt/ACTIVE/SCRAPERS/EUROPE', '/opt/ACTIVE/OPENDATA/DATA', '/home/tudor/SCRAPER_DATA']
    csvs = []
    for p in paths:
        try:
            result = subprocess.run(['ssh', 'raspi', f'find {p} -name "*.csv" -type f 2>/dev/null'],
                                    capture_output=True, text=True, timeout=60)
            for c in result.stdout.strip().split('\n'):
                if c and c.endswith('.csv'):
                    csvs.append(f'raspi:{c}')
        except: pass
    return csvs

def read_csv_file(path):
    """Read CSV, handling remote files"""
    rows = []
    try:
        if path.startswith('raspi:'):
            remote_path = path[6:]
            result = subprocess.run(['ssh', 'raspi', f'cat "{remote_path}"'],
                                    capture_output=True, text=True, timeout=30)
            content = result.stdout
            reader = csv.DictReader(content.splitlines())
            rows = list(reader)
        else:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                rows = list(csv.DictReader(f))
    except Exception as e:
        pass
    return rows

def extract_emails(rows):
    """Extract emails from rows"""
    emails = []
    if not rows: return emails
    email_cols = [c for c in rows[0].keys() if 'email' in c.lower()]
    for r in rows:
        for ec in email_cols:
            e = r.get(ec, '').strip().lower()
            if e and '@' in e and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e):
                emails.append(e)
    return emails

def analyze():
    full_mode = '--full' in sys.argv
    
    print(f"\n{'='*70}")
    print("MASTER CONTACT ANALYZER - All CSVs on raspibig + raspi")
    print(f"{'='*70}\n")
    
    print("Scanning raspibig...")
    local_csvs = find_csvs_local()
    print(f"  Found {len(local_csvs)} CSV files")
    
    print("Scanning raspi (via SSH)...")
    remote_csvs = find_csvs_remote()
    print(f"  Found {len(remote_csvs)} CSV files")
    
    all_csvs = local_csvs + remote_csvs
    print(f"\nTotal CSV files: {len(all_csvs)}\n")
    
    # Collect all emails
    all_emails = []
    file_stats = []
    
    for i, csv_path in enumerate(all_csvs):
        if not full_mode and i >= 50:  # Limit in quick mode
            print(f"  ... and {len(all_csvs)-50} more (use --full for all)")
            break
        
        rows = read_csv_file(csv_path)
        emails = extract_emails(rows)
        
        if emails:
            all_emails.extend(emails)
            machine = 'raspi' if csv_path.startswith('raspi:') else 'raspibig'
            name = Path(csv_path.replace('raspi:','')).name
            file_stats.append((name, machine, len(rows), len(emails), len(set(emails))))
            print(f"  {name}: {len(emails)} emails")
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")
    
    unique_emails = set(all_emails)
    print(f"Total emails found: {len(all_emails)}")
    print(f"Unique emails: {len(unique_emails)}")
    print(f"Duplicates: {len(all_emails) - len(unique_emails)}")
    
    # Domain breakdown
    domains = Counter(e.split('@')[1] for e in unique_emails)
    print(f"\nTOP 15 DOMAINS:")
    for d, c in domains.most_common(15):
        print(f"  {d}: {c}")
    
    # Free vs corporate
    free = {'gmail.com','yahoo.com','yahoo.ro','hotmail.com','outlook.com','icloud.com','mail.ru','yandex.ru'}
    free_cnt = sum(1 for e in unique_emails if e.split('@')[1] in free)
    print(f"\nCorporate: {len(unique_emails)-free_cnt} | Personal: {free_cnt}")
    
    # Files with most contacts
    print(f"\nTOP 10 FILES BY CONTACTS:")
    for name, machine, rows, emails, uniq in sorted(file_stats, key=lambda x: -x[3])[:10]:
        print(f"  [{machine}] {name}: {uniq} unique / {emails} total")
    
    # Global duplicates (emails appearing in multiple files)
    email_files = defaultdict(set)
    for csv_path in all_csvs[:50]:
        rows = read_csv_file(csv_path)
        for e in set(extract_emails(rows)):
            email_files[e].add(Path(csv_path.replace('raspi:','')).name)
    
    cross_file = {e: f for e, f in email_files.items() if len(f) > 1}
    print(f"\nCROSS-FILE DUPLICATES: {len(cross_file)} emails in multiple files")
    
    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    analyze()
