#!/usr/bin/env python3
"""
Cross-Enrich Romania - Multi-Method Matching

Matches by: CUI, company name, phone, website domain, email domain

Run via cron:
    0 3 * * * /opt/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/cross_enrich_multi.py >> /opt/ACTIVE/INFRA/LOGS/cross_enrich.log 2>&1
"""

import sys
import re
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime

DB_MASTER = "dbname=interjob_master user=tudor"
DB_ROMANIA = "dbname=romania_emails user=tudor"

def normalize_name(name):
    if not name:
        return None
    name = name.upper().strip()
    name = re.sub(r'\b(S\.?R\.?L\.?|S\.?A\.?|S\.?C\.?|S\.?N\.?C\.?|P\.?F\.?A\.?|I\.?I\.?|S\.?R\.?L\.?-D\.?)\b', '', name)
    name = re.sub(r'[^A-Z0-9]', '', name)
    return name if len(name) >= 3 else None

def normalize_phone(phone):
    if not phone:
        return None
    phone = re.sub(r'[^0-9]', '', phone)
    if phone.startswith('40'):
        phone = '0' + phone[2:]
    if phone.startswith('004'):
        phone = phone[3:]
    return phone if len(phone) >= 9 else None

def get_domain(url_or_email):
    if not url_or_email:
        return None
    if '@' in url_or_email:
        return url_or_email.split('@')[1].lower().strip()
    m = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url_or_email.lower())
    return m.group(1) if m else None

def build_lookups():
    """Build lookup dictionaries from enriched sources."""
    by_cui = {}
    by_name = {}
    by_phone = {}
    by_domain = {}

    # Source: romania_emails.contacts
    conn = psycopg2.connect(DB_ROMANIA)
    cur = conn.cursor()
    cur.execute("""
        SELECT company_name, cui, email, phone, website
        FROM contacts
        WHERE (email IS NOT NULL AND email != '') OR (phone IS NOT NULL AND phone != '')
    """)

    for name, cui, email, phone, website in cur.fetchall():
        e, p = email or '', phone or ''

        if cui and cui.strip():
            cui = cui.strip()
            if cui not in by_cui:
                by_cui[cui] = (e, p)

        norm_name = normalize_name(name)
        if norm_name and norm_name not in by_name:
            by_name[norm_name] = (e, p)

        norm_phone = normalize_phone(phone)
        if norm_phone and norm_phone not in by_phone:
            by_phone[norm_phone] = (e, name or '')

        domain = get_domain(website) or get_domain(email)
        if domain and domain not in by_domain:
            by_domain[domain] = (e, p)

    conn.close()

    # Source: interjob_master.contacts (via companies)
    conn = psycopg2.connect(DB_MASTER)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name, c.cui, ct.email, ct.phone, c.website
        FROM contacts ct
        JOIN companies c ON ct.company_id = c.id
        WHERE (ct.email IS NOT NULL AND ct.email != '') OR (ct.phone IS NOT NULL AND ct.phone != '')
    """)

    for name, cui, email, phone, website in cur.fetchall():
        e, p = email or '', phone or ''

        if cui and cui.strip() and cui not in by_cui:
            by_cui[cui.strip()] = (e, p)

        norm_name = normalize_name(name)
        if norm_name and norm_name not in by_name:
            by_name[norm_name] = (e, p)

        norm_phone = normalize_phone(phone)
        if norm_phone and norm_phone not in by_phone:
            by_phone[norm_phone] = (e, name or '')

        domain = get_domain(website) or get_domain(email)
        if domain and domain not in by_domain:
            by_domain[domain] = (e, p)

    conn.close()

    return by_cui, by_name, by_phone, by_domain

def enrich_companies(by_cui, by_name, by_phone, by_domain):
    """Enrich companies table using all matching methods."""
    conn = psycopg2.connect(DB_MASTER)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, cui, phone, website
        FROM companies
        WHERE (country = 'Romania' OR country = 'RO')
        AND ((email IS NULL OR email = '') AND (phone IS NULL OR phone = ''))
    """)
    companies = cur.fetchall()

    matches = []
    stats = {'cui': 0, 'name': 0, 'phone': 0, 'domain': 0}

    for cid, name, cui, phone, website in companies:
        email_found, phone_found = None, None

        # 1. CUI match
        if cui and cui.strip() in by_cui:
            email_found, phone_found = by_cui[cui.strip()]
            stats['cui'] += 1

        # 2. Name match
        if not email_found:
            norm_name = normalize_name(name)
            if norm_name and norm_name in by_name:
                email_found, phone_found = by_name[norm_name]
                stats['name'] += 1

        # 3. Phone match
        if not email_found:
            norm_phone = normalize_phone(phone)
            if norm_phone and norm_phone in by_phone:
                email_found, _ = by_phone[norm_phone]
                stats['phone'] += 1

        # 4. Domain match
        if not email_found:
            domain = get_domain(website)
            if domain and domain in by_domain:
                email_found, phone_found = by_domain[domain]
                stats['domain'] += 1

        if email_found or phone_found:
            matches.append((email_found or '', phone_found or '', cid))

    # Batch update
    if matches:
        execute_batch(cur, """
            UPDATE companies
            SET email = COALESCE(NULLIF(%s, ''), email),
                phone = COALESCE(NULLIF(%s, ''), phone),
                updated_at = NOW()
            WHERE id = %s
        """, matches, page_size=5000)
        conn.commit()

    conn.close()
    return len(matches), stats

def enrich_insolvency(by_cui, by_name, by_phone, by_domain):
    """Enrich insolvency table using all matching methods."""
    conn = psycopg2.connect(DB_MASTER)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, company_name, cui
        FROM insolvency
        WHERE cui IS NOT NULL AND cui != ''
        AND ((company_email IS NULL OR company_email = '')
             AND (company_phone IS NULL OR company_phone = ''))
    """)
    records = cur.fetchall()

    matches = []
    stats = {'cui': 0, 'name': 0}

    for rid, name, cui in records:
        email_found, phone_found = None, None

        # 1. CUI match
        if cui and cui.strip() in by_cui:
            email_found, phone_found = by_cui[cui.strip()]
            stats['cui'] += 1

        # 2. Name match
        if not email_found:
            norm_name = normalize_name(name)
            if norm_name and norm_name in by_name:
                email_found, phone_found = by_name[norm_name]
                stats['name'] += 1

        if email_found or phone_found:
            matches.append((email_found or '', phone_found or '', rid))

    # Batch update
    if matches:
        execute_batch(cur, """
            UPDATE insolvency
            SET company_email = COALESCE(NULLIF(%s, ''), company_email),
                company_phone = COALESCE(NULLIF(%s, ''), company_phone)
            WHERE id = %s
        """, matches, page_size=5000)
        conn.commit()

    conn.close()
    return len(matches), stats

def main():
    print(f"\n=== Cross-Enrich Romania {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    print("Building lookups...")
    by_cui, by_name, by_phone, by_domain = build_lookups()
    print(f"  CUI: {len(by_cui)}, Name: {len(by_name)}, Phone: {len(by_phone)}, Domain: {len(by_domain)}")

    print("\nEnriching companies...")
    count, stats = enrich_companies(by_cui, by_name, by_phone, by_domain)
    print(f"  Enriched: {count}")
    print(f"  By method: CUI={stats['cui']}, Name={stats['name']}, Phone={stats['phone']}, Domain={stats['domain']}")

    print("\nEnriching insolvency...")
    count, stats = enrich_insolvency(by_cui, by_name, by_phone, by_domain)
    print(f"  Enriched: {count}")
    print(f"  By method: CUI={stats['cui']}, Name={stats['name']}")

    print("\n=== Done ===")

if __name__ == '__main__':
    main()
