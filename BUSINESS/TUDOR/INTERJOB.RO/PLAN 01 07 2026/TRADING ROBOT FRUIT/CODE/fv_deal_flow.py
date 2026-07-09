#!/usr/bin/env python3
"""Match F&V offers to buyers + deal lifecycle management."""

import json
import os
import csv
import uuid
from datetime import datetime

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "..", "DATA", "offers_ledger.jsonl")
BUYERS_PATH = os.path.join(os.path.dirname(__file__), "..", "DATA", "buyers_list.csv")
DEALS_PATH = os.path.join(os.path.dirname(__file__), "..", "DATA", "deals.jsonl")
REQUESTS_LEDGER = os.path.join(os.path.dirname(__file__), "..", "..", "..",
    "PLAN 01 07 2026", "DATA", "00_SHARED_leads_si_dnc", "requests_ledger.jsonl")

MATCH_WEIGHTS = {"product": 0.35, "quality": 0.20, "price": 0.20, "context": 0.15, "origin": 0.05, "quantity": 0.05}
SUPPLIER_SCORE_BONUS = 5

SUPPLIER_UNKNOWN = "email_unknown"

COMPLETENESS_FIELDS = ["product_ro", "quality_class", "quantity_kg", "price_per_unit", "currency", "origin", "delivery_terms"]

_ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
PRICEBOOK_PATH = os.path.join(_ROOT_DIR, "DATA", "price_book.json")

def load_offers(ledger_path=LEDGER_PATH):
    # Try PG first, JSONL fallback
    try:
        import psycopg2
        dsn = os.environ.get("TRADING_PG_DSN", "dbname=interjob_master user=tudor")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("""SELECT offer_id, source_email_id, extracted_at, product_ro, product_en,
                              category, quality_class, quantity_kg, price_per_unit, currency,
                              origin, delivery_terms, completeness, context, raw_snippet,
                              supplier_email, from_email, entry_type, internal_only
                       FROM trading_offers ORDER BY extracted_at DESC""")
        cols = [d[0] for d in cur.description]
        offers = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        if offers:
            return offers
    except Exception:
        pass
    offers = []
    if not os.path.exists(ledger_path):
        return offers
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                offers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return offers

def load_buyers(buyers_path=BUYERS_PATH):
    buyers = []
    if not os.path.exists(buyers_path):
        return buyers
    with open(buyers_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("email"):
                buyers.append(row)
    return buyers

def load_deals(deals_path=DEALS_PATH):
    # Try PG first, JSONL fallback
    try:
        import psycopg2
        dsn = os.environ.get("TRADING_PG_DSN", "dbname=interjob_master user=tudor")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("""SELECT deal_id, status, created_at, score, product, quantity_kg,
                              price_eur_kg, offer_id, supplier, buyer, history,
                              negotiation_rounds, terms
                       FROM trading_deals ORDER BY created_at DESC""")
        cols = [d[0] for d in cur.description]
        deals = []
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            for k in ("supplier", "buyer", "history", "terms"):
                if isinstance(d.get(k), str):
                    try:
                        d[k] = json.loads(d[k])
                    except (json.JSONDecodeError, TypeError):
                        pass
            deals.append(d)
        cur.close()
        conn.close()
        if deals:
            return deals
    except Exception:
        pass
    deals = []
    if not os.path.exists(deals_path):
        return deals
    with open(deals_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                deals.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return deals

def active_deal_exists(deals, supplier_email, buyer_email, product):
    for d in deals:
        if d.get("status") in ("proposed", "negotiating"):
            sup = d.get("supplier", {}).get("email", "")
            buy = d.get("buyer", {}).get("email", "")
            if sup == supplier_email and buy == buyer_email and d.get("product") == product:
                return True
    return False

def _get_supplier_email(offer):
    return offer.get("supplier_email") or offer.get("from_email") or SUPPLIER_UNKNOWN


def _median_price_for_product(product, currency="RON", offers=None):
    if offers is None:
        offers = load_offers()
    prices = []
    for o in offers:
        if o.get("product_ro", "").lower() == product.lower() and o.get("entry_type") != "request":
            if o.get("currency", "RON") == currency and o.get("price_per_unit"):
                try:
                    prices.append(float(o["price_per_unit"]))
                except (ValueError, TypeError):
                    continue
    if not prices:
        return None
    prices.sort()
    n = len(prices)
    if n % 2 == 1:
        return prices[n // 2]
    return (prices[n // 2 - 1] + prices[n // 2]) / 2.0


def score_supplier(offer, deals):
    email = _get_supplier_email(offer)
    scores = {}

    filled = sum(1 for f in COMPLETENESS_FIELDS if offer.get(f))
    scores["completeness"] = round((filled / len(COMPLETENESS_FIELDS)) * 100, 1)

    price = offer.get("price_per_unit")
    product = offer.get("product_ro", "")
    currency = offer.get("currency", "RON")
    if price and product:
        try:
            price = float(price)
        except (ValueError, TypeError):
            price = None
    if price and product:
        median = _median_price_for_product(product, currency)
        if median is not None and median > 0:
            ratio = price / median
            if ratio <= 0.9:
                scores["price_competitiveness"] = 100
            elif ratio <= 1.0:
                scores["price_competitiveness"] = round(80 - (ratio - 0.9) * 200, 1)
            elif ratio <= 1.2:
                scores["price_competitiveness"] = round(60 - (ratio - 1.0) * 200, 1)
            else:
                scores["price_competitiveness"] = max(0, round(40 - (ratio - 1.2) * 100, 1))
        else:
            scores["price_competitiveness"] = 50
    else:
        scores["price_competitiveness"] = 50

    sup_deals = [d for d in deals if d.get("supplier", {}).get("email") == email]
    total = len(sup_deals)
    if total > 0:
        advanced = sum(1 for d in sup_deals if d.get("status") in ("negotiating", "accepted", "closed"))
        scores["response_rate"] = round((advanced / total) * 100, 1)
    else:
        scores["response_rate"] = 50

    overall = scores["completeness"] * 0.4 + scores["price_competitiveness"] * 0.4 + scores["response_rate"] * 0.2
    scores["overall"] = round(overall, 1)
    return scores


def update_supplier_score(deals):
    suppliers = {}
    for d in deals:
        email = d.get("supplier", {}).get("email")
        if not email:
            continue
        if email not in suppliers:
            suppliers[email] = {"total_deals": 0, "advanced": 0, "products": set()}
        suppliers[email]["total_deals"] += 1
        suppliers[email]["products"].add(d.get("product", ""))
        if d.get("status") in ("negotiating", "accepted", "closed"):
            suppliers[email]["advanced"] += 1

    for email, data in suppliers.items():
        rate = round((data["advanced"] / data["total_deals"]) * 100, 1) if data["total_deals"] > 0 else 0
        data["response_rate"] = rate
        data["products"] = sorted(data["products"])
    return suppliers


def match_offer_to_buyer(offer, buyer):
    score = 0.0
    details = []

    if offer.get("product_ro", "").lower() in buyer.get("wants", "").lower():
        score += MATCH_WEIGHTS["product"]
        details.append("product_match")
    elif buyer.get("wants_all", "").lower() == "yes":
        score += MATCH_WEIGHTS["product"] * 0.5
        details.append("product_partial")

    o_q = (offer.get("quality_class") or "").lower()
    b_q = (buyer.get("quality") or "").lower()
    if b_q == "industrial":
        score += MATCH_WEIGHTS["quality"]
        details.append("quality_industrial_any")
    elif o_q and b_q:
        if o_q == b_q:
            score += MATCH_WEIGHTS["quality"]
            details.append("quality_exact")
        elif o_q == "extra" and b_q in ("clasa_ii", "clasa_iii"):
            score += MATCH_WEIGHTS["quality"] * 0.8
            details.append("quality_overspec")
        elif o_q == "clasa_i" and b_q == "extra":
            # un grad sub cererea retail; aproape acceptabil
            score += MATCH_WEIGHTS["quality"] * 0.8
            details.append("quality_one_below")

    o_price = offer.get("price_per_unit")
    b_max_price = None
    try:
        b_max_price = float(buyer.get("max_price", 0)) if buyer.get("max_price") else None
    except (ValueError, TypeError):
        pass
    if o_price and b_max_price:
        if o_price <= b_max_price:
            score += MATCH_WEIGHTS["price"]
            details.append("price_ok")
        elif o_price <= b_max_price * 1.15:
            score += MATCH_WEIGHTS["price"] * 0.5
            details.append("price_near")
    elif o_price and not b_max_price:
        score += MATCH_WEIGHTS["price"] * 0.3
        details.append("price_no_ref")

    o_origin = (offer.get("origin") or "").lower()
    b_origin = (buyer.get("origin") or "").lower()
    if o_origin and b_origin and (o_origin == b_origin
                                  or b_origin in o_origin or o_origin in b_origin):
        score += MATCH_WEIGHTS["origin"]
        details.append("origin_match")

    buyer_name_lower = buyer.get("name", "").lower()
    search_text = (offer.get("context") or "") + (offer.get("raw_snippet") or "").lower()
    buyer_words = [w for w in buyer_name_lower.split() if len(w) > 2]
    if any(w in search_text for w in buyer_words) or buyer_name_lower[:4] in search_text:
        score += MATCH_WEIGHTS["context"]
        details.append("context_mention")

    o_qty = offer.get("quantity_kg")
    b_qty = None
    try:
        b_qty = float(buyer.get("min_qty_kg", 0)) if buyer.get("min_qty_kg") else None
    except (ValueError, TypeError):
        pass
    if b_qty and not o_qty:
        score += MATCH_WEIGHTS["quantity"] * 0.3
        details.append("qty_unknown_offer")
    elif o_qty and b_qty:
        if o_qty >= b_qty:
            score += MATCH_WEIGHTS["quantity"]
            details.append("qty_ok")
        elif o_qty >= b_qty * 0.5:
            score += MATCH_WEIGHTS["quantity"] * 0.5
            details.append("qty_partial")
    elif o_qty and not b_qty:
        score += MATCH_WEIGHTS["quantity"] * 0.3
        details.append("qty_no_buyer_ref")

    return round(score * 100, 1), details

def run_matching(offers, buyers, deals):
    matches = []
    active_keys = {(d.get("supplier", {}).get("email", ""), d.get("buyer", {}).get("email", ""),
                    d.get("product")) for d in deals if d.get("status") in ("proposed", "negotiating")}
    for offer in offers:
        if not offer.get("price_per_unit"):
            continue
        if offer.get("entry_type") == "request":
            continue
        if offer.get("internal_only"):
            continue
        supplier_email = _get_supplier_email(offer)

        sup_score = score_supplier(offer, deals)
        offer["supplier_score"] = sup_score

        for buyer in buyers:
            if not buyer.get("email"):
                continue
            if (supplier_email, buyer["email"], offer.get("product_ro", "")) in active_keys:
                continue
            score, details = match_offer_to_buyer(offer, buyer)
            if sup_score.get("overall", 0) > 70:
                score = min(100.0, score + SUPPLIER_SCORE_BONUS)
                details.append("supplier_bonus")
            if score >= 60:
                matches.append({
                    "offer_id": offer.get("offer_id"),
                    "product": offer.get("product_ro"),
                    "supplier_email": supplier_email,
                    "buyer_email": buyer["email"],
                    "buyer_name": buyer.get("name", "?"),
                    "score": score,
                    "details": details,
                    "offer_price": offer.get("price_per_unit"),
                    "offer_qty": offer.get("quantity_kg"),
                    "offer_origin": offer.get("origin"),
                    "supplier_score": sup_score,
                    "ready": score >= 80,
                })
    return sorted(matches, key=lambda x: x["score"], reverse=True)

def _pg_insert_deal(deal):
    """Dual-write: INSERT deal into PG trading_deals (fail-safe)."""
    try:
        import psycopg2
        from psycopg2.extras import Json
        dsn = os.environ.get("TRADING_PG_DSN", "dbname=interjob_master user=tudor")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO trading_deals
               (deal_id, status, created_at, score, product, quantity_kg, price_eur_kg,
                offer_id, supplier, buyer, history, negotiation_rounds, terms)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (deal_id) DO NOTHING""",
            (deal.get("deal_id"), deal.get("status"), deal.get("created_at"),
             deal.get("score"), deal.get("product"), deal.get("quantity_kg"),
             deal.get("price_eur_kg"), deal.get("offer_id"),
             Json(deal.get("supplier")), Json(deal.get("buyer")),
             Json(deal.get("history", [])), deal.get("negotiation_rounds", 0),
             Json(deal.get("terms"))))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def open_deal(offer, buyer, score, deals_path=DEALS_PATH):
    deal = {
        "deal_id": f"deal_fv_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4]}",
        "status": "proposed",
        "created_at": datetime.now().isoformat(),
        "score": score,
        "product": offer.get("product_ro"),
        "quantity_kg": offer.get("quantity_kg"),
        "price_eur_kg": offer.get("price_per_unit"),
        "supplier": {"email": _get_supplier_email(offer), "offer_id": offer.get("offer_id")},
        "buyer": {"name": buyer.get("name", "?"), "email": buyer["email"]},
        "offer_id": offer.get("offer_id"),
        "history": [{"date": datetime.now().isoformat(), "action": "proposed", "by": "fv-trader"}],
        "negotiation_rounds": 0,
        "terms": {"delivery": offer.get("delivery_terms"), "origin": offer.get("origin")},
    }
    os.makedirs(os.path.dirname(deals_path), exist_ok=True)
    with open(deals_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(deal, ensure_ascii=False) + "\n")
    _pg_insert_deal(deal)
    try:
        from wa_notify import notify
        notify(f"Deal deschis: {deal['product']} -> {buyer.get('name','?')}\nOferta: {deal['offer_id']}\nPret: {deal.get('price_eur_kg')} {offer.get('currency','EUR')}/kg\nOrigine: {deal.get('terms',{}).get('origin','?')}", business="cumparlegume")
    except Exception:
        pass
    return deal

def list_deals(status=None, deals_path=DEALS_PATH):
    deals = load_deals(deals_path)
    if status:
        deals = [d for d in deals if d.get("status") == status]
    return sorted(deals, key=lambda x: x.get("created_at", ""), reverse=True)

def _pg_update_deal_status(deal_id, new_status):
    """Update deal status in PG (fail-safe)."""
    try:
        import psycopg2
        dsn = os.environ.get("TRADING_PG_DSN", "dbname=interjob_master user=tudor")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("UPDATE trading_deals SET status=%s WHERE deal_id=%s",
                    (new_status, deal_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def update_deal_status(deal_id, new_status, deals_path=DEALS_PATH):
    deals = load_deals(deals_path)
    updated = False
    for i, d in enumerate(deals):
        if d.get("deal_id") == deal_id:
            d["status"] = new_status
            d["history"].append({"date": datetime.now().isoformat(), "action": new_status, "by": "fv-dealer"})
            deals[i] = d
            updated = True
            break
    if updated:
        tmp = deals_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for d in deals:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        os.replace(tmp, deals_path)
        _pg_update_deal_status(deal_id, new_status)
        return True
    return False

def deal_summary(deals):
    counts = {"proposed": 0, "negotiating": 0, "accepted": 0, "closed": 0, "stalled": 0, "rejected": 0}
    for d in deals:
        s = d.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FV Deal Flow")
    parser.add_argument("--match", action="store_true", help="Run buyer matching")
    parser.add_argument("--open-deal", action="store_true")
    parser.add_argument("--offer-id", help="Offer ID for --open-deal")
    parser.add_argument("--buyer-email", help="Buyer email for --open-deal")
    parser.add_argument("--deals", action="store_true")
    parser.add_argument("--status", help="Filter deals by status")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--supplier-scores", action="store_true", help="Show supplier score summary from deals")
    args = parser.parse_args()

    if args.match:
        offers = load_offers()
        buyers = load_buyers()
        deals = load_deals()
        matches = run_matching(offers, buyers, deals)
        clean = [{
            "offer_id": m["offer_id"],
            "product": m["product"],
            "supplier_email": m["supplier_email"],
            "buyer_name": m["buyer_name"],
            "buyer_email": m["buyer_email"],
            "details": m["details"],
            "offer_price": m["offer_price"],
            "offer_qty": m["offer_qty"],
            "offer_origin": m["offer_origin"],
        } for m in matches[:20]]
        # Telegram alert for matches
        if matches:
            try:
                from tg_notify import notify as _tg
                lines = [f"Trading robot: {len(matches)} meciuri gasite"]
                for m in matches[:5]:
                    lines.append(f"- {m['product']} -> {m['buyer_name']} ({m['offer_price']} EUR/kg)")
                _tg("\n".join(lines))
            except Exception:
                pass
        print(json.dumps({
            "total_matches": len(matches),
            "matches": clean
        }, indent=2, ensure_ascii=False))

    elif args.supplier_scores:
        deals = load_deals()
        suppliers = update_supplier_score(deals)
        print(json.dumps(suppliers, indent=2, ensure_ascii=False))

    elif args.open_deal:
        if not args.offer_id or not args.buyer_email:
            print('{"error": "Need --offer-id and --buyer-email"}')
            exit(1)
        offers = load_offers()
        buyers = load_buyers()
        offer = next((o for o in offers if o.get("offer_id") == args.offer_id), None)
        buyer = next((b for b in buyers if b.get("email") == args.buyer_email), None)
        if not offer or not buyer:
            print(f'{{"error": "Offer or buyer not found"}}')
            exit(1)
        deal = open_deal(offer, buyer, 100)
        print(json.dumps(deal, indent=2, ensure_ascii=False))

    elif args.deals or args.summary:
        deals = list_deals(status=args.status)
        if args.summary:
            print(json.dumps(deal_summary(deals), indent=2))
        else:
            print(json.dumps(deals[:20], indent=2, ensure_ascii=False))
    else:
        offers = load_offers()
        buyers = load_buyers()
        deals = load_deals()
        print(json.dumps({
            "offers_in_ledger": len(offers),
            "buyers_in_list": len(buyers),
            "active_deals": deal_summary(deals)
        }, indent=2))
