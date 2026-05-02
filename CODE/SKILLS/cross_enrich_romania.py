#!/usr/bin/env python3
"""
Cross-Enrich Romania Tables

Enriches tables with missing contacts using data from enriched tables.
Matches by CUI (company tax ID).

Sources (have contacts):
- romania_emails.contacts (149K, 0% gaps)
- interjob_master.contacts (570K, 0% gaps)
- interjob_master.ted_winners (83K RO, 0% gaps)
- interjob_master.agencies (5K RO, 0% gaps)

Targets (need enrichment):
- interjob_master.companies (1M, 620K gaps)
- interjob_master.insolvency (1M, 841K gaps)

Usage:
    python3 cross_enrich_romania.py --dry-run
    python3 cross_enrich_romania.py --target companies --batch 10000
    python3 cross_enrich_romania.py --target insolvency --batch 10000
    python3 cross_enrich_romania.py --all
"""

import sys
import argparse
import psycopg2
from psycopg2.extras import execute_batch

DB_MASTER = "dbname=interjob_master user=tudor"
DB_ROMANIA = "dbname=romania_emails user=tudor"


def get_enrichment_lookup():
    """Build CUI -> (email, phone) lookup from all enriched sources."""
    lookup = {}

    # Source 1: romania_emails.contacts
    print("  Loading romania_emails.contacts...")
    conn = psycopg2.connect(DB_ROMANIA)
    cur = conn.cursor()
    cur.execute("""
        SELECT cui, email, phone
        FROM contacts
        WHERE cui IS NOT NULL AND cui != ''
        AND ((email IS NOT NULL AND email != '') OR (phone IS NOT NULL AND phone != ''))
    """)
    for cui, email, phone in cur.fetchall():
        cui = cui.strip()
        if cui and cui not in lookup:
            lookup[cui] = (email or '', phone or '')
        elif cui and (not lookup[cui][0] and email):
            lookup[cui] = (email, lookup[cui][1])
        elif cui and (not lookup[cui][1] and phone):
            lookup[cui] = (lookup[cui][0], phone)
    print(f"    {len(lookup)} CUIs loaded")
    conn.close()

    # Source 2: interjob_master.contacts (join with companies for CUI)
    print("  Loading interjob_master.contacts...")
    conn = psycopg2.connect(DB_MASTER)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.cui, ct.email, ct.phone
        FROM contacts ct
        JOIN companies c ON ct.company_id = c.id
        WHERE c.cui IS NOT NULL AND c.cui != ''
        AND ((ct.email IS NOT NULL AND ct.email != '') OR (ct.phone IS NOT NULL AND ct.phone != ''))
    """)
    count_before = len(lookup)
    for cui, email, phone in cur.fetchall():
        cui = cui.strip()
        if cui and cui not in lookup:
            lookup[cui] = (email or '', phone or '')
        elif cui and (not lookup[cui][0] and email):
            lookup[cui] = (email, lookup[cui][1])
        elif cui and (not lookup[cui][1] and phone):
            lookup[cui] = (lookup[cui][0], phone)
    print(f"    +{len(lookup) - count_before} new CUIs")

    # Source 3: ted_winners (RO)
    print("  Loading interjob_master.ted_winners (RO)...")
    cur.execute("""
        SELECT DISTINCT ON (contractor) contractor, contractor_email
        FROM ted_winners
        WHERE contractor_country = 'RO'
        AND contractor_email IS NOT NULL AND contractor_email != ''
    """)
    # TED doesn't have CUI, skip for now
    print(f"    (skipped - no CUI column)")

    # Source 4: agencies (no CUI column - skip)
    print("  Loading interjob_master.agencies (RO)...")
    print(f"    (skipped - no CUI column)")

    conn.close()
    print(f"  Total lookup: {len(lookup)} CUIs with contacts")
    return lookup


def enrich_companies(lookup, batch_size=10000, dry_run=False):
    """Enrich interjob_master.companies table."""
    print("\n=== Enriching companies ===")

    conn = psycopg2.connect(DB_MASTER)
    cur = conn.cursor()

    # Get companies without contacts
    print("  Finding companies without contacts...")
    cur.execute("""
        SELECT id, cui
        FROM companies
        WHERE (country = 'Romania' OR country = 'RO')
        AND cui IS NOT NULL AND cui != ''
        AND ((email IS NULL OR email = '') AND (phone IS NULL OR phone = ''))
    """)
    rows = cur.fetchall()
    print(f"  Found {len(rows)} companies without contacts")

    # Match against lookup
    updates = []
    for company_id, cui in rows:
        cui = cui.strip()
        if cui in lookup:
            email, phone = lookup[cui]
            if email or phone:
                updates.append((email, phone, company_id))

    print(f"  Matched {len(updates)} companies with contacts")

    if dry_run:
        print("  [DRY RUN] Would update:")
        print(f"    - {sum(1 for u in updates if u[0])} with email")
        print(f"    - {sum(1 for u in updates if u[1])} with phone")
        conn.close()
        return len(updates)

    # Batch update
    print(f"  Updating in batches of {batch_size}...")
    updated = 0
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        execute_batch(cur, """
            UPDATE companies
            SET email = COALESCE(NULLIF(%s, ''), email),
                phone = COALESCE(NULLIF(%s, ''), phone),
                updated_at = NOW()
            WHERE id = %s
        """, batch)
        conn.commit()
        updated += len(batch)
        print(f"    Updated {updated}/{len(updates)}")

    conn.close()
    return updated


def enrich_insolvency(lookup, batch_size=10000, dry_run=False):
    """Enrich interjob_master.insolvency table."""
    print("\n=== Enriching insolvency ===")

    conn = psycopg2.connect(DB_MASTER)
    cur = conn.cursor()

    # Get insolvency records without contacts
    # Note: insolvency has liquidator_email/phone, not company contacts
    # We'll add company_email/phone columns if they don't exist
    print("  Checking for company contact columns...")
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'insolvency' AND column_name = 'company_email'
    """)
    has_columns = cur.fetchone() is not None

    if not has_columns:
        if dry_run:
            print("  [DRY RUN] Would add company_email and company_phone columns")
            # In dry run, just count records with CUI
            print("  Finding insolvency records with CUI...")
            cur.execute("""
                SELECT id, cui FROM insolvency
                WHERE cui IS NOT NULL AND cui != ''
            """)
        else:
            print("  Adding company_email and company_phone columns...")
            cur.execute("""
                ALTER TABLE insolvency
                ADD COLUMN IF NOT EXISTS company_email TEXT,
                ADD COLUMN IF NOT EXISTS company_phone TEXT
            """)
            conn.commit()
            # Get insolvency records without company contacts
            print("  Finding insolvency records without company contacts...")
            cur.execute("""
                SELECT id, cui
                FROM insolvency
                WHERE cui IS NOT NULL AND cui != ''
                AND ((company_email IS NULL OR company_email = '')
                     AND (company_phone IS NULL OR company_phone = ''))
            """)
    else:
        # Get insolvency records without company contacts
        print("  Finding insolvency records without company contacts...")
        cur.execute("""
            SELECT id, cui
            FROM insolvency
            WHERE cui IS NOT NULL AND cui != ''
            AND ((company_email IS NULL OR company_email = '')
                 AND (company_phone IS NULL OR company_phone = ''))
        """)
    rows = cur.fetchall()
    print(f"  Found {len(rows)} insolvency records without company contacts")

    # Match against lookup
    updates = []
    for record_id, cui in rows:
        cui = cui.strip()
        if cui in lookup:
            email, phone = lookup[cui]
            if email or phone:
                updates.append((email, phone, record_id))

    print(f"  Matched {len(updates)} records with contacts")

    if dry_run:
        print("  [DRY RUN] Would update:")
        print(f"    - {sum(1 for u in updates if u[0])} with email")
        print(f"    - {sum(1 for u in updates if u[1])} with phone")
        conn.close()
        return len(updates)

    # Batch update
    print(f"  Updating in batches of {batch_size}...")
    updated = 0
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        execute_batch(cur, """
            UPDATE insolvency
            SET company_email = COALESCE(NULLIF(%s, ''), company_email),
                company_phone = COALESCE(NULLIF(%s, ''), company_phone)
            WHERE id = %s
        """, batch)
        conn.commit()
        updated += len(batch)
        print(f"    Updated {updated}/{len(updates)}")

    conn.close()
    return updated


def main():
    parser = argparse.ArgumentParser(description='Cross-enrich Romania tables')
    parser.add_argument('--target', choices=['companies', 'insolvency', 'all'],
                        default='all', help='Target table(s)')
    parser.add_argument('--batch', type=int, default=10000, help='Batch size')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    args = parser.parse_args()

    print("=== Cross-Enrich Romania Tables ===\n")

    # Build lookup
    print("Building enrichment lookup from sources...")
    lookup = get_enrichment_lookup()

    # Enrich targets
    total_updated = 0

    if args.target in ('companies', 'all'):
        updated = enrich_companies(lookup, args.batch, args.dry_run)
        total_updated += updated

    if args.target in ('insolvency', 'all'):
        updated = enrich_insolvency(lookup, args.batch, args.dry_run)
        total_updated += updated

    print(f"\n=== DONE: {total_updated} records {'would be ' if args.dry_run else ''}enriched ===")


if __name__ == '__main__':
    main()
