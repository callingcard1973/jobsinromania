#!/usr/bin/env python3
"""
Export jobs from database to catalog files on Desktop
Saves to: C:/Users/apami/OneDrive/Desktop/CATALOG JOBS
Formats: CSV and JSON
"""

import sys, os
import json
import csv
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from db_client import get_conn
except ImportError:
    print("[ERROR] Cannot import db_client. Ensure you're in D:/AUTOMATION directory.")
    sys.exit(1)

# Output directory
CATALOG_DIR = Path("C:/Users/apami/OneDrive/Desktop/CATALOG JOBS")
CATALOG_DIR.mkdir(parents=True, exist_ok=True)

def export_to_csv():
    """Export jobs to CSV file"""
    conn = get_conn()
    if not conn:
        print("[ERROR] Cannot connect to database")
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT job_id, domain, company, title, salary, location, description,
                   deployed, date_posted, valid_through, created_at
            FROM job_listings
            ORDER BY domain, company
        """)

        rows = cur.fetchall()

        if not rows:
            print("[WARNING] No jobs found in database")
            conn.close()
            return False

        # Write CSV
        csv_file = CATALOG_DIR / f"jobs_catalog_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Job ID', 'Domain', 'Company', 'Title', 'Salary', 'Location',
                           'Description', 'Deployed', 'Posted Date', 'Valid Through', 'Created'])
            for row in rows:
                writer.writerow(row)

        print(f"[OK] CSV exported: {csv_file}")
        print(f"     {len(rows)} jobs written")

        # Also write latest symlink for easy access
        latest_csv = CATALOG_DIR / "jobs_catalog_LATEST.csv"
        with open(latest_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Job ID', 'Domain', 'Company', 'Title', 'Salary', 'Location',
                           'Description', 'Deployed', 'Posted Date', 'Valid Through', 'Created'])
            for row in rows:
                writer.writerow(row)

        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] CSV export failed: {e}")
        conn.close()
        return False

def export_to_json():
    """Export jobs to JSON file"""
    conn = get_conn()
    if not conn:
        print("[ERROR] Cannot connect to database")
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT job_id, domain, company, title, salary, location, description,
                   deployed, date_posted, valid_through, created_at
            FROM job_listings
            ORDER BY domain, company
        """)

        rows = cur.fetchall()

        if not rows:
            print("[WARNING] No jobs found in database")
            conn.close()
            return False

        # Build job list
        jobs = []
        for row in rows:
            job = {
                'job_id': row[0],
                'domain': row[1],
                'company': row[2],
                'title': row[3],
                'salary': row[4],
                'location': row[5],
                'description': row[6],
                'deployed': row[7],
                'date_posted': row[8].isoformat() if row[8] else None,
                'valid_through': row[9].isoformat() if row[9] else None,
                'created_at': row[10].isoformat() if row[10] else None,
            }
            jobs.append(job)

        # Write JSON
        json_file = CATALOG_DIR / f"jobs_catalog_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_jobs': len(jobs),
                'jobs': jobs
            }, f, indent=2)

        print(f"[OK] JSON exported: {json_file}")
        print(f"     {len(jobs)} jobs written")

        # Also write latest version
        latest_json = CATALOG_DIR / "jobs_catalog_LATEST.json"
        with open(latest_json, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_jobs': len(jobs),
                'jobs': jobs
            }, f, indent=2)

        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] JSON export failed: {e}")
        conn.close()
        return False

def main():
    """Export jobs to both formats"""
    print(f"[INFO] Exporting jobs catalog to: {CATALOG_DIR}")
    print("=" * 70)

    csv_ok = export_to_csv()
    json_ok = export_to_json()

    print("=" * 70)

    if csv_ok or json_ok:
        print("[OK] Catalog export complete")
        print(f"[INFO] Latest files: jobs_catalog_LATEST.csv, jobs_catalog_LATEST.json")
        return 0
    else:
        print("[ERROR] Catalog export failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
