#!/usr/bin/env python3
"""Check ANOFM emails overlap with other campaign CSVs and DBs."""
import psycopg2, csv, glob, os

# Get all ANOFM emails
conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()
cur.execute("SELECT DISTINCT LOWER(email) FROM jobs WHERE email IS NOT NULL AND email != ''")
anofm_emails = {r[0] for r in cur.fetchall()}
print(f"ANOFM unique emails: {len(anofm_emails)}")

# Check DNC
cur.execute("SELECT LOWER(email) FROM dnc")
dnc = {r[0] for r in cur.fetchall()}
print(f"ANOFM DNC: {len(dnc)}")
overlap_dnc = anofm_emails & dnc
print(f"ANOFM in DNC: {len(overlap_dnc)}")

# Check send_log
cur.execute("SELECT DISTINCT LOWER(email) FROM send_log")
sent = {r[0] for r in cur.fetchall()}
print(f"ANOFM already sent: {len(sent)}")
conn.close()

# Check global send tracker
import sqlite3
for db_path in ["/opt/ACTIVE/INFRA/SKILLS/global_sends.db",
                "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/global_sends.db"]:
    if os.path.exists(db_path):
        db = sqlite3.connect(db_path)
        cur = db.cursor()
        cur.execute("SELECT DISTINCT LOWER(email) FROM sent_emails")
        global_sent = {r[0] for r in cur.fetchall()}
        overlap_global = anofm_emails & global_sent
        print(f"\nGlobal tracker ({db_path}): {len(global_sent)} total")
        print(f"ANOFM overlap with global: {len(overlap_global)}")

        # Recent (14 days)
        cur.execute("SELECT DISTINCT LOWER(email) FROM sent_emails WHERE sent_date > date('now', '-14 days')")
        recent = {r[0] for r in cur.fetchall()}
        overlap_recent = anofm_emails & recent
        print(f"ANOFM overlap with recent 14 days: {len(overlap_recent)} (will be SKIPPED)")
        db.close()

# Check RO campaign CSVs
print("\n--- RO Campaign CSV overlaps ---")
ro_base = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA"
for f in sorted(glob.glob(f"{ro_base}/ro_*.csv")):
    try:
        with open(f) as fh:
            csv_emails = {r["email"].lower().strip() for r in csv.DictReader(fh) if r.get("email")}
        overlap = anofm_emails & csv_emails
        if overlap:
            print(f"  {os.path.basename(f):40s} {len(csv_emails):>5} emails, {len(overlap):>5} overlap with ANOFM")
    except:
        pass

# Check other DBs
print("\n--- DB overlaps ---")
for db_name in ["romania_emails", "interjob_master"]:
    try:
        conn = psycopg2.connect(dbname=db_name, user="tudor", host="localhost", password="tudor")
        cur = conn.cursor()
        if db_name == "romania_emails":
            cur.execute("SELECT DISTINCT LOWER(email) FROM contacts WHERE email IS NOT NULL AND email != ''")
        else:
            cur.execute("SELECT DISTINCT LOWER(email) FROM companies WHERE email IS NOT NULL AND email != '' AND country = 'RO'")
        db_emails = {r[0] for r in cur.fetchall()}
        overlap = anofm_emails & db_emails
        print(f"  {db_name:20s} {len(db_emails):>7} emails, {len(overlap):>5} overlap with ANOFM")
        conn.close()
    except Exception as e:
        print(f"  {db_name}: {e}")

# Summary
clean = anofm_emails - dnc - sent
print(f"\n=== SUMMARY ===")
print(f"ANOFM total unique: {len(anofm_emails)}")
print(f"  - DNC: {len(overlap_dnc)}")
print(f"  - Already sent: {len(sent)}")
print(f"  = Clean remaining: {len(clean)}")
print(f"  - Will be skipped (recent 14d): {len(overlap_recent) if 'overlap_recent' in dir() else '?'}")
print(f"  = Actually sendable: ~{len(clean) - len(overlap_recent) if 'overlap_recent' in dir() else len(clean)}")
