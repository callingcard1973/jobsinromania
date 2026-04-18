#!/usr/bin/env python3
"""Verify and clean all EU funding data: ASCII, emails, phones, junk."""
import psycopg2
import re

DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql", "port": 5432}
conn = psycopg2.connect(**DB)
cur = conn.cursor()

for tbl in ["beneficiari_privati", "proiecte"]:
    print(f"\n=== {tbl} ===")

    # Count total
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    total = cur.fetchone()[0]

    # Bad emails (no @ or no dot after @)
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE email LIKE '%%@%%' AND email NOT LIKE '%%@%%.%%'")
    bad_email = cur.fetchone()[0]

    # Emails without @
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE email IS NOT NULL AND email <> '' AND email NOT LIKE '%%@%%'")
    no_at = cur.fetchone()[0]

    # Bad phones
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE telefon IS NOT NULL AND telefon <> '' AND telefon NOT LIKE '+40%%'")
    bad_phone = cur.fetchone()[0]

    # +400 phones
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE telefon LIKE '+400%%'")
    double_zero = cur.fetchone()[0]

    # No contact at all
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE (email IS NULL OR email = '') AND (telefon IS NULL OR telefon = '')")
    no_contact = cur.fetchone()[0]

    # Good emails
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE email LIKE '%%@%%.%%'")
    good_email = cur.fetchone()[0]

    # Good phones
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE telefon LIKE '+40%%' AND telefon NOT LIKE '+400%%'")
    good_phone = cur.fetchone()[0]

    print(f"  Total: {total}")
    print(f"  Good email: {good_email} | Bad email (no dot): {bad_email} | No @: {no_at}")
    print(f"  Good phone: {good_phone} | Bad phone: {bad_phone} | +400 bug: {double_zero}")
    print(f"  No contact: {no_contact}")

    # FIX: Clear bad emails
    cur.execute(f"UPDATE {tbl} SET email = '' WHERE email IS NOT NULL AND email <> '' AND email NOT LIKE '%%@%%.%%'")
    print(f"  FIXED: cleared {cur.rowcount} bad emails")

    # FIX: +400 phones
    cur.execute(f"UPDATE {tbl} SET telefon = REPLACE(telefon, '+400', '+40') WHERE telefon LIKE '+400%%'")
    print(f"  FIXED: {cur.rowcount} +400 phones")

    # FIX: Normalize remaining non-+40 phones
    cur.execute(f"SELECT id, telefon FROM {tbl} WHERE telefon IS NOT NULL AND telefon <> '' AND telefon NOT LIKE '+40%%'")
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
        if new_phone != phone:
            cur.execute(f"UPDATE {tbl} SET telefon = %s WHERE id = %s", (new_phone, rid))
            fixed += 1
    print(f"  FIXED: {fixed} more phones normalized")

    # FIX: Lowercase + trim emails
    cur.execute(f"UPDATE {tbl} SET email = LOWER(TRIM(email)) WHERE email LIKE '%% %%' OR email <> LOWER(email)")
    print(f"  FIXED: {cur.rowcount} emails lowered/trimmed")

    # DELETE: junk rows (no email AND no phone)
    cur.execute(f"DELETE FROM {tbl} WHERE (email IS NULL OR email = '') AND (telefon IS NULL OR telefon = '')")
    print(f"  DELETED: {cur.rowcount} junk rows")

    conn.commit()

# Final summary
print("\n=== FINAL ===")
for tbl in ["beneficiari_privati", "proiecte"]:
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE email LIKE '%%@%%.%%'")
    email = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE telefon LIKE '+40%%'")
    phone = cur.fetchone()[0]
    print(f"  {tbl}: {total} total | {email} email | {phone} phone")

conn.close()
print("\nDone!")
