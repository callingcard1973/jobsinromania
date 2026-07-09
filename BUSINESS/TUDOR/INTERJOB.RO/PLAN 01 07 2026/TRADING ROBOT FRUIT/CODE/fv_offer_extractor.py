#!/usr/bin/env python3
"""Parses F&V email content into structured product offers."""

import json
import os
import re
import uuid
from datetime import datetime

try:
    from legume_taxonomy import normalize_tag as _tax_normalize, is_produce as _tax_is_produce
except ImportError:
    _tax_normalize = None
    _tax_is_produce = None

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "..", "DATA", "offers_ledger.jsonl")

PRODUCT_DB = [
    "rosii", "tomate", "rosii taranesti", "castraveti", "cornichon",
    "ardei", "ardei gras", "ardei iute", "ardei kapia", "ceapa",
    "ceapa verde", "ceapa rosie", "usturoi", "cartofi", "cartofi noi",
    "morcovi", "telina", "pastarnac", "sfecla", "ridichi", "varza",
    "varza rosie", "varza creata", "conopida", "brocoli", "salata",
    "salata iceberg", "salata rucola", "spanac", "mazare", "fasole",
    "fasole verde", "fasole pastai", "vinete", "dovlecei", "dovleac",
    "dovleac plumat", "porumb", "porumb zaharat", "ciuperci",
    "pepene", "pepene rosu", "pepene galben", "struguri", "struguri albi",
    "struguri negri", "struguri masa", "mere", "pere", "prune",
    "prune uscate", "capsuni", "zmeura", "afine", "coacaze", "mure",
    "cirese", "visine", "cai", "piersici", "nectarine", "gutui",
    "nuci", "alune", "migdale", "alune de padure", "arahide",
    "banane", "portocale", "lamai", "lime", "grapefruit", "kiwi",
    "avocado", "mango", "ananas", "papaya", "curmale", "smochine",
    "rodii", "kaki",
    # --- CEREALE (DIRECTIA 5 unified ledger: grau/porumb/orz/naut/floarea-soarelui etc.) ---
    "grau", "grau durum", "porumb boabe", "orz", "naut", "naut furajer",
    "floarea-soarelui", "floarea soarelui", "rapita", "triticale", "ovaz",
    "secara", "sorg", "soia", "mustar", "mustar depreciat",
    "sparturi cereale", "cereale umiditate", "cereale depreciate",
]

CEREAL_PRODUCTS = {
    "grau", "grau durum", "porumb boabe", "orz", "naut", "naut furajer",
    "floarea-soarelui", "floarea soarelui", "rapita", "triticale", "ovaz",
    "secara", "sorg", "soia", "mustar", "mustar depreciat",
    "sparturi cereale", "cereale umiditate", "cereale depreciate",
}

def product_category(name):
    """Return 'cereal', 'fv', or 'unknown' for a normalized product name."""
    if not name:
        return "unknown"
    if name.strip().lower() in CEREAL_PRODUCTS:
        return "cereal"
    return "fv"

PRODUCT_ALIASES = {
    "cornichon": "castraveti",
    "tomate": "rosii",
    "rosii taranesti": "rosii",
    "kaki": "curmale",
}

def normalize_product(raw_name):
    raw_lower = raw_name.strip().lower()
    if _tax_normalize is not None:
        t = _tax_normalize(raw_lower)
        if _tax_is_produce and _tax_is_produce(t):
            return t
    if raw_lower in PRODUCT_ALIASES:
        return PRODUCT_ALIASES[raw_lower]
    matches = [p for p in PRODUCT_DB if p in raw_lower]
    if matches:
        best = max(matches, key=len)
        return PRODUCT_ALIASES.get(best, best)
    return raw_name.strip()

def extract_quantity(text):
    patterns = [
        (r"(\d+[.,]?\d*)\s*(kg|kilograme|kilogram)", lambda m: float(m.group(1).replace(",", "."))),
        (r"(\d+[.,]?\d*)\s*(tone|to|t)(?![a-z])(?!\s*\d)", lambda m: float(m.group(1).replace(",", ".")) * 1000),
        (r"(\d+[.,]?\d*)\s*(paleti|palet)", lambda m: float(m.group(1).replace(",", ".")) * 500),
    ]
    for pattern, converter in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return converter(m)
    return None

def extract_price(text):
    patterns = [
        (r"(\d+[.,]\d{2,3})\s*(eur|euro|\u20ac)", lambda m: ("EUR", float(m.group(1).replace(",", ".")))),
        (r"(\d+[.,]\d{2,3})\s*(ron|lei)", lambda m: ("RON", float(m.group(1).replace(",", ".")))),
        (r"(\d+[.,]\d{2,3})\s*(/kg\b)", lambda m: ("EUR", float(m.group(1).replace(",", ".")))),
        (r"(\d+[.,]\d{2,3})\s*(euro)", lambda m: ("EUR", float(m.group(1).replace(",", ".")))),
        (r"(\d+[.,]\d{2})\s+RON\b", lambda m: ("RON", float(m.group(1).replace(",", ".")))),
        (r"(\d+[.,]\d{2})\s+EUR\b", lambda m: ("EUR", float(m.group(1).replace(",", ".")))),
    ]
    for pattern, converter in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return converter(m)
    return (None, None)

def extract_quality(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["extra", "clasa i", "clasa 1"]):
        return "extra"
    if any(w in text_lower for w in ["clasa ii", "clasa 2", "standard"]):
        return "clasa_II"
    if any(w in text_lower for w in ["clasa iii", "clasa 3", "industrial"]):
        return "clasa_III"
    return None

def extract_delivery_terms(text):
    text_lower = text.lower()
    if "fob" in text_lower:
        return "FOB"
    if "cif" in text_lower:
        return "CIF"
    if "dap" in text_lower:
        return "DAP"
    if "exw" in text_lower or "ex works" in text_lower:
        return "EXW"
    if "franco" in text_lower:
        return "Franco"
    return None

def extract_origin(text):
    ro_counties = [
        "Alba", "Arad", "Arge", "Bacau", "Bihor", "Bistrita", "Botosani",
        "Braila", "Brasov", "Bucuresti", "Buzau", "Calarasi", "Caras",
        "Cluj", "Constanta", "Covasna", "Dambovita", "Dolj", "Galati",
        "Giurgiu", "Gorj", "Harghita", "Hunedoara", "Ialomita", "Iasi",
        "Ilfov", "Maramures", "Mehedinti", "Mures", "Neamt", "Olt",
        "Prahova", "Salaj", "Satu Mare", "Sibiu", "Suceava", "Teleorman",
        "Timis", "Tulcea", "Vaslui", "Valcea", "Vrancea"
    ]
    for county in ro_counties:
        if county.lower() in text.lower():
            return "Romania, " + county
    countries = ["Romania", "Bulgaria", "Ungaria", "Polonia", "Italia",
                 "Spania", "Grecia", "Olanda", "Germania", "Franta",
                 "Turcia", "Moldova", "Ucraina", "Serbia"]
    for country in countries:
        if country.lower() in text.lower():
            return country
    return None

def parse_profi_pricelist(raw_text, email_id=None, subject=None, supplier_email=None):
    lines = raw_text.strip().split("\n")
    data_lines = []
    in_table = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if "PROFI CODE" in stripped or "raspuns" in stripped.lower():
            in_table = True
            continue
        if in_table and re.match(r"^\d{3,}", stripped):
            data_lines.append(stripped)

    if not data_lines:
        return None

    email_context = (raw_text[:800] + " " + (subject or "")).lower()
    offers = []
    for line in data_lines:
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 6:
            parts = line.strip().split(",")

        text_combined = " ".join(parts)
        product_name = ""

        product_patterns = [
            r"(CASTRAVETI[^0-9]*)", r"(DOVLECEI)", r"(ROSII[^0-9]*)",
            r"(VINETE)", r"(MERE)", r"(PERE)", r"(PRUNE)", r"(CAPSUNI)",
            r"(ARDEI[^0-9]*)", r"(CEAPA)", r"(USTUROI)", r"(CARTOFI)", r"(MORCOVI)",
            r"(VARZA)", r"(CONOPIDA)", r"(BROCOLI)", r"(SALATA)", r"(SPANAC)",
            r"(DOVLEAC)", r"(FASOLE)", r"(MAZARE)", r"(PEPENE)", r"(STRUGURI)",
        ]
        for p in product_patterns:
            m = re.search(p, text_combined, re.IGNORECASE)
            if m:
                product_name = m.group(1).strip().lower()
                break

        if not product_name:
            continue

        prices = re.findall(r"(\d+[.,]\d{2,3})", text_combined)
        supplier_price = None
        if len(prices) >= 2:
            supplier_price = float(prices[-1].replace(",", "."))
        elif len(prices) == 1:
            supplier_price = float(prices[0].replace(",", "."))

        offers.append({
            "offer_id": f"fv_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}",
            "source_email_id": email_id,
            "extracted_at": datetime.now().isoformat(),
            "product_ro": normalize_product(product_name) or product_name,
            "product_en": "",
            "quality_class": None,
            "quantity_kg": None,
            "price_per_unit": supplier_price,
            "currency": "RON",
            "origin": None,
            "delivery_terms": None,
            "completeness": "partial",
            "context": email_context,
            "raw_snippet": line.strip()[:200],
            "supplier_email": (supplier_email or ""),
        })

    return offers if offers else None

def parse_email_to_offers(raw_text, email_id=None, subject=None, supplier_email=None):
    email_context = (raw_text[:800] + " " + (subject or "")).lower()

    profi_offers = parse_profi_pricelist(raw_text, email_id, subject, supplier_email=supplier_email)
    if profi_offers:
        return profi_offers

    text_lower = raw_text.lower()
    products_found = [p for p in PRODUCT_DB if p in text_lower]
    if not products_found:
        products_found = [normalize_product(subject)] if subject else ["unknown"]

    offers = []
    for prod in products_found[:5]:
        qty = extract_quantity(raw_text)
        currency, price = extract_price(raw_text)
        quality = extract_quality(raw_text)
        delivery = extract_delivery_terms(raw_text)
        origin = extract_origin(raw_text)

        filled = sum(1 for v in [prod, qty, price, quality] if v is not None)
        completeness = "complete" if filled >= 3 else "partial"

        offers.append({
            "offer_id": f"fv_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}",
            "source_email_id": email_id,
            "extracted_at": datetime.now().isoformat(),
            "product_ro": prod,
            "product_en": prod,
            "quality_class": quality,
            "quantity_kg": qty,
            "price_per_unit": price,
            "currency": currency or "EUR",
            "origin": origin,
            "delivery_terms": delivery,
            "completeness": completeness,
            "context": email_context,
            "raw_snippet": raw_text[:200],
            "supplier_email": (supplier_email or ""),
        })

    return offers

def pg_insert_offer(offer):
    """Dual-write: INSERT offer into PG trading_offers (fail-safe, never crashes)."""
    try:
        import hashlib as _h
        import psycopg2
        dsn = os.environ.get("TRADING_PG_DSN", "dbname=interjob_master user=tudor")
        base = "|".join([
            str(offer.get("supplier_email") or offer.get("from_email") or ""),
            str(offer.get("product_ro", "")),
            str(offer.get("price_per_unit", "")),
            str(offer.get("quantity_kg", "")),
            str(offer.get("source_email_id", "")),
        ])
        oh = _h.sha256(base.encode("utf-8")).hexdigest()[:16]
        oid = offer.get("offer_id") or oh
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO trading_offers
               (offer_id,source_email_id,extracted_at,product_ro,product_en,category,
                quality_class,quantity_kg,price_per_unit,currency,origin,delivery_terms,
                completeness,context,raw_snippet,supplier_email,from_email,entry_type,
                internal_only,offer_hash)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (offer_hash) DO NOTHING""",
            (oid, offer.get("source_email_id"), offer.get("extracted_at"),
             offer.get("product_ro"), offer.get("product_en"),
             offer.get("category") or product_category(offer.get("product_ro", "")),
             offer.get("quality_class"), offer.get("quantity_kg"), offer.get("price_per_unit"),
             offer.get("currency"), offer.get("origin"), offer.get("delivery_terms"),
             offer.get("completeness"), offer.get("context"), offer.get("raw_snippet"),
             offer.get("supplier_email"), offer.get("from_email"), offer.get("entry_type"),
             offer.get("internal_only", False), oh))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def append_to_ledger(offers, ledger_path=LEDGER_PATH):
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        for offer in offers:
            f.write(json.dumps(offer, ensure_ascii=False) + "\n")
            pg_insert_offer(offer)
    return len(offers)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FV Offer Extractor")
    parser.add_argument("--file", help="Raw email file path")
    parser.add_argument("--text", help="Raw email text directly")
    parser.add_argument("--email-id", help="Source email ID")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--supplier")
    args = parser.parse_args()

    raw = ""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            raw = f.read()
    elif args.text:
        raw = args.text
    else:
        print('{"error": "Provide --file or --text"}')
        exit(1)

    offers = parse_email_to_offers(raw, email_id=args.email_id, subject=args.subject, supplier_email=args.supplier)
    n = append_to_ledger(offers)
    print(json.dumps({"extracted": len(offers), "saved": n, "offers": offers}, indent=2, ensure_ascii=False))
