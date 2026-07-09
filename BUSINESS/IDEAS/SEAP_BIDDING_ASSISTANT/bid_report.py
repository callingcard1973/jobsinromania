"""
SEAP Bid Intelligence Report — CLI
Usage:
  python bid_report.py --cpv 45233          # by CPV prefix
  python bid_report.py --cpv 45233140-2     # exact CPV
  python bid_report.py --company erbasu     # by company name
  python bid_report.py --buyer "primaria"   # by buyer name
  python bid_report.py --cpv 45 --year 2025 --top 20
"""
import csv, sys, argparse, re
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "DATA"
PROFILES = DATA / "winner_profiles.csv"
CONTRACTS = DATA / "winner_contracts_detail.csv"


def load_contracts(cpv_prefix="", company="", buyer="", year=""):
    rows = []
    with open(CONTRACTS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if cpv_prefix and not r["cpv"].replace("-","").startswith(cpv_prefix.replace("-","")):
                continue
            if company and company.lower() not in r["winner"].lower():
                continue
            if buyer and buyer.lower() not in r["buyer"].lower():
                continue
            if year and r["year"] != year:
                continue
            try:
                r["value_ron"] = float(r["value_ron"] or 0)
            except:
                r["value_ron"] = 0.0
            rows.append(r)
    return rows


def load_profiles(cpv_prefix="", company=""):
    rows = []
    with open(PROFILES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if cpv_prefix and not any(
                c.replace("-","").startswith(cpv_prefix.replace("-",""))
                for c in r["cpv_codes"].split("; ")
            ):
                continue
            if company and company.lower() not in r["name"].lower():
                continue
            try:
                r["total_ron_M"] = float(r["total_ron_M"] or 0)
                r["contracts"]   = int(r["contracts"] or 0)
                r["avg_ron"]     = float(r["avg_ron"] or 0)
                r["min_ron"]     = float(r["min_ron"] or 0)
                r["max_ron"]     = float(r["max_ron"] or 0)
            except:
                pass
            rows.append(r)
    return rows


def fmt_ron(v):
    if v >= 1e6: return f"{v/1e6:.1f}M RON"
    if v >= 1e3: return f"{v/1e3:.0f}K RON"
    return f"{v:.0f} RON"


def report(args):
    cpv   = args.cpv or ""
    comp  = args.company or ""
    buyer = args.buyer or ""
    year  = args.year or ""
    top_n = args.top

    contracts = load_contracts(cpv, comp, buyer, year)
    if not contracts:
        print("❌ No contracts found for given filters.")
        return

    # Aggregate by winner
    winners = defaultdict(lambda: {"contracts": 0, "total": 0.0, "values": [], "buyers": set(), "cpvs": set()})
    for c in contracts:
        w = winners[c["winner"]]
        w["contracts"] += 1
        w["total"] += c["value_ron"]
        if c["value_ron"] > 0: w["values"].append(c["value_ron"])
        if c["buyer"]: w["buyers"].add(c["buyer"])
        if c["cpv"]:   w["cpvs"].add(c["cpv"])

    sorted_w = sorted(winners.items(), key=lambda x: x[1]["total"], reverse=True)[:top_n]

    all_values = [c["value_ron"] for c in contracts if c["value_ron"] > 0]
    total_market = sum(all_values)
    avg_val = total_market / len(all_values) if all_values else 0
    median_val = sorted(all_values)[len(all_values)//2] if all_values else 0

    # Buyer frequency
    buyer_freq = defaultdict(int)
    for c in contracts:
        if c["buyer"]: buyer_freq[c["buyer"]] += 1
    top_buyers = sorted(buyer_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    # CPV breakdown
    cpv_freq = defaultdict(lambda: {"count": 0, "total": 0.0})
    for c in contracts:
        cpv_freq[c["cpv"]]["count"] += 1
        cpv_freq[c["cpv"]]["total"] += c["value_ron"]
    top_cpvs = sorted(cpv_freq.items(), key=lambda x: x[1]["total"], reverse=True)[:8]

    # Year breakdown
    year_freq = defaultdict(lambda: {"count": 0, "total": 0.0})
    for c in contracts:
        year_freq[c["year"]]["count"] += 1
        year_freq[c["year"]]["total"] += c["value_ron"]

    # Print report
    W = 72
    print("=" * W)
    print("  SEAP BID INTELLIGENCE REPORT")
    filters = []
    if cpv:   filters.append(f"CPV: {cpv}")
    if comp:  filters.append(f"Company: {comp}")
    if buyer: filters.append(f"Buyer: {buyer}")
    if year:  filters.append(f"Year: {year}")
    print(f"  Filters: {' | '.join(filters) or 'none'}")
    print("=" * W)

    print(f"\n📊 MARKET OVERVIEW")
    print(f"  Total contracts:  {len(contracts):,}")
    print(f"  Total value:      {fmt_ron(total_market)}")
    print(f"  Unique winners:   {len(winners):,}")
    print(f"  Unique buyers:    {len(buyer_freq):,}")
    print(f"  Avg contract:     {fmt_ron(avg_val)}")
    print(f"  Median contract:  {fmt_ron(median_val)}")
    print(f"  Min contract:     {fmt_ron(min(all_values)) if all_values else 'N/A'}")
    print(f"  Max contract:     {fmt_ron(max(all_values)) if all_values else 'N/A'}")

    print(f"\n📅 BY YEAR")
    for y, d in sorted(year_freq.items()):
        print(f"  {y}: {d['count']:>6,} contracts | {fmt_ron(d['total'])}")

    print(f"\n🏆 TOP {top_n} WINNERS")
    print(f"  {'#':<4} {'Company':<38} {'Contracts':>9} {'Total':>12} {'Avg':>10} {'Market%':>7}")
    print(f"  {'-'*4} {'-'*38} {'-'*9} {'-'*12} {'-'*10} {'-'*7}")
    for i, (name, d) in enumerate(sorted_w, 1):
        pct = d["total"] / total_market * 100 if total_market else 0
        avg = d["total"] / d["contracts"] if d["contracts"] else 0
        print(f"  {i:<4} {name[:38]:<38} {d['contracts']:>9,} {fmt_ron(d['total']):>12} {fmt_ron(avg):>10} {pct:>6.1f}%")

    print(f"\n🏛️  TOP BUYERS")
    for buyer_name, cnt in top_buyers:
        print(f"  {cnt:>5} contracts — {buyer_name[:60]}")

    if len(top_cpvs) > 1:
        print(f"\n📋 TOP CPV CODES")
        for cpv_code, d in top_cpvs:
            print(f"  {cpv_code} — {d['count']:,} contracts | {fmt_ron(d['total'])}")

    print(f"\n💡 BID STRATEGY INSIGHT")
    if sorted_w:
        top_name, top_d = sorted_w[0]
        top_pct = top_d["total"] / total_market * 100 if total_market else 0
        if top_pct > 30:
            print(f"  ⚠️  Market dominated by {top_name[:35]} ({top_pct:.0f}%). Hard to enter.")
        elif top_pct > 15:
            print(f"  ⚡ {top_name[:35]} leads ({top_pct:.0f}%). Competitive but possible.")
        else:
            print(f"  ✅ Fragmented market. No single dominant player. Good opportunity.")

    concentration = sum(d["total"] for _, d in sorted_w[:3]) / total_market * 100 if total_market else 0
    print(f"  Top 3 winners hold {concentration:.0f}% of market value.")
    print(f"  Sweet spot bid: {fmt_ron(median_val)} (median contract size)")

    print("=" * W)
    return {"contracts": contracts, "winners": sorted_w, "market_total": total_market,
            "avg": avg_val, "median": median_val, "top_buyers": top_buyers}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cpv",     default="", help="CPV code or prefix (e.g. 45, 45233140)")
    p.add_argument("--company", default="", help="Company name fragment")
    p.add_argument("--buyer",   default="", help="Buyer name fragment")
    p.add_argument("--year",    default="", help="Year (2023/2024/2025)")
    p.add_argument("--top",     default=15, type=int, help="Top N winners")
    args = p.parse_args()

    if not any([args.cpv, args.company, args.buyer]):
        print("Usage: python bid_report.py --cpv 45233 [--year 2025] [--top 20]")
        sys.exit(1)

    report(args)
