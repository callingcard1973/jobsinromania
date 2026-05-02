#!/usr/bin/env python3
"""Exclude sector campaign emails from ANOFM DB. Mark them so send_campaign skips them."""
import psycopg2, csv, glob, os

RO_BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA"

# Collect all sector campaign emails
sector_emails = set()
for f in sorted(glob.glob(f"{RO_BASE}/ro_*.csv")):
    with open(f) as fh:
        for r in csv.DictReader(fh):
            if r.get("email"):
                sector_emails.add(r["email"].lower().strip())
    print(f"  {os.path.basename(f):40s} {len(sector_emails):>6} cumulative")

print(f"\nTotal sector emails to exclude: {len(sector_emails)}")

# Mark in ANOFM DB as 'reserved_sector'
conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()

# First check current state
cur.execute("SELECT campaign_status, count(*) FROM jobs GROUP BY campaign_status")
print("\nBefore:")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL':20s} {r[1]:>7}")

# Mark sector emails
marked = 0
for email in sector_emails:
    cur.execute("UPDATE jobs SET campaign_status = 'reserved_sector' WHERE LOWER(email) = %s AND (campaign_status IS NULL OR campaign_status = '')", (email,))
    marked += cur.rowcount
conn.commit()

# Verify
cur.execute("SELECT campaign_status, count(*) FROM jobs GROUP BY campaign_status")
print(f"\nMarked {marked} rows as reserved_sector")
print("\nAfter:")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL':20s} {r[1]:>7}")

# How many left for ANOFM
cur.execute("SELECT count(DISTINCT LOWER(email)) FROM jobs WHERE email IS NOT NULL AND email != '' AND (campaign_status IS NULL OR campaign_status = '')")
remaining = cur.fetchone()[0]
print(f"\nANOFM remaining (not reserved, not sent, not DNC): {remaining}")
conn.close()
