#!/usr/bin/env python3
"""Dedup RO construction contacts from romania_emails + anofm + TED winners. Save to CSV."""
import psycopg2, csv

emails = {}  # email -> (row, source)
dnc = set()

# Source 1: romania_emails (CAEN 41-43)
conn = psycopg2.connect(dbname="romania_emails", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()
cur.execute("""SELECT DISTINCT ON (LOWER(email)) email, company_name, city, contact_name, phone, sector_name
    FROM contacts WHERE email IS NOT NULL AND email != ''
    AND (caen LIKE '41%%' OR caen LIKE '42%%' OR caen LIKE '43%%' OR sector_name ILIKE '%%construct%%')
    ORDER BY LOWER(email), id""")
for r in cur.fetchall():
    e = r[0].lower().strip()
    if e not in emails:
        emails[e] = (list(r), "romania_emails")
conn.close()
src1 = len(emails)

# Source 2: anofm (construction jobs)
conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()
cur.execute("""SELECT DISTINCT ON (LOWER(email)) email, company_name, city, contact_person, phone, sector
    FROM jobs WHERE email IS NOT NULL AND email != ''
    AND (sector ILIKE '%%construct%%' OR occupation ILIKE '%%construct%%'
    OR occupation ILIKE '%%zidar%%' OR occupation ILIKE '%%fierari%%'
    OR occupation ILIKE '%%dulgh%%' OR occupation ILIKE '%%instal%%')
    ORDER BY LOWER(email), id""")
for r in cur.fetchall():
    e = r[0].lower().strip()
    if e not in emails:
        emails[e] = (list(r), "anofm_construction")
conn.close()
src2 = len(emails) - src1

# Source 3: TED winners matched to emails
conn = psycopg2.connect(dbname="interjob_master", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()
cur.execute("""SELECT DISTINCT winner_name FROM tenders
    WHERE country = 'RO' AND cpv_code LIKE '45%%' AND winner_name IS NOT NULL AND winner_name != ''""")
winners = set()
for r in cur.fetchall():
    for name in r[0].split("---"):
        name = name.strip()
        if name and len(name) > 3:
            winners.add(name.upper())
conn.close()

# Match winners against both DBs
for db, tbl, cols in [
    ("romania_emails", "contacts", "email, company_name, city, contact_name, phone, sector_name"),
    ("anofm", "jobs", "email, company_name, city, contact_person, phone, sector"),
]:
    conn = psycopg2.connect(dbname=db, user="tudor", host="localhost", password="tudor")
    cur = conn.cursor()
    cur.execute(f"SELECT DISTINCT ON (LOWER(email)) {cols} FROM {tbl} WHERE email IS NOT NULL AND email != '' ORDER BY LOWER(email), id")
    for r in cur.fetchall():
        e = r[0].lower().strip()
        if e not in emails and r[1] and r[1].upper() in winners:
            emails[e] = (list(r), "ted_winner")
    conn.close()
src3 = len(emails) - src1 - src2

# Remove DNC
conn = psycopg2.connect(dbname="interjob_master", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()
cur.execute("SELECT LOWER(email) FROM dnc_list")
dnc = {r[0] for r in cur.fetchall()}
conn.close()

clean = {e: v for e, v in emails.items() if e not in dnc}

print(f"romania_emails: {src1}")
print(f"anofm (new): {src2}")
print(f"TED winners (new): {src3}")
print(f"Total unique: {len(emails)}")
print(f"DNC removed: {len(emails) - len(clean)}")
print(f"Clean: {len(clean)}")

with open("/tmp/ro_construction_deduped.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["email", "company_name", "city", "contact_name", "phone", "sector", "source"])
    for e, (row, src) in clean.items():
        w.writerow(list(row) + [src])
print(f"Saved to /tmp/ro_construction_deduped.csv")
