import csv
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import normalize_email, get_email_domain

INPUT = '../DATA/segmented.csv'
OUTPUT = '../DATA/enriched.csv'

DB_HOST = '192.168.100.21'
DB_PORT = 5432
DB_NAME = 'interjob_master'
DB_USER = 'tudor'

def load_master_db():
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary")
        return None, None
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                                user=DB_USER, connect_timeout=5)
    except Exception as e:
        print(f"Cannot reach raspibig: {e}")
        return None, None

    cur = conn.cursor()
    email_map = {}
    try:
        cur.execute("SELECT email, 'employer' FROM employers WHERE email IS NOT NULL")
        for email, role in cur.fetchall():
            email_map[normalize_email(email)] = ('employer', None)
    except Exception:
        pass
    try:
        cur.execute("SELECT email, id FROM applicants WHERE email IS NOT NULL")
        for email, rid in cur.fetchall():
            email_map[normalize_email(email)] = ('worker', rid)
    except Exception:
        pass

    domain_map = {}
    try:
        cur.execute("SELECT email FROM employers WHERE email IS NOT NULL")
        for (email,) in cur.fetchall():
            d = get_email_domain(normalize_email(email))
            if d:
                domain_map[d] = 'known_company'
    except Exception:
        pass

    conn.close()
    return email_map, domain_map

def main():
    email_map, domain_map = load_master_db()
    skip_enrich = email_map is None

    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) + ['in_master_db', 'master_db_role', 'master_db_id']
        for row in reader:
            rows.append(row)

    for row in rows:
        email = row.get('E-mail 1 - Value', '')
        domain = get_email_domain(email)
        if skip_enrich:
            row['in_master_db'] = 'false'
            row['master_db_role'] = ''
            row['master_db_id'] = ''
            continue
        if email in email_map:
            role, rid = email_map[email]
            row['in_master_db'] = 'true'
            row['master_db_role'] = role
            row['master_db_id'] = rid or ''
            row['score'] = min(100, int(row.get('score', 0)) + 25)
        elif domain in domain_map:
            row['in_master_db'] = 'true'
            row['master_db_role'] = 'known_company'
            row['master_db_id'] = ''
            row['score'] = min(100, int(row.get('score', 0)) + 25)
        else:
            row['in_master_db'] = 'false'
            row['master_db_role'] = ''
            row['master_db_id'] = ''

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    found = sum(1 for r in rows if r.get('in_master_db') == 'true')
    print(f"Enriched {len(rows)} rows. Found in master DB: {found} → {OUTPUT}")

if __name__ == '__main__':
    main()
