#!/usr/bin/env python3
"""Match FV offers (ledger) to CAEN 4631 traders + fabrici conserve. Fara scoruri.

Usage:
  python GRAIN/fv_buyer_match.py              # report
  python GRAIN/fv_buyer_match.py --json        # write matched deals
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(HERE), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import config as CFG

BUYERS_FILE = os.path.join(CFG.DATA, "producers_by_caen", "enriched_final.csv")
CONSERVE_FILE = os.path.join(os.path.dirname(os.path.dirname(CFG.ROOT)),
                              "COOP GOSPODARII DE ALTADATA", "DATA",
                              "DATE_fabrici_conserve_cerere.csv")
OUTPUT_JSONL = os.path.join(CFG.DATA, "fv_matched_deals.jsonl")


def load_buyers_caen4631():
    path = BUYERS_FILE
    if not os.path.exists(path):
        path = os.path.join(CFG.DATA, "enriched_final.csv")
    if not os.path.exists(path):
        return []
    buyers = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("caen", "").strip() == "4631":
                buyers.append(r)
    return buyers


def load_fabrici_conserve():
    path = CONSERVE_FILE
    if not os.path.exists(path):
        print("  (fabrici conserve csv not found: %s)" % path, file=sys.stderr)
        return []
    fabrici = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fabrici.append({
                "cui": "",
                "name": r.get("factory_name", "?"),
                "email": r.get("email", ""),
                "phone": r.get("phone", ""),
                "city": r.get("city", ""),
                "website": r.get("website", ""),
                "products": r.get("products", ""),
                "raw_demand": r.get("raw_demand", ""),
            })
    return fabrici


def load_fv_offers():
    path = os.path.join(CFG.DATA, "offers_ledger.jsonl")
    if not os.path.exists(path):
        print("  offers_ledger.jsonl not found", file=sys.stderr)
        return []
    offers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            offer = json.loads(line)
            if offer.get("entry_type") == "offer":
                offers.append(offer)
    return offers


def main():
    do_json = "--json" in sys.argv

    offers = load_fv_offers()
    buyers_4631 = load_buyers_caen4631()
    fabrici = load_fabrici_conserve()

    print("=== FV Buyer Match ===")
    print("  Oferte FV (ledger):  %d" % len(offers))
    print("  Cumparatori CAEN 4631: %d" % len(buyers_4631))
    print("  Fabrici conserve:     %d" % len(fabrici))
    print()

    if not offers:
        print("  Nici o oferta.")
        return 0

    all_buyers = buyers_4631 + fabrici

    lines_out = []
    for off in offers:
        offer_id = off.get("offer_id") or off.get("source_email_id", "?")
        product = off.get("product_ro", "?")
        qty = off.get("quantity_kg") or ""
        price = off.get("price_per_unit") or off.get("price") or ""
        currency = off.get("currency") or off.get("price_currency") or ""
        origin = off.get("origin") or ""
        supplier_email = off.get("from_email", "")

        for b in all_buyers:
            deal = {
                "offer_id": offer_id,
                "product": product,
                "quantity_kg": qty,
                "price": price,
                "currency": currency,
                "origin": origin,
                "supplier_email": supplier_email,
                "cui": b.get("cui", ""),
                "buyer": b.get("name") or b.get("factory_name") or "?",
                "buyer_email": b.get("email", ""),
                "buyer_phone": b.get("phone", ""),
                "buyer_source": "caen4631" if b.get("caen") == "4631" else "fabrica_conserve",
                "buyer_city": b.get("city") or b.get("city", ""),
                "buyer_website": b.get("website", ""),
                "buyer_products": b.get("products") or b.get("raw_demand") or "",
            }
            lines_out.append(deal)

    print("  Total match-uri: %d" % len(lines_out))

    if do_json:
        with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
            for d in lines_out:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        print("  Scris: %s" % OUTPUT_JSONL)
    else:
        print("  Dry-run. Adauga --json pentru a scrie.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
