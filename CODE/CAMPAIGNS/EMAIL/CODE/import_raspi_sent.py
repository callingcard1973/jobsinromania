import psycopg2
conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()
with open("/tmp/raspi_sent_emails.txt") as f:
    emails = [l.strip() for l in f if l.strip()]
added = 0
for e in emails:
    cur.execute("INSERT INTO send_log(email, campaign, sector) VALUES(%s, %s, %s)", (e, "ANOFM", "RASPI_IMPORT"))
    added += 1
conn.commit()
print(f"Imported {added}/{len(emails)} raspi sent emails to anofm.send_log")
cur.execute("SELECT count(*) FROM send_log")
print(f"Total send_log: {cur.fetchone()[0]}")
conn.close()
