#!/usr/bin/env python3
"""CEREALE commodity price benchmark — keystone for grain trading (INTERNAL/GATED).

Fetches public grain references (best-effort, each source fails soft), normalizes
to EUR/ton + RON/ton per product, stores daily rows in cereale_price_benchmark.

Products (canonical RO): grau, porumb, orz, floarea-soarelui, rapita.

Sources:
  - euronext_matif : MATIF milling wheat + corn front-month futures (public quotes)
  - brm            : Bursa Romana de Marfuri grain listings (best-effort)
  - constanta_fob  : Constanta port FOB (STUB -> manual CSV cereale_port_prices.csv)
  - apia_madr      : MADR/APIA reference prices (best-effort)
  - manual         : any manual-entry CSV rows

No external sends. No scores published. Read-only on trading_offers.

Usage:
  python3 cereale_benchmark.py fetch          # fetch all sources, store rows
  python3 cereale_benchmark.py get grau       # print current best benchmark
  python3 cereale_benchmark.py status         # per-source live vs stub report
"""
import csv
import datetime as dt
import json
import os
import re
import sys
import urllib.request

try:
    import psycopg2
except ImportError:
    psycopg2 = None

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "DATA")
PORT_CSV = os.path.join(DATA_DIR, "cereale_port_prices.csv")
FX_FALLBACK = 4.97  # EUR->RON fallback if live FX unavailable

PRODUCTS = ["grau", "porumb", "orz", "floarea-soarelui", "rapita"]

DB = dict(host="127.0.0.1", dbname="interjob_master", user="tudor", password="tudor")

UA = {"User-Agent": "Mozilla/5.0 (cereale-benchmark internal)"}


def _conn():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not available")
    return psycopg2.connect(**DB)


def _fx_eur_ron():
    """Live EUR->RON from BNR; fallback to constant. Best-effort."""
    try:
        req = urllib.request.Request("https://www.bnr.ro/nbrfxrates.xml", headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", "ignore")
        m = re.search(r'<Rate currency="EUR"[^>]*>([\d.]+)</Rate>', xml)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return FX_FALLBACK


# ---------------------------------------------------------------------------
# Source fetchers. Each returns list of dicts:
#   {product, price_eur_ton, ref_date, note} ; price already EUR/ton.
# On failure raise or return [] -> marked stub in status.
# ---------------------------------------------------------------------------

def fetch_euronext_matif(fx):
    """MATIF milling wheat (EBM) + corn (EMA) front-month, EUR/ton.

    Euronext publishes delayed quotes via a JSON endpoint. Front-month product
    codes rotate; we query the instrument summary and take the nearest contract.
    Best-effort: if endpoint/shape changes, raise -> stub.
    """
    out = []
    endpoints = {
        "grau": "https://live.euronext.com/en/ajax/getDetailedQuote/EBM-DEC2025-EUR-XPAR",
        "porumb": "https://live.euronext.com/en/ajax/getDetailedQuote/EMA-NOV2025-EUR-XPAR",
    }
    got = False
    for product, url in endpoints.items():
        try:
            req = urllib.request.Request(url, headers=UA, method="POST")
            with urllib.request.urlopen(req, timeout=12) as r:
                html = r.read().decode("utf-8", "ignore")
            m = re.search(r'data-last[^>]*>\s*([\d]+[.,]?\d*)', html) or \
                re.search(r'"last(?:Price)?"\s*:\s*"?([\d]+[.,]?\d*)', html)
            if m:
                price = float(m.group(1).replace(",", "."))
                if 100 < price < 600:  # sanity: milling wheat/corn EUR/ton band
                    out.append({"product": product, "price_eur_ton": round(price, 2),
                                "ref_date": dt.date.today(), "note": "MATIF front-month"})
                    got = True
        except Exception:
            continue
    if not got:
        raise RuntimeError("MATIF endpoint returned no parseable quote")
    return out


def fetch_brm(fx):
    """Bursa Romana de Marfuri grain listings. Prices usually RON/ton.

    BRM does not expose a stable public price API; site is often JS-rendered.
    Best-effort HTML scrape of any grain price table; raise if nothing found.
    """
    try:
        req = urllib.request.Request("https://www.brm.ro/", headers=UA)
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", "ignore").lower()
    except Exception as e:
        raise RuntimeError("BRM unreachable: %s" % e)
    out = []
    for product, kw in [("grau", "grau"), ("porumb", "porumb"), ("orz", "orz"),
                        ("floarea-soarelui", "floarea"), ("rapita", "rapita")]:
        m = re.search(kw + r"[^0-9]{0,40}(\d{3,4}[.,]?\d*)\s*(?:lei|ron)", html)
        if m:
            ron = float(m.group(1).replace(",", "."))
            out.append({"product": product, "price_eur_ton": round(ron / fx, 2),
                        "ref_date": dt.date.today(), "note": "BRM listing (RON->EUR)"})
    if not out:
        raise RuntimeError("BRM: no grain price table parseable (JS-rendered?)")
    return out


def fetch_constanta_fob(fx):
    """Constanta port FOB grain. No reliable public free source -> STUB.

    Manual-entry CSV: DATA/cereale_port_prices.csv
      columns: product,price_eur_ton,ref_date[,note]
    """
    if not os.path.exists(PORT_CSV):
        raise RuntimeError("STUB: no public source; manual CSV missing (%s)" % PORT_CSV)
    out = []
    with open(PORT_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out.append({"product": row["product"].strip(),
                            "price_eur_ton": float(row["price_eur_ton"]),
                            "ref_date": dt.date.fromisoformat(row["ref_date"].strip()),
                            "note": row.get("note", "Constanta FOB manual")})
            except (KeyError, ValueError):
                continue
    if not out:
        raise RuntimeError("STUB: manual CSV present but empty")
    return out


def fetch_apia_madr(fx):
    """MADR/APIA published reference prices. No stable machine endpoint -> best-effort.

    MADR does not publish daily grain reference prices in a scrapeable feed;
    treated as best-effort and normally raises (stub) until a source is wired.
    """
    raise RuntimeError("STUB: MADR/APIA publishes no daily machine-readable grain feed")


SOURCES = {
    "euronext_matif": fetch_euronext_matif,
    "brm": fetch_brm,
    "constanta_fob": fetch_constanta_fob,
    "apia_madr": fetch_apia_madr,
}


def fetch_all(store=True):
    fx = _fx_eur_ron()
    report = {}
    rows = []
    for name, fn in SOURCES.items():
        try:
            recs = fn(fx)
            for rec in recs:
                rec["source"] = name
                rec["price_ron_ton"] = round(rec["price_eur_ton"] * fx, 2)
                rows.append(rec)
            report[name] = {"status": "LIVE", "rows": len(recs)}
        except Exception as e:
            report[name] = {"status": "STUB", "reason": str(e)[:200]}
    if store and rows:
        _store(rows)
    return report, rows, fx


def _store(rows):
    con = _conn()
    cur = con.cursor()
    for r in rows:
        cur.execute(
            """INSERT INTO cereale_price_benchmark
                 (product, source, price_eur_ton, price_ron_ton, ref_date, note)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (product, source, ref_date) DO UPDATE
                 SET price_eur_ton=EXCLUDED.price_eur_ton,
                     price_ron_ton=EXCLUDED.price_ron_ton,
                     fetched_at=now(), note=EXCLUDED.note""",
            (r["product"], r["source"], r["price_eur_ton"], r["price_ron_ton"],
             r["ref_date"], r.get("note")))
    con.commit()
    cur.close()
    con.close()


# Preference order when several sources have a value for a product.
SOURCE_PRIORITY = ["euronext_matif", "constanta_fob", "brm", "apia_madr", "manual"]


def get_benchmark(product):
    """Return current best reference for a grain product, or None.

    Picks the most recent ref_date; ties broken by SOURCE_PRIORITY.
    Returns dict {product, price_eur_ton, price_ron_ton, source, ref_date}.
    """
    con = _conn()
    cur = con.cursor()
    cur.execute(
        """SELECT product, source, price_eur_ton, price_ron_ton, ref_date
             FROM cereale_price_benchmark
            WHERE product=%s AND price_eur_ton IS NOT NULL
            ORDER BY ref_date DESC""", (product,))
    rows = cur.fetchall()
    cur.close()
    con.close()
    if not rows:
        return None
    newest = rows[0][4]
    cands = [r for r in rows if r[4] == newest]
    cands.sort(key=lambda r: SOURCE_PRIORITY.index(r[1]) if r[1] in SOURCE_PRIORITY else 99)
    r = cands[0]
    return {"product": r[0], "source": r[1], "price_eur_ton": r[2],
            "price_ron_ton": r[3], "ref_date": r[4].isoformat()}


def _main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "fetch":
        report, rows, fx = fetch_all(store=True)
        print("FX EUR->RON:", fx)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print("stored rows:", len(rows))
    elif cmd == "get":
        prod = sys.argv[2] if len(sys.argv) > 2 else "grau"
        print(json.dumps(get_benchmark(prod), ensure_ascii=False))
    else:
        report, _, fx = fetch_all(store=False)
        print("FX EUR->RON:", fx)
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()
