#!/usr/bin/env python3
"""Trading Robot LEGUME-FRUCTE: potriveste producatori (supply) cu cumparatori (demand).

Supply  = producatori via-profi (cu produse reale: rosii, ardei, castraveti...).
Demand  = cumparatori locali (lanturi RO) + cumparatori internationali (export).
Produse normalizate multilingv (RO/EN/DE/IT/FR/PL) prin legume_taxonomy => match cross-limba.
Scrie rezultatele in CLAUDE TRADING ROBOT/. NU trimite emailuri.

DEPRECATED matching: round-robin buyer pairing. For demand-driven matching use CODE/fv_request_supplier_matcher.py.
"""
import csv
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASE, "CODE"))
import legume_taxonomy as tax  # noqa: E402

SRC = os.path.join(BASE, "..", "COOP GOSPODARII DE ALTADATA", "SURSE_IUNIE", "SUPERMARKETURI")
SUPPLY_CSV = os.path.join(SRC, "FURNIZORI", "DATA", "via_profi_producers_complete_scraped.csv")
DEMAND_LOCAL_CSV = os.path.join(SRC, "DATA", "SUPPLIERS", "vegetable_buyers_master.csv")
DEMAND_INTL_CSV = os.path.join(SRC, "EXPORT", "DATA", "eu_wholesale_buyers_master.csv")
OUT_DIR = os.path.join(BASE, "CLAUDE TRADING ROBOT")

MAX_LOCAL = 3   # cumparatori locali propusi / producator
MAX_INTL = 2    # cumparatori intl propusi / producator export-capabil


def _split_products(raw):
    """Extrage doar tokenii care sunt legume-fructe cunoscute (normalizate canonic)."""
    out = set()
    for chunk in (raw or "").replace("|", ",").split(","):
        t = tax.normalize_tag(chunk)
        if tax.is_produce(t):
            out.add(t)
    return out


def load_supply():
    out = []
    with open(SUPPLY_CSV, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            email = (r.get("email") or "").strip()
            phone = (r.get("phone") or "").strip()
            if not email and not phone:
                continue
            products = _split_products(r.get("products"))
            if not products:
                continue  # WHY: fara produs identificabil nu putem face trade pe fruct
            out.append({
                "name": (r.get("name") or "").strip(),
                "email": email, "phone": phone,
                "county": (r.get("county") or "").strip().upper(),
                "products": products,
                "export": bool((r.get("website") or "").strip()),
            })
    return out


def load_local_buyers():
    out = []
    with open(DEMAND_LOCAL_CSV, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            email = (r.get("email") or "").strip()
            if not email:
                continue
            out.append({
                "name": (r.get("name") or "").strip(),
                "email": email,
                "chain": (r.get("chain") or "").strip(),
                "loc": ((r.get("city") or "") + " " + (r.get("country") or "")).strip().upper(),
            })
    return out


def load_intl_buyers():
    out = []
    with open(DEMAND_INTL_CSV, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            email = (r.get("email") or "").strip()
            if not email:
                continue
            out.append({"email": email, "country": (r.get("country") or "").strip()})
    return out


def run():
    supply = load_supply()
    local = load_local_buyers()
    intl = load_intl_buyers()
    matches = []
    nl, ni = len(local), len(intl)
    for i, s in enumerate(supply):
        prod = ",".join(sorted(s["products"]))
        # local: preferential acelasi judet, altfel pool national rotativ (index stabil)
        same = [b for b in local if s["county"] and s["county"] in b["loc"]]
        pool = same if same else [local[(i + k) % nl] for k in range(MAX_LOCAL)] if nl else []
        for b in pool[:MAX_LOCAL]:
            matches.append({"scope": "local", "product": prod,
                            "producer": s["name"], "producer_email": s["email"],
                            "producer_phone": s["phone"], "county": s["county"],
                            "buyer": b["chain"] or b["name"], "buyer_email": b["email"]})
        # intl: doar producatori export-capabili (au website)
        if s["export"] and ni:
            for k in range(MAX_INTL):
                b = intl[(i + k) % ni]
                matches.append({"scope": "intl", "product": prod,
                                "producer": s["name"], "producer_email": s["email"],
                                "producer_phone": s["phone"], "county": s["county"],
                                "buyer": "EU wholesale " + (b["country"] or "?"),
                                "buyer_email": b["email"]})
    return supply, local, intl, matches


def write_outputs(supply, local, intl, matches):
    os.makedirs(OUT_DIR, exist_ok=True)
    cols = ["scope", "product", "producer", "producer_email", "producer_phone",
            "county", "buyer", "buyer_email"]
    with open(os.path.join(OUT_DIR, "matches_legume_fructe.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(matches)

    prod_count = defaultdict(int)
    for s in supply:
        for p in s["products"]:
            prod_count[p] += 1
    exporters = sum(1 for s in supply if s["export"])
    n_local_m = sum(1 for m in matches if m["scope"] == "local")
    n_intl_m = sum(1 for m in matches if m["scope"] == "intl")
    with open(os.path.join(OUT_DIR, "REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("# Trading Robot LEGUME-FRUCTE - rezultate\n\n")
        fh.write("Producatori cu produs identificabil (supply): %d\n" % len(supply))
        fh.write("  din care export-capabili (au website): %d\n" % exporters)
        fh.write("Cumparatori locali contactabili (demand): %d\n" % len(local))
        fh.write("Cumparatori internationali (export): %d\n" % len(intl))
        fh.write("Match-uri propuse: %d (local %d + intl %d)\n\n"
                 % (len(matches), n_local_m, n_intl_m))
        fh.write("Top produse oferite de producatori:\n")
        for p, n in sorted(prod_count.items(), key=lambda x: -x[1])[:15]:
            fh.write("  %-14s %d producatori\n" % (p, n))
        fh.write("\nFisier: matches_legume_fructe.csv. NU s-a trimis niciun email.\n")
    return len(supply), len(local), len(intl)


def main():
    print("WARNING: trading_robot.py uses deprecated round-robin pairing; prefer fv_request_supplier_matcher.py", file=sys.stderr)
    supply, local, intl, matches = run()
    ns, nl, ni = write_outputs(supply, local, intl, matches)
    print("supply=%d local_buyers=%d intl_buyers=%d matches=%d -> %s"
          % (ns, nl, ni, len(matches), OUT_DIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
