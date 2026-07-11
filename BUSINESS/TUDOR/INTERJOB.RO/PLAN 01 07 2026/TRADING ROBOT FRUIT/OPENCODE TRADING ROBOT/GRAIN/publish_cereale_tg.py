#!/usr/bin/env python3
"""Publish cereale offers to a dedicated Telegram channel (@cereale_romania).

Reads cereale offers from PG (trading_offers WHERE category='cereal').
Builds a cereale-only post and sends it to the Telegram channel.
Dry-run by default; use --post to actually send.

Config: DATA/telegram_cereale.json (gitignored, copy from .template).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"
CFG = DATA / "telegram_cereale.json"
TG_API = "https://api.telegram.org"


def load_cereale_offers():
    """Read cereale offers from PG."""
    try:
        import psycopg2
        conn = psycopg2.connect("dbname=interjob_master user=tudor")
        cur = conn.cursor()
        cur.execute("""SELECT product_ro, quantity_kg, origin, price_per_unit, currency
                       FROM trading_offers
                       WHERE category='cereal' AND (internal_only IS NULL OR internal_only = false)
                       ORDER BY extracted_at DESC""")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"PG error: {e}", file=sys.stderr)
        return []


def build_cereale_post(rows):
    """Build a cereale-only Telegram post from PG rows."""
    if not rows:
        return None
    lines = ["Cereale disponibile — Cumpar Legume:", ""]
    seen = set()
    for product_ro, qty, origin, price, currency in rows:
        p = (product_ro or "?").lower()
        if p in seen:
            continue
        seen.add(p)
        qty_str = f"{int(qty/1000)} to" if qty else "cantitate la cerere"
        price_str = f"{price} {currency}/kg" if price else "pret la negociere"
        origin_str = f" - {origin}" if origin else ""
        lines.append(f"- {product_ro} ({qty_str}) {price_str}{origin_str}")
    lines.append("")
    lines.append("Contact: office@cumparlegume.com")
    text = "\n".join(lines)
    return text.encode("ascii", "ignore").decode("ascii")


def post_tg(text, token, chat_id):
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
    }).encode()
    req = urllib.request.Request(f"{TG_API}/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    do_post = "--post" in sys.argv
    cfg_path = CFG
    if not cfg_path.exists():
        print(f"Config not found: {cfg_path}")
        print("Copy DATA/telegram_cereale.json.template to telegram_cereale.json and fill in token + chat_id.")
        sys.exit(2)

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    token = cfg.get("token")
    chat = cfg.get("chat_id")
    if not token or not chat or "PUT_" in str(token):
        print("Config incomplete. Fill in bot token and chat_id in telegram_cereale.json.")
        sys.exit(2)

    rows = load_cereale_offers()
    text = build_cereale_post(rows)
    if not text:
        print("No cereale offers in PG. Nothing to publish.")
        return

    print("=" * 50)
    print(text)
    print("=" * 50)

    if not do_post:
        print("\n[DRY-RUN] Add --post to publish to Telegram.")
        return

    res = post_tg(text, token, chat)
    print(f"\nPosted to {chat}: {res.get('result', {}).get('message_id')}")


if __name__ == "__main__":
    main()
