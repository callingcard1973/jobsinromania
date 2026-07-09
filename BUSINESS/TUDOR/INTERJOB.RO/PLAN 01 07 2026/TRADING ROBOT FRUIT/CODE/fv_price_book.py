#!/usr/bin/env python3
"""Maintains F&V price book: benchmarks, trends, EU market comparison."""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "..", "DATA", "offers_ledger.jsonl")
PRICEBOOK_PATH = os.path.join(os.path.dirname(__file__), "..", "DATA", "price_book.json")


def offer_date(o):
    """Data ofertei: extracted_at (poller) sau timestamp (inbox); '' daca lipseste."""
    return o.get("extracted_at") or o.get("timestamp") or ""

def load_offers(ledger_path=LEDGER_PATH, max_age_days=60):
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
    cutoff = datetime.now() - timedelta(days=max_age_days)
    valid = []
    for o in offers:
        # cereri nu intra in price book; doar oferte (cu pret)
        if o.get("entry_type") == "request":
            continue
        # daca data lipseste, pastreaza oferta
        raw = offer_date(o)
        try:
            if raw and datetime.fromisoformat(raw[:19]) < cutoff:
                continue
        except (ValueError, TypeError):
            pass
        valid.append(o)
    return valid

def build_price_book(offers, include_trend=False):
    book = {}
    groups = defaultdict(list)
    for o in offers:
        # moneda in cheie: nu amesteca EUR cu RON in acelasi benchmark
        cur = (o.get("currency") or "RON").upper()
        key = (o.get("product_ro", "unknown"), o.get("quality_class", "unknown"),
               o.get("origin", "unknown"), cur)
        if o.get("price_per_unit") is not None and o["price_per_unit"] > 0:
            groups[key].append(o)

    for (product, quality, origin, currency), group in groups.items():
        prices = sorted([o["price_per_unit"] for o in group if o.get("price_per_unit")])
        if not prices:
            continue

        avg_p = sum(prices) / len(prices)
        median_p = prices[len(prices) // 2] if len(prices) % 2 else (prices[len(prices)//2-1] + prices[len(prices)//2]) / 2

        latest = max(group, key=offer_date)
        last_offer_date = offer_date(latest)[:10]

        entry = {
            "product": product,
            "quality": quality,
            "origin": origin,
            "currency": currency,
            "last_updated": last_offer_date,
            "benchmark": {
                "min_price_eur_kg": min(prices),
                "max_price_eur_kg": max(prices),
                "avg_price_eur_kg": round(avg_p, 3),
                "median_price_eur_kg": round(median_p, 3),
                "offer_count": len(prices),
                "last_price_eur_kg": latest.get("price_per_unit"),
            },
            "available_offers": [
                {"from": g.get("source_email_id", "?"), "price": g.get("price_per_unit"),
                 "qty_kg": g.get("quantity_kg"), "date": offer_date(g)[:10]}
                for g in sorted(group, key=offer_date, reverse=True)[:5]
            ],
            "confidence": "high" if len(prices) >= 5 else "medium" if len(prices) >= 2 else "low",
        }

        if include_trend and len(prices) >= 10:
            mid = len(prices) // 2
            first_half = sum(prices[:mid]) / mid
            second_half = sum(prices[mid:]) / (len(prices) - mid)
            diff_pct = ((second_half - first_half) / first_half) * 100
            if diff_pct > 10:
                entry["benchmark"]["trend"] = "up"
            elif diff_pct < -10:
                entry["benchmark"]["trend"] = "down"
            else:
                entry["benchmark"]["trend"] = "stable"

        key_str = f"{product}|{quality}|{origin}|{currency}"
        book[key_str] = entry

    return book

def save_price_book(book, path=PRICEBOOK_PATH):
    # nu suprascrie un book existent cu unul gol (ledger gol/eroare => pastreaza ce era)
    if not book and os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # scriere atomica: temp + replace (crash la mijloc nu corupe price_book.json)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(book, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def get_trends(book):
    trends = []
    for key, entry in book.items():
        b = entry.get("benchmark", {})
        if b.get("trend") in ("up", "down"):
            trends.append({"product": entry["product"], "trend": b["trend"],
                           "change": f"{entry['quality']} / {entry['origin']}"})
    return sorted(trends, key=lambda x: x["product"])

def build_forecast(offers):
    """Analyze price history grouped by product+month and produce a 30-day forecast.

    Returns dict: {product: {current_avg, forecast_avg, direction, confidence,
                             mom_change_pct, data_points, months_analyzed}}
    """
    groups = defaultdict(list)
    for o in offers:
        raw = offer_date(o)
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(raw[:19])
        except (ValueError, TypeError):
            continue
        prod = o.get("product_ro", "unknown")
        price = o.get("price_per_unit")
        if price is None or price <= 0:
            continue
        month_key = dt.strftime("%Y-%m")
        groups[(prod, month_key)].append(price)

    product_monthly = defaultdict(dict)
    for (prod, month_key), prices in groups.items():
        avg = sum(prices) / len(prices)
        product_monthly[prod][month_key] = {
            "avg_price": round(avg, 3),
            "count": len(prices),
        }

    forecast = {}
    for prod, months in product_monthly.items():
        total_points = sum(m["count"] for m in months.values())
        if total_points < 3:
            continue
        sorted_months = sorted(months.items())
        if len(sorted_months) < 2:
            continue

        changes = []
        for i in range(1, len(sorted_months)):
            prev_avg = sorted_months[i - 1][1]["avg_price"]
            curr_avg = sorted_months[i][1]["avg_price"]
            if prev_avg <= 0:
                continue
            change_pct = round(((curr_avg - prev_avg) / prev_avg) * 100, 2)
            changes.append(change_pct)

        if not changes:
            continue

        avg_mom_change = sum(changes) / len(changes)
        current_avg = sorted_months[-1][1]["avg_price"]
        forecast_avg = round(current_avg * (1 + avg_mom_change / 100), 3)

        if avg_mom_change > 5:
            direction = "up"
        elif avg_mom_change < -5:
            direction = "down"
        else:
            direction = "stable"

        conf = "high" if len(changes) >= 3 else "medium" if len(changes) >= 2 else "low"

        forecast[prod] = {
            "current_avg": current_avg,
            "forecast_avg": forecast_avg,
            "direction": direction,
            "confidence": conf,
            "mom_change_pct": round(avg_mom_change, 2),
            "data_points": total_points,
            "months_analyzed": len(sorted_months),
            "period": f"{sorted_months[0][0]} -> {sorted_months[-1][0]}",
        }

    return forecast

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FV Price Book")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild from scratch")
    parser.add_argument("--product", help="Filter by product name")
    parser.add_argument("--trends", action="store_true", help="Show trending products only")
    parser.add_argument("--dump", action="store_true", help="Print full price book")
    parser.add_argument("--forecast", action="store_true", help="Generate 30-day price forecast")
    args = parser.parse_args()

    construe_book = args.rebuild or args.forecast

    offers = load_offers()
    book = build_price_book(offers, include_trend=True)
    if construe_book:
        if args.forecast:
            book["forecast"] = build_forecast(offers)
        save_price_book(book)

    view = book
    if args.product:
        p = args.product.lower()
        view = {k: v for k, v in book.items() if p in v.get("product", "").lower()}

    if args.trends:
        trends = get_trends(view)
        print(json.dumps({"product_count": len(view), "trending": trends}, indent=2, ensure_ascii=False))
    elif args.dump or args.product:
        print(json.dumps(view, indent=2, ensure_ascii=False))
    else:
        out = {"product_count": len(book), "status": "rebuild_ok"}
        if "forecast" in book:
            out["forecast_count"] = len(book["forecast"])
        print(json.dumps(out, indent=2))
