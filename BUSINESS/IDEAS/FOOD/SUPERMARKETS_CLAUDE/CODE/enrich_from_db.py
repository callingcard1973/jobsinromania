#!/usr/bin/env python3
"""Enrich food_distribution contacts from interjob_master (no scraping).

4-pass: exact name, phone, prefix, trigram. Uses enrich_master_index for lookups.

Usage:
    python enrich_from_db.py                  # Enrich food_distribution DB
    python enrich_from_db.py --dry-run        # Show what would be enriched
    python enrich_from_db.py --stats          # Show enrichment stats
    python enrich_from_db.py --export out.csv # Export enriched data
"""

import csv
import os
import re
import sys

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

from shared_utils import normalize, DB_MASTER, DB_FOOD
from enrich_master_index import build_master_index

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")


def enrich(dry_run=False):
    """Run enrichment passes."""
    conn_master = psycopg2.connect(**DB_MASTER)
    conn_food = psycopg2.connect(**DB_FOOD)

    # Build index
    by_name, by_phone = build_master_index(conn_master)
    conn_master.close()

    # Get records needing enrichment
    cur = conn_food.cursor()
    cur.execute("""
        SELECT id, company, phone, email, cui, website
        FROM contacts
        WHERE (email IS NULL OR email = '')
        ORDER BY id
    """)
    no_email = cur.fetchall()
    print(f"\nRecords needing email: {len(no_email)}")

    # -- Pass 1: Exact name match
    updates = []
    matched_ids = set()
    for row in no_email:
        cid, company, phone, email, cui, website = row
        norm = normalize(company)
        if norm and norm in by_name:
            match = by_name[norm]
            updates.append({
                "id": cid,
                "email": match["email"],
                "phone": match["phone"] if not phone else phone,
                "cui": match["cui"] if not cui else cui,
                "website": match["website"] if not website else website,
            })
            matched_ids.add(cid)

    print(f"Pass 1 (exact name): {len(updates)} matches")

    # -- Pass 2: Phone match for remaining
    phone_updates = []
    for row in no_email:
        cid, company, phone, email, cui, website = row
        if cid in matched_ids or not phone:
            continue
        clean_phone = re.sub(r'[^0-9+]', '', str(phone))
        if len(clean_phone) >= 9:
            key = clean_phone[-9:]
            if key in by_phone:
                match = by_phone[key]
                if match.get("email"):
                    phone_updates.append({
                        "id": cid,
                        "email": match["email"],
                        "cui": match["cui"] if not cui else cui,
                        "website": match["website"] if not website else website,
                    })
                    matched_ids.add(cid)

    print(f"Pass 2 (phone match): {len(phone_updates)} matches")

    # -- Pass 3: Prefix match (O(1) lookups)
    fuzzy_updates = []
    remaining = [r for r in no_email if r[0] not in matched_ids]
    prefix_index = {}
    for key in by_name:
        if len(key) >= 8 and by_name[key].get("email"):
            px = key[:12]
            if px not in prefix_index:
                prefix_index[px] = key

    for row in remaining:
        cid, company, phone, email, cui, website = row
        norm = normalize(company)
        if not norm or len(norm) < 8:
            continue
        px = norm[:12]
        if px in prefix_index:
            match = by_name[prefix_index[px]]
            fuzzy_updates.append({
                "id": cid,
                "email": match["email"],
                "phone": match["phone"] if not phone else phone,
                "cui": match["cui"] if not cui else cui,
                "website": match["website"] if not website else website,
            })
            matched_ids.add(cid)

    print(f"Pass 3 (prefix match): {len(fuzzy_updates)} matches")

    # -- Pass 4: Server-side trigram fuzzy match in batches
    trigram_updates = []
    remaining2 = [(r[0], normalize(r[1])) for r in no_email
                  if r[0] not in matched_ids and len(normalize(r[1])) >= 6]
    if remaining2:
        print(f"Pass 4 (trigram): matching {len(remaining2)} remaining in batches...")
        conn_master2 = psycopg2.connect(**DB_MASTER)
        cur2 = conn_master2.cursor()
        cur2.execute("SET pg_trgm.similarity_threshold = 0.5")

        # Process in batches of 50
        batch_size = 50
        for i in range(0, len(remaining2), batch_size):
            batch = remaining2[i:i + batch_size]
            for fid, norm in batch:
                if fid in matched_ids:
                    continue
                cur2.execute("""
                    SELECT email, phone, website, cui
                    FROM companies
                    WHERE country = 'RO'
                    AND email IS NOT NULL AND email <> ''
                    AND UPPER(name) %% %s
                    ORDER BY similarity(UPPER(name), %s) DESC
                    LIMIT 1
                """, (norm, norm))
                row = cur2.fetchone()
                if row and row[0]:
                    trigram_updates.append({
                        "id": fid, "email": row[0],
                        "phone": row[1] or "", "cui": row[3] or "",
                        "website": row[2] or "",
                    })
                    matched_ids.add(fid)

            if (i + batch_size) % 500 == 0:
                print(f"  ... processed {i + batch_size}/{len(remaining2)}, found {len(trigram_updates)}")

        conn_master2.close()
        print(f"Pass 4 (trigram): {len(trigram_updates)} matches")

    all_updates = updates + phone_updates + fuzzy_updates + trigram_updates
    total_enriched = len(all_updates)
    print(f"\nTotal enrichable: {total_enriched} / {len(no_email)} ({100*total_enriched//max(len(no_email),1)}%)")

    if dry_run:
        print("\n[DRY RUN] No changes made.")
        for u in all_updates[:10]:
            print(f"  id={u['id']}: email={u['email']}, cui={u.get('cui','')}")
        conn_food.close()
        return

    update_sql = """UPDATE contacts SET
        email = COALESCE(NULLIF(%(email)s, ''), email),
        phone = COALESCE(NULLIF(%(phone)s, ''), phone),
        cui = COALESCE(NULLIF(%(cui)s, ''), cui),
        website = COALESCE(NULLIF(%(website)s, ''), website)
        WHERE id = %(id)s"""
    for u in all_updates:
        u.setdefault("phone", "")
        u.setdefault("cui", "")
        u.setdefault("website", "")

    execute_batch(cur, update_sql, all_updates, page_size=500)
    conn_food.commit()
    print(f"\nUpdated {total_enriched} records in food_distribution.contacts")

    conn_food.close()


def show_stats():
    """Show current enrichment stats."""
    conn = psycopg2.connect(**DB_FOOD)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE email IS NOT NULL AND email <> ''),
               COUNT(*) FILTER (WHERE phone IS NOT NULL AND phone <> ''),
               COUNT(*) FILTER (WHERE cui IS NOT NULL AND cui <> ''),
               COUNT(*) FILTER (WHERE website IS NOT NULL AND website <> '')
        FROM contacts""")
    total, w_email, w_phone, w_cui, w_web = cur.fetchone()
    print(f"Total: {total}")
    print(f"With email: {w_email} ({100*w_email//total}%)")
    print(f"With phone: {w_phone} ({100*w_phone//total}%)")
    print(f"With CUI: {w_cui} ({100*w_cui//total}%)")
    print(f"With website: {w_web} ({100*w_web//total}%)")
    print(f"Missing email: {total - w_email}")
    cur.execute("SELECT * FROM contacts_by_category")
    print(f"\nBy category:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} total, {row[2]} with email")
    conn.close()


def export_enriched(output):
    """Export enriched contacts to CSV."""
    conn = psycopg2.connect(**DB_FOOD)
    cur = conn.cursor()
    cur.execute("""SELECT company, cui, county, city, address, phone,
                          email, website, category, subcategory, source
                   FROM contacts ORDER BY category, county, company""")
    rows = cur.fetchall()
    headers = [d[0] for d in cur.description]
    conn.close()
    with open(output, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    print(f"Exported {len(rows)} contacts to {output}")


def main():
    args = sys.argv[1:]
    if "--stats" in args:
        show_stats()
    elif "--dry-run" in args:
        enrich(dry_run=True)
    elif "--export" in args:
        idx = args.index("--export")
        output = args[idx + 1] if idx + 1 < len(args) else "enriched_contacts.csv"
        export_enriched(output)
    else:
        enrich(dry_run=False)
        print("\n--- Post-enrichment stats ---")
        show_stats()


if __name__ == "__main__":
    main()
