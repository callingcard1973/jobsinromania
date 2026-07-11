#!/usr/bin/env python3
"""FIX: MATIF Euronext front-month grain benchmark fetcher.

Replaces the hardcoded expired-contract URLs in cereale_benchmark.py
with dynamic front-month contract resolution. Run standalone to verify,
then integrate into cereale_benchmark.fetch_euronext_matif.

Euronext contract month codes (Euronext uses letter codes + year):
  EBM (Milling Wheat): H(Mar) K(May) U(Sep) Z(Dec)
  EMA (Corn/Maize):    H(Mar) M(Jun) U(Sep) Z(Dec)

Usage:
  python GRAIN/fix_matif_benchmark.py          # fetch front-month quotes
  python GRAIN/fix_matif_benchmark.py --test    # show what URLs would be built
"""
import json
import re
import sys
import urllib.request
from datetime import date

UA = {"User-Agent": "Mozilla/5.0 (cereale-benchmark fix_matif; internal)"}

# Euronext instrument -> contract month codes (Euronext letter codes)
INSTRUMENTS = {
    "grau": {
        "code": "EBM",
        "months": [3, 5, 9, 12],     # Mar, May, Sep, Dec
        "month_letters": {3: "MAR", 5: "MAY", 9: "SEP", 12: "DEC"},
        "name": "Euronext Milling Wheat",
    },
    "porumb": {
        "code": "EMA",
        "months": [3, 6, 9, 12],      # Mar, Jun, Sep, Dec
        "month_letters": {3: "MAR", 6: "JUN", 9: "SEP", 12: "DEC"},
        "name": "Euronext Maize",
    },
}


def front_month(contract_months, today=None):
    """Return (month_num, year) of the front-month contract."""
    if today is None:
        today = date.today()
    this_year = today.year
    next_year = this_year + 1

    # Current month has already started - find next contract month.
    # Front-month = the next contract month (or current month if we're in it).
    current = today.month
    for m in sorted(contract_months):
        if m >= current:
            return (m, this_year)
    # All this year's contracts are past -> first month next year.
    return (min(contract_months), next_year)


def build_url(instr, month_num, year):
    """Build Euronext detailed quote URL for a contract."""
    ml = instr["month_letters"][month_num]
    code = instr["code"]
    return f"https://live.euronext.com/en/ajax/getDetailedQuote/{code}-{ml}{year}-EUR-XPAR"


def fetch_contract(url, product, timeout=15):
    """Fetch one Euronext contract URL, extract last price.
    
    Returns (price_eur_ton, note) or raises.
    """
    req = urllib.request.Request(url, headers=UA, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        html = r.read().decode("utf-8", "ignore")

    price = None
    patterns = [
        r'data-last[^>]*>\s*([\d]+[.,]?\d*)',
        r'"last(?:Price)?"\s*:\s*"?([\d]+[.,]?\d*)',
        r'<span[^>]*class="[^"]*last[^"]*"[^>]*>\s*([\d]+[.,]?\d*)',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            val = float(m.group(1).replace(",", "."))
            if 50 < val < 800:
                price = val
                break

    if price is None:
        # Try alternate endpoint: Euronext summary API
        summary_url = url.replace("getDetailedQuote", "getInstrumentSummary")
        try:
            req2 = urllib.request.Request(summary_url, headers=UA, method="POST")
            with urllib.request.urlopen(req2, timeout=timeout) as r:
                html2 = r.read().decode("utf-8", "ignore")
            for pat in patterns:
                m = re.search(pat, html2)
                if m:
                    val = float(m.group(1).replace(",", "."))
                    if 50 < val < 800:
                        price = val
                        break
        except Exception:
            pass

    if price is None:
        raise RuntimeError(f"No parseable price in {url}")
    return price


def fetch_all(today=None):
    """Fetch all MATIF front-month grain quotes.
    
    Returns list of {product, price_eur_ton, ref_date, note, source}.
    """
    if today is None:
        today = date.today()
    results = []
    errors = []

    for product, instr in INSTRUMENTS.items():
        fm_month, fm_year = front_month(instr["months"], today)
        url = build_url(instr, fm_month, fm_year)

        contract_label = f'{instr["code"]}-{instr["month_letters"][fm_month]}{fm_year}'
        try:
            price = fetch_contract(url, product)
            results.append({
                "product": product,
                "price_eur_ton": round(price, 2),
                "ref_date": today.isoformat(),
                "note": f"MATIF {contract_label} front-month",
                "source": "euronext_matif",
            })
        except Exception as e:
            errors.append({"product": product, "contract": contract_label,
                           "error": str(e)[:200]})
            # Fallback: try next contract back if front-month expired.
            if fm_month == min(instr["months"]):
                continue  # already at first month of year, can't go back
            prev_months = [m for m in instr["months"] if m < fm_month]
            if prev_months:
                fallback_month = max(prev_months)
                fallback_url = build_url(instr, fallback_month, fm_year)
                fb_label = f'{instr["code"]}-{instr["month_letters"][fallback_month]}{fm_year}'
                try:
                    price = fetch_contract(fallback_url, product)
                    results.append({
                        "product": product,
                        "price_eur_ton": round(price, 2),
                        "ref_date": today.isoformat(),
                        "note": f"MATIF {fb_label} (fallback front-month)",
                        "source": "euronext_matif",
                    })
                    errors.pop()  # clear the error since we got data
                except Exception as e2:
                    errors[-1]["fallback_error"] = str(e2)[:200]

    return results, errors


def _test_urls(today=None):
    """Print the URLs that would be built, without fetching."""
    if today is None:
        today = date.today()
    lines = []
    for product, instr in INSTRUMENTS.items():
        fm_month, fm_year = front_month(instr["months"], today)
        url = build_url(instr, fm_month, fm_year)
        ml = instr["month_letters"][fm_month]
        label = f'{instr["code"]}-{ml}{fm_year}'
        lines.append(f"  {product:12s} -> {label:18s}  {url}")
    return "\n".join(lines)


def main():
    if "--test" in sys.argv:
        print("Front-month contracts for", date.today())
        print(_test_urls())
        print("\nUse --dry to test-fetch without output.")
        return 0

    if "--dry" in sys.argv:
        results, errors = fetch_all()
        print("Results:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        if errors:
            print("\nErrors:")
            print(json.dumps(errors, indent=2, ensure_ascii=False))
        return 0

    results, errors = fetch_all()
    out = {"results": results, "errors": errors,
           "fx_eur_ron": None}  # caller should fill fx

    if results:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        print(f"\nOK: {len(results)} quotes fetched.", file=sys.stderr)
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        print(f"\nFAIL: all {len(INSTRUMENTS)} instruments failed.", file=sys.stderr)
        return 1

    if errors:
        print(f"WARN: {len(errors)} errors:", file=sys.stderr)
        for e in errors:
            print(f"  {e['product']} ({e['contract']}): {e['error']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
