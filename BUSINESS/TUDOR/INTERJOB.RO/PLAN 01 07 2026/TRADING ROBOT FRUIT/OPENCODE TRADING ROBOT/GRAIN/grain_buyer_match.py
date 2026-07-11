#!/usr/bin/env python3
"""Match cereale offers (PG) to all CAEN 4621 traders. Fara scoruri.

Usage:
  python GRAIN/grain_buyer_match.py              # report
  python GRAIN/grain_buyer_match.py --csv         # write matched deals
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(HERE), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import config as CFG

BUYERS_FILE = os.path.join(CFG.DATA, "producers_by_caen", "enriched_final.csv")
OUTPUT_CSV = os.path.join(CFG.DATA, "grain_matched_deals.csv")


def load_buyers():
    path = BUYERS_FILE
    if not os.path.exists(path):
        path = os.path.join(CFG.DATA, "enriched_final.csv")
    if not os.path.exists(path):
        print("ERROR: enriched_final.csv not found", file=sys.stderr)
        return []
    buyers = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("caen", "").strip() == "4621":
                buyers.append(r)
    return buyers


def load_offers():
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 unavailable", file=sys.stderr)
        return []
    con = psycopg2.connect(**CFG.DB)
    cur = con.cursor()
    cur.execute("""SELECT offer_id, product_ro, quantity_kg, price_per_unit,
                          currency, origin, supplier_email, from_email
                   FROM trading_offers WHERE category='cereal'
                   ORDER BY offer_id DESC""")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    con.close()
    return rows


def main():
    do_csv = "--csv" in sys.argv

    offers = load_offers()
    buyers = load_buyers()

    print("=== Grain Buyer Match ===")
    print("  Oferte cereale PG: %d" % len(offers))
    print("  Cumparatori CAEN 4621: %d" % len(buyers))
    print()

    if not offers or not buyers:
        return 1

    rows_out = []
    for off in offers:
        for b in buyers:
            rows_out.append({
                "offer_id": off["offer_id"],
                "product": off["product_ro"],
                "quantity_kg": off.get("quantity_kg") or "",
                "price": off.get("price_per_unit") or "",
                "currency": off.get("currency") or "",
                "origin": off.get("origin") or "",
                "cui": b.get("cui", ""),
                "buyer": b.get("name", "?"),
                "buyer_email": b.get("email", ""),
                "buyer_phone": b.get("phone", ""),
                "buyer_caen": "4621",
                "buyer_city": b.get("city", ""),
                "buyer_county": b.get("county", ""),
                "buyer_website": b.get("website", ""),
            })

    print("  Total match-uri: %d" % len(rows_out))

    if do_csv:
        with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "offer_id", "product", "quantity_kg", "price", "currency",
                "origin", "cui", "buyer", "buyer_email", "buyer_phone",
                "buyer_caen", "buyer_city", "buyer_county", "buyer_website",
            ])
            w.writeheader()
            w.writerows(rows_out)
        print("  Scris: %s" % OUTPUT_CSV)
    else:
        print("  Dry-run. Adauga --csv pentru a scrie.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
