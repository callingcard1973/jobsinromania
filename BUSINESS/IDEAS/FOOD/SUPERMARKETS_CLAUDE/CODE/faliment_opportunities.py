#!/usr/bin/env python3
"""Find bankrupt food companies as acquisition opportunities.

Cross-references insolvency data with companies table to find
food companies with liquidator contacts and company emails.
"""

import csv
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")

FOOD_KEYWORDS = [
    "aliment", "lact", "dairy", "lapte", "branz", "cheese",
    "carne", "meat", "abator", "carmangerie",
    "panif", "paine", "bread", "patiser", "cofet",
    "conserv", "legum", "fruct", "agri", "farm", "ferma",
    "horeca", "restaurant", "hotel", "catering", "cantina",
    "distribut", "logist", "transport", "frigorific", "cold",
    "supermarket", "magazin", "comert", "retail",
    "en.gros", "angro", "wholesale",
    "peste", "fish", "miere", "honey", "vin", "wine",
    "zahar", "sugar", "ulei", "oil", "cereale", "grain",
    "suc", "juice", "bere", "beer", "bauturi",
]


def _keyword_cond():
    return " OR ".join(
        f"i.company_name ILIKE '%%{kw}%%'" for kw in FOOD_KEYWORDS[:20])


def _safe_query(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params or ())
    return cur.fetchall(), [d[0] for d in cur.description]


def find_opportunities(conn_master):
    """Find bankrupt food companies -- acquisition opportunities."""
    print(f"\n{'=' * 60}")
    print("OPPORTUNITIES: Bankrupt Food Companies")
    print("=" * 60)

    kc = _keyword_cond()
    rows, _ = _safe_query(conn_master, f"""
        SELECT DISTINCT ON (i.cui)
            i.company_name, i.cui, i.liquidator_name, i.liquidator_email,
            i.liquidator_phone, i.date_filed, i.sector
        FROM insolvency i
        WHERE (i.sector = 'food_meat' OR {kc})
        AND i.cui IS NOT NULL AND i.cui != ''
        ORDER BY i.cui, i.date_filed DESC NULLS LAST
    """)

    print(f"\nTotal bankrupt food companies: {len(rows)}")

    categories = {}
    with_contact = []
    for name, cui, liq_name, liq_email, liq_phone, date_filed, sector in rows:
        name_lower = (name or "").lower()
        cat = "other"
        for kw in FOOD_KEYWORDS:
            if kw in name_lower:
                cat = kw
                break
        if sector == "food_meat":
            cat = "food_meat"
        categories[cat] = categories.get(cat, 0) + 1
        if liq_email or liq_phone:
            with_contact.append({
                "company": name, "cui": cui,
                "liquidator": liq_name or "",
                "liquidator_email": liq_email or "",
                "liquidator_phone": liq_phone or "",
                "date_filed": str(date_filed or ""),
                "sector": sector or "",
            })

    print(f"With liquidator contact: {len(with_contact)}")
    print(f"\nBy keyword:")
    for cat, cnt in sorted(categories.items(), key=lambda x: -x[1])[:15]:
        print(f"  {cat}: {cnt}")

    # Cross-reference with companies table for emails
    rows2, _ = _safe_query(conn_master, f"""
        SELECT i.company_name, i.cui, c.email, c.phone, c.website,
               c.city, c.sector_name, i.date_filed
        FROM insolvency i
        JOIN companies c ON c.cui = i.cui AND c.country = 'RO'
        WHERE (i.sector = 'food_meat' OR {kc})
        AND c.email IS NOT NULL AND c.email != ''
        AND i.cui IS NOT NULL AND i.cui != ''
        GROUP BY i.company_name, i.cui, c.email, c.phone, c.website,
                 c.city, c.sector_name, i.date_filed
        ORDER BY i.date_filed DESC NULLS LAST
        LIMIT 500
    """)

    print(f"\nBankrupt food companies WITH email (via companies table): {len(rows2)}")
    if rows2:
        print(f"\nTop opportunities (first 30):")
        for name, cui, email, phone, website, city, sn, date_f in rows2[:30]:
            print(f"  {name[:40]:40s} | {city or '':15s} | {email[:30]:30s} | filed: {date_f}")

    out_path = os.path.join(DATA_DIR, "bankrupt_food_opportunities.csv")
    if rows2:
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(["company", "cui", "email", "phone", "website",
                        "city", "sector", "date_filed"])
            w.writerows(rows2)
        print(f"\nExported to: {out_path}")

    return rows2


def export_all(conn_master, conn_food, output):
    """Export combined cross-match + opportunities."""
    from faliment_cross_match import flag_insolvent_contacts
    flagged = flag_insolvent_contacts(conn_master, conn_food)
    opps = find_opportunities(conn_master)

    all_rows = []
    for f in flagged:
        all_rows.append({
            "type": "insolvent_contact", "company": f["company"],
            "cui": f["insolvent_cui"], "email": f["email"],
            "category": f["category"], "county": f["county"],
        })
    for row in opps:
        all_rows.append({
            "type": "bankrupt_opportunity", "company": row[0],
            "cui": row[1], "email": row[2],
            "category": row[6] or "", "county": row[5] or "",
        })

    with open(output, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=["type", "company", "cui",
                                           "email", "category", "county"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nCombined export: {len(all_rows)} rows to {output}")
