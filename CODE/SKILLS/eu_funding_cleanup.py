#!/usr/bin/env python3
"""Clean EU funding DB: normalize phones, verify emails, delete junk."""
import psycopg2
import re

DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql", "port": 5432}
conn = psycopg2.connect(**DB)
cur = conn.cursor()

# -- Check current state --
for tbl in ["beneficiari_privati", "proiecte"]:
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE email LIKE '%%@%%'")
    good_email = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE telefon LIKE '+40%%'")
    good_phone = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE telefon != '' AND telefon NOT LIKE '+40%%'")
    bad_phone = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE email != '' AND email NOT LIKE '%%@%%'")
    bad_email = cur.fetchone()[0]
    print(f"{tbl}: {total} total | email OK: {good_email} BAD: {bad_email} | phone +40: {good_phone} BAD: {bad_phone}")

# -- Fix phones --
print("\n=== Normalizing phones ===")
for tbl in ["beneficiari_privati", "proiecte"]:
    cur.execute(f"SELECT id, telefon FROM {tbl} WHERE telefon != ''")
    rows = cur.fetchall()
    fixed = 0
    for rid, phone in rows:
        digits = re.sub(r"\D", "", str(phone))
        new_phone = phone
        if len(digits) == 10 and digits.startswith("0"):
            new_phone = "+40" + digits[1:]
        elif len(digits) == 9:
            new_phone = "+40" + digits
        elif len(digits) == 11 and digits.startswith("40"):
            new_phone = "+" + digits
        elif len(digits) == 12 and digits.startswith("0040"):
            new_phone = "+40" + digits[4:]
        if new_phone != phone:
            cur.execute(f"UPDATE {tbl} SET telefon = %s WHERE id = %s", (new_phone, rid))
            fixed += 1
    conn.commit()
    print(f"  {tbl}: fixed {fixed} phones")

# -- Fix emails: delete broken ones (no @) --
print("\n=== Cleaning bad emails ===")
for tbl in ["beneficiari_privati", "proiecte"]:
    cur.execute(f"UPDATE {tbl} SET email = '' WHERE email != '' AND email NOT LIKE '%%@%%'")
    print(f"  {tbl}: cleared {cur.rowcount} bad emails")
    # Also clear emails with spaces or weird chars
    cur.execute(f"UPDATE {tbl} SET email = LOWER(TRIM(email)) WHERE email LIKE '%% %%' OR email != LOWER(email)")
    print(f"  {tbl}: lowered/trimmed {cur.rowcount} emails")
conn.commit()

# -- Delete rows with no email AND no phone (useless) --
print("\n=== Deleting junk rows (no email, no phone) ===")
for tbl in ["beneficiari_privati", "proiecte"]:
    cur.execute(f"DELETE FROM {tbl} WHERE (email = '' OR email IS NULL) AND (telefon = '' OR telefon IS NULL)")
    print(f"  {tbl}: deleted {cur.rowcount} junk rows")
conn.commit()

# -- Final stats --
print("\n=== AFTER CLEANUP ===")
for tbl in ["beneficiari_privati", "proiecte"]:
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE email LIKE '%%@%%'")
    good_email = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE telefon LIKE '+40%%'")
    good_phone = cur.fetchone()[0]
    print(f"  {tbl}: {total} total | email: {good_email} | phone +40: {good_phone}")

conn.close()
print("\nDone!")
