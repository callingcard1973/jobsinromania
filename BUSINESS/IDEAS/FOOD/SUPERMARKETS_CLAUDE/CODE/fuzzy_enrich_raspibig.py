#!/usr/bin/env python3
"""Fuzzy (trigram) enrichment for SEAP food winners on raspibig.

Uses pg_trgm similarity to match winner names against companies table.
Run ON raspibig: python3 /tmp/fuzzy_enrich_raspibig.py

Threshold: 0.45 similarity (tuned for Romanian company names).
"""

import psycopg2

from shared_utils import (normalize as norm, load_enriched, save_enriched,
                          print_stats, SEAP_COLS as COLS)

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
THRESHOLD = 0.45
BATCH = 50


def main():
    enriched = load_enriched(ENRICHED)

    need = [(cui, r) for cui, r in enriched.items()
            if not r.get("email") and cui and len(norm(r.get("winner_name", ""))) >= 5]
    print(f"Need email: {len(need)}")

    conn = psycopg2.connect(dbname="interjob_master", user="tudor", password="tudor")
    cur = conn.cursor()

    # Ensure pg_trgm is available
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.commit()
    cur.execute("SET pg_trgm.similarity_threshold = %s", (THRESHOLD,))

    # Pass 1: Fuzzy match against companies (name with email)
    print(f"Pass 1: Fuzzy vs companies (threshold={THRESHOLD})...")
    hit = 0
    for i in range(0, len(need), BATCH):
        batch = need[i:i + BATCH]
        for cui, r in batch:
            if cui not in enriched or enriched[cui].get("email"):
                continue
            n = norm(r.get("winner_name", ""))
            if not n or len(n) < 5:
                continue
            cur.execute(
                "SELECT email, phone, website, city, address, sector_name, name, "
                "similarity(UPPER(name), %s) AS sim "
                "FROM companies "
                "WHERE country = 'RO' "
                "AND email IS NOT NULL AND email <> '' "
                "AND UPPER(name) %% %s "
                "ORDER BY sim DESC LIMIT 1",
                (n, n))
            row = cur.fetchone()
            if row and row[0]:
                enriched[cui]["email"] = row[0]
                enriched[cui]["phone"] = enriched[cui].get("phone") or row[1] or ""
                enriched[cui]["website"] = enriched[cui].get("website") or row[2] or ""
                enriched[cui]["city"] = enriched[cui].get("city") or row[3] or ""
                enriched[cui]["address"] = enriched[cui].get("address") or row[4] or ""
                enriched[cui]["sector"] = enriched[cui].get("sector") or row[5] or ""
                enriched[cui]["match_source"] = f"fuzzy:{row[7]:.2f}"
                hit += 1

        if (i + BATCH) % 200 == 0:
            print(f"  {i + BATCH}/{len(need)} processed, {hit} found")

    print(f"Pass 1 fuzzy: {hit} new emails")

    # Pass 2: Fuzzy match against food_distribution contacts
    print("Pass 2: Fuzzy vs food_distribution...")
    try:
        conn2 = psycopg2.connect(dbname="food_distribution", user="tudor", password="tudor")
        cur2 = conn2.cursor()
        cur2.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        conn2.commit()
        cur2.execute("SET pg_trgm.similarity_threshold = %s", (THRESHOLD,))

        hit2 = 0
        need2 = [(cui, r) for cui, r in enriched.items()
                 if not r.get("email") and cui and len(norm(r.get("winner_name", ""))) >= 5]
        for i in range(0, len(need2), BATCH):
            batch = need2[i:i + BATCH]
            for cui, r in batch:
                n = norm(r.get("winner_name", ""))
                if not n:
                    continue
                cur2.execute(
                    "SELECT email, phone, website, county, company, "
                    "similarity(UPPER(company), %s) AS sim "
                    "FROM contacts "
                    "WHERE email IS NOT NULL AND email <> '' "
                    "AND UPPER(company) %% %s "
                    "ORDER BY sim DESC LIMIT 1",
                    (n, n))
                row = cur2.fetchone()
                if row and row[0]:
                    enriched[cui]["email"] = row[0]
                    enriched[cui]["phone"] = enriched[cui].get("phone") or row[1] or ""
                    enriched[cui]["website"] = enriched[cui].get("website") or row[2] or ""
                    enriched[cui]["city"] = enriched[cui].get("city") or row[3] or ""
                    enriched[cui]["match_source"] = f"fuzzy_fd:{row[5]:.2f}"
                    hit2 += 1

            if (i + BATCH) % 200 == 0:
                print(f"  {i + BATCH}/{len(need2)} processed, {hit2} found")

        print(f"Pass 2 fuzzy food_distribution: {hit2} new emails")
        conn2.close()
    except Exception as ex:
        print(f"Pass 2 error: {ex}")

    conn.close()

    print_stats(enriched)
    save_enriched(enriched, ENRICHED, COLS)
    print(f"\nSaved: {ENRICHED}")


if __name__ == "__main__":
    main()
