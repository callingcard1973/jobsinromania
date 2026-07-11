#!/usr/bin/env python3
"""Grain/port-specific landed-price calculator: origin county -> Constanta port.

Transport dominates thin grain margins, so a "cheap far" offer and a "pricey near"
offer are only comparable AFTER adding haulage. Given an offer's origin county
(+ qty), this computes delivered price to Constanta port (default) or a named buyer
silo, and returns an FOB-origin vs CPT-Constanta comparison.

Rates come from DATA/cereale_transport_rates.csv (per-county EUR/ton). Counties not
listed fall back to a km-band table. This is the GRAIN/PORT-specific module — it
does NOT touch the generic landed_price.py (owned by another task); if that generic
module exists it is only wrapped/consulted, never edited.

Internal/gated: pure calculation, nothing sent externally, no scores.
"""
import argparse
import csv
import json
import os
import re
import sys

RATES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                         "DATA", "cereale_transport_rates.csv")

# Fallback when a county is missing from the CSV: EUR/ton by road-distance band.
KM_BANDS = [
    (100, 7), (200, 12), (300, 17), (400, 22),
    (500, 28), (600, 33), (700, 38), (10 ** 9, 42),
]

_RATES = None


def load_rates(path=RATES_CSV):
    """Return {county_lower: {'km': float, 'eur_per_ton': float}}."""
    global _RATES
    if _RATES is not None:
        return _RATES
    _RATES = {}
    if not os.path.exists(path):
        return _RATES
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            if line.lower().startswith("county,"):
                continue
            parts = [p.strip() for p in line.rstrip("\n").split(",")]
            if len(parts) < 3:
                continue
            county, km, rate = parts[0], parts[1], parts[2]
            try:
                _RATES[county.lower()] = {"km": float(km), "eur_per_ton": float(rate)}
            except ValueError:
                continue
    return _RATES


def _county_from_origin(origin):
    """Extract a bare county name from an origin string like 'Romania, Ialomita'."""
    if not origin:
        return None
    s = re.sub(r"^\s*romania\s*,?\s*", "", origin.strip(), flags=re.IGNORECASE)
    s = re.sub(r"^jud\.?\s*", "", s.strip(), flags=re.IGNORECASE)
    return s.strip() or None


def transport_eur_per_ton(county):
    """Per-ton haulage county->Constanta. Uses CSV, else km-band fallback."""
    rates = load_rates()
    if not county:
        return None, "unknown-county"
    key = county.strip().lower()
    if key in rates:
        return rates[key]["eur_per_ton"], "csv"
    # No county row: cannot know km, so use a conservative mid band.
    return KM_BANDS[3][1], "fallback-midband"


def _to_eur_per_ton(offer):
    """Normalize an offer's price to EUR/ton. Handles per_ton and per_kg bases."""
    price = offer.get("price_per_unit")
    if price is None:
        return None, offer.get("currency") or "EUR"
    cur = (offer.get("currency") or "EUR").upper()
    basis = offer.get("price_basis")
    if basis == "per_ton":
        return float(price), cur
    # F&V-style per-kg price -> per ton.
    if offer.get("quantity_kg") and not offer.get("quantity_tons"):
        return float(price) * 1000.0, cur
    return float(price) * 1000.0, cur


def get_landed_constanta(offer, destination="Constanta port"):
    """Return FOB-origin vs CPT-Constanta comparison for a grain offer.

    offer: dict with origin, price_per_unit, currency, price_basis, quantity_tons.
    Returns a dict; transport in EUR/ton (RON offers keep currency, transport noted).
    """
    county = _county_from_origin(offer.get("origin"))
    fob_price, currency = _to_eur_per_ton(offer)
    transport, src = transport_eur_per_ton(county)
    tons = offer.get("quantity_tons")
    if tons is None and offer.get("quantity_kg"):
        tons = offer["quantity_kg"] / 1000.0

    result = {
        "product": offer.get("product_ro"),
        "origin_county": county,
        "destination": destination,
        "currency": currency,
        "fob_origin_eur_per_ton": fob_price,
        "transport_eur_per_ton": transport,
        "transport_source": src,
        "quantity_tons": tons,
    }
    if fob_price is not None and transport is not None:
        # Transport rates are EUR/ton; only sum cleanly for EUR offers.
        if currency == "EUR":
            cpt = round(fob_price + transport, 2)
        else:
            cpt = None
            result["note"] = ("offer is %s/ton; transport is EUR/ton - convert "
                              "before summing" % currency)
        result["cpt_constanta_eur_per_ton"] = cpt
        if cpt is not None and tons:
            result["fob_total_eur"] = round(fob_price * tons, 2)
            result["transport_total_eur"] = round(transport * tons, 2)
            result["cpt_total_eur"] = round(cpt * tons, 2)
    return result


def main():
    ap = argparse.ArgumentParser(description="Grain landed-price to Constanta (gated).")
    ap.add_argument("--county", help="Origin county.")
    ap.add_argument("--price", type=float, help="FOB price per ton.")
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--tons", type=float, help="Quantity in tons.")
    ap.add_argument("--product", default="grau")
    ap.add_argument("--demo", action="store_true", help="3 offers, different counties.")
    args = ap.parse_args()

    if args.demo:
        offers = [
            {"product_ro": "grau", "origin": "Romania, Ialomita",
             "price_per_unit": 195, "currency": "EUR", "price_basis": "per_ton",
             "quantity_tons": 500},
            {"product_ro": "porumb boabe", "origin": "Romania, Dolj",
             "price_per_unit": 188, "currency": "EUR", "price_basis": "per_ton",
             "quantity_tons": 120},
            {"product_ro": "floarea-soarelui", "origin": "Romania, Timis",
             "price_per_unit": 380, "currency": "EUR", "price_basis": "per_ton",
             "quantity_tons": 300},
        ]
        out = [get_landed_constanta(o) for o in offers]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        print("\nRead: a 'cheap far' Timis offer can land dearer than a 'pricey near' "
              "Ialomita one once haulage is added. Rates in cereale_transport_rates.csv "
              "are STARTER values - edit before trading.", file=sys.stderr)
        return 0

    if args.county is None or args.price is None:
        ap.error("provide --county and --price (or --demo)")
    offer = {"product_ro": args.product, "origin": "Romania, " + args.county,
             "price_per_unit": args.price, "currency": args.currency,
             "price_basis": "per_ton", "quantity_tons": args.tons}
    print(json.dumps(get_landed_constanta(offer), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
