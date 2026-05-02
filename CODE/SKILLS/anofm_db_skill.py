#!/usr/bin/env python3
"""ANOFM DB Skill: import from CSVs, romania_emails, interjob_master.
Usage:
  python3 anofm_db_skill.py --import-csv    Import all ANOFM CSVs
  python3 anofm_db_skill.py --import-ro     Import from romania_emails.contacts
  python3 anofm_db_skill.py --import-master Import from interjob_master (RO companies)
  python3 anofm_db_skill.py --import-all    All of the above
  python3 anofm_db_skill.py --status        Show stats
  python3 anofm_db_skill.py --latest        Import only latest CSV
"""
# --
import psycopg2
import csv
import glob
import os
import re
import sys
import argparse
import unicodedata

ANOFM_DB = {"dbname": "anofm", "user": "tudor", "host": "/var/run/postgresql"}
MASTER_DB = {"dbname": "interjob_master", "user": "tudor", "host": "/var/run/postgresql"}
ROMANIA_DB = {"dbname": "romania_emails", "user": "tudor", "host": "/var/run/postgresql"}
CSV_DIR = "/opt/ACTIVE/SCRAPER_DATA/csv/ANOFM"
HDD_DIR = "/mnt/hdd/SCRAPER_DATA/csv/ANOFM"

# --
def to_ascii(t):
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii').strip()

def norm_phone(p):
    if not p: return ''
    digits = re.sub(r'\D', '', str(p))
    if len(digits) == 10 and digits.startswith('0'): return '+40' + digits[1:]
    elif len(digits) == 9: return '+40' + digits
    elif len(digits) == 11 and digits.startswith('40'): return '+' + digits
    return p.strip()

def norm_email(e):
    if not e: return ''
    e = e.strip().lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e): return ''
    try: e.encode('ascii')
    except Exception: return ''
    return e

# --
def ensure_db():
    """Create anofm DB + table if not exists."""
    conn = psycopg2.connect(dbname="postgres", user="tudor", host="/var/run/postgresql")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'anofm'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE anofm OWNER tudor")
    conn.close()
    conn = psycopg2.connect(**ANOFM_DB)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id SERIAL PRIMARY KEY, company_name TEXT, company_normalized TEXT,
        company_address TEXT, company_city TEXT, company_postal_code TEXT,
        company_website TEXT, company_org_number TEXT, contact_person TEXT,
        email TEXT, phone TEXT, job_title TEXT, job_id TEXT UNIQUE,
        job_description TEXT, occupation TEXT, sector TEXT, city TEXT,
        region TEXT, municipality TEXT, country TEXT DEFAULT 'RO',
        employment_type TEXT, contract_type TEXT, working_hours TEXT,
        positions_available INTEGER DEFAULT 1, start_date TEXT,
        application_deadline TEXT, salary TEXT, salary_min TEXT,
        salary_max TEXT, salary_currency TEXT DEFAULT 'RON',
        source_url TEXT, posting_date TEXT, expiry_date TEXT,
        scrape_date TEXT, fingerprint TEXT, source TEXT DEFAULT 'anofm_csv',
        created_at TIMESTAMP DEFAULT NOW())""")
    for idx in ['email', 'company_normalized', 'sector', 'city', 'scrape_date', 'source']:
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_anofm_{idx} ON jobs({idx})")
    conn.commit()
    conn.close()

# --
def import_csv(path):
    """Import one ANOFM CSV."""
    conn = psycopg2.connect(**ANOFM_DB)
    cur = conn.cursor()
    ins, skip = 0, 0
    with open(path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            jid = row.get('job_id', '').strip()
            if not jid: skip += 1; continue
            pos = row.get('positions_available', '1')
            pos = int(pos) if pos and pos.isdigit() else 1
            try:
                cur.execute("""INSERT INTO jobs (company_name, company_normalized,
                    company_address, company_city, company_website, company_org_number,
                    contact_person, email, phone, job_title, job_id, job_description,
                    occupation, sector, city, region, municipality, positions_available,
                    salary, source_url, posting_date, expiry_date, scrape_date, fingerprint, source)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (job_id) DO UPDATE SET email=EXCLUDED.email, phone=EXCLUDED.phone,
                    positions_available=EXCLUDED.positions_available, scrape_date=EXCLUDED.scrape_date""",
                    (to_ascii(row.get('company_name','')), to_ascii(row.get('company_normalized','')),
                     to_ascii(row.get('company_address','')), to_ascii(row.get('company_city','')),
                     row.get('company_website',''), row.get('company_org_number',''),
                     to_ascii(row.get('contact_person_1','')),
                     norm_email(row.get('email_1','')), norm_phone(row.get('phone_1','')),
                     to_ascii(row.get('job_title','')), jid,
                     to_ascii(row.get('job_description',''))[:500],
                     to_ascii(row.get('occupation','')), to_ascii(row.get('sector','')),
                     to_ascii(row.get('city','')), to_ascii(row.get('region','')),
                     to_ascii(row.get('municipality','')), pos,
                     row.get('salary',''), row.get('source_url',''),
                     row.get('posting_date',''), row.get('expiry_date',''),
                     row.get('scrape_date',''), row.get('fingerprint',''), 'anofm_csv'))
                ins += 1
            except Exception:
                conn.rollback(); skip += 1
    conn.commit(); conn.close()
    return ins, skip

# --
def import_all_csvs():
    """Import all ANOFM CSVs from both dirs."""
    csvs = sorted(glob.glob(f"{CSV_DIR}/anofm_2*.csv") + glob.glob(f"{HDD_DIR}/anofm_2*.csv"))
    print(f"Found {len(csvs)} ANOFM CSVs")
    total_ins = 0
    for path in csvs:
        ins, skip = import_csv(path)
        total_ins += ins
        if ins > 0:
            print(f"  {os.path.basename(path)}: {ins}")
    print(f"Total imported: {total_ins}")

def import_latest():
    """Import only the most recent CSV."""
    csvs = sorted(glob.glob(f"{CSV_DIR}/anofm_2*.csv") + glob.glob(f"{HDD_DIR}/anofm_2*.csv"))
    if csvs:
        ins, skip = import_csv(csvs[-1])
        print(f"{os.path.basename(csvs[-1])}: {ins} inserted, {skip} skipped")

# --
def import_romania_emails():
    """Import contacts from romania_emails DB as employer data."""
    try:
        src = psycopg2.connect(**ROMANIA_DB)
    except Exception:
        print("romania_emails DB not accessible"); return
    dst = psycopg2.connect(**ANOFM_DB)
    sc, dc = src.cursor(), dst.cursor()
    sc.execute("SELECT email, phone, company, city, source FROM contacts WHERE email IS NOT NULL LIMIT 200000")
    ins = 0
    for email, phone, company, city, source in sc:
        email = norm_email(email)
        if not email: continue
        jid = f"ro_emails_{email}"
        try:
            dc.execute("""INSERT INTO jobs (company_name, company_normalized, email, phone,
                city, job_id, source) VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (job_id) DO NOTHING""",
                (to_ascii(company), to_ascii(company), email, norm_phone(phone),
                 to_ascii(city), jid, 'romania_emails'))
            ins += 1
        except Exception:
            dst.rollback()
    dst.commit(); src.close(); dst.close()
    print(f"romania_emails: {ins} imported")

# --
def import_master():
    """Import Romanian companies from interjob_master."""
    try:
        src = psycopg2.connect(**MASTER_DB)
    except Exception:
        print("interjob_master DB not accessible"); return
    dst = psycopg2.connect(**ANOFM_DB)
    sc, dc = src.cursor(), dst.cursor()
    sc.execute("""SELECT name, email, phone, city, country FROM companies
        WHERE country='RO' AND email IS NOT NULL AND email LIKE '%%@%%' LIMIT 500000""")
    ins = 0
    for name, email, phone, city, country in sc:
        email = norm_email(email)
        if not email: continue
        jid = f"master_ro_{email}"
        try:
            dc.execute("""INSERT INTO jobs (company_name, company_normalized, email, phone,
                city, country, job_id, source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (job_id) DO NOTHING""",
                (to_ascii(name), to_ascii(name), email, norm_phone(phone),
                 to_ascii(city), 'RO', jid, 'interjob_master'))
            ins += 1
        except Exception:
            dst.rollback()
    dst.commit(); src.close(); dst.close()
    print(f"interjob_master RO: {ins} imported")

# --
def status():
    conn = psycopg2.connect(**ANOFM_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs WHERE email LIKE '%%@%%.%%'")
    emails = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs WHERE phone LIKE '+40%%'")
    phones = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT company_normalized) FROM jobs WHERE company_normalized != ''")
    companies = cur.fetchone()[0]
    cur.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY count DESC")
    sources = cur.fetchall()
    cur.execute("SELECT sector, COUNT(*) FROM jobs WHERE sector != '' GROUP BY sector ORDER BY count DESC LIMIT 10")
    sectors = cur.fetchall()
    conn.close()
    print(f"ANOFM DB: {total} jobs | {emails} email | {phones} phone | {companies} companies")
    print("Sources:", ", ".join(f"{s}:{c}" for s, c in sources))
    print("Top sectors:", ", ".join(f"{s}:{c}" for s, c in sectors))

# --
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--import-csv', action='store_true')
    p.add_argument('--import-ro', action='store_true')
    p.add_argument('--import-master', action='store_true')
    p.add_argument('--import-all', action='store_true')
    p.add_argument('--latest', action='store_true')
    p.add_argument('--status', action='store_true')
    a = p.parse_args()
    ensure_db()
    if a.status: status()
    elif a.import_all:
        import_all_csvs()
        import_romania_emails()
        import_master()
        status()
    elif a.import_csv: import_all_csvs()
    elif a.import_ro: import_romania_emails()
    elif a.import_master: import_master()
    elif a.latest: import_latest()
    else: status()

if __name__ == '__main__':
    main()
