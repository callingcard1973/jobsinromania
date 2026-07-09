#!/usr/bin/env python3
"""Cross-match food distribution contacts with insolvency data.

Finds:
1. Food companies in our DB that are insolvent (risk flagging)
2. Insolvent food companies with assets/clients to acquire
3. Bankrupt food companies by sector for cooperative opportunities

Usage:
    python faliment_cross_match.py                    # Full report + cross-match
    python faliment_cross_match.py --flag-insolvent   # Flag our contacts that are insolvent
    python faliment_cross_match.py --opportunities    # Bankrupt food companies to acquire
    python faliment_cross_match.py --export out.csv   # Export results
"""

import csv
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import psycopg2
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

from shared_utils import DB_MASTER, DB_FOOD, normalize
from faliment_opportunities import FOOD_KEYWORDS, find_opportunities, export_all

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")


def safe_query(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params or ())
    return cur.fetchall(), [d[0] for d in cur.description]


def insolvency_stats(conn):
    """Overview of food-related insolvency records."""
    print("=" * 60)
    print("INSOLVENCY DATA -- Food Sector Overview")
    print("=" * 60)

    # Total insolvency
    rows, _ = safe_query(conn, """
        SELECT COUNT(*), COUNT(DISTINCT cui)
        FROM insolvency
    """)
    print(f"\nTotal insolvency records: {rows[0][0]:,}")
    print(f"Unique companies (by CUI): {rows[0][1]:,}")

    # Food sector
    rows, _ = safe_query(conn, """
        SELECT COUNT(*), COUNT(DISTINCT cui)
        FROM insolvency WHERE sector = 'food_meat'
    """)
    print(f"\nFood sector (food_meat): {rows[0][0]:,} records, {rows[0][1]:,} unique CUIs")

    # By keyword in company name
    keyword_cond = " OR ".join(
        f"company_name ILIKE '%%{kw}%%'" for kw in FOOD_KEYWORDS[:20]
    )
    rows, _ = safe_query(conn, f"""
        SELECT COUNT(DISTINCT cui) FROM insolvency
        WHERE ({keyword_cond})
        AND cui IS NOT NULL AND cui != ''
    """)
    print(f"Food-related by name keywords: {rows[0][0]:,} unique CUIs")

    # Combined
    rows, _ = safe_query(conn, f"""
        SELECT COUNT(DISTINCT cui) FROM insolvency
        WHERE (sector = 'food_meat' OR {keyword_cond})
        AND cui IS NOT NULL AND cui != ''
    """)
    print(f"Combined (sector + keywords): {rows[0][0]:,} unique CUIs")

    # Sector breakdown
    rows, _ = safe_query(conn, """
        SELECT sector, COUNT(DISTINCT cui) AS cuis
        FROM insolvency
        WHERE sector IS NOT NULL
        GROUP BY sector ORDER BY cuis DESC LIMIT 10
    """)
    print(f"\nTop sectors in insolvency:")
    for sector, cnt in rows:
        print(f"  {sector}: {cnt:,} companies")


def flag_insolvent_contacts(conn_master, conn_food):
    """Flag food_distribution contacts that appear in insolvency."""
    print(f"\n{'=' * 60}")
    print("FLAG: Food Distribution Contacts in Insolvency")
    print("=" * 60)

    # Get all insolvent company names (normalized) + CUI
    rows, _ = safe_query(conn_master, """
        SELECT DISTINCT company_name, cui FROM insolvency
        WHERE cui IS NOT NULL AND cui != ''
    """)
    insolvent_by_name = {}
    insolvent_by_cui = {}
    for name, cui in rows:
        norm = normalize(name)
        if norm and len(norm) >= 4:
            insolvent_by_name[norm] = cui
        if cui:
            insolvent_by_cui[cui.strip()] = name

    print(f"Insolvent companies indexed: {len(insolvent_by_name)} names, {len(insolvent_by_cui)} CUIs")

    # Get food_distribution contacts
    rows, _ = safe_query(conn_food, """
        SELECT id, company, cui, email, category, county FROM contacts
    """)

    flagged = []
    for cid, company, cui, email, cat, county in rows:
        matched_cui = None
        match_type = None

        # CUI match
        if cui and cui.strip() in insolvent_by_cui:
            matched_cui = cui.strip()
            match_type = "CUI"
        else:
            # Name match
            norm = normalize(company)
            if norm and norm in insolvent_by_name:
                matched_cui = insolvent_by_name[norm]
                match_type = "name"

        if matched_cui:
            flagged.append({
                "id": cid, "company": company, "cui": cui or "",
                "email": email or "", "category": cat or "",
                "county": county or "", "insolvent_cui": matched_cui,
                "match_type": match_type,
            })

    print(f"\nFlagged as insolvent: {len(flagged)}")
    with_email = [f for f in flagged if f["email"]]
    print(f"With email (remove from campaigns!): {len(with_email)}")

    if flagged:
        print(f"\nInsolvent contacts (first 30):")
        for f in flagged[:30]:
            email_flag = f" [{f['email']}]" if f["email"] else ""
            print(f"  {f['company'][:45]:45s} | {f['category']:12s} | CUI:{f['insolvent_cui']}{email_flag}")

    # Export
    out_path = os.path.join(DATA_DIR, "insolvent_contacts_flagged.csv")
    if flagged:
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=flagged[0].keys())
            w.writeheader()
            w.writerows(flagged)
        print(f"\nExported to: {out_path}")

    return flagged


def main():
    args = sys.argv[1:]

    conn_master = psycopg2.connect(**DB_MASTER)

    if "--export" in args:
        idx = args.index("--export")
        output = args[idx + 1] if idx + 1 < len(args) else "faliment_food_results.csv"
        conn_food = psycopg2.connect(**DB_FOOD)
        export_all(conn_master, conn_food, output)
        conn_food.close()
        conn_master.close()
        return

    if "--flag-insolvent" in args:
        conn_food = psycopg2.connect(**DB_FOOD)
        flag_insolvent_contacts(conn_master, conn_food)
        conn_food.close()
        conn_master.close()
        return

    if "--opportunities" in args:
        find_opportunities(conn_master)
        conn_master.close()
        return

    # Full report
    insolvency_stats(conn_master)

    conn_food = psycopg2.connect(**DB_FOOD)
    flag_insolvent_contacts(conn_master, conn_food)
    conn_food.close()

    find_opportunities(conn_master)
    conn_master.close()


if __name__ == "__main__":
    main()
