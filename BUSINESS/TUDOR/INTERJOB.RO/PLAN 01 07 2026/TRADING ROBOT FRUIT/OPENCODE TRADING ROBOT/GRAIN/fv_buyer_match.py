#!/usr/bin/env python3
import csv, json, os, sys
from common import setup, data_path, open_db, log

CFG = setup()
VEGFRU_DB = data_path("VegFru.db")
CONSERVE_FILE = os.path.join(os.path.dirname(os.path.dirname(CFG.ROOT)),
                              "COOP GOSPODARII DE ALTADATA", "DATA",
                              "DATE_fabrici_conserve_cerere.csv")
OUTPUT_JSONL = data_path("fv_matched_deals.jsonl")


def load_buyers():
    con = open_db("VegFru.db")
    if not con:
        log("ERROR: VegFru.db not found (run _PIPELINE/enrich_to_db.py first)")
        return []
    cur = con.execute("SELECT firma_cui, firma_nume, email_principal, telefon_fix, "
                      "caen_principal, oras, judet, certificari_gmp, insolventa, "
                      "rating_financiar, valoare_contracte "
                      "FROM trading_partners WHERE caen_principal='4631'")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    return rows


def load_fabrici():
    if not os.path.exists(CONSERVE_FILE):
        log("(fabrici conserve csv not found)")
        return []
    fabrici = []
    for r in csv.DictReader(open(CONSERVE_FILE, encoding="utf-8")):
        fabrici.append(dict(firma_cui="", firma_nume=r.get("factory_name", "?"),
                            email_principal=r.get("email", ""),
                            telefon_fix=r.get("phone", ""), caen_principal="FABRICA",
                            oras=r.get("city", ""), judet="",
                            certificari_gmp="", insolventa="",
                            rating_financiar="", valoare_contracte="",
                            buyer_source="fabrica_conserve",
                            buyer_products=(r.get("products") or r.get("raw_demand") or "")))
    return fabrici


def load_offers():
    path = data_path("offers_ledger.jsonl")
    if not os.path.exists(path):
        alt = os.path.join(os.path.dirname(CFG.ROOT), "DATA", "offers_ledger.jsonl")
        if os.path.exists(alt):
            path = alt
    if not os.path.exists(path):
        log("offers_ledger.jsonl not found")
        return []
    offers = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        offer = json.loads(line)
        if offer.get("entry_type") == "offer":
            offers.append(offer)
    return offers


def main():
    do_json = "--json" in sys.argv
    offers = load_offers()
    buyers = load_buyers()
    fabrici = load_fabrici()

    print("=== FV Buyer Match ===")
    print("  Oferte: %d  CAEN 4631: %d  Fabrici: %d" % (len(offers), len(buyers), len(fabrici)))
    enriched = sum(1 for b in buyers if b["certificari_gmp"] or b["insolventa"] or b["rating_financiar"])
    print("    (enrich: %d)" % enriched)
    print()
    if not offers:
        log("Nici o oferta.")
        return 0

    all_buyers = buyers + fabrici
    lines_out = [dict(offer_id=o.get("offer_id") or o.get("source_email_id", "?"),
                      product=o.get("product_ro", "?"),
                      quantity_kg=o.get("quantity_kg") or "",
                      price=o.get("price_per_unit") or o.get("price") or "",
                      currency=o.get("currency") or o.get("price_currency") or "",
                      origin=o.get("origin") or "",
                      supplier_email=o.get("from_email", ""),
                      cui=b.get("firma_cui", ""),
                      buyer=b.get("firma_nume", "?"),
                      buyer_email=b.get("email_principal", ""),
                      buyer_phone=b.get("telefon_fix", ""),
                      buyer_source=b.get("buyer_source", "caen4631"),
                      buyer_city=b.get("oras", ""),
                      buyer_judet=b.get("judet", ""),
                      gmp_certificat="Y" if b.get("certificari_gmp") else "",
                      insolventa=b.get("insolventa", ""),
                      rating_financiar=b.get("rating_financiar", ""),
                      valoare_contracte=b.get("valoare_contracte", ""),
                      buyer_products=b.get("buyer_products") or "")
                 for o in offers for b in all_buyers]

    print("  Match-uri: %d" % len(lines_out))
    if do_json:
        with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
            for d in lines_out:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        log("Scris: " + OUTPUT_JSONL)
    else:
        log("Dry-run. Adauga --json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
