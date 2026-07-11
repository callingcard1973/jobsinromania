#!/usr/bin/env python3
import csv, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(HERE), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import config as CFG

VEGFRU_DB = os.path.join(CFG.DATA, "VegFru.db")
CONSERVE_FILE = os.path.join(os.path.dirname(os.path.dirname(CFG.ROOT)),
                              "COOP GOSPODARII DE ALTADATA", "DATA",
                              "DATE_fabrici_conserve_cerere.csv")
OUTPUT_JSONL = os.path.join(CFG.DATA, "fv_matched_deals.jsonl")


def load_buyers_from_db():
    path = VEGFRU_DB
    if not os.path.exists(path):
        print("ERROR: %s not found (run GRAIN/_PIPELINE/enrich_to_db.py first)" % path, file=sys.stderr)
        return []
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT firma_cui, firma_nume, email_principal, telefon_fix, "
                "caen_principal, oras, judet, certificari_gmp, insolventa, "
                "rating_financiar, valoare_contracte "
                "FROM trading_partners WHERE caen_principal='4631'")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    return rows


def load_fabrici_conserve():
    path = CONSERVE_FILE
    if not os.path.exists(path):
        print("  (fabrici conserve csv not found: %s)" % path, file=sys.stderr)
        return []
    fabrici = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fabrici.append({
                "firma_cui": "",
                "firma_nume": r.get("factory_name", "?"),
                "email_principal": r.get("email", ""),
                "telefon_fix": r.get("phone", ""),
                "caen_principal": "FABRICA",
                "oras": r.get("city", ""),
                "judet": "",
                "certificari_gmp": "",
                "insolventa": "",
                "rating_financiar": "",
                "valoare_contracte": "",
                "buyer_source": "fabrica_conserve",
                "buyer_products": r.get("products", "") or r.get("raw_demand", ""),
            })
    return fabrici


def load_fv_offers():
    path = os.path.join(CFG.DATA, "offers_ledger.jsonl")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(CFG.ROOT), "DATA", "offers_ledger.jsonl")
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
    buyers_4631 = load_buyers_from_db()
    fabrici = load_fabrici_conserve()

    print("=== FV Buyer Match (SQLite) ===")
    print("  Oferte FV (ledger):  %d" % len(offers))
    print("  Cumparatori CAEN 4631 (VegFru.db): %d" % len(buyers_4631))
    enriched = sum(1 for b in buyers_4631 if b["certificari_gmp"] or b["insolventa"] or b["rating_financiar"])
    print("    din care cu date enrich: %d" % enriched)
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
                "cui": b.get("firma_cui", ""),
                "buyer": b.get("firma_nume", "?"),
                "buyer_email": b.get("email_principal", ""),
                "buyer_phone": b.get("telefon_fix", ""),
                "buyer_source": b.get("buyer_source", "caen4631"),
                "buyer_city": b.get("oras", ""),
                "buyer_judet": b.get("judet", ""),
                "gmp_certificat": "Y" if b.get("certificari_gmp") else "",
                "insolventa": b.get("insolventa", ""),
                "rating_financiar": b.get("rating_financiar", ""),
                "valoare_contracte": b.get("valoare_contracte", ""),
                "buyer_products": b.get("buyer_products") or "",
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
