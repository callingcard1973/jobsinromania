"""Patch all DNC writers to use master_dnc table."""
import re

# 1. trash_to_dnc.py — write to master_dnc instead of all 29 tables
f = "/opt/ACTIVE/INFRA/SKILLS/trash_to_dnc.py"
content = open(f).read()

# Find the add_dnc function and replace entirely
old_start = "def add_dnc(sender, subject):"
old_end = "    return True"

# Find the function boundaries
lines = content.split('\n')
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if line.startswith("def add_dnc("):
        start_idx = i
    if start_idx and i > start_idx and line.strip() == "return True":
        end_idx = i
        break

if start_idx and end_idx:
    new_func = '''def add_dnc(sender, subject):
    """Add to master_dnc + blacklist.txt backup."""
    expires = (datetime.now() + timedelta(days=DNC_MONTHS * 30)).strftime("%Y-%m-%d")
    reason = f"Deleted by Tudor {datetime.now().strftime('%Y-%m-%d')}. Subj: {subject[:80]}"
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""INSERT INTO master_dnc (email, reason, source, expires_at)
            VALUES (%s, %s, 'deleted', %s)
            ON CONFLICT (email) DO UPDATE SET reason=EXCLUDED.reason, expires_at=EXCLUDED.expires_at""",
            (sender, reason, expires))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"master_dnc error: {e}")
    # Also write to blacklist.txt as backup
    add_to_blacklist(sender)
    return True'''
    lines = lines[:start_idx] + new_func.split('\n') + lines[end_idx+1:]
    open(f, 'w').write('\n'.join(lines))
    print("trash_to_dnc.py: patched to use master_dnc")

# 2. bounce_cleaner.py — write to master_dnc
f2 = "/opt/ACTIVE/INFRA/SKILLS/bounce_cleaner.py"
content2 = open(f2).read()

old_db = """def clean_db_tables(blacklist):
    \"\"\"Add bounced emails to DNC tables in PostgreSQL.\"\"\"
    added = 0
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        # Add to norway_virgil DNC
        for e in blacklist:
            cur.execute("INSERT INTO norway_virgil_dnc (email, reason) VALUES (%s, 'bounce') ON CONFLICT DO NOTHING", (e,))
            added += cur.rowcount
        # Mark in master_emails
        bl_list = list(blacklist)[:5000]
        if bl_list:
            cur.execute("UPDATE master_emails SET is_bounced=TRUE WHERE LOWER(email) IN %s AND is_bounced IS NOT TRUE",
                (tuple(bl_list),))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"DB error: {e}")
    return added"""

new_db = """def clean_db_tables(blacklist):
    \"\"\"Add bounced emails to master_dnc.\"\"\"
    added = 0
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        for e in blacklist:
            cur.execute("INSERT INTO master_dnc (email, reason, source) VALUES (%s, 'bounce', 'bounce_cleaner') ON CONFLICT DO NOTHING", (e,))
            added += cur.rowcount
        # Also mark in master_emails
        bl_list = list(blacklist)[:5000]
        if bl_list:
            cur.execute("UPDATE master_emails SET is_bounced=TRUE WHERE LOWER(email) IN %s AND is_bounced IS NOT TRUE",
                (tuple(bl_list),))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"DB error: {e}")
    return added"""

if old_db in content2:
    content2 = content2.replace(old_db, new_db)
    open(f2, 'w').write(content2)
    print("bounce_cleaner.py: patched to use master_dnc")
else:
    print("bounce_cleaner.py: pattern not found, check manually")

# 3. email_executor.py — write to master_dnc
f3 = "/opt/ACTIVE/INFRA/SKILLS/email_executor.py"
content3 = open(f3).read()
if "email_sender" in content3 and "master_dnc" not in content3:
    content3 = content3.replace(
        'dbname="email_sender", user="tudor")',
        'dbname="interjob_master", user="tudor", password="scraper123")')
    content3 = content3.replace(
        "INSERT INTO dnc (email, reason, expires_at)",
        "INSERT INTO master_dnc (email, reason, expires_at, source) ")
    content3 = content3.replace(
        "VALUES (%s, %s, %s) ON CONFLICT (email)",
        "VALUES (%s, %s, %s, 'manual') ON CONFLICT (email)")
    open(f3, 'w').write(content3)
    print("email_executor.py: patched to use master_dnc")

# 4. Create daily backup cron script
backup_script = """#!/bin/bash
# Daily backup of master_dnc to CSV
psql -d interjob_master -c "COPY master_dnc TO STDOUT WITH CSV HEADER" > /opt/ACTIVE/INFRA/BACKUPS/master_dnc.csv 2>/dev/null
"""
with open("/opt/ACTIVE/INFRA/SKILLS/backup_master_dnc.sh", "w") as f:
    f.write(backup_script)
import os
os.chmod("/opt/ACTIVE/INFRA/SKILLS/backup_master_dnc.sh", 0o755)
print("backup_master_dnc.sh: created")

print("\nDone. All writers use master_dnc now.")
