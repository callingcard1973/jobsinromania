#!/usr/bin/env python3
"""Trading Robot F&V — runner care executa ciclul complet sau partial."""

import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
DATA_DIR = BASE / ".." / "DATA"
CODE_DIR = BASE

sys.path.insert(0, str(CODE_DIR))

def phase_poll(email, password, days=7, provider="yahoo"):
    from fv_email_poller import fetch_fv_emails, LEDGER_PATH
    result = fetch_fv_emails(email, password, days=days, save_raw=True, provider=provider)
    saved = 0
    for offer in result["offers"]:
        bp = offer.get("body_path", "")
        if bp and os.path.exists(bp):
            from fv_offer_extractor import parse_email_to_offers, append_to_ledger
            with open(bp, "r", encoding="utf-8") as f:
                raw = f.read()
            offers = parse_email_to_offers(raw, email_id=offer["email_id"], subject=offer["subject"], supplier_email=offer.get("supplier_email", ""))
            saved += append_to_ledger(offers)
    result["offers_extracted"] = saved
    result["phase"] = "poll"
    return result

def phase_pricebook():
    from fv_price_book import load_offers, build_price_book, save_price_book
    offers = load_offers()
    book = build_price_book(offers, include_trend=True)
    save_price_book(book)
    return {"phase": "pricebook", "product_count": len(book), "total_offers": len(offers)}

def phase_matching():
    from fv_deal_flow import load_offers, load_buyers, load_deals, run_matching
    offers = load_offers()
    buyers = load_buyers()
    deals = load_deals()
    matches = run_matching(offers, buyers, deals)
    ready = [m for m in matches if m["ready"]]
    potential = [m for m in matches if not m["ready"]]
    return {"phase": "matching", "total_matches": len(matches), "ready_80plus": len(ready), "potential_60_79": len(potential)}

def phase_report():
    from fv_price_book import load_offers
    from fv_deal_flow import load_deals, deal_summary
    offers = load_offers()
    deals = load_deals()
    complete = sum(1 for o in offers if o.get("completeness") == "complete")
    partial = sum(1 for o in offers if o.get("completeness") == "partial")
    products = set(o.get("product_ro") for o in offers if o.get("product_ro"))
    return {
        "phase": "report",
        "offers_total": len(offers),
        "offers_complete": complete,
        "offers_partial": partial,
        "unique_products": len(products),
        "products": sorted(products),
        "deals": deal_summary(deals),
    }

def run_cycle(email, password, days=7, skip_poll=False, skip_pricebook=False, skip_matching=False):
    results = {}
    errors = []

    if not skip_poll:
        try:
            r = phase_poll(email, password, days)
            results["poll"] = {"new_offers": r.get("new_offers", 0), "extracted": r.get("offers_extracted", 0)}
        except Exception as e:
            errors.append(f"poll: {e}")
            results["poll"] = {"error": str(e)}

    if not skip_pricebook:
        try:
            results["pricebook"] = phase_pricebook()
        except Exception as e:
            errors.append(f"pricebook: {e}")
            results["pricebook"] = {"error": str(e)}

    if not skip_matching:
        try:
            results["matching"] = phase_matching()
        except Exception as e:
            errors.append(f"matching: {e}")
            results["matching"] = {"error": str(e)}

    results["report"] = phase_report()
    if errors:
        results["errors"] = errors
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trading Robot F&V Runner")
    parser.add_argument("--email", default="apaminerala@yahoo.com")
    parser.add_argument("--password", help="Yahoo app password")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--skip-poll", action="store_true")
    parser.add_argument("--skip-pricebook", action="store_true")
    parser.add_argument("--skip-matching", action="store_true")
    parser.add_argument("--phase", choices=["poll", "pricebook", "matching", "report"], help="Run single phase")
    args = parser.parse_args()

    if args.phase == "poll":
        if not args.password:
            print('{"error": "Password required for poll"}')
            exit(1)
        print(json.dumps(phase_poll(args.email, args.password, args.days), indent=2, ensure_ascii=False))
    elif args.phase == "pricebook":
        print(json.dumps(phase_pricebook(), indent=2))
    elif args.phase == "matching":
        print(json.dumps(phase_matching(), indent=2, ensure_ascii=False))
    elif args.phase == "report":
        print(json.dumps(phase_report(), indent=2, ensure_ascii=False))
    else:
        if not args.password:
            print('{"error": "Password required for full cycle with poll"}')
            exit(1)
        result = run_cycle(args.email, args.password, args.days, args.skip_poll, args.skip_pricebook, args.skip_matching)
        print(json.dumps(result, indent=2, ensure_ascii=False))
