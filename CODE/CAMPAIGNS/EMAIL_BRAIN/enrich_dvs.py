import imaplib, email, psycopg2

env = {}
with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
    for l in f:
        if "=" in l and not l.startswith("#"):
            k, v = l.strip().split("=", 1)
            env[k] = v.strip().strip('"')

# Get email content
imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
imap.login("manpower.dristor@gmail.com", env["GMAIL_MANPOWERDRISTOR_APP_PASSWORD"])
imap.select("INBOX")
_, nums = imap.search(None, '(FROM "dvsinvestgrup")')
if nums[0]:
    _, data = imap.fetch(nums[0].split()[-1], "(RFC822)")
    msg = email.message_from_bytes(data[0][1])
    print("Subject:", msg.get("Subject"))
    print("From:", msg.get("From"))
    print("Date:", msg.get("Date"))
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            print("Body:", part.get_payload(decode=True).decode(errors="replace")[:800])
            break
else:
    # Try SOLONET folder
    imap.select("SOLONET")
    _, nums = imap.search(None, '(FROM "dvsinvestgrup")')
    if nums[0]:
        _, data = imap.fetch(nums[0].split()[-1], "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        print("Subject:", msg.get("Subject"))
        print("Body:", msg.walk().__next__().get_payload(decode=True).decode(errors="replace")[:500])
imap.logout()

# DB enrichment
conn = psycopg2.connect(host="/var/run/postgresql", dbname="interjob_master",
    user="tudor", password="scraper123")
cur = conn.cursor()
cur.execute("SELECT name, city, phone, email FROM companies WHERE LOWER(name) LIKE '%dvs invest%' OR LOWER(email) LIKE '%dvsinvest%' LIMIT 5")
for r in cur.fetchall():
    print(f"DB match: {r[0]} | {r[1]} | {r[2]} | {r[3]}")
cur.close(); conn.close()

# Send log
conn2 = psycopg2.connect(host="/var/run/postgresql", dbname="email_sender", user="tudor")
cur2 = conn2.cursor()
cur2.execute("SELECT campaign, subject FROM send_log WHERE LOWER(email)='dvsinvestgrup@gmail.com'")
for r in cur2.fetchall():
    print(f"Campaign: {r[0]} | Subject: {r[1]}")
cur2.close(); conn2.close()
