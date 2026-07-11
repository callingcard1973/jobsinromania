#!/usr/bin/env python3
"""WhatsApp internal-notification bridge for TRADING ROBOT FRUIT.

POSTs a notification to the local whatsapp.js Express server (default 127.0.0.1:5523).
Dry-run default; use --send to actually send. INTERNAL + opt-in only — NEVER cold outreach.

Config: DATA/whatsapp_internal.json (gitignored) = {"tudor_number": "407xxxxxxxx", ...}.
Templates: deal_ready, publish_approval, extractor_summary, cron_failure.

Examples:
  python whatsapp_bridge.py --template deal_ready --data '{"score":85,"product":"grau","buyer_name":"X","price":1.2,"currency":"RON","qty":20000,"supplier":"s@x.com"}'
  python whatsapp_bridge.py --text "test from robot" --send
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "DATA")
CONFIG = os.path.join(DATA, "whatsapp_internal.json")
DEFAULT_PORT = 5523


def load_config():
    if not os.path.exists(CONFIG):
        return {}
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


TEMPLATES = {
    "deal_ready": lambda d: (
        f"Deal ready [{d.get('score','?')}] - {d.get('product','?')}\n"
        f"Buyer: {d.get('buyer_name','?')}\n"
        f"Price: {d.get('price','?')} {d.get('currency','')}/kg | Qty: {d.get('qty','?')} kg\n"
        f"Supplier: {d.get('supplier','?')}\n"
        f"Review & approve in Telegram bot."
    ),
    "publish_approval": lambda d: (
        f"Publish approval needed [{d.get('business','cumparlegume')}]\n"
        f"Channels: {d.get('channels','FB+TG+WP')}\n"
        f"Offer: {d.get('summary','?')}\n"
        f"Approve/Reject/Edit in Telegram bot."
    ),
    "extractor_summary": lambda d: (
        f"Extractor run: +{d.get('new_offers','?')} offers ({d.get('new_cereal',0)} cereal)\n"
        f"Ledger now: {d.get('total_offers','?')} | priced: {d.get('priced','?')}\n"
        f"Top product: {d.get('top_product','?')}"
    ),
    "cron_failure": lambda d: (
        f"Cron failure: {d.get('job','?')}\n"
        f"Exit: {d.get('exit','?')} | last: {str(d.get('last_error','?'))[:120]}\n"
        f"Check raspibig logs."
    ),
}


def main():
    ap = argparse.ArgumentParser(description="WhatsApp internal notification bridge")
    ap.add_argument("--to", help="recipient (number or chat id); default = tudor_number from config")
    ap.add_argument("--text", help="raw text to send")
    ap.add_argument("--template", choices=list(TEMPLATES), help="use a named template")
    ap.add_argument("--data", help="JSON dict of fields for the template")
    ap.add_argument("--business", default="cumparlegume")
    ap.add_argument("--port", type=int, default=int(os.environ.get("WA_PORT", DEFAULT_PORT)))
    ap.add_argument("--token", default=os.environ.get("WA_AUTH_TOKEN", ""))
    ap.add_argument("--send", action="store_true", help="actually POST (default: dry-run)")
    args = ap.parse_args()

    cfg = load_config()
    to = args.to or cfg.get("tudor_number")
    if not to:
        print("error: no --to and no tudor_number in DATA/whatsapp_internal.json", file=sys.stderr)
        sys.exit(2)

    if args.template:
        fields = json.loads(args.data) if args.data else {}
        text = TEMPLATES[args.template](fields)
    elif args.text:
        text = args.text
    else:
        print("error: provide --text or --template", file=sys.stderr)
        sys.exit(2)

    payload = {"to": to, "text": text, "business": args.business}
    url = f"http://127.0.0.1:{args.port}/send"

    if not args.send:
        print(json.dumps({"dry_run": True, "url": url, "payload": payload}, indent=2, ensure_ascii=False))
        print("--- message ---\n" + text)
        return

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    if args.token:
        req.add_header("x-wa-token", args.token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"connection error: {e} (is whatsapp.js running on port {args.port}?)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
