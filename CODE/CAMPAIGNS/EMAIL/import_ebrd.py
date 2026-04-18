#!/usr/bin/env python3
"""Import EBRD PSD scraped data into interjob_master PostgreSQL."""
import csv, psycopg2

CSV = "/opt/ACTIVE/SCRAPERS/EBRD/data/ebrd_psd_details.csv"
DB = dict(dbname="interjob_master", user="tudor", password="tudor", host="localhost")

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Create table
cur.execute("""
CREATE TABLE IF NOT EXISTS ebrd_projects (
    psd_id INTEGER PRIMARY KEY,
    project_id TEXT,
    title TEXT,
    country TEXT,
    sector TEXT,
    notice_type TEXT,
    status TEXT,
    ebrd_finance TEXT,
    finance_desc TEXT,
    total_cost TEXT,
    overview TEXT,
    contact_name TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    contact_website TEXT,
    contact_address TEXT,
    company_contact_raw TEXT,
    url TEXT,
    imported_at TIMESTAMP DEFAULT NOW()
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_ebrd_country ON ebrd_projects(country)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_ebrd_sector ON ebrd_projects(sector)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_ebrd_email ON ebrd_projects(contact_email) WHERE contact_email IS NOT NULL AND contact_email != ''")
conn.commit()

# Import CSV
with open(CSV, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    imported = 0
    skipped = 0
    for row in reader:
        try:
            psd_id = int(row["psd_id"])
        except (ValueError, KeyError):
            skipped += 1
            continue
        try:
            cur.execute("""
                INSERT INTO ebrd_projects (psd_id, project_id, title, country, sector, notice_type,
                    status, ebrd_finance, finance_desc, total_cost, overview,
                    contact_name, contact_email, contact_phone, contact_website,
                    contact_address, company_contact_raw, url)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (psd_id) DO NOTHING
            """, (psd_id, row.get("project_id",""), row.get("title",""),
                  row.get("country",""), row.get("sector",""), row.get("notice_type",""),
                  row.get("status",""), row.get("ebrd_finance",""), row.get("finance_desc",""),
                  row.get("total_cost",""), row.get("overview",""),
                  row.get("contact_name",""), row.get("contact_email",""),
                  row.get("contact_phone",""), row.get("contact_website",""),
                  row.get("contact_address",""), row.get("company_contact_raw",""),
                  row.get("url","")))
            imported += 1
        except Exception as e:
            print(f"Error psd_id {psd_id}: {e}")
            skipped += 1
            conn.rollback()
            continue

conn.commit()

# Stats
cur.execute("SELECT COUNT(*) FROM ebrd_projects")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM ebrd_projects WHERE contact_email != '' AND contact_email IS NOT NULL")
with_email = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM ebrd_projects WHERE country = 'Romania'")
romania = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT country) FROM ebrd_projects")
countries = cur.fetchone()[0]

print(f"Imported: {imported}, Skipped: {skipped}")
print(f"Total in DB: {total}")
print(f"With email: {with_email}")
print(f"Romania: {romania}")
print(f"Countries: {countries}")

# Top countries
cur.execute("SELECT country, COUNT(*) c FROM ebrd_projects GROUP BY country ORDER BY c DESC LIMIT 10")
print("\nTop countries:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Romania with emails
cur.execute("SELECT psd_id, title, contact_name, contact_email FROM ebrd_projects WHERE country='Romania' AND contact_email != '' AND contact_email IS NOT NULL ORDER BY psd_id")
rows = cur.fetchall()
print(f"\nRomania with emails ({len(rows)}):")
for r in rows:
    print(f"  #{r[0]}: {r[1][:60]} | {r[2]} | {r[3]}")

cur.close()
conn.close()
