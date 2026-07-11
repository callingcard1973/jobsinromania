#!/usr/bin/env python3
import csv, os, sys
from common import setup, data_path, open_db, log

CFG = setup()
GRAIN_DB = data_path("grain.db")
OUTPUT_CSV = data_path("grain_matched_deals.csv")


def load_buyers():
    con = open_db("grain.db")
    if not con:
        log("ERROR: grain.db not found (run _PIPELINE/enrich_to_db.py first)")
        return []
    cur = con.execute("SELECT firma_cui, firma_nume, email_principal, telefon_fix, "
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
        log("psycopg2 unavailable")
        return []
    try:
        con = psycopg2.connect(**CFG.DB)
        cur = con.cursor()
        cur.execute("SELECT offer_id, product_ro, quantity_kg, price_per_unit, "
                    "currency, origin, supplier_email, from_email "
                    "FROM trading_offers WHERE category='cereal' ORDER BY offer_id DESC")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        con.close()
        return rows
    except Exception as e:
        log("PG error: %s" % e)
        return []


FIELD_NAMES = ["offer_id","product","quantity_kg","price","currency","origin",
               "cui","buyer","buyer_email","buyer_phone","buyer_caen",
               "buyer_city","buyer_county","gmp_certificat","insolventa",
               "rating_financiar","valoare_contracte"]


def main():
    do_csv = "--csv" in sys.argv
    offers = load_offers()
    buyers = load_buyers()

    print("=== Grain Buyer Match ===")
    print("  Oferte: %d  Cumparatori: %d" % (len(offers), len(buyers)))
    enriched = sum(1 for b in buyers if b["certificari_gmp"] or b["insolventa"] or b["rating_financiar"])
    print("    (enrich: %d)" % enriched)
    print()
    if not offers or not buyers:
        return 1

    rows_out = [dict(offer_id=o["offer_id"], product=o["product_ro"],
                     quantity_kg=o.get("quantity_kg") or "",
                     price=o.get("price_per_unit") or "",
                     currency=o.get("currency") or "",
                     origin=o.get("origin") or "",
                     cui=b["firma_cui"], buyer=b["firma_nume"],
                     buyer_email=b["email_principal"],
                     buyer_phone=b["telefon_fix"],
                     buyer_caen="4621", buyer_city=b["oras"],
                     buyer_county=b["judet"],
                     gmp_certificat="Y" if b["certificari_gmp"] else "",
                     insolventa=b["insolventa"],
                     rating_financiar=b["rating_financiar"],
                     valoare_contracte=b["valoare_contracte"])
                for o in offers for b in buyers]

    print("  Match-uri: %d" % len(rows_out))
    if do_csv:
        with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELD_NAMES)
            w.writeheader()
            w.writerows(rows_out)
        log("Scris: " + OUTPUT_CSV)
    else:
        log("Dry-run. Adauga --csv.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
