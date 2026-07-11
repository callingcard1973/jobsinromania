#!/usr/bin/env python3
"""OPENCODE TRADING ROBOT — unified runner for TWO SEPARATE desks.

  fv    : fruit/vegetables desk  (JSONL ledger + price_book.json)
  grain : cultura mare desk      (PostgreSQL trading_offers + cereale_price_benchmark)
  all   : runs both, distinctly (never merged)

Each desk keeps its own data model, benchmarks, buyers and publishing.
Gated: publishing is dry-run by default; --post needed (per HARD rules).
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
for p in (ROOT, os.path.join(ROOT, "CODE"), os.path.join(ROOT, "GRAIN")):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG  # noqa: E402


# ---------------------------------------------------------------------------
# FRUIT / VEG DESK
# ---------------------------------------------------------------------------
def run_fv(args):
    import fv_email_poller
    import fv_offer_extractor as fv
    import fv_price_book
    import fv_deal_flow

    print("== FV DESK: poll email ==")
    pw = os.environ.get("YAHOO_APAMINERALA_APP_PASSWORD") or args.password
    if pw:
        res = fv_email_poller.fetch_fv_emails(
            CFG.YAHOO_INBOX, pw, days=args.days, save_raw=True, provider="yahoo")
        print("FV fetched:", res.get("total_fetched"))
        for o in res.get("offers", []):
            offers = fv.parse_email_to_offers(
                open(o["body_path"], encoding="utf-8").read() if o.get("body_path")
                else "", email_id=o["email_id"], subject=o["subject"],
                supplier_email=o.get("supplier_email"))
            fv.append_to_ledger(offers)
    else:
        print("no Yahoo password -> skip poll (set YAHOO_APAMINERALA_APP_PASSWORD)")

    print("== FV DESK: rebuild price book ==")
    os.system('python CODE/fv_price_book.py --rebuild')

    print("== FV DESK: match buyers ==")
    os.system('python CODE/fv_deal_flow.py')

    if args.publish:
        print("== FV DESK: publish (POST) ==")
        os.system('python CODE/fv_publish_all.py --post')
    else:
        print("== FV DESK: publish DRY (add --publish to post) ==")
        os.system('python CODE/fv_publish_all.py')
    return 0


# ---------------------------------------------------------------------------
# GRAIN / CULTURA MARE DESK
# ---------------------------------------------------------------------------
def run_grain(args):
    import cereale_benchmark as bench
    import cereale_spread_alert as spread
    import publish_cereale_tg as tg

    print("== GRAIN DESK: benchmark fetch ==")
    report, rows, fx = bench.fetch_all(store=True)
    print("FX EUR->RON:", fx, "| sources:",
          {k: v.get("status") for k, v in report.items()})

    print("== GRAIN DESK: spread alerts ==")
    alerts = spread.scan(send=not args.dry)
    print("grain spread alerts:", len(alerts))

    print("== GRAIN DESK: publish to Telegram ==")
    if args.publish:
        os.system('python GRAIN/publish_cereale_tg.py --post')
    else:
        os.system('python GRAIN/publish_cereale_tg.py')
    return 0


def run_status():
    import json
    print("== STATUS ==")
    if os.path.exists(CFG.FV_LEDGER):
        n = sum(1 for _ in open(CFG.FV_LEDGER, encoding="utf-8") if _.strip())
        print("FV ledger offers:", n)
    else:
        print("FV ledger: none")
    try:
        import psycopg2
        con = psycopg2.connect(**CFG.DB)
        cur = con.cursor()
        for q, label in (("SELECT count(*) FROM trading_offers WHERE category='cereal'",
                         "GRAIN offers (PG)"),
                        ("SELECT count(*) FROM cereale_price_benchmark",
                         "GRAIN benchmark rows (PG)")):
            try:
                cur.execute(q)
                print(label + ":", cur.fetchone()[0])
            except Exception as e:
                print(label + ": n/a (" + str(e)[:60] + ")")
        cur.close(); con.close()
    except Exception as e:
        print("GRAIN PG status unavailable:", str(e)[:80])
    return 0


def main():
    ap = argparse.ArgumentParser(description="OPENCODE TRADING ROBOT (FV + GRAIN, separate desks)")
    ap.add_argument("desk", choices=["fv", "grain", "all", "status"], default="status", nargs="?")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--password", default="")
    ap.add_argument("--publish", action="store_true", help="actually post (default dry-run)")
    ap.add_argument("--dry", action="store_true", help="grain: do not send alerts")
    args = ap.parse_args()

    if args.desk == "fv":
        return run_fv(args)
    if args.desk == "grain":
        return run_grain(args)
    if args.desk == "status":
        return run_status()
    # all
    run_fv(args)
    run_grain(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
