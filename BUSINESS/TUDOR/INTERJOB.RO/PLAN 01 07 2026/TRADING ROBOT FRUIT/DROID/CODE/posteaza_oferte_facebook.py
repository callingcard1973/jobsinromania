#!/usr/bin/env python3
"""Posteaza periodic pe pagina FB cumparlegume: ce AVEM (oferte) + ce CERem.

Dry-run by default (printeaza textul). Posteaza efectiv DOAR cu --post.
Token + page_id din DATA/fb_cumparlegume.json sau env FB_CUMPARLEGUME_TOKEN /
FB_CUMPARLEGUME_PAGE_ID. ASCII-only. Nu publica preturi (negociere privata).
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"
LEDGER = DATA / "offers_ledger.jsonl"
CONFIG = DATA / "fb_cumparlegume.json"
GRAPH = "https://graph.facebook.com/v21.0"


def load_ledger():
    items = []
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return items


def _qty(o):
    q = o.get("quantity_kg")
    return f"{int(q/1000)} to" if q else "cantitate la cerere"


def build_post(items):
    # OFERIM = oferte reale (nu internal_only, nu cereri)
    offers = [o for o in items if o.get("entry_type") != "request"
              and not o.get("internal_only")]
    requests = [o for o in items if o.get("entry_type") == "request"]

    lines = ["Gospodarii de Altadata - ce avem azi:", ""]
    if offers:
        lines.append("OFERIM (disponibil de la producatori):")
        seen = set()
        for o in offers:
            p = (o.get("product_ro") or "?").lower()
            if p in seen:
                continue
            seen.add(p)
            org = o.get("origin") or ""
            lines.append(f"- {p} ({_qty(o)})" + (f" - {org}" if org else ""))
        lines.append("")
    if requests:
        lines.append("CUMPARAM (avem cumparatori pentru):")
        seen = set()
        for o in requests:
            p = (o.get("product_ro") or "?").lower()
            if p in seen:
                continue
            seen.add(p)
            lines.append(f"- {p} ({_qty(o)})")
        lines.append("")
    lines.append("Contact: office@cumparlegume.com")
    text = "\n".join(lines)
    return text.encode("ascii", "ignore").decode("ascii")


def load_config():
    token = os.getenv("FB_CUMPARLEGUME_TOKEN")
    page = os.getenv("FB_CUMPARLEGUME_PAGE_ID")
    if CONFIG.exists():
        c = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = token or c.get("access_token")
        page = page or c.get("page_id")
    return token, page


def post_to_fb(text, token, page):
    data = urllib.parse.urlencode({"message": text, "access_token": token}).encode()
    req = urllib.request.Request(f"{GRAPH}/{page}/feed", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    do_post = "--post" in sys.argv
    text = build_post(load_ledger())
    print("=" * 50)
    print(text)
    print("=" * 50)
    if not do_post:
        print("\n[DRY-RUN] adauga --post ca sa publici pe FB cumparlegume.")
        return
    token, page = load_config()
    if not token or not page:
        print("\nLIPSA token/page_id (DATA/fb_cumparlegume.json sau env). Nu postez.")
        sys.exit(2)
    res = post_to_fb(text, token, page)
    print("\nPostat:", res)


if __name__ == "__main__":
    main()
