#!/usr/bin/env python3
"""Enrich EU funding contractors with contact info from internal DBs + ANAF."""
# --
import psycopg2
import re
import unicodedata

EU_DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql"}
MASTER_DB = {"dbname": "interjob_master", "user": "tudor", "host": "/var/run/postgresql"}
ROMANIA_DB = {"dbname": "romania", "user": "tudor", "host": "/var/run/postgresql"}
ANOFM_DB = {"dbname": "anofm", "user": "tudor", "host": "/var/run/postgresql"}

# --
def to_ascii(t):
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii').strip()

def norm(name):
    """Normalize company name for matching."""
    if not name: return ''
    n = to_ascii(name).upper().strip()
    for suffix in [' SRL', ' S.R.L', ' SA', ' S.A', ' PFA', ' II', ' SNC']:
        n = n.replace(suffix, '')
    n = re.sub(r'[^A-Z0-9 ]', '', n).strip()
    return re.sub(r'\s+', ' ', n)

# --
def build_lookup():
    """Build company lookup from all internal DBs."""
    lookup = {}  # normalized_name -> {emails: set, phones: set, city}

    def add(name, email, phone, city):
        key = norm(name)
        if not key: return
        if key not in lookup:
            lookup[key] = {'emails': set(), 'phones': set(), 'city': to_ascii(city or '')}
        if email and '@' in email: lookup[key]['emails'].add(email.strip().lower())
        if phone and len(phone) > 5: lookup[key]['phones'].add(phone.strip())
        if city and not lookup[key]['city']: lookup[key]['city'] = to_ascii(city)

    for db, query, label in [
        (ROMANIA_DB, "SELECT company_name, email, phone, city FROM companies WHERE email LIKE '%%@%%' LIMIT 500000", "romania"),
        (ROMANIA_DB, "SELECT company_name, email_2, phone_2, city FROM companies WHERE email_2 LIKE '%%@%%' LIMIT 200000", "romania_alt"),
        (MASTER_DB, "SELECT name, email, phone, city FROM companies WHERE country='RO' AND email LIKE '%%@%%' LIMIT 500000", "interjob_master"),
        (ANOFM_DB, "SELECT company_name, email, phone, city FROM jobs WHERE email LIKE '%%@%%' LIMIT 200000", "anofm"),
    ]:
        try:
            conn = psycopg2.connect(**db)
            cur = conn.cursor()
            cur.execute(query)
            for name, email, phone, city in cur:
                add(name, email, phone, city)
            conn.close()
            print(f"  {label}: {len(lookup)} total")
        except Exception as e:
            print(f"  {label}: {e}")

    print(f"  Total lookup: {len(lookup)} companies")
    return lookup

# --
def main():
    print("Building company lookup...")
    lookup = build_lookup()

    conn = psycopg2.connect(**EU_DB)
    cur = conn.cursor()
    cur.execute("SELECT id, contractors FROM beneficiari_privati WHERE contractors IS NOT NULL AND contractors != '' LIMIT 50000")
    rows = cur.fetchall()
    print(f"Found {len(rows)} anunturi with contractors")

    enriched = 0
    for rid, contractors_str in rows:
        names = [c.strip() for c in contractors_str.split(',') if c.strip()]
        results = []
        for name in names:
            key = norm(name)
            match = lookup.get(key)
            if match:
                emails = ', '.join(sorted(match['emails'])[:3])
                phones = ', '.join(sorted(match['phones'])[:3])
                info = name
                if emails: info += f" | emails: {emails}"
                if phones: info += f" | phones: {phones}"
                if match['city']: info += f" | {match['city']}"
                results.append(info)
                enriched += 1
            else:
                results.append(name)
        # Update with enriched info
        enriched_str = '; '.join(results)
        if enriched_str != contractors_str:
            cur.execute("UPDATE beneficiari_privati SET contractors = %s WHERE id = %s",
                        (to_ascii(enriched_str), rid))

    conn.commit()
    conn.close()
    print(f"Enriched {enriched} contractors out of {len(rows)} records")
    # Reverse: push new contacts from EU funding back to internal DBs
    reverse_enrich(lookup)

def reverse_enrich(lookup):
    """Push emails/phones from EU funding beneficiari + contractors back to romania DB."""
    conn_eu = psycopg2.connect(**EU_DB)
    cur_eu = conn_eu.cursor()
    # Beneficiari (project owners) with email
    cur_eu.execute("SELECT beneficiar, email, telefon, judet FROM beneficiari_privati WHERE email LIKE '%%@%%'")
    new_contacts = {}
    for name, email, phone, city in cur_eu:
        key = norm(name)
        if not key: continue
        existing = lookup.get(key)
        email = email.strip().lower() if email else ''
        phone = phone.strip() if phone else ''
        if existing:
            new_emails = {email} - existing['emails'] if email else set()
            new_phones = {phone} - existing['phones'] if phone else set()
            if new_emails or new_phones:
                new_contacts[key] = {'name': name, 'emails': new_emails, 'phones': new_phones, 'city': to_ascii(city or '')}
        elif email:
            new_contacts[key] = {'name': name, 'emails': {email}, 'phones': {phone} if phone else set(), 'city': to_ascii(city or '')}
    conn_eu.close()
    if not new_contacts:
        print("Reverse: 0 new contacts"); return
    # Insert new contacts into romania.companies
    try:
        conn_ro = psycopg2.connect(**ROMANIA_DB)
        cur_ro = conn_ro.cursor()
        inserted = 0
        for key, data in new_contacts.items():
            for email in data['emails']:
                if not email: continue
                phone = next(iter(data['phones']), '')
                try:
                    cur_ro.execute("""INSERT INTO companies (company_name, company_name_normalized, email, phone, city)
                        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        (to_ascii(data['name']), key, email, phone, data['city']))
                    inserted += cur_ro.rowcount
                except Exception:
                    conn_ro.rollback()
        conn_ro.commit(); conn_ro.close()
        print(f"Reverse: {inserted} new contacts pushed to romania DB")
    except Exception as e:
        print(f"Reverse: {e}")

if __name__ == "__main__":
    main()
