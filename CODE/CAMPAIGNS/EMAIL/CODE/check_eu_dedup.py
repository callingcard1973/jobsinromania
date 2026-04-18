import psycopg2

conn = psycopg2.connect(dbname="european_funds", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()

cur.execute("SELECT count(*), count(DISTINCT LOWER(email)) FROM proiecte WHERE email IS NOT NULL AND email != ''")
pt, pu = cur.fetchone()
print(f"Proiecte: {pt} rows, {pu} unique emails ({pt-pu} duplicates)")

cur.execute("SELECT count(*), count(DISTINCT LOWER(email)) FROM beneficiari_privati WHERE email IS NOT NULL AND email != ''")
at, au = cur.fetchone()
print(f"Achizitii: {at} rows, {au} unique emails ({at-au} duplicates)")

# Overlap between the two
cur.execute("""SELECT count(DISTINCT LOWER(p.email)) FROM proiecte p
    JOIN beneficiari_privati b ON LOWER(p.email) = LOWER(b.email)
    WHERE p.email IS NOT NULL AND p.email != '' AND b.email IS NOT NULL AND b.email != ''""")
overlap = cur.fetchone()[0]
print(f"\nOverlap proiecte<->achizitii: {overlap}")
conn.close()

# Overlap with ANOFM
conn2 = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur2 = conn2.cursor()
cur2.execute("SELECT DISTINCT LOWER(email) FROM jobs WHERE email IS NOT NULL AND email != ''")
anofm = {r[0] for r in cur2.fetchall()}
conn2.close()

conn3 = psycopg2.connect(dbname="european_funds", user="tudor", host="localhost", password="tudor")
cur3 = conn3.cursor()
cur3.execute("SELECT DISTINCT LOWER(email) FROM proiecte WHERE email IS NOT NULL AND email != ''")
proiecte_emails = {r[0] for r in cur3.fetchall()}
cur3.execute("SELECT DISTINCT LOWER(email) FROM beneficiari_privati WHERE email IS NOT NULL AND email != ''")
achizitii_emails = {r[0] for r in cur3.fetchall()}
conn3.close()

print(f"Overlap proiecte<->ANOFM: {len(proiecte_emails & anofm)}")
print(f"Overlap achizitii<->ANOFM: {len(achizitii_emails & anofm)}")
print(f"Overlap all 3: {len(proiecte_emails & achizitii_emails & anofm)}")

# Also check romania_emails
conn4 = psycopg2.connect(dbname="romania_emails", user="tudor", host="localhost", password="tudor")
cur4 = conn4.cursor()
cur4.execute("SELECT DISTINCT LOWER(email) FROM contacts WHERE email IS NOT NULL AND email != ''")
ro = {r[0] for r in cur4.fetchall()}
conn4.close()

print(f"\nOverlap proiecte<->romania_emails: {len(proiecte_emails & ro)}")
print(f"Overlap achizitii<->romania_emails: {len(achizitii_emails & ro)}")

total_unique = len(proiecte_emails | achizitii_emails)
print(f"\nTotal EU unique (proiecte+achizitii deduped): {total_unique}")
print(f"Same person gets 2 emails if both campaigns run: {overlap}")
