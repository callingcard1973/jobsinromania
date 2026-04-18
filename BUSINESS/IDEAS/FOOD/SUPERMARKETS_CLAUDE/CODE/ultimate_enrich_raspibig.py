#!/usr/bin/env python3
"""Ultimate enrichment: SQLite index (3.5M) + ANAF API + rapidfuzz.

Run ON raspibig: python3 /tmp/ultimate_enrich_raspibig.py

Pass 1: CUI exact match vs SQLite enrichment_index (3.5M companies)
Pass 2: Normalized name exact match vs SQLite index
Pass 3: rapidfuzz prefix-bucket matching (85%+ threshold)
Pass 4: ANAF API bulk lookup (100 CUIs/request) for phone/address
"""

import sqlite3
import time
from collections import defaultdict

from shared_utils import (normalize as norm, load_enriched, save_enriched,
                          apply_match, print_stats, SEAP_COLS as COLS)

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
INDEX_DB = "/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_INDEX/enrichment_index.db"

try:
    from rapidfuzz import fuzz
    FUZZY = True
except ImportError:
    FUZZY = False


def main():
    enriched = load_enriched(ENRICHED)
    need_email = {c: r for c, r in enriched.items()
                  if not r.get("email") and c}
    need_phone = {c: r for c, r in enriched.items()
                  if not r.get("phone") and c}
    print(f"Total: {len(enriched)}, need email: {len(need_email)}, need phone: {len(need_phone)}")

    conn = sqlite3.connect(INDEX_DB)
    cur = conn.cursor()
    total_new_email = 0
    total_new_phone = 0

    # -- Pass 1: CUI exact match (indexed, fast)
    print("\nPass 1: CUI exact match vs enrichment index...")
    hit_e, hit_p = 0, 0
    for cui in list(need_email.keys()):
        cur.execute(
            "SELECT email, phone, website, city, address FROM companies "
            "WHERE cui = ? AND email IS NOT NULL AND email != '' "
            "ORDER BY priority LIMIT 1", (cui,))
        row = cur.fetchone()
        if row and row[0]:
            apply_match(enriched, cui, row[0], row[1], row[2], row[3], row[4], "idx_cui")
            hit_e += 1
            del need_email[cui]
    # Phone-only pass for those with email but no phone
    for cui in list(need_phone.keys()):
        if cui not in enriched or enriched[cui].get("phone"):
            del need_phone[cui]
            continue
        cur.execute(
            "SELECT phone, city, address FROM companies "
            "WHERE cui = ? AND phone IS NOT NULL AND phone != '' "
            "ORDER BY priority LIMIT 1", (cui,))
        row = cur.fetchone()
        if row and row[0]:
            enriched[cui]["phone"] = row[0]
            enriched[cui]["city"] = enriched[cui].get("city") or row[1] or ""
            enriched[cui]["address"] = enriched[cui].get("address") or row[2] or ""
            hit_p += 1
            del need_phone[cui]
    print(f"  CUI match: {hit_e} emails, {hit_p} phones")
    total_new_email += hit_e
    total_new_phone += hit_p

    # -- Pass 2: Normalized name exact match
    print("\nPass 2: Name exact match vs enrichment index...")
    hit_e = 0
    for cui in list(need_email.keys()):
        n = norm(enriched[cui].get("winner_name", ""))
        if not n or len(n) < 4:
            continue
        cur.execute(
            "SELECT email, phone, website, city, address FROM companies "
            "WHERE name_normalized = ? AND email IS NOT NULL AND email != '' "
            "ORDER BY priority LIMIT 1", (n,))
        row = cur.fetchone()
        if row and row[0]:
            apply_match(enriched, cui, row[0], row[1], row[2], row[3], row[4], "idx_name")
            hit_e += 1
            del need_email[cui]
    print(f"  Name match: {hit_e} emails")
    total_new_email += hit_e

    # -- Pass 3: rapidfuzz prefix-bucket matching
    if FUZZY:
        print("\nPass 3: rapidfuzz prefix-bucket matching (threshold 85%)...")
        # Build prefix buckets from index (only companies with email)
        buckets = defaultdict(list)
        cur.execute(
            "SELECT name_normalized, email, phone, website, city, address "
            "FROM companies WHERE email IS NOT NULL AND email != ''")
        idx_count = 0
        for row in cur:
            n = row[0]
            if n and len(n) >= 3:
                prefix = n[:3]
                buckets[prefix].append(row)
                idx_count += 1
        print(f"  Index: {idx_count} companies with email in {len(buckets)} buckets")

        hit_e = 0
        for cui in list(need_email.keys()):
            n = norm(enriched[cui].get("winner_name", ""))
            if not n or len(n) < 5:
                continue
            prefix = n[:3]
            candidates = buckets.get(prefix, [])
            best_score, best_row = 0, None
            for row in candidates:
                score = fuzz.ratio(n, row[0])
                if score > best_score:
                    best_score = score
                    best_row = row
            if best_score >= 85 and best_row:
                apply_match(enriched, cui, best_row[1], best_row[2],
                            best_row[3], best_row[4], best_row[5],
                            f"rapidfuzz:{best_score}")
                hit_e += 1
                del need_email[cui]
        print(f"  rapidfuzz: {hit_e} emails")
        total_new_email += hit_e
    else:
        print("\nPass 3: SKIPPED (no rapidfuzz)")

    conn.close()

    # -- Pass 4: ANAF API for phone/address (remaining without phone)
    print("\nPass 4: ANAF API bulk lookup for phone/address...")
    try:
        import requests
        need_anaf = [c for c, r in enriched.items()
                     if not r.get("phone") and c and c.isdigit()]
        print(f"  {len(need_anaf)} CUIs need phone from ANAF")
        hit_p = 0
        for i in range(0, len(need_anaf), 100):
            batch = need_anaf[i:i + 100]
            payload = [{"cui": int(c), "data": "2026-03-08"} for c in batch]
            try:
                resp = requests.post(
                    "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva",
                    json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("found", []):
                        dd = item.get("date_generale", {})
                        cui_str = str(dd.get("cui", ""))
                        phone = dd.get("telefon", "").strip()
                        addr = dd.get("adresa", "").strip()
                        city_val = dd.get("localitate", "").strip()
                        if cui_str in enriched:
                            if phone and not enriched[cui_str].get("phone"):
                                enriched[cui_str]["phone"] = phone
                                hit_p += 1
                            if addr and not enriched[cui_str].get("address"):
                                enriched[cui_str]["address"] = addr
                            if city_val and not enriched[cui_str].get("city"):
                                enriched[cui_str]["city"] = city_val
            except Exception as ex:
                print(f"    ANAF batch error: {ex}")
            time.sleep(1.1)
            if (i + 100) % 500 == 0:
                print(f"    {i + 100}/{len(need_anaf)} queried, {hit_p} phones")
        print(f"  ANAF API: {hit_p} new phones")
        total_new_phone += hit_p
    except ImportError:
        print("  SKIPPED (no requests)")

    # -- Stats
    print(f"\nNEW this run: {total_new_email} emails, {total_new_phone} phones")
    print_stats(enriched)
    save_enriched(enriched, ENRICHED, COLS)
    print(f"\nSaved: {ENRICHED}")


if __name__ == "__main__":
    main()
