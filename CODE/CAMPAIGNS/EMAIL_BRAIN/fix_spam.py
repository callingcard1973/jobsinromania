"""Fix: don't DNC interested leads, add OWN emails, remove wrong DNC."""
import psycopg2

# 1. Remove wrong DNC entries
conn = psycopg2.connect(host="/var/run/postgresql",
    dbname="interjob_master", user="tudor", password="scraper123")
cur = conn.cursor()
cur.execute("""DELETE FROM master_dnc WHERE source='deleted'
    AND email IN (SELECT sender_email FROM campaign_responses
    WHERE category IN ('INTERESTED','REPLY'))
    RETURNING email""")
removed = cur.fetchall()
conn.commit()
print(f"Removed {len(removed)} interested leads from DNC:")
for r in removed:
    print(f"  {r[0]}")

# 2. Add INTERESTED check to trash_to_dnc
f = "/opt/ACTIVE/INFRA/SKILLS/trash_to_dnc.py"
content = open(f).read()
if "INTERESTED" not in content:
    old = "            subject = decode_subj(msg)"
    new = """            # Skip if sender was INTERESTED (Tudor replied, then cleaned inbox)
            try:
                ic = psycopg2.connect(host="/var/run/postgresql",
                    dbname="interjob_master", user="tudor", password="scraper123")
                icc = ic.cursor()
                icc.execute("SELECT COUNT(*) FROM campaign_responses WHERE sender_email=%s AND category IN ('INTERESTED','REPLY')", (sender,))
                if icc.fetchone()[0] > 0:
                    icc.close(); ic.close()
                    continue
                icc.close(); ic.close()
            except Exception:
                pass
            subject = decode_subj(msg)"""
    content = content.replace(old, new, 1)
    open(f, "w").write(content)
    print("Added INTERESTED skip to trash_to_dnc")

# 3. Fix gmail_label_actions OWN_DOMAINS
f2 = "/opt/ACTIVE/INFRA/SKILLS/gmail_label_actions.py"
content2 = open(f2).read()
if "manpowerdristor" not in content2:
    content2 = content2.replace(
        '"seicarescu.com"}',
        '"seicarescu.com", "gmail.com"}')
    open(f2, "w").write(content2)
    print("Fixed OWN_DOMAINS in gmail_label_actions")

# 4. Remove manpowerdristor solonet drafts
cur.execute("DELETE FROM solonet_orders WHERE contact_email LIKE '%manpowerdristor%' OR contact_email LIKE '%manpower.dristor%' RETURNING company")
removed2 = cur.fetchall()
conn.commit()
print(f"Removed {len(removed2)} self-referencing solonet drafts")

cur.close()
conn.close()
print("Done")
