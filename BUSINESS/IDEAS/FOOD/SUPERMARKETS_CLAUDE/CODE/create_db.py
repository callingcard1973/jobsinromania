#!/usr/bin/env python3
"""Create food_distribution PostgreSQL database on raspibig.

Creates table, imports ROMANIA_FOOD_DISTRIBUTION_CONTACTS.csv,
adds indexes for fast querying.

Usage:
    python create_db.py                     # Create DB + import CSV
    python create_db.py --drop              # Drop and recreate
    python create_db.py --stats             # Show stats only
    python create_db.py --csv file.csv      # Import specific CSV
"""

import csv
import os
import sys

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

from shared_utils import DB_MASTER, DB_FOOD

DB_NAME = "food_distribution"
DB_NEW = DB_FOOD

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")
DEFAULT_CSV = os.path.join(DATA_DIR, "ROMANIA_FOOD_DISTRIBUTION_CONTACTS.csv")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    company TEXT,
    cui TEXT,
    county TEXT,
    city TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    website TEXT,
    category TEXT,
    subcategory TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_category ON contacts(category);
CREATE INDEX IF NOT EXISTS idx_contacts_county ON contacts(county);
CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company);
CREATE INDEX IF NOT EXISTS idx_contacts_cui ON contacts(cui);
"""

VIEWS = """
CREATE OR REPLACE VIEW contacts_with_email AS
    SELECT * FROM contacts WHERE email IS NOT NULL AND email != '';

CREATE OR REPLACE VIEW contacts_by_category AS
    SELECT category, COUNT(*) as total,
           COUNT(CASE WHEN email != '' THEN 1 END) as with_email,
           COUNT(DISTINCT county) as counties
    FROM contacts GROUP BY category ORDER BY total DESC;

CREATE OR REPLACE VIEW contacts_by_county AS
    SELECT county, COUNT(*) as total,
           COUNT(CASE WHEN email != '' THEN 1 END) as with_email,
           COUNT(DISTINCT category) as categories
    FROM contacts WHERE county != ''
    GROUP BY county ORDER BY total DESC;
"""


def create_database(drop=False):
    """Create the food_distribution database."""
    conn = psycopg2.connect(**DB_MASTER)
    conn.autocommit = True
    cur = conn.cursor()
    if drop:
        cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
        print(f"Dropped database {DB_NAME}")
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
    if not cur.fetchone():
        cur.execute(f"CREATE DATABASE {DB_NAME} OWNER tudor")
        print(f"Created database {DB_NAME}")
    else:
        print(f"Database {DB_NAME} already exists")
    conn.close()


def create_schema():
    """Create table, indexes, views."""
    conn = psycopg2.connect(**DB_NEW)
    cur = conn.cursor()
    cur.execute(CREATE_TABLE)
    cur.execute(CREATE_INDEXES)
    cur.execute(VIEWS)
    conn.commit()
    conn.close()
    print("Schema created (table + indexes + views)")


def import_csv(csv_path):
    """Import CSV into contacts table."""
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return 0

    conn = psycopg2.connect(**DB_NEW)
    cur = conn.cursor()

    # Clear existing data
    cur.execute("TRUNCATE contacts RESTART IDENTITY")

    cols = ["company", "cui", "county", "city", "address", "phone",
            "email", "website", "category", "subcategory", "source"]
    insert_sql = f"""INSERT INTO contacts ({', '.join(cols)})
        VALUES %s"""

    rows = []
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = tuple(row.get(c, "") or "" for c in cols)
            rows.append(values)

    if rows:
        execute_values(cur, insert_sql, rows, page_size=1000)
        conn.commit()

    conn.close()
    print(f"Imported {len(rows)} contacts from {os.path.basename(csv_path)}")
    return len(rows)


def show_stats():
    """Show database statistics."""
    conn = psycopg2.connect(**DB_NEW)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM contacts")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM contacts WHERE email != ''")
    with_email = cur.fetchone()[0]

    print(f"\nTotal contacts: {total}")
    print(f"With email: {with_email}")

    cur.execute("SELECT * FROM contacts_by_category")
    print(f"\nBy category:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} total, {row[2]} with email, {row[3]} counties")

    cur.execute("SELECT * FROM contacts_by_county LIMIT 15")
    print(f"\nTop 15 counties:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} total, {row[2]} with email")

    conn.close()


def main():
    args = sys.argv[1:]
    drop = "--drop" in args
    stats_only = "--stats" in args
    csv_path = DEFAULT_CSV

    for i, arg in enumerate(args):
        if arg == "--csv" and i + 1 < len(args):
            csv_path = args[i + 1]

    if stats_only:
        show_stats()
        return

    # Step 1: Create database
    create_database(drop=drop)

    # Step 2: Create schema
    create_schema()

    # Step 3: Import CSV
    if os.path.exists(csv_path):
        import_csv(csv_path)
        show_stats()
    else:
        print(f"\nCSV not found: {csv_path}")
        print("Run consolidate.py first, then re-run create_db.py")


if __name__ == "__main__":
    main()
