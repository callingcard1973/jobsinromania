#!/usr/bin/env python3
"""
Applicant Search System - Unified search across all applicant sources.

Usage:
    python3 applicant_search.py --stats              # Show statistics
    python3 applicant_search.py --search "welder"    # Search by skill/keyword
    python3 applicant_search.py --country Nepal      # Filter by country
    python3 applicant_search.py --skill welding      # Filter by skill
    python3 applicant_search.py --all                # List all applicants
    python3 applicant_search.py --export FILE.csv    # Export to CSV
    python3 applicant_search.py --consolidate        # Rebuild master database
"""

import sqlite3
import csv
import json
import argparse
import os
from pathlib import Path
from datetime import datetime

# Data sources
SOURCES = {
    'workers_db': '/opt/WORKERS/data/workers.db',
    'applications_db': '/opt/WORKERS/data/applications.db',
    'cv_inbox': '/opt/ACTIVE/OPENDATA/DATA/CV_INBOX/real_applicants.csv',
    'factoryjobs': '/opt/WORKERS/data/factoryjobs.eu_applications.csv',
}

MASTER_DB = '/opt/ACTIVE/OPENDATA/DATA/master_applicants.db'

def init_master_db():
    """Initialize master applicants database."""
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        nationality TEXT,
        location TEXT,
        skills TEXT,
        experience TEXT,
        target_jobs TEXT,
        cv_file TEXT,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_email ON applicants(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_nationality ON applicants(nationality)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_skills ON applicants(skills)')
    conn.commit()
    return conn

def consolidate():
    """Consolidate all sources into master database."""
    conn = init_master_db()
    c = conn.cursor()
    
    added = 0
    skipped = 0
    
    # Source 1: workers.db
    if os.path.exists(SOURCES['workers_db']):
        wconn = sqlite3.connect(SOURCES['workers_db'])
        wc = wconn.cursor()
        for row in wc.execute('SELECT name, email, phone, nationality, current_location, skills, experience_years, target_jobs, cv_path FROM workers'):
            try:
                c.execute('''INSERT OR IGNORE INTO applicants 
                    (name, email, phone, nationality, location, skills, experience, target_jobs, cv_file, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (row[0], row[1], row[2], row[3], row[4], row[5], str(row[6]) if row[6] else '', row[7], row[8], 'workers_db'))
                if c.rowcount > 0:
                    added += 1
                else:
                    skipped += 1
            except:
                skipped += 1
        wconn.close()
    
    # Source 2: applications.db
    if os.path.exists(SOURCES['applications_db']):
        aconn = sqlite3.connect(SOURCES['applications_db'])
        ac = aconn.cursor()
        try:
            for row in ac.execute('SELECT first_name, last_name, email, phone, nationality, current_location, skills, experience_years FROM applications'):
                name = f"{row[0] or ''} {row[1] or ''}".strip()
                try:
                    c.execute('''INSERT OR IGNORE INTO applicants 
                        (name, email, phone, nationality, location, skills, experience, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (name, row[2], row[3], row[4], row[5], row[6], str(row[7]) if row[7] else '', 'applications_db'))
                    if c.rowcount > 0:
                        added += 1
                    else:
                        skipped += 1
                except:
                    skipped += 1
        except:
            pass
        aconn.close()
    
    # Source 3: CV inbox
    if os.path.exists(SOURCES['cv_inbox']):
        with open(SOURCES['cv_inbox']) as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    c.execute('''INSERT OR IGNORE INTO applicants 
                        (name, email, phone, cv_file, source)
                        VALUES (?, ?, ?, ?, ?)''',
                        (row.get('name', ''), row.get('email', ''), row.get('phone', ''), 
                         row.get('cv_files', ''), 'cv_inbox'))
                    if c.rowcount > 0:
                        added += 1
                    else:
                        skipped += 1
                except:
                    skipped += 1
    
    # Source 4: factoryjobs applications
    if os.path.exists(SOURCES['factoryjobs']):
        with open(SOURCES['factoryjobs']) as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = f"{row.get('First_Name', '')} {row.get('Last_Name', '')}".strip()
                try:
                    c.execute('''INSERT OR IGNORE INTO applicants 
                        (name, email, phone, nationality, location, skills, experience, cv_file, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (name, row.get('Email', ''), row.get('Phone', ''), 
                         row.get('Nationality', ''), row.get('Current_Location', ''),
                         row.get('Skills', ''), row.get('Experience_Years', ''),
                         row.get('CV_File', ''), 'factoryjobs'))
                    if c.rowcount > 0:
                        added += 1
                    else:
                        skipped += 1
                except:
                    skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"Consolidation complete: {added} added, {skipped} duplicates skipped")
    return added, skipped

def get_stats():
    """Get statistics from master database."""
    if not os.path.exists(MASTER_DB):
        consolidate()
    
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    
    total = c.execute('SELECT COUNT(*) FROM applicants').fetchone()[0]
    by_source = c.execute('SELECT source, COUNT(*) FROM applicants GROUP BY source').fetchall()
    by_country = c.execute("SELECT nationality, COUNT(*) FROM applicants WHERE nationality != '' AND nationality IS NOT NULL GROUP BY nationality ORDER BY COUNT(*) DESC LIMIT 10").fetchall()
    with_phone = c.execute("SELECT COUNT(*) FROM applicants WHERE phone != '' AND phone IS NOT NULL").fetchone()[0]
    with_cv = c.execute("SELECT COUNT(*) FROM applicants WHERE cv_file != '' AND cv_file IS NOT NULL").fetchone()[0]
    
    conn.close()
    
    print("=" * 60)
    print("APPLICANT DATABASE STATISTICS")
    print("=" * 60)
    print(f"\nTotal applicants: {total}")
    print(f"With phone: {with_phone}")
    print(f"With CV: {with_cv}")
    
    print("\nBy source:")
    for src, cnt in by_source:
        print(f"  {src}: {cnt}")
    
    print("\nTop nationalities:")
    for nat, cnt in by_country:
        print(f"  {nat}: {cnt}")

def search(query=None, country=None, skill=None, show_all=False):
    """Search applicants."""
    if not os.path.exists(MASTER_DB):
        consolidate()
    
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    
    sql = 'SELECT name, email, phone, nationality, skills, source FROM applicants WHERE 1=1'
    params = []
    
    if query:
        sql += ' AND (name LIKE ? OR email LIKE ? OR skills LIKE ? OR location LIKE ?)'
        q = f'%{query}%'
        params.extend([q, q, q, q])
    
    if country:
        sql += ' AND nationality LIKE ?'
        params.append(f'%{country}%')
    
    if skill:
        sql += ' AND skills LIKE ?'
        params.append(f'%{skill}%')
    
    sql += ' ORDER BY name'
    
    results = c.execute(sql, params).fetchall()
    conn.close()
    
    if not results:
        print("No applicants found matching criteria.")
        return
    
    print(f"\nFound {len(results)} applicants:\n")
    print(f"{'Name':<25} {'Email':<30} {'Phone':<15} {'Country':<12}")
    print("-" * 85)
    
    for row in results:
        name = (row[0] or '')[:24]
        email = (row[1] or '')[:29]
        phone = (row[2] or '')[:14]
        nat = (row[3] or '')[:11]
        print(f"{name:<25} {email:<30} {phone:<15} {nat:<12}")

def export_csv(filename):
    """Export to CSV."""
    if not os.path.exists(MASTER_DB):
        consolidate()
    
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    
    results = c.execute('SELECT name, email, phone, nationality, location, skills, experience, cv_file, source FROM applicants ORDER BY name').fetchall()
    conn.close()
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'email', 'phone', 'nationality', 'location', 'skills', 'experience', 'cv_file', 'source'])
        writer.writerows(results)
    
    print(f"Exported {len(results)} applicants to {filename}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Applicant Search System')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--search', type=str, help='Search by keyword')
    parser.add_argument('--country', type=str, help='Filter by country')
    parser.add_argument('--skill', type=str, help='Filter by skill')
    parser.add_argument('--all', action='store_true', help='List all applicants')
    parser.add_argument('--export', type=str, help='Export to CSV file')
    parser.add_argument('--consolidate', action='store_true', help='Rebuild master database')
    
    args = parser.parse_args()
    
    if args.consolidate:
        consolidate()
    elif args.stats:
        get_stats()
    elif args.export:
        export_csv(args.export)
    elif args.search or args.country or args.skill or args.all:
        search(query=args.search, country=args.country, skill=args.skill, show_all=args.all)
    else:
        get_stats()

def remove_applicant(email):
    """Remove applicant from database and optionally archive."""
    if not os.path.exists(MASTER_DB):
        print("Database not found. Run --consolidate first.")
        return
    
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()
    
    # Check if exists
    result = c.execute('SELECT name, email, source FROM applicants WHERE email = ?', (email,)).fetchone()
    if not result:
        print(f"Applicant with email '{email}' not found.")
        conn.close()
        return
    
    print(f"Found: {result[0]} ({result[1]}) from {result[2]}")
    
    # Archive to removed table
    c.execute('''CREATE TABLE IF NOT EXISTS removed_applicants (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        nationality TEXT,
        reason TEXT,
        removed_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''INSERT INTO removed_applicants (name, email, phone, nationality, reason)
        SELECT name, email, phone, nationality, 'manual_removal' FROM applicants WHERE email = ?''', (email,))
    
    c.execute('DELETE FROM applicants WHERE email = ?', (email,))
    conn.commit()
    conn.close()
    
    print(f"Removed and archived: {email}")

def remove_batch(emails_file):
    """Remove multiple applicants from a file (one email per line)."""
    if not os.path.exists(emails_file):
        print(f"File not found: {emails_file}")
        return
    
    with open(emails_file) as f:
        emails = [line.strip() for line in f if line.strip() and '@' in line]
    
    print(f"Removing {len(emails)} applicants...")
    for email in emails:
        remove_applicant(email)

def clear_inbox():
    """Clear processed emails from CV inbox folders."""
    inbox_dir = Path('/opt/ACTIVE/OPENDATA/DATA/CV_INBOX')
    archived = 0
    
    archive_dir = inbox_dir / 'ARCHIVED'
    archive_dir.mkdir(exist_ok=True)
    
    for folder in inbox_dir.iterdir():
        if folder.is_dir() and folder.name not in ['ARCHIVED', '.']:
            for subfolder in folder.iterdir():
                if subfolder.is_dir():
                    # Move to archive
                    dest = archive_dir / folder.name / subfolder.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        subfolder.rename(dest)
                        archived += 1
                    except:
                        pass
    
    print(f"Archived {archived} folders to {archive_dir}")

# Add to argument parser
if __name__ == '__main__':
    import sys
    
    # Quick CLI handling for additional commands
    if len(sys.argv) > 1:
        if sys.argv[1] == '--remove' and len(sys.argv) > 2:
            remove_applicant(sys.argv[2])
            sys.exit(0)
        elif sys.argv[1] == '--remove-batch' and len(sys.argv) > 2:
            remove_batch(sys.argv[2])
            sys.exit(0)
        elif sys.argv[1] == '--clear-inbox':
            clear_inbox()
            sys.exit(0)
