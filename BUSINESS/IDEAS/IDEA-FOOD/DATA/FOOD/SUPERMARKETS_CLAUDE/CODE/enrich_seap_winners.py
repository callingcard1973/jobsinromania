#!/usr/bin/env python3
"""Enrich SEAP food winners with contact data from interjob_master + SSH sources.

Usage:
    python enrich_seap_winners.py --all         # Full pipeline (extract+enrich)
    python enrich_seap_winners.py --extract     # Extract from SEAP only
    python enrich_seap_winners.py --enrich      # Enrich existing extract
    python enrich_seap_winners.py --stats       # Show current stats
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

from shared_utils import normalize, DB_MASTER as DB
from seap_extract import extract_from_seap

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")
OUTPUT = os.path.join(DATA_DIR, "seap_food_winners_enriched.csv")

CONTRACTORS_CSV = "/opt/ACTIVE/OPENDATA/DATA/CONTRACTOR_MATCHES/contractors_enriched.csv"

OUT_COLS = ["winner_name", "cui", "email", "phone", "website", "city",
            "address", "sector", "wins", "total_value_ron",
            "distinct_buyers", "match_source"]


def enrich_internal(winners):
    """Enrich from all internal sources."""
    print("\nEnriching from internal sources...")
    enriched = {normalize(w["winner_name"]): {
        **w, "email": "", "phone": "", "website": "",
        "city": "", "address": "", "sector": "", "match_source": "",
    } for w in winners.values()}

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # -- Source 1: companies by CUI
    cuis = [w["cui"] for w in winners.values() if w.get("cui")]
    if cuis:
        batch_size = 500
        cui_matches = 0
        for i in range(0, len(cuis), batch_size):
            batch = cuis[i:i + batch_size]
            placeholders = ','.join(['%s'] * len(batch))
            cur.execute(f"""
                SELECT cui, email, phone, website, city, address, name, sector_name
                FROM companies WHERE cui IN ({placeholders})
                AND country = 'RO'
            """, batch)
            for cui, email, phone, website, city, addr, name, sector in cur:
                # Find winner by CUI
                for norm, e in enriched.items():
                    if e.get("cui") == cui and not e["email"]:
                        if email:
                            e["email"] = email
                            e["match_source"] = "companies_cui"
                        e["phone"] = e["phone"] or phone or ""
                        e["website"] = e["website"] or website or ""
                        e["city"] = e["city"] or city or ""
                        e["address"] = e["address"] or addr or ""
                        e["sector"] = e["sector"] or sector or ""
                        cui_matches += 1
                        break
        print(f"  Companies by CUI: {cui_matches} matches")

    # -- Source 2: companies by name
    cur.execute("""
        SELECT name, email, phone, website, city, address, cui, sector_name
        FROM companies WHERE country = 'RO'
        AND (email IS NOT NULL AND email != '' OR phone IS NOT NULL AND phone != '')
    """)
    by_name = {}
    for name, email, phone, website, city, addr, cui, sector in cur:
        norm = normalize(name)
        if not norm:
            continue
        rec = dict(email=email or "", phone=phone or "", website=website or "",
                   city=city or "", address=addr or "", cui=cui or "", sector=sector or "")
        if norm not in by_name or (email and not by_name[norm].get("email")):
            by_name[norm] = rec

    name_matches = prefix_matches = 0
    for norm, e in enriched.items():
        if e["email"]:
            continue
        if norm in by_name:
            rec = by_name[norm]
            if rec.get("email"):
                e["email"] = rec["email"]
                e["match_source"] = "companies_name"
            e["phone"] = e["phone"] or rec.get("phone", "")
            e["website"] = e["website"] or rec.get("website", "")
            e["city"] = e["city"] or rec.get("city", "")
            e["address"] = e["address"] or rec.get("address", "")
            e["sector"] = e["sector"] or rec.get("sector", "")
            e["cui"] = e["cui"] or rec.get("cui", "")
            name_matches += 1

    # Prefix match
    prefix_index = {}
    for n, rec in by_name.items():
        if len(n) >= 10 and rec.get("email"):
            px = n[:10]
            if px not in prefix_index:
                prefix_index[px] = rec

    for norm, e in enriched.items():
        if e["email"] or not norm or len(norm) < 10:
            continue
        px = norm[:10]
        if px in prefix_index:
            rec = prefix_index[px]
            e["email"] = rec["email"]
            e["phone"] = e["phone"] or rec.get("phone", "")
            e["website"] = e["website"] or rec.get("website", "")
            e["city"] = e["city"] or rec.get("city", "")
            e["cui"] = e["cui"] or rec.get("cui", "")
            e["match_source"] = "companies_prefix"
            prefix_matches += 1

    print(f"  Companies by name: {name_matches} exact, {prefix_matches} prefix")
    conn.close()

    # -- Source 3: contractors_enriched.csv (via SSH)
    import subprocess
    cmd = ["ssh", "tudor@192.168.100.21",
           "python3", "-c", f"""
import csv, json
data = {{}}
try:
    with open('{CONTRACTORS_CSV}', 'r', encoding='utf-8', errors='ignore') as f:
        for row in csv.DictReader(f):
            cui = row.get('cui', '').strip()
            email = row.get('email', '').strip()
            if cui and email:
                data[cui] = {{'email': email, 'phone': row.get('phone', ''),
                             'website': row.get('website', '')}}
except: pass
print(json.dumps(data))
"""]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    contractor_matches = 0
    if result.returncode == 0:
        contractors = __import__('json').loads(result.stdout)
        for norm, e in enriched.items():
            if e["email"] or not e.get("cui"):
                continue
            if e["cui"] in contractors:
                c = contractors[e["cui"]]
                e["email"] = c["email"]
                e["phone"] = e["phone"] or c.get("phone", "")
                e["website"] = e["website"] or c.get("website", "")
                e["match_source"] = "contractors_csv"
                contractor_matches += 1
    print(f"  Contractors CSV: {contractor_matches}")

    # Stats
    with_email = sum(1 for e in enriched.values() if e["email"])
    with_phone = sum(1 for e in enriched.values() if e["phone"])
    total = len(enriched)
    print(f"\n  TOTAL: {total}")
    print(f"  With email: {with_email} ({100 * with_email // total}%)")
    print(f"  With phone: {with_phone} ({100 * with_phone // total}%)")
    print(f"  No contact: {total - with_email}")

    # Export
    rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in OUT_COLS})
    print(f"\n  Exported: {OUTPUT}")
    return enriched


def show_stats():
    """Show current enrichment stats."""
    if not os.path.exists(OUTPUT):
        print("No enriched file yet. Run --all first.")
        return
    with open(OUTPUT, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    total = len(rows)
    with_email = sum(1 for r in rows if r.get("email"))
    with_phone = sum(1 for r in rows if r.get("phone"))
    with_cui = sum(1 for r in rows if r.get("cui"))
    print(f"Total winners: {total}")
    print(f"With email: {with_email} ({100 * with_email // total}%)")
    print(f"With phone: {with_phone} ({100 * with_phone // total}%)")
    print(f"With CUI: {with_cui}")
    print(f"No contact: {total - with_email}")

    # By match source
    sources = {}
    for r in rows:
        s = r.get("match_source", "") or "none"
        sources[s] = sources.get(s, 0) + 1
    print(f"\nBy source:")
    for s, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {s}: {cnt}")


def main():
    args = sys.argv[1:]

    if "--stats" in args:
        show_stats()
        return

    if "--all" in args or "--extract" in args:
        winners = extract_from_seap()
        if "--extract" not in args or "--all" in args:
            enrich_internal(winners)
        return

    if "--enrich" in args:
        # Load existing extracted data
        path = os.path.join(DATA_DIR, "seap_food_winners_with_cui.csv")
        if not os.path.exists(path):
            print("Run --extract first")
            return
        winners = {}
        with open(path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                norm = normalize(row["winner_name"])
                winners[norm] = row
        enrich_internal(winners)
        return

    print(__doc__)


if __name__ == "__main__":
    main()
