#!/usr/bin/env python3
"""Cross-match SEAP food winners with food_distribution contacts.

Also provides tender export functionality.
"""

import csv
import os

from shared_utils import normalize

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")


def _safe_query(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params or ())
    return cur.fetchall(), [d[0] for d in cur.description]


def cross_match(conn_master, conn_food):
    """Cross-match SEAP winners with food_distribution contacts."""
    print(f"\n{'=' * 60}")
    print("CROSS-MATCH: SEAP Winners vs Food Distribution DB")
    print("=" * 60)

    rows, _ = _safe_query(conn_master, """
        SELECT DISTINCT winner_name FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
        AND winner_name IS NOT NULL AND winner_name != ''
    """)
    seap_winners = {}
    for (name,) in rows:
        norm = normalize(name)
        if norm and len(norm) >= 4:
            seap_winners[norm] = name

    print(f"SEAP food winners (normalized): {len(seap_winners)}")

    rows, _ = _safe_query(conn_food, """
        SELECT company, email, category, county FROM contacts
        WHERE company IS NOT NULL AND company != ''
    """)
    food_contacts = {}
    for company, email, cat, county in rows:
        norm = normalize(company)
        if norm and len(norm) >= 4:
            food_contacts[norm] = {
                "company": company, "email": email or "",
                "category": cat or "", "county": county or "",
            }

    print(f"Food distribution contacts (normalized): {len(food_contacts)}")

    # Exact match
    matches = []
    for norm, orig_name in seap_winners.items():
        if norm in food_contacts:
            rec = food_contacts[norm]
            matches.append({
                "seap_winner": orig_name,
                "fd_company": rec["company"],
                "email": rec["email"],
                "category": rec["category"],
                "county": rec["county"],
            })

    print(f"\nExact name matches: {len(matches)}")

    # Prefix match (first 12 chars)
    prefix_matches = []
    seap_prefixes = {k[:12]: v for k, v in seap_winners.items() if len(k) >= 12}
    for norm, rec in food_contacts.items():
        if len(norm) < 12:
            continue
        px = norm[:12]
        if px in seap_prefixes and norm not in seap_winners:
            prefix_matches.append({
                "seap_winner": seap_prefixes[px],
                "fd_company": rec["company"],
                "email": rec["email"],
                "category": rec["category"],
                "county": rec["county"],
            })

    print(f"Prefix matches (12-char): {len(prefix_matches)}")

    all_matches = matches + prefix_matches
    if all_matches:
        print(f"\nMatched companies (first 30):")
        for m in all_matches[:30]:
            email_flag = " [HAS EMAIL]" if m["email"] else ""
            print(f"  {m['seap_winner'][:45]:45s} | {m['category']:12s} | "
                  f"{m['county']:15s}{email_flag}")

    with_email = [m for m in all_matches if m["email"]]
    print(f"\nWith email: {len(with_email)} (contactable for tender alerts)")

    out_path = os.path.join(DATA_DIR, "seap_food_overlap.csv")
    if all_matches:
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=all_matches[0].keys())
            w.writeheader()
            w.writerows(all_matches)
        print(f"Exported to: {out_path}")

    return all_matches


def export_tenders(conn, output):
    """Export all Romanian food tenders to CSV."""
    rows, headers = _safe_query(conn, """
        SELECT ted_id, title, buyer_name, winner_name,
               value, currency, date_published, date_awarded,
               cpv_code, source
        FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
        ORDER BY date_published DESC
    """)
    with open(output, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    print(f"Exported {len(rows)} food tenders to {output}")
