#!/usr/bin/env python3
"""Find latest ANOFM CSV, dedup against existing anofm.jobs, import new emails only.
Mark source as ANOFM_FRESH_YYYYMMDD.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/anofm_fresh_import.py
"""
import csv, glob, os, sys
from pathlib import Path
from datetime import datetime, date

import psycopg2

DB_PARAMS = dict(dbname="anofm", user="tudor", password="tudor", host="localhost")
ANOFM_DIR = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/DOCKER/PROGRAMS/"
SOURCE_TAG = f"ANOFM_FRESH_{date.today().strftime('%Y%m%d')}"


def find_latest_csv():
    """Find the most recent ANOFM CSV file."""
    csvs = glob.glob(os.path.join(ANOFM_DIR, "*.csv"))
    if not csvs:
        print(f"No CSVs found in {ANOFM_DIR}")
        return None
    latest = max(csvs, key=os.path.getmtime)
    print(f"Latest CSV: {latest} ({os.path.getsize(latest):,} bytes)")
    return latest


def get_existing_emails(conn):
    """Get all existing emails from anofm.jobs."""
    cur = conn.cursor()
    cur.execute("SELECT LOWER(email) FROM jobs WHERE email IS NOT NULL AND email != ''")
    existing = {r[0].strip() for r in cur.fetchall()}
    print(f"Existing emails in DB: {len(existing):,}")
    return existing


def parse_csv(filepath):
    """Read ANOFM CSV and extract rows with emails."""
    rows = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            # Find email column (could be 'email', 'Email', 'EMAIL', 'e-mail')
            email_col = None
            for col in fields:
                if col.lower().replace("-", "").replace("_", "") in ("email", "emailaddress", "mail"):
                    email_col = col
                    break
            if not email_col:
                print(f"No email column found in {fields}")
                return []

            for row in reader:
                email = (row.get(email_col, "") or "").strip().lower()
                if email and "@" in email:
                    try:
                        email.encode("ascii")
                    except UnicodeEncodeError:
                        continue  # Skip unicode emails
                    row["_email"] = email
                    rows.append(row)
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return rows


def import_new_rows(conn, new_rows, fields):
    """Insert new rows into anofm.jobs."""
    if not new_rows:
        return 0

    cur = conn.cursor()
    inserted = 0
    # Map common ANOFM fields to DB columns
    col_map = {
        "company": ["company", "companie", "denumire", "angajator", "firma"],
        "sector": ["sector", "domeniu", "categorie"],
        "location": ["location", "localitate", "judet", "oras", "adresa"],
        "phone": ["phone", "telefon", "tel"],
        "position": ["position", "pozitie", "meserie", "functie", "job"],
    }

    for row in new_rows:
        email = row["_email"]
        # Extract mapped values
        vals = {}
        for db_col, csv_names in col_map.items():
            for cn in csv_names:
                for f in fields:
                    if f.lower().replace(" ", "").replace("_", "") == cn:
                        v = row.get(f, "").strip()
                        if v:
                            vals[db_col] = v
                            break
                if db_col in vals:
                    break

        try:
            cur.execute(
                "INSERT INTO jobs (email, company, sector, location, phone, position, "
                "source, campaign_status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, NULL) "
                "ON CONFLICT DO NOTHING",
                (
                    email,
                    vals.get("company", ""),
                    vals.get("sector", ""),
                    vals.get("location", ""),
                    vals.get("phone", ""),
                    vals.get("position", ""),
                    SOURCE_TAG,
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"  Insert error for {email}: {e}")
            conn.rollback()
            continue

    conn.commit()
    return inserted


def main():
    # Find latest CSV
    csv_path = find_latest_csv()
    if not csv_path:
        sys.exit(1)

    # Parse CSV
    rows = parse_csv(csv_path)
    print(f"Rows with valid email: {len(rows):,}")
    if not rows:
        print("No rows to import.")
        return

    # Connect to DB
    try:
        conn = psycopg2.connect(**DB_PARAMS)
    except Exception as e:
        print(f"DB connection error: {e}")
        sys.exit(1)

    # Get existing emails
    existing = get_existing_emails(conn)

    # Filter new
    new_rows = [r for r in rows if r["_email"] not in existing]
    print(f"New emails (not in DB): {len(new_rows):,}")

    if not new_rows:
        print("No new emails to import.")
        conn.close()
        return

    # Get field names from CSV
    fields = [k for k in rows[0].keys() if k != "_email"]

    # Dry-run check
    if "--dry-run" in sys.argv:
        print(f"DRY RUN: Would import {len(new_rows)} new emails. Source: {SOURCE_TAG}")
        for r in new_rows[:10]:
            print(f"  {r['_email']}")
        if len(new_rows) > 10:
            print(f"  ... and {len(new_rows) - 10} more")
        conn.close()
        return

    # Import
    inserted = import_new_rows(conn, new_rows, fields)
    conn.close()

    print(f"\n{'='*50}")
    print(f"ANOFM FRESH IMPORT COMPLETE")
    print(f"{'='*50}")
    print(f"Source:     {os.path.basename(csv_path)}")
    print(f"Tag:        {SOURCE_TAG}")
    print(f"Total rows: {len(rows):,}")
    print(f"New:        {len(new_rows):,}")
    print(f"Inserted:   {inserted:,}")
    print(f"Skipped:    {len(rows) - len(new_rows):,} (already in DB)")


if __name__ == "__main__":
    main()
