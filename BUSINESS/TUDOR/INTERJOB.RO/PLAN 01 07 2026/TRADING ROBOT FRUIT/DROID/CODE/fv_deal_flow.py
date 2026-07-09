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

SUPPLIER_UNKNOWN = "email_unknown"

def load_offers(ledger_path=LEDGER_PATH):
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
        # oferte interne (ex: Vointa = inteligenta de pret) raman in price book,
        # dar nu genereaza dealuri/outreach catre cumparatori
        if offer.get("internal_only"):
            continue
        supplier_email = offer.get("supplier_email") or SUPPLIER_UNKNOWN
        for buyer in buyers:
            if not buyer.get("email"):
                continue
            if (supplier_email, buyer["email"], offer.get("product_ro", "")) in active_keys:
                continue
            score, details = match_offer_to_buyer(offer, buyer)
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
                    "ready": score >= 80,
                })
    return sorted(matches, key=lambda x: x["score"], reverse=True)

def open_deal(offer, buyer, score, deals_path=DEALS_PATH):
    deal = {
        "deal_id": f"deal_fv_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4]}",
        "status": "proposed",
        "created_at": datetime.now().isoformat(),
        "score": score,
        "product": offer.get("product_ro"),
        "quantity_kg": offer.get("quantity_kg"),
        "price_eur_kg": offer.get("price_per_unit"),
        "supplier": {"email": offer.get("supplier_email") or SUPPLIER_UNKNOWN, "offer_id": offer.get("offer_id")},
        "buyer": {"name": buyer.get("name", "?"), "email": buyer["email"]},
        "offer_id": offer.get("offer_id"),
        "history": [{"date": datetime.now().isoformat(), "action": "proposed", "by": "fv-trader"}],
        "negotiation_rounds": 0,
        "terms": {"delivery": offer.get("delivery_terms"), "origin": offer.get("origin")},
    }
    os.makedirs(os.path.dirname(deals_path), exist_ok=True)
    with open(deals_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(deal, ensure_ascii=False) + "\n")
    return deal

def list_deals(status=None, deals_path=DEALS_PATH):
    deals = load_deals(deals_path)
    if status:
        deals = [d for d in deals if d.get("status") == status]
    return sorted(deals, key=lambda x: x.get("created_at", ""), reverse=True)

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
    args = parser.parse_args()

    if args.match:
        offers = load_offers()
        buyers = load_buyers()
        deals = load_deals()
        matches = run_matching(offers, buyers, deals)
        ready = [m for m in matches if m["ready"]]
        potential = [m for m in matches if not m["ready"]]
        print(json.dumps({
            "total_matches": len(matches),
            "ready_80plus": len(ready),
            "potential_60_79": len(potential),
            "matches": matches[:20]
        }, indent=2, ensure_ascii=False))

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
