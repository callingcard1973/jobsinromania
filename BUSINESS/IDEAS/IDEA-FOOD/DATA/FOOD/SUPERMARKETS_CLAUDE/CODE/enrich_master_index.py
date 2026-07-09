#!/usr/bin/env python3
"""Build master lookup index from interjob_master for enrichment.

Indexes companies, contacts, and extra tables (executori, anevar, etc.)
by normalized name and phone number.
"""

import re

from shared_utils import normalize


def build_master_index(conn):
    """Build lookup index from interjob_master.companies.

    Returns (by_name, by_phone) dicts for O(1) lookups.
    """
    print("Building master index from interjob_master.companies...")
    cur = conn.cursor()

    cur.execute("""
        SELECT name, email, phone, website, cui
        FROM companies
        WHERE country = 'RO'
        AND (email IS NOT NULL AND email <> ''
             OR phone IS NOT NULL AND phone <> '')
    """)

    by_name = {}
    by_phone = {}
    count = 0
    for row in cur:
        name, email, phone, website, cui = row
        norm = normalize(name)
        if not norm:
            continue
        rec = {"email": email or "", "phone": phone or "",
               "website": website or "", "cui": cui or "",
               "name": name or ""}
        if norm not in by_name or (email and not by_name[norm].get("email")):
            by_name[norm] = rec
        if phone:
            clean_phone = re.sub(r'[^0-9+]', '', str(phone))
            if len(clean_phone) >= 9:
                by_phone[clean_phone[-9:]] = rec
        count += 1

    print(f"  Indexed {count} companies -> {len(by_name)} unique names, {len(by_phone)} phones")

    # Also index contacts table
    cur.execute("""
        SELECT c.name, ct.email, ct.phone
        FROM contacts ct
        JOIN companies c ON c.id = ct.company_id
        WHERE c.country = 'RO'
        AND ct.email IS NOT NULL AND ct.email <> ''
    """)
    contacts_added = 0
    for row in cur:
        name, email, phone = row
        norm = normalize(name)
        if norm and norm not in by_name and email:
            by_name[norm] = {"email": email, "phone": phone or "",
                             "website": "", "cui": "", "name": name}
            contacts_added += 1

    print(f"  Added {contacts_added} from contacts table")

    # Also index other tables with Romanian entities
    extra_tables = [
        ("executori", "nume", "email", "telefon"),
        ("anevar_evaluatori", "nume", "email", "telefon"),
        ("primarii", "denumire", "email", "telefon"),
        ("consultanti_fiscali", "nume", "email", "telefon"),
        ("firme_audit", "nume", "email", "telefon"),
    ]
    for table, name_col, email_col, phone_col in extra_tables:
        try:
            cur.execute(f"""
                SELECT {name_col}, {email_col}, {phone_col}
                FROM {table}
                WHERE {email_col} IS NOT NULL AND {email_col} <> ''
            """)
            added = 0
            for row in cur:
                name, email, phone = row
                norm = normalize(name)
                if norm and norm not in by_name and email:
                    by_name[norm] = {"email": email, "phone": phone or "",
                                     "website": "", "cui": "", "name": name}
                    added += 1
            if added:
                print(f"  Added {added} from {table}")
        except Exception:
            conn.rollback()

    return by_name, by_phone
