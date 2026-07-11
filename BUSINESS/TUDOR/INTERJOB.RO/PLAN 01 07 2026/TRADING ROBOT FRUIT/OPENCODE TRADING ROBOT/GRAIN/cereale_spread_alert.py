#!/usr/bin/env python3
"""CEREALE spread alert vs commodity benchmark (INTERNAL ONLY, GATED).

Reads grain offers from trading_offers (category='cereal' or grain product name),
compares offered price to cereale_price_benchmark. If the spread exceeds the
threshold (env CEREALE_SPREAD_PCT, default 8%), emits an internal tg/wa alert
to Tudor. De-dups via cereale_spread_alerts (one alert per offer_id).

READ-ONLY on trading_offers. No external sends, no auto-reply, no scores exposed.

Usage:
  python3 cereale_spread_alert.py run          # scan + alert
  python3 cereale_spread_alert.py test         # send ONE test alert to Tudor
"""
import os
import re
import sys

try:
    import psycopg2
except ImportError:
    psycopg2 = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cereale_benchmark as bench

try:
    from tg_notify import notify as tg
except Exception:
    def tg(_t, **_k):
        return False
try:
    from wa_notify import notify as wa
except Exception:
    def wa(_t, **_k):
        return False

THRESHOLD = float(os.environ.get("CEREALE_SPREAD_PCT", "8")) / 100.0

DB = dict(host="127.0.0.1", dbname="interjob_master", user="tudor", password="tudor")

# Map free-text product to canonical benchmark product.
GRAIN_MAP = [
    ("grau", "grau"), ("wheat", "grau"), ("porumb", "porumb"), ("corn", "porumb"),
    ("maize", "porumb"), ("orz", "orz"), ("barley", "orz"),
    ("floarea", "floarea-soarelui"), ("sunflower", "floarea-soarelui"),
    ("rapita", "rapita"), ("rapeseed", "rapita"), ("canola", "rapita"),
]


def _conn():
    return psycopg2.connect(**DB)


def _canonical(product_ro):
    if not product_ro:
        return None
    p = product_ro.lower()
    for kw, canon in GRAIN_MAP:
        if kw in p:
            return canon
    return None


def _to_eur_ton(price_per_unit, currency, fx):
    """Offers store price_per_unit; grain typically RON or EUR per kg or per ton.

    Heuristic: <10 => per kg (multiply 1000); >=10 => already per ton.
    Convert RON->EUR via fx.
    """
    if price_per_unit is None:
        return None
    v = float(price_per_unit)
    per_ton = v * 1000 if v < 10 else v
    cur = (currency or "").upper()
    if cur == "RON" or cur == "LEI":
        per_ton = per_ton / fx
    return round(per_ton, 2)


def _already_alerted(cur, offer_id):
    cur.execute("SELECT 1 FROM cereale_spread_alerts WHERE offer_id=%s", (offer_id,))
    return cur.fetchone() is not None


def scan(send=True):
    fx = bench._fx_eur_ron()
    con = _conn()
    cur = con.cursor()
    cur.execute(
        """SELECT offer_id, product_ro, price_per_unit, currency,
                  supplier_email, from_email
             FROM trading_offers
            WHERE (category='cereal'
                   OR product_ro ~* 'grau|porumb|orz|floarea|rapita|wheat|corn|barley|sunflower|rapeseed')
              AND price_per_unit IS NOT NULL""")
    offers = cur.fetchall()
    alerts = []
    for offer_id, product_ro, ppu, currency, sup, frm in offers:
        canon = _canonical(product_ro)
        if not canon:
            continue
        b = bench.get_benchmark(canon)
        if not b or not b["price_eur_ton"]:
            continue
        offered = _to_eur_ton(ppu, currency, fx)
        if offered is None or offered <= 0:
            continue
        bm = b["price_eur_ton"]
        spread = (offered - bm) / bm
        if abs(spread) < THRESHOLD:
            continue
        if _already_alerted(cur, offer_id):
            continue
        direction = "below" if spread < 0 else "above"
        contact = sup or frm or "n/a"
        msg = (
            "[CEREALE spread alert - INTERN]\n"
            "Produs: %s (%s)\n"
            "Oferit: %.0f EUR/t | Benchmark: %.0f EUR/t (%s)\n"
            "Spread: %+.1f%% (%s benchmark)\n"
            "Furnizor: %s\n"
            "offer_id: %s"
            % (canon, product_ro or "", offered, bm, b["source"],
               spread * 100, direction, contact, offer_id))
        if send:
            tg(msg)
            wa(msg, business="cumparlegume")
            cur.execute(
                """INSERT INTO cereale_spread_alerts
                     (offer_id, product, offered_eur_ton, benchmark_eur_ton,
                      benchmark_source, spread_pct, direction)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (offer_id) DO NOTHING""",
                (offer_id, canon, offered, bm, b["source"],
                 round(spread * 100, 2), direction))
            con.commit()
        alerts.append({"offer_id": offer_id, "product": canon, "offered": offered,
                       "benchmark": bm, "source": b["source"],
                       "spread_pct": round(spread * 100, 1), "direction": direction})
    cur.close()
    con.close()
    return alerts


def _main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "test":
        ok = tg("[CEREALE spread alert - TEST]\n"
                "Modul cereale_spread_alert LIVE. Prag %.0f%%. "
                "Doar intern, fara trimiteri externe." % (THRESHOLD * 100))
        print("test tg sent:", ok)
    else:
        res = scan(send=(cmd == "run"))
        import json
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print("alerts:", len(res))


if __name__ == "__main__":
    _main()
