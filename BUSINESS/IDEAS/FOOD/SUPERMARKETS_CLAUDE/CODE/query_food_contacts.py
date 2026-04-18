#!/usr/bin/env python3
"""Query interjob_master for food distribution contacts.

Usage:
    python query_food_contacts.py --category supermarket --email-only
    python query_food_contacts.py --county Bucharest --output results.csv
    python query_food_contacts.py --extract-all --output masterdb_food_companies.csv
"""

import csv
import sys

try:
    import psycopg2
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

from shared_utils import DB_MASTER as DB

CATEGORIES = {
    "supermarket": "sector ILIKE '%retail%' OR sector ILIKE '%52%'",
    "distributor": "sector ILIKE '%wholesale%' OR sector LIKE '51%'",
    "engros": "sector ILIKE '%wholesale%' OR sector LIKE '51%'",
    "processor": "sector LIKE '15%' OR sector ILIKE '%food%'",
    "dairy": "sector ILIKE '%dairy%' OR sector ILIKE '%lact%' OR sector ILIKE '%105%'",
    "meat": "sector ILIKE '%meat%' OR sector ILIKE '%abat%' OR sector ILIKE '%151%'",
    "logistics": "sector ILIKE '%transport%' OR sector ILIKE '%logist%' OR sector LIKE '60%'",
    "horeca": "sector ILIKE '%hotel%' OR sector ILIKE '%restaurant%' OR sector LIKE '55%'",
    "agriculture": "sector ILIKE '%agric%' OR sector LIKE '01%' OR sector LIKE '02%'",
    "cold-storage": "sector ILIKE '%cold%' OR sector ILIKE '%refriger%' OR sector ILIKE '%frigorific%'",
}

COLS = "name, cui, city, address, phone, email, website, sector, sector_name"


def query(category=None, county=None, email_only=False, output=None):
    conditions = ["country = 'RO'"]
    params = []
    if category and category in CATEGORIES:
        conditions.append(f"({CATEGORIES[category]})")
    if county:
        conditions.append("LOWER(city) LIKE %s")
        params.append(f"%{county.lower()}%")
    if email_only:
        conditions.append("email IS NOT NULL AND email != ''")

    sql = f"SELECT {COLS} FROM companies WHERE " + " AND ".join(conditions)
    sql += " ORDER BY name LIMIT 50000"

    conn = psycopg2.connect(**DB)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description]
    finally:
        conn.close()

    if output:
        with open(output, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)
        print(f"Exported {len(rows)} rows to {output}")
    else:
        print(f"Found {len(rows)} records")
        for row in rows[:20]:
            print(f"  {row[0]} | {row[5] or '-'} | {row[2] or '-'}")
        if len(rows) > 20:
            print(f"  ... and {len(rows) - 20} more")


def extract_all(output):
    """Extract all food-related RO companies."""
    sql = f"""SELECT {COLS} FROM companies
        WHERE country = 'RO'
        AND (sector ILIKE '%retail%' OR sector ILIKE '%agric%'
             OR sector LIKE '15%' OR sector LIKE '51%' OR sector LIKE '52%'
             OR sector ILIKE '%hotel%' OR sector ILIKE '%restaurant%'
             OR sector ILIKE '%food%' OR sector ILIKE '%transport%'
             OR sector LIKE '55%' OR sector LIKE '01%')
        AND email IS NOT NULL AND email != ''
        ORDER BY name"""
    conn = psycopg2.connect(**DB)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description]
    finally:
        conn.close()

    with open(output, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    print(f"Extracted {len(rows)} food companies to {output}")


def main():
    args = sys.argv[1:]
    category = county = output = None
    email_only = False
    do_extract = False

    i = 0
    while i < len(args):
        if args[i] == "--category" and i + 1 < len(args):
            category = args[i + 1]; i += 2
        elif args[i] == "--county" and i + 1 < len(args):
            county = args[i + 1]; i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output = args[i + 1]; i += 2
        elif args[i] == "--email-only":
            email_only = True; i += 1
        elif args[i] == "--extract-all":
            do_extract = True; i += 1
        else:
            i += 1

    if do_extract:
        extract_all(output or "masterdb_food_companies.csv")
    elif category or county or email_only:
        query(category, county, email_only, output)
    else:
        print("Usage:")
        print("  --category supermarket|distributor|engros|processor|dairy|meat|logistics|horeca|agriculture|cold-storage")
        print("  --county Bucharest|Cluj|...")
        print("  --email-only")
        print("  --output file.csv")
        print("  --extract-all  (extract all food-related RO companies)")


if __name__ == "__main__":
    main()
