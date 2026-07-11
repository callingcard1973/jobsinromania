#!/usr/bin/env python3
import csv, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(HERE), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import config as CFG

GRAIN_DB = os.path.join(CFG.DATA, "grain.db")
OUTPUT_CSV = os.path.join(CFG.DATA, "grain_matched_deals.csv")


def load_buyers():
    path = GRAIN_DB
    if not os.path.exists(path):
        print("ERROR: %s not found (run GRAIN/_PIPELINE/enrich_to_db.py first)" % path, file=sys.stderr)
        return []
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT firma_cui, firma_nume, email_principal, telefon_fix, "
                "caen_principal, oras, judet, certificari_gmp, insolventa, "
                "rating_financiar, valoare_contracte "
                "FROM trading_partners WHERE caen_principal='4621'")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    return rows


def load_offers():
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 unavailable", file=sys.stderr)
        return []
    try:
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
    except Exception as e:
        print("  (nu pot citi PG trading_offers: %s)" % e, file=sys.stderr)
        return []


def main():
    do_csv = "--csv" in sys.argv

    offers = load_offers()
    buyers = load_buyers()

    print("=== Grain Buyer Match (SQLite) ===")
    print("  Oferte cereale PG: %d" % len(offers))
    print("  Cumparatori CAEN 4621 (grain.db): %d" % len(buyers))
    enriched = sum(1 for b in buyers if b["certificari_gmp"] or b["insolventa"] or b["rating_financiar"])
    print("    din care cu date enrich: %d" % enriched)
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
                "cui": b["firma_cui"],
                "buyer": b["firma_nume"],
                "buyer_email": b["email_principal"],
                "buyer_phone": b["telefon_fix"],
                "buyer_caen": "4621",
                "buyer_city": b["oras"],
                "buyer_county": b["judet"],
                "gmp_certificat": "Y" if b["certificari_gmp"] else "",
                "insolventa": b["insolventa"],
                "rating_financiar": b["rating_financiar"],
                "valoare_contracte": b["valoare_contracte"],
            })

    print("  Total match-uri: %d" % len(rows_out))

    if do_csv:
        with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "offer_id", "product", "quantity_kg", "price", "currency",
                "origin", "cui", "buyer", "buyer_email", "buyer_phone",
                "buyer_caen", "buyer_city", "buyer_county",
                "gmp_certificat", "insolventa", "rating_financiar", "valoare_contracte",
            ])
            w.writeheader()
            w.writerows(rows_out)
        print("  Scris: %s" % OUTPUT_CSV)
    else:
        print("  Dry-run. Adauga --csv pentru a scrie.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
