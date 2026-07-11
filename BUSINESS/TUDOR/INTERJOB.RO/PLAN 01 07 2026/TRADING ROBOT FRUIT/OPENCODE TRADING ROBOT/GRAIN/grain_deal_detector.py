#!/usr/bin/env python3
import csv, json, os, re, sqlite3, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(HERE), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import config as CFG

DATA = CFG.DATA
PORT_CSV = os.path.join(DATA, "cereale_port_prices.csv")
GRAIN_DB = os.path.join(DATA, "grain.db")
PENDING = os.path.join(DATA, "grain_alerts_pending.jsonl")
TG_CFG_PATH = CFG.TG_CEREALE_CFG

N2_PCT = float(os.environ.get("GRAIN_N2_PCT", "-3"))
N2_TONS = float(os.environ.get("GRAIN_N2_TONS", "500"))
FX_EUR_RON = float(os.environ.get("GRAIN_FX_EUR_RON", "4.97"))
FX_USD_EUR = float(os.environ.get("GRAIN_FX_USD_EUR", "0.92"))

GRAIN_MAP = [("grau", "grau"), ("wheat", "grau"), ("porumb", "porumb"),
             ("corn", "porumb"), ("orz", "orz"), ("barley", "orz"),
             ("floarea", "floarea-soarelui"), ("sunflower", "floarea-soarelui"),
             ("rapita", "rapita"), ("naut", "naut"), ("soia", "soia"),
             ("mustar", "mustar"), ("mustard", "mustar"), ("mazare", "mazare"),
             ("lucerna", "lucerna"), ("chickpea", "naut")]

MARKET_PREF = ["Constanta", "Odesa", "Ucraina", "Rusia", "MATIF",
               "Euronext", "CBOT", "general"]


def canonical(product):
    p = (product or "").lower()
    for kw, canon in GRAIN_MAP:
        if kw in p:
            return canon
    return None


def to_eur_ton(price, currency):
    if price is None:
        return None
    v = float(price)
    per_ton = v * 1000 if v < 10 else v
    cur = (currency or "EUR").upper()
    if cur in ("RON", "LEI"):
        per_ton /= FX_EUR_RON
    elif cur == "USD":
        per_ton *= FX_USD_EUR
    return round(per_ton, 2)


def load_benchmarks():
    path = PORT_CSV
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("value_type") or "price") != "price":
                continue
            try:
                val = float(r.get("value") or r.get("price_eur_ton"))
            except (TypeError, ValueError):
                continue
            eur = to_eur_ton(val if val >= 10 else val, r.get("currency") or "EUR")
            prod, mkt = r["product"].strip(), (r.get("market") or "Constanta").strip()
            cur = out.setdefault(prod, {})
            if mkt not in cur or r["ref_date"] > cur[mkt][1]:
                cur[mkt] = (eur, r["ref_date"], r.get("currency") or "EUR")
    return out


def regional_benchmark(product, benchmarks):
    mkts = benchmarks.get(product, {})
    for pref in MARKET_PREF:
        if pref in mkts:
            return dict(market=pref, eur_ton=mkts[pref][0],
                        ref_date=mkts[pref][1], currency=mkts[pref][2])
    return None


def load_pg_offers(only_new=False):
    try:
        import psycopg2
    except ImportError:
        return []
    try:
        con = psycopg2.connect(**CFG.DB)
        cur = con.cursor()
        cur.execute("""SELECT offer_id, product_ro, quantity_kg, price_per_unit,
                      currency, origin, supplier_email, from_email,
                               extracted_at
                       FROM trading_offers WHERE category='cereal'
                       ORDER BY offer_id DESC""")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        con.close()
        return rows
    except Exception as e:
        print("  PG error: %s" % e, file=sys.stderr)
        return []


def load_jsonl(path):
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def already_alerted():
    return {a.get("offer_id") for a in load_jsonl(PENDING)}


def build_alert(offer, bench):
    prod = canonical(offer.get("product_ro"))
    eur = to_eur_ton(offer.get("price_per_unit"), offer.get("currency"))
    qty_t = (offer.get("quantity_kg") or 0) / 1000.0
    diff = None
    if eur and bench:
        diff = round((eur - bench["eur_ton"]) / bench["eur_ton"] * 100, 1)
    level = "N1"
    if (diff is not None and diff <= N2_PCT) or qty_t >= N2_TONS:
        level = "N2"
    lines = ["ALERTA CEREALE [%s]" % level,
             "Produs: %s (%s)" % (prod, offer.get("product_ro", "")),
             "Cantitate: %s" % ("%.1f t" % qty_t if qty_t else "necunoscuta"),
             "Origine: %s" % (offer.get("origin") or "necunoscuta"),
             "Pret: %s" % ("%.0f EUR/t" % eur if eur else "fara pret")]
    if bench:
        lines.append("Benchmark: %.0f EUR/t (%s, %s)"
                     % (bench["eur_ton"], bench["market"], bench["ref_date"]))
        if diff is not None:
            lines.append("Diferenta: %+.1f%%" % diff)
    else:
        lines.append("Benchmark: indisponibil")
    lines.append("Furnizor: %s" % (offer.get("supplier_email")
                                   or offer.get("from_email") or "n/a"))
    lines.append("ID: %s" % offer.get("offer_id"))
    return level, diff, eur, "\n".join(lines)


def send_telegram(text):
    token = os.environ.get("TG_CUMPARLEGUME_TOKEN")
    chat = os.environ.get("TG_CUMPARLEGUME_CHAT")
    tg_path = TG_CFG_PATH if os.path.exists(TG_CFG_PATH) else None
    if not tg_path:
        alt = os.path.join(DATA, "telegram_cumparlegume.json")
        if os.path.exists(alt):
            tg_path = alt
    if tg_path:
        with open(tg_path, encoding="utf-8") as f:
            c = json.load(f)
        token = token or c.get("token")
        chat = chat or c.get("chat_id")
    if not token or not chat:
        return False, "no telegram config"
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/sendMessage" % token, data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()).get("ok", False), "sent"
    except Exception as e:
        return False, str(e)[:150]


def main():
    do_send = "--send" in sys.argv
    limit = 0
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    offers = load_pg_offers()
    print("=== Grain Deal Detector ===")
    print("  Oferte PG: %d" % len(offers))

    if not offers:
        return 0

    benchmarks = load_benchmarks()
    print("  Benchmark-uri: %d produse" % len(benchmarks))
    done = already_alerted()
    print("  Deja alertate: %d" % len(done))

    alerts = []
    for o in offers:
        prod = canonical(o.get("product_ro"))
        if not prod or o.get("offer_id") in done:
            continue
        bench = regional_benchmark(prod, benchmarks)
        level, diff, eur, text = build_alert(o, bench)
        rec = dict(alert_id="oc_%s" % datetime.now(timezone.utc)
                   .strftime("%Y%m%d%H%M%S%f")[:-3],
                   offer_id=o.get("offer_id"), product=prod, level=level,
                   price_eur_ton=eur, diff_pct=diff,
                   benchmark=bench, text=text, sent=False,
                   created_at=datetime.now(timezone.utc).isoformat())
        alerts.append(rec)
        print(text)
        print("-" * 40)
        if limit and len(alerts) >= limit:
            break

    with open(PENDING, "a", encoding="utf-8") as f:
        for a in alerts:
            if do_send:
                ok, info = send_telegram(a["text"])
                a["sent"], a["send_info"] = ok, info
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    print("alerts=%d N2=%d send=%s" % (len(alerts),
          sum(1 for a in alerts if a["level"] == "N2"), do_send))
    return 0


if __name__ == "__main__":
    sys.exit(main())
