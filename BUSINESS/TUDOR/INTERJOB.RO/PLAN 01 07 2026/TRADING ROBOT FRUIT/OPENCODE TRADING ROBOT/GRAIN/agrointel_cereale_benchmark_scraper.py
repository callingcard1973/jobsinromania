#!/usr/bin/env python3
"""[CLAUDE GRAIN DESK 2026-07-10] Scrapes agrointel.ro grain prices into cereale_port_prices.csv.

Primary target: DAILY category https://agrointel.ro/category/burse-si-preturi
("Piata cerealelor, la zi" articles -> source=agrointel_daily). Also supports
the weekly retrospective ("piata-cerealelor-retrospectiva" ->
source=agrointel_weekly). Extracts grau/porumb/orz/rapita/floarea-soarelui/soia
quotes per market (Euronext/MATIF/Constanta/Odesa/Rusia/CBOT/Ucraina).
Values may be absolute prices OR deltas -> column value_type (price/delta).
Dedup on ref_date+market+product+value_type. price_eur_ton is filled ONLY for
Constanta EUR absolute prices (kept compatible with cereale_benchmark.py).
--backfill N walks category pages 1..N (max 36). No sends, no DB. Local CSV only.
Secondary source (not implemented yet): bursacereale.com.
"""
import argparse
import csv
import html as _html
import os
import re
import sys
import unicodedata
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "DATA", "cereale_port_prices.csv")
CATEGORY_URL = "https://agrointel.ro/category/burse-si-preturi"
UA = {"User-Agent": "Mozilla/5.0 (grain-desk internal benchmark reader)"}
FIELDS = ["product", "price_eur_ton", "ref_date", "note", "market",
          "currency", "value", "value_type", "source", "source_url"]

PRODUCTS = [("grau", ["grau", "graul"]), ("porumb", ["porumb"]),
            ("orz", ["orz"]), ("rapita", ["rapita"]),
            ("floarea-soarelui", ["floarea-soarelui", "floarea soarelui"]),
            ("soia", ["soia"])]
MARKETS = [("Euronext", ["euronext"]), ("MATIF", ["matif"]),
           ("Constanta", ["constanta"]), ("Odesa", ["odesa", "cpt odesa"]),
           ("Rusia", ["rusesc", "rusia", "ruseasca"]),
           ("CBOT", ["cbot", "chicago"]), ("Ucraina", ["ucrain"])]
DAILY_SLUG = r"piata-cerealelor-la-zi"
WEEKLY_SLUG = r"piata-cerealelor-retrospectiva"
MONTHS = {"ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4, "mai": 5,
          "iunie": 6, "iulie": 7, "august": 8, "septembrie": 9,
          "octombrie": 10, "noiembrie": 11, "decembrie": 12}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")


def to_text(page_html):
    t = re.sub(r"<(script|style).*?</\1>", " ", page_html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _html.unescape(t)
    for ch in ("–", "—", "−"):
        t = t.replace(ch, "-")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t)


def category_articles(page_no, slug):
    """Article URLs (document order = newest first) on a category page."""
    url = CATEGORY_URL if page_no == 1 else "%s/page/%d" % (CATEGORY_URL, page_no)
    page = fetch(url)
    urls = re.findall(r'href="(https://agrointel\.ro/\d+/%s[^"]*)"' % slug, page)
    out = []
    for u in urls:
        if u not in out:
            out.append(u)
    return out


def find_latest_url(slug):
    urls = category_articles(1, slug)
    if not urls:
        raise RuntimeError("no article matching '%s' on category page 1" % slug)
    return urls[0]


def ref_date_from_article(page_html, text):
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', page_html) or \
        re.search(r'published_time"\s+content="(\d{4}-\d{2}-\d{2})', page_html)
    year = int(m.group(1)[:4]) if m else 2026
    pub = m.group(1) if m else None
    # END of the retrospective week from title, e.g. "24 iunie-1 iulie"
    t = re.search(r"retrospectiva saptamanii\s+\d{1,2}\s*(?:[a-z]+)?\s*-\s*"
                  r"(\d{1,2})\s+([a-z]+)", text[:400], re.I)
    if t and t.group(2).lower() in MONTHS:
        return "%04d-%02d-%02d" % (year, MONTHS[t.group(2).lower()], int(t.group(1)))
    return pub or "unknown"


def _num(s):
    return float(s.replace(",", "."))


def _range_mid(m1, m2):
    a, b = _num(m1), _num(m2)
    return round((a + b) / 2, 2)


def _positions(low, table):
    """[(index, canonical)] for every keyword occurrence, sorted by index."""
    out = []
    for canon, kws in table:
        for kw in kws:
            out += [(m.start(), canon) for m in re.finditer(re.escape(kw), low)]
    return sorted(out)


def _nearest_before(pos_list, p, window):
    cands = [(p - i, c) for i, c in pos_list if 0 <= p - i <= window]
    return min(cands)[1] if cands else None


def _nearest_around(pos_list, p, back, fwd):
    """Market is usually named right AFTER the number ("... la Euronext");
    prefer a forward hit, fall back to the nearest backward one."""
    ahead = [(i - p, c) for i, c in pos_list if p <= i <= p + fwd]
    if ahead:
        return min(ahead)[1]
    behind = [(p - i, c) for i, c in pos_list if p - back <= i < p]
    return min(behind)[1] if behind else None


DELTA_PATS = [
    (r"(?:minus|scadere de|a scazut cu(?: aproximativ)?|a pierdut)\s+"
     r"(\d+[.,]?\d*)\s*(?:-\s*(\d+[.,]?\d*))?\s*(eur|euro|usd|dolari)", -1),
    (r"(?:plus(?: de)?|apreciere de|crestere de|a crescut cu)\s+"
     r"(\d+[.,]?\d*)\s*(?:-\s*(\d+[.,]?\d*))?\s*(eur|euro|usd|dolari)", +1),
]
PRICE_PAT = (r"(?:pana la|la|sub pragul de|in jurul valorii de)\s+"
             r"(?:aproximativ|circa)?\s*(\d{3}[.,]?\d*)"
             r"\s*(?:-\s*(\d{3}[.,]?\d*))?\s*(eur|usd)\s*/?t")


def extract_quotes(text):
    """Proximity pairing: nearest product before the number, market in a window."""
    low = text.lower()
    prod_pos = _positions(low, PRODUCTS)
    mkt_pos = _positions(low, MARKETS)
    quotes, seen = [], set()

    def add(m, value, vtype, cur, note):
        prod = _nearest_before(prod_pos, m.start(), 350)
        if not prod:
            return
        market = _nearest_around(mkt_pos, m.start(), 150, 60) or "general"
        key = (prod, market, vtype, value, cur)
        if key in seen:
            return
        seen.add(key)
        quotes.append(dict(product=prod, market=market, currency=cur,
                           value=value, value_type=vtype, note=note))

    for pat, sign in DELTA_PATS:
        for m in re.finditer(pat, low):
            v = _range_mid(m.group(1), m.group(2)) if m.group(2) else _num(m.group(1))
            cur = "USD" if m.group(3) in ("usd", "dolari") else "EUR"
            note = "delta saptamanal"
            if m.group(2):
                note += " (interval %s-%s)" % (m.group(1), m.group(2))
            add(m, sign * v, "delta", cur, note)
    for m in re.finditer(PRICE_PAT, low):
        v = _range_mid(m.group(1), m.group(2)) if m.group(2) else _num(m.group(1))
        note = "pret absolut"
        if m.group(2):
            note += " (interval %s-%s)" % (m.group(1), m.group(2))
        if "sub pragul" in low[max(0, m.start() - 5):m.start() + 15]:
            note += " (sub prag)"
        add(m, v, "price", m.group(3).upper(), note)
    return quotes


def load_existing(path):
    rows, keys = [], set()
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                # upgrade legacy rows to extended schema
                r.setdefault("market", "Constanta")
                r.setdefault("currency", "EUR")
                r.setdefault("value", r.get("price_eur_ton", ""))
                r.setdefault("value_type", "price")
                r.setdefault("source", "manual")
                r.setdefault("source_url", "")
                rows.append({k: (r.get(k) or "") for k in FIELDS})
                keys.add((r["ref_date"], r["market"], r["product"], r["value_type"]))
    return rows, keys


def append_quotes(quotes, ref_date, source, source_url,
                  csv_path=CSV_PATH, dry_run=False):
    rows, keys = load_existing(csv_path)
    added = 0
    for q in quotes:
        key = (ref_date, q["market"], q["product"], q["value_type"])
        if key in keys:
            continue
        keys.add(key)
        is_ct_price = (q["market"] == "Constanta" and q["currency"] == "EUR"
                       and q["value_type"] == "price")
        rows.append(dict(product=q["product"],
                         price_eur_ton=q["value"] if is_ct_price else "",
                         ref_date=ref_date, note=source + " - " + q["note"],
                         market=q["market"], currency=q["currency"],
                         value=q["value"], value_type=q["value_type"],
                         source=source, source_url=source_url))
        added += 1
    if not dry_run:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return added


def process_article(url, source, csv_path, dry_run, verbose=True):
    page = fetch(url)
    text = to_text(page)
    ref_date = ref_date_from_article(page, text)
    quotes = extract_quotes(text)
    if verbose:
        for q in quotes:
            print("%-16s %-10s %8s %-3s %-6s %s" % (
                q["product"], q["market"], q["value"], q["currency"],
                q["value_type"], q["note"]))
    added = append_quotes(quotes, ref_date, source, url, csv_path, dry_run)
    print("url=%s ref_date=%s quotes=%d appended=%d dry_run=%s"
          % (url, ref_date, len(quotes), added, dry_run))
    return added


def main():
    ap = argparse.ArgumentParser(description="agrointel grain price scraper")
    ap.add_argument("--url", help="article URL (default: auto-find latest)")
    ap.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    ap.add_argument("--backfill", type=int, default=0, metavar="N",
                    help="walk category pages 1..N (max 36) for history")
    ap.add_argument("--csv", default=CSV_PATH)
    ap.add_argument("--dry-run", action="store_true", help="print quotes, no CSV write")
    args = ap.parse_args()
    slug = DAILY_SLUG if args.mode == "daily" else WEEKLY_SLUG
    source = "agrointel_daily" if args.mode == "daily" else "agrointel_weekly"
    if args.url:
        source = ("agrointel_weekly" if "retrospectiva" in args.url
                  else "agrointel_daily")
        process_article(args.url, source, args.csv, args.dry_run)
    elif args.backfill:
        total = 0
        for page_no in range(1, min(args.backfill, 36) + 1):
            for url in category_articles(page_no, slug):
                try:
                    total += process_article(url, source, args.csv,
                                             args.dry_run, verbose=False)
                except Exception as e:
                    print("SKIP %s: %s" % (url, str(e)[:120]))
        print("backfill done, rows added: %d" % total)
    else:
        process_article(find_latest_url(slug), source, args.csv, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
