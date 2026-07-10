#!/usr/bin/env python3
"""Match inbound cereal offers to enriched traders/producers.

Reads:
  - PG `trading_offers` (category='cereal')
  - `enriched_final.csv` (12,360 CUI, CAEN 0111/0113/4621/4631, with contacts)

Writes: matched_deals.csv + console report.

Usage:
  python GRAIN/buyer_match.py                # match + report
  python GRAIN/buyer_match.py --csv          # also write matched_deals.csv
  python GRAIN/buyer_match.py --status       # counts only
"""
import csv
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(HERE), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import config as CFG

try:
    import psycopg2
except ImportError:
    psycopg2 = None

# Product -> (CAEN codes, keywords in company name)
# NOTE: Keep keywords specific to end-use, NOT generic ("agro","cereal" match everything).
MATCH_RULES = {
    "grau": {
        "caens": ["4621", "4631", "0111", "0113"],
        "kws": ["grau", "wheat", "moara", "faina", "panificatie", "morarit", "pain"],
    },
    "porumb": {
        "caens": ["4621", "4631", "0111", "0113"],
        "kws": ["porumb", "corn", "maize", "furaj", "nutritie", "animal"],
    },
    "orz": {
        "caens": ["4621", "4631", "0111", "0113"],
        "kws": ["orz", "barley", "malta", "berarie", "bere"],
    },
    "floarea-soarelui": {
        "caens": ["4621", "4631", "0111", "0113"],
        "kws": ["floarea", "sunflower", "ulei", "seminte", "oil", "seed"],
    },
    "rapita": {
        "caens": ["4621", "4631", "0111", "0113"],
        "kws": ["rapita", "rapeseed", "canola", "ulei", "oil"],
    },
    "soia": {
        "caens": ["4621", "4631", "0111", "0113"],
        "kws": ["soia", "soy", "soya", "oleaginos"],
    },
    "naut": {
        "caens": ["4621", "4631", "0111", "0113"],
        "kws": ["naut", "chickpea", "legume"],
    },
}

ROMANIAN_COUNTIES = {
    "Alba", "Arad", "Arges", "Argeș", "Bacau", "Bacău", "Bihor", "Bistrita-Nasaud",
    "Bistrița-Năsăud", "Botosani", "Botoșani", "Braila", "Brăila", "Brasov", "Brașov",
    "Bucuresti", "București", "Buzau", "Buzău", "Calarasi", "Călărași",
    "Caras-Severin", "Caraș-Severin", "Cluj", "Constanta", "Constanța", "Covasna",
    "Dambovita", "Dâmbovița", "Dolj", "Galati", "Galați", "Giurgiu", "Gorj",
    "Harghita", "Hunedoara", "Ialomita", "Ialomița", "Iasi", "Iași", "Ilfov",
    "Maramures", "Maramureș", "Mehedinti", "Mehedinți", "Mures", "Mureș",
    "Neamt", "Neamț", "Olt", "Prahova", "Salaj", "Sălaj", "Satu Mare",
    "Sibiu", "Suceava", "Teleorman", "Timis", "Timiș", "Tulcea", "Valcea",
    "Vâlcea", "Vaslui", "Vrancea",
}


def load_buyers():
    path = os.path.join(CFG.DATA, "producers_by_caen", "enriched_final.csv")
    if not os.path.exists(path):
        path = os.path.join(CFG.DATA, "enriched_final.csv")
    if not os.path.exists(path):
        print("ERROR: enriched_final.csv not found in DATA/")
        return []
    buyers = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            buyers.append(r)
    return buyers


def load_offers():
    if psycopg2 is None:
        print("psycopg2 unavailable")
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


def extract_county(loc):
    """Extract county name from a location string."""
    if not loc:
        return ""
    for cty in sorted(ROMANIAN_COUNTIES, key=len, reverse=True):
        if cty.lower() in loc.lower():
            return cty
    return ""


def buyer_region_score(buyer, offer_county):
    """Score 3 if county matches, 1 otherwise."""
    if not offer_county:
        return 1
    bc = (buyer.get("county") or "").strip()
    if not bc:
        return 1
    if bc.lower() == offer_county.lower():
        return 3
    return 1


def match(buyers, offers):
    """Match each offer to best buyers. Returns list of match dicts."""
    matches = []
    for off in offers:
        product_key = off["product_ro"].strip().lower()
        # Normalize: "grau durum" -> "grau" for matching
        canon = product_key.split()[0] if product_key else ""
        rules = MATCH_RULES.get(canon)
        if not rules:
            # Try full product name
            for p, r in MATCH_RULES.items():
                if p in product_key:
                    rules = r
                    canon = p
                    break
        if not rules:
            print("  SKIP %s: no match rules for product '%s'" % (
                off["offer_id"], product_key))
            continue

        offer_county = extract_county(off.get("origin") or "")

        scored = []
        for b in buyers:
            bname = (b.get("name") or "").lower()
            b_caen = (b.get("caen") or "").strip()
            b_email = (b.get("email") or "").strip()
            b_phone = (b.get("phone") or "").strip()

            # CAEN filter: must match one of the target CAEN codes
            caen_match = b_caen in rules["caens"]
            # Keyword match
            kw_match = any(kw in bname for kw in rules["kws"])
            # Region score
            region = buyer_region_score(b, offer_county)

            score = 0
            if caen_match or kw_match:
                if caen_match:
                    score += 2  # generic trader but in right sector
                if kw_match:
                    score += 5  # specific product interest
                score += region

            if score > 0:
                scored.append({
                    "offer_id": off["offer_id"],
                    "product": off["product_ro"],
                    "quantity_kg": off.get("quantity_kg") or 0,
                    "price": off.get("price_per_unit") or 0,
                    "currency": off.get("currency") or "",
                    "origin": off.get("origin") or "",
                    "cui": b.get("cui", ""),
                    "buyer": b.get("name") or "?",
                    "buyer_email": b_email,
                    "buyer_phone": b_phone,
                    "buyer_caen": b_caen,
                    "buyer_localitate": b.get("city") or "",
                    "buyer_judet": b.get("county") or "",
                    "match_score": score,
                    "match_type": ("caen+produs" if caen_match and kw_match else
                                   "doar_caen" if caen_match else "produs_nume"),
                })

        scored.sort(key=lambda x: -x["match_score"])
        # Keep top matches only: min score 6 and cap at 200 per offer
        scored = [s for s in scored if s["match_score"] >= 6][:200]
        matches.append({"offer": off, "buyers": scored})

    return matches


def status(buyers, offers):
    """Print counts only."""
    print("=== Buyer Match Status ===")
    print("  Cereal offers (PG):    %d" % len(offers))
    print("  Enriched buyers:       %d" % len(buyers))
    caens = Counter(b.get("caen", "") for b in buyers)
    print("  CAEN distribution:")
    for c, n in caens.most_common():
        print("    %s: %d" % (c, n))
    print("  Buyers with email:     %d" %
          sum(1 for b in buyers if b.get("email") and "@" in (b.get("email") or "")))
    print("  Buyers with phone:     %d" %
          sum(1 for b in buyers if b.get("phone")))
    return 0


def print_match_report(matches):
    print("\n=== Buyer Match Report ===")
    for m in matches:
        off = m["offer"]
        buyers = m["buyers"]
        print("\n--- Offer: %s (%s)" % (off["offer_id"], off["product_ro"]))
        if off.get("quantity_kg"):
            print("    Qty: %.0f kg  Price: %s %s" % (
                off["quantity_kg"], off.get("price_per_unit") or "?",
                off.get("currency") or ""))
        if off.get("origin"):
            print("    Origin: %s" % off["origin"])
        print("    Matched buyers: %d" % len(buyers))
        if buyers:
            print("    Top 10:")
            for b in buyers[:10]:
                print("      [%d] %s (CAEN %s, %s, %s)" % (
                    b["match_score"], b["buyer"][:40],
                    b["buyer_caen"], b["buyer_judet"],
                    b["buyer_email"] or b["buyer_phone"][:15] or "-"))
        else:
            print("    (no matches)")


def write_matches_csv(matches, path=None):
    if not path:
        path = os.path.join(CFG.DATA, "matched_deals.csv")
    all_rows = []
    for m in matches:
        off = m["offer"]
        for b in m["buyers"]:
            all_rows.append({
                "offer_id": off["offer_id"],
                "product": off["product_ro"],
                "quantity_kg": off.get("quantity_kg") or 0,
                "price": off.get("price_per_unit") or 0,
                "currency": off.get("currency") or "",
                "origin": off.get("origin") or "",
                "cui": b["cui"],
                "buyer": b["buyer"],
                "buyer_email": b["buyer_email"],
                "buyer_phone": b["buyer_phone"],
                "buyer_caen": b["buyer_caen"],
                "buyer_judet": b["buyer_judet"],
                "match_score": b["match_score"],
                "match_type": b["match_type"],
            })
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "offer_id", "product", "quantity_kg", "price", "currency",
            "origin", "cui", "buyer", "buyer_email", "buyer_phone",
            "buyer_caen", "buyer_judet", "match_score", "match_type",
        ])
        writer.writeheader()
        writer.writerows(all_rows)
    print("\n  Scris: %s (%d matches)" % (path, len(all_rows)))
    return path


def main():
    do_csv = "--csv" in sys.argv
    do_status = "--status" in sys.argv

    buyers = load_buyers()
    if not buyers:
        return 1

    offers = load_offers()

    if do_status:
        return status(buyers, offers)

    print("=== Matching %d offers to %d buyers ===" % (len(offers), len(buyers)))
    matches = match(buyers, offers)
    print_match_report(matches)

    if do_csv:
        write_matches_csv(matches)

    total_matches = sum(len(m["buyers"]) for m in matches)
    print("\n  Total matches: %d (%.1f avg per offer)" % (
        total_matches, total_matches / max(len(matches), 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
