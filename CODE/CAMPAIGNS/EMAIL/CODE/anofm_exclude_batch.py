#!/usr/bin/env python3
"""Batch exclude sector campaign emails from ANOFM DB."""
import psycopg2, csv, glob

conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()

# Collect all sector emails
sector_emails = set()
base = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA"
for f in sorted(glob.glob(f"{base}/ro_*.csv")):
    with open(f) as fh:
        for r in csv.DictReader(fh):
            if r.get("email"):
                sector_emails.add(r["email"].lower().strip())
print(f"Sector emails: {len(sector_emails)}")

# Batch update using IN clause (chunks of 1000)
marked = 0
emails = list(sector_emails)
for i in range(0, len(emails), 1000):
    chunk = emails[i:i+1000]
    placeholders = ",".join(["%s"] * len(chunk))
    cur.execute(f"UPDATE jobs SET campaign_status = 'reserved_sector' WHERE LOWER(email) IN ({placeholders}) AND (campaign_status IS NULL OR campaign_status = '')", chunk)
    marked += cur.rowcount

conn.commit()

cur.execute("SELECT campaign_status, count(*) FROM jobs GROUP BY campaign_status")
print("\nStatus:")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL':20s} {r[1]:>7}")

cur.execute("SELECT count(DISTINCT LOWER(email)) FROM jobs WHERE email IS NOT NULL AND email != '' AND (campaign_status IS NULL OR campaign_status = '')")
remaining = cur.fetchone()[0]
print(f"\nMarked: {marked} rows as reserved_sector")
print(f"ANOFM remaining unique emails: {remaining}")
conn.close()
