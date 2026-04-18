#!/usr/bin/env python3
"""Create anofm database and import latest CSV data."""
# --
import psycopg2
import csv
import glob
import os
import re
import unicodedata

ADMIN_DB = {"dbname": "postgres", "user": "tudor", "host": "/var/run/postgresql"}
DB = {"dbname": "anofm", "user": "tudor", "host": "/var/run/postgresql"}
CSV_DIR = "/opt/ACTIVE/SCRAPER_DATA/csv/ANOFM"

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
def create_db():
    conn = psycopg2.connect(**ADMIN_DB)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'anofm'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE anofm OWNER tudor")
        print("Created database anofm")
    else:
        print("Database anofm exists")
    conn.close()

# --
def create_tables():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id SERIAL PRIMARY KEY,
        company_name TEXT,
        company_normalized TEXT,
        company_address TEXT,
        company_city TEXT,
        company_postal_code TEXT,
        company_website TEXT,
        company_org_number TEXT,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        job_title TEXT,
        job_id TEXT UNIQUE,
        job_description TEXT,
        occupation TEXT,
        sector TEXT,
        city TEXT,
        region TEXT,
        municipality TEXT,
        country TEXT DEFAULT 'RO',
        employment_type TEXT,
        contract_type TEXT,
        working_hours TEXT,
        positions_available INTEGER DEFAULT 1,
        start_date TEXT,
        application_deadline TEXT,
        salary TEXT,
        salary_min TEXT,
        salary_max TEXT,
        salary_currency TEXT DEFAULT 'RON',
        source_url TEXT,
        posting_date TEXT,
        expiry_date TEXT,
        scrape_date TEXT,
        fingerprint TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anofm_email ON jobs(email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anofm_company ON jobs(company_normalized)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anofm_sector ON jobs(sector)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anofm_city ON jobs(city)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anofm_date ON jobs(scrape_date)")
    conn.commit()
    conn.close()
    print("Tables created")

# --
def import_csv(path):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = norm_email(row.get('email_1', ''))
            phone = norm_phone(row.get('phone_1', ''))
            job_id = row.get('job_id', '').strip()
            if not job_id:
                skipped += 1
                continue
            try:
                pos = row.get('positions_available', '1')
                pos = int(pos) if pos and pos.isdigit() else 1
            except Exception:
                pos = 1
            try:
                cur.execute("""
                INSERT INTO jobs (company_name, company_normalized, company_address,
                    company_city, company_postal_code, company_website, company_org_number,
                    contact_person, email, phone, job_title, job_id, job_description,
                    occupation, sector, city, region, municipality, country,
                    employment_type, contract_type, working_hours, positions_available,
                    start_date, application_deadline, salary, salary_min, salary_max,
                    salary_currency, source_url, posting_date, expiry_date,
                    scrape_date, fingerprint)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (job_id) DO UPDATE SET
                    email=EXCLUDED.email, phone=EXCLUDED.phone,
                    positions_available=EXCLUDED.positions_available,
                    scrape_date=EXCLUDED.scrape_date
                """, (
                    to_ascii(row.get('company_name', '')),
                    to_ascii(row.get('company_normalized', '')),
                    to_ascii(row.get('company_address', '')),
                    to_ascii(row.get('company_city', '')),
                    row.get('company_postal_code', ''),
                    row.get('company_website', ''),
                    row.get('company_org_number', ''),
                    to_ascii(row.get('contact_person_1', '')),
                    email, phone,
                    to_ascii(row.get('job_title', '')),
                    job_id,
                    to_ascii(row.get('job_description', ''))[:500],
                    to_ascii(row.get('occupation', '')),
                    to_ascii(row.get('sector', '')),
                    to_ascii(row.get('city', '')),
                    to_ascii(row.get('region', '')),
                    to_ascii(row.get('municipality', '')),
                    row.get('country', 'RO'),
                    row.get('employment_type', ''),
                    row.get('contract_type', ''),
                    row.get('working_hours', ''),
                    pos,
                    row.get('start_date', ''),
                    row.get('application_deadline', ''),
                    row.get('salary', ''),
                    row.get('salary_min', ''),
                    row.get('salary_max', ''),
                    row.get('salary_currency', 'RON'),
                    row.get('source_url', ''),
                    row.get('posting_date', ''),
                    row.get('expiry_date', ''),
                    row.get('scrape_date', ''),
                    row.get('fingerprint', ''),
                ))
                inserted += 1
            except Exception as e:
                conn.rollback()
                skipped += 1
                continue
    conn.commit()
    conn.close()
    return inserted, skipped

# --
def main():
    create_db()
    create_tables()
    # Import all CSVs
    csvs = sorted(glob.glob(f"{CSV_DIR}/anofm_*.csv"))
    print(f"Found {len(csvs)} CSV files")
    total_ins = 0
    total_skip = 0
    for path in csvs:
        ins, skip = import_csv(path)
        total_ins += ins
        total_skip += skip
        print(f"  {os.path.basename(path)}: {ins} inserted, {skip} skipped")
    # Stats
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs WHERE email LIKE '%%@%%.%%'")
    emails = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs WHERE phone LIKE '+40%%'")
    phones = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT company_normalized) FROM jobs")
    companies = cur.fetchone()[0]
    cur.execute("SELECT sector, COUNT(*) FROM jobs GROUP BY sector ORDER BY count DESC LIMIT 10")
    sectors = cur.fetchall()
    conn.close()
    print(f"\n=== ANOFM DB ===")
    print(f"Total jobs: {total}")
    print(f"With email: {emails}")
    print(f"With phone: {phones}")
    print(f"Unique companies: {companies}")
    print(f"Top sectors:")
    for s, c in sectors:
        print(f"  {s}: {c}")

if __name__ == "__main__":
    main()
