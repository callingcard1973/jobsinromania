#!/usr/bin/env python3
"""Match buyer requests (cereri) against supplier list — inverse matching."""

import json, os, csv, sys, argparse

try:
    from legume_taxonomy import normalize_tag as _tax_normalize
except ImportError:
    _tax_normalize = None

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "..", "DATA")
LEDGER = os.path.join(DATA, "offers_ledger.jsonl")
SUPPLIERS = os.path.join(DATA, "suppliers_list.csv")

MATCH_WEIGHTS = {"product": 0.40, "quality": 0.20, "quantity": 0.15, "origin": 0.10, "email": 0.15}

PRODUCT_SYNONYMS = {
    "vinete": ["vinete", "eggplant", "eggplants"],
    "gogosari": ["gogosari", "gogosar", "round peppers", "ardei gogosar"],
    "ardei kapia": ["ardei kapia", "ardei capia", "kapia", "kapia peppers"],
    "ardei gras": ["ardei gras", "ardei", "bell peppers"],
    "ardei iute": ["ardei iute", "hot peppers", "chili"],
    "visine": ["visine", "visini", "sour cherries", "visine"],
    "cirese": ["cirese", "cherries", "cirese"],
    "rosii": ["rosii", "tomate", "tomatoes", "rosii"],
    "castraveti": ["castraveti", "cucumbers", "castraveti"],
    "dovlecei": ["dovlecei", "zucchini", "dovlecel", "zucchini"],
    "ceapa": ["ceapa", "onions", "ceapa"],
    "varza": ["varza", "cabbage", "varza"],
    "morcovi": ["morcovi", "carrots", "morcov"],
    "cartofi": ["cartofi", "potatoes", "cartof"],
    "usturoi": ["usturoi", "garlic", "usturoi"],
    "conopida": ["conopida", "cauliflower", "conopida"],
}

def load_requests():
    entries = []
    if not os.path.exists(LEDGER):
        return entries
    with open(LEDGER, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("entry_type") == "request":
                entries.append(e)
    return entries

def load_suppliers():
    suppliers = []
    if not os.path.exists(SUPPLIERS):
        return suppliers
    with open(SUPPLIERS, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("name"):
                suppliers.append(row)
    return suppliers

def normalize_product(name):
    name = name.lower().strip()
    for key, synonyms in PRODUCT_SYNONYMS.items():
        if name in synonyms or any(s in name for s in synonyms):
            return key
    return _tax_normalize(name) if _tax_normalize else name

def product_matches(supplies_str, request_product):
    request_norm = normalize_product(request_product)
    supplies_lower = supplies_str.lower()
    if request_norm in supplies_lower:
        return True
    word_variants = PRODUCT_SYNONYMS.get(request_norm, [request_norm])
    for variant in word_variants:
        if variant in supplies_lower:
            return True
    return False

def match_request_to_suppliers(request, suppliers):
    matches = []
    r_product = request.get("product_ro", "")
    r_quality = (request.get("quality") or "").lower()
    r_qty = request.get("quantity_kg") or 0
    r_origin = (request.get("origin") or "").lower()

    for s in suppliers:
        supplies = s.get("supplies", "")
        if not product_matches(supplies, r_product):
            continue

        score = 0.0
        details = []

        score += MATCH_WEIGHTS["product"]
        details.append("product_match")

        s_quality = (s.get("quality") or "").lower()
        if r_quality == "industrial":
            score += MATCH_WEIGHTS["quality"]
            details.append("quality_industrial_any")
        elif s_quality and r_quality and s_quality == r_quality:
            score += MATCH_WEIGHTS["quality"]
            details.append("quality_exact")
        elif s_quality == "clasa_i" and r_quality in ("clasa_ii", "industrial"):
            score += MATCH_WEIGHTS["quality"] * 0.7
            details.append("quality_overspec")

        s_max_qty = None
        try:
            s_max_qty = float(s.get("max_qty_kg", 0)) if s.get("max_qty_kg") else None
        except (ValueError, TypeError):
            pass
        if s_max_qty and r_qty:
            if s_max_qty >= r_qty:
                score += MATCH_WEIGHTS["quantity"]
                details.append("qty_sufficient")
            elif s_max_qty >= r_qty * 0.5:
                score += MATCH_WEIGHTS["quantity"] * 0.6
                details.append("qty_partial")
            else:
                score += MATCH_WEIGHTS["quantity"] * 0.3
                details.append("qty_low")

        s_origin = (s.get("origin") or "").lower()
        if s_origin and r_origin and s_origin == r_origin:
            score += MATCH_WEIGHTS["origin"]
            details.append("origin_same_county")
        elif s_origin and r_origin:
            score += MATCH_WEIGHTS["origin"] * 0.3
            details.append("origin_different")

        s_email = (s.get("email") or "").lower()
        if s_email and s_email != "necunoscut@cauta":
            score += MATCH_WEIGHTS["email"]
            details.append("email_known")
        else:
            score += MATCH_WEIGHTS["email"] * 0.2
            details.append("email_unknown")

        score = round(score * 100, 1)
        matches.append({
            "request_id": request.get("source_email_id", "?"),
            "product": r_product,
            "supplier": s.get("name", "?"),
            "supplier_email": s_email if s_email and s_email != "necunoscut@cauta" else "LIPSA",
            "score": score,
            "details": details,
            "supplier_origin": s_origin,
            "supplier_qty_kg": s_max_qty,
            "supplier_quality": s_quality or "necunoscuta",
        })

    return sorted(matches, key=lambda x: x["score"], reverse=True)

def run_all_matches():
    requests = load_requests()
    suppliers = load_suppliers()
    all_matches = []
    for req in requests:
        matches = match_request_to_suppliers(req, suppliers)
        all_matches.extend(matches)
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    return all_matches, requests, suppliers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match buyer requests to suppliers")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    matches, requests, suppliers = run_all_matches()
    ready = [m for m in matches if m["score"] >= 80]
    potential = [m for m in matches if 60 <= m["score"] < 80]

    result = {
        "requests_count": len(requests),
        "suppliers_count": len(suppliers),
        "total_matches": len(matches),
        "ready_80plus": len(ready),
        "potential_60_79": len(potential),
    }

    if args.json:
        result["matches"] = matches
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Cereri: {len(requests)} | Furnizori: {len(suppliers)}")
        print(f"Match-uri totale: {len(matches)} | Ready (80%+): {len(ready)} | Potential (60-79%): {len(potential)}")
        print()
        for m in matches:
            tag = "READY" if m["score"] >= 80 else "POTENTIAL"
            print(f"[{tag}] {m['product']} -> {m['supplier']} ({m['score']}%)")
            print(f"       Email: {m['supplier_email']} | Origine: {m['supplier_origin']} | Qty max: {m['supplier_qty_kg']}kg")
            print(f"       Detalii: {', '.join(m['details'])}")
            print()
