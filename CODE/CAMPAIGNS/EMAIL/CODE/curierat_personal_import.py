#!/usr/bin/env python3
"""Import curierat personal emails into anofm DB as a separate campaign table."""
import psycopg2, csv

PERSONAL = {"gmail.com","yahoo.com","yahoo.ro","hotmail.com","hotmail.ro","outlook.com",
    "live.com","icloud.com","ymail.com","aol.com","mail.ru","protonmail.com",
    "web.de","gmx.de","gmx.net","t-online.de","orange.fr","free.fr","wp.pl","o2.pl"}

conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()

# Create table
cur.execute("""CREATE TABLE IF NOT EXISTS curierat_personal (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    company_name TEXT,
    city TEXT,
    contact_name TEXT,
    phone TEXT,
    sector TEXT,
    campaign_status VARCHAR(20),
    last_contacted TIMESTAMP
)""")
cur.execute("TRUNCATE curierat_personal")

# Import only personal emails
with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/ro_curierat_2751.csv") as f:
    added = 0
    for r in csv.DictReader(f):
        email = r.get("email","").lower().strip()
        if not email: continue
        domain = email.split("@")[1] if "@" in email else ""
        if domain not in PERSONAL: continue
        cur.execute("""INSERT INTO curierat_personal(email,company_name,city,contact_name,phone,sector)
            VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(email) DO NOTHING""",
            (email, r.get("company_name",""), r.get("city",""), r.get("contact_name",""),
             r.get("phone",""), r.get("sector","")))
        added += cur.rowcount

# Remove DNC
cur.execute("""DELETE FROM curierat_personal WHERE LOWER(email) IN (SELECT LOWER(email) FROM dnc)""")
removed = cur.rowcount

conn.commit()
cur.execute("SELECT count(*) FROM curierat_personal")
total = cur.fetchone()[0]
conn.close()
print(f"Imported {added} personal emails, removed {removed} DNC, total: {total}")
