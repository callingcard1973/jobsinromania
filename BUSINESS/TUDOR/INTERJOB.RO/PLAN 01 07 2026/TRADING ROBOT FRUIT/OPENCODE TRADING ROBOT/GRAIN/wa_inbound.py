#!/usr/bin/env python3
"""GRAIN desk — WhatsApp/SMS inbound receiver (auto-feed into grain ledger).

The whatsapp-connector (PUBLISHING_ROBOT/connectors/whatsapp.js) is send-only
today. This module lets it (or any source) POST inbound grain messages here:

  POST /inbound   {"text": "...", "phone": "407...", "msg_id": "wa-123"}
  -> parse -> dual-write JSONL ledger + PostgreSQL trading_offers (category=cereal)

GATED: parse + store only. No auto-reply, nothing sent externally.
Run:  python GRAIN/wa_inbound.py --port 5524
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(HERE), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG  # noqa: E402
import cereale_intake as ci  # noqa: E402

try:
    import psycopg2
except ImportError:
    psycopg2 = None


def _offer_hash(o):
    import hashlib
    raw = "|".join(str(o.get(k, "")) for k in
                   ("product_ro", "quantity_kg", "price_per_unit", "currency",
                    "origin", "contact_phone", "channel", "entry_type"))
    return "cer_" + hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def write_pg(offer):
    """Best-effort dual-write grain offer into PostgreSQL trading_offers."""
    if psycopg2 is None:
        return False
    try:
        con = psycopg2.connect(**CFG.DB)
        cur = con.cursor()
        cur.execute(
            """INSERT INTO trading_offers
                 (offer_id, source_email_id, extracted_at, product_ro, product_en,
                  category, quality_class, quantity_kg, price_per_unit, currency,
                  origin, delivery_terms, completeness, context, raw_snippet,
                  entry_type, internal_only, offer_hash)
               VALUES (%s,%s,%s,%s,%s,'cereal',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s)
               ON CONFLICT (offer_hash) DO NOTHING""",
            (offer["offer_id"], offer.get("source_email_id"),
             offer.get("extracted_at"), offer.get("product_ro"),
             offer.get("product_en"), offer.get("grain_quality") and json.dumps(offer["grain_quality"]),
             offer.get("quantity_kg"), offer.get("price_per_unit"),
             offer.get("currency"), offer.get("origin"),
             offer.get("delivery_terms"), offer.get("completeness"),
             offer.get("context"), offer.get("raw_snippet"),
             offer.get("entry_type"), _offer_hash(offer)))
        con.commit(); cur.close(); con.close()
        return True
    except Exception as e:
        sys.stderr.write("PG write failed: %s\n" % e)
        return False


def handle_inbound(payload):
    text = (payload.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "empty text"}
    offer = ci.ingest(text, channel=payload.get("channel", "whatsapp"),
                      from_phone=payload.get("phone"),
                      msg_id=payload.get("msg_id"), store=True)
    write_pg(offer)
    return {"ok": True, "offer_id": offer["offer_id"],
            "product": offer.get("product_ro"), "stored_pg": True}


class _H(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/inbound":
            return self._send({"error": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception as e:
            return self._send({"error": str(e)}, 400)
        self._send(handle_inbound(payload))

    def log_message(self, *a):
        pass


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Grain WhatsApp inbound receiver")
    ap.add_argument("--port", type=int, default=int(os.environ.get("GRAIN_WA_PORT", 5524)))
    args = ap.parse_args()
    print("GRAIN inbound listening on :%d POST /inbound  (Ctrl-C to stop)" % args.port)
    HTTPServer(("127.0.0.1", args.port), _H).serve_forever()


if __name__ == "__main__":
    main()
