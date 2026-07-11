#!/usr/bin/env python3
"""GATED WhatsApp/SMS intake for cereale (grain) offers -> offer ledger.

Grain outreach is 97% phone (7934 traders, 153 email), so grain offers arrive as
free-text WhatsApp/SMS messages, not emails. This parses RO phrasing like
"vand grau 500t umiditate 13 pret 195 eur/to Ialomita" into structured offer
fields and ingests them into the SAME ledger F&V uses (DATA/offers_ledger.jsonl +
PG trading_offers via fv_offer_extractor.append_to_ledger), tagged
channel=whatsapp/sms, entry_type=offer, category=cereal.

Gated: parse + store only. No auto-reply, nothing sent externally.

Inbound WhatsApp: raspibig whatsapp-connector (wa_notify.py) is SEND-ONLY today,
so this ships a manual-paste CLI (--from-text / --from-file). Hooking the
connector's RECEIVE side to feed messages here is a separate go-live step (see
note in main()). The 4653-CUI phone call-list is the contact base for matching a
sender phone to a known trader.
"""
import argparse
import csv
import json
import os
import re
import sys
import uuid
from datetime import datetime

# Wrap (do not edit) the F&V extractor: reuse its ledger writer + county/product logic.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fv_offer_extractor as fv  # noqa: E402

# Canonical grain buyer/trader base lives in SILOZURI (PLAN 01 07 2026 root).
# Resolve robustly: env override, else walk up to PLAN 01 07 2026 then SILOZURI/DATA.
import config as _cfg  # noqa: E402
CALLLIST_PATH = _cfg.resolve_silozuri("cereale_trading_B_phone_calllist.csv")

# RO grain vocabulary -> canonical product tag (checked longest-first at parse).
GRAIN_TERMS = {
    "grau durum": "grau durum", "grau furajer": "grau", "grau panificatie": "grau",
    "grau": "grau", "porumb boabe": "porumb boabe", "porumb": "porumb boabe",
    "orz furajer": "orz", "orzoaica": "orz", "orz": "orz",
    "floarea soarelui": "floarea-soarelui", "floarea-soarelui": "floarea-soarelui",
    "fs": "floarea-soarelui", "srf": "floarea-soarelui",
    "rapita": "rapita", "triticale": "triticale", "ovaz": "ovaz",
    "secara": "secara", "sorg": "sorg", "soia": "soia",
    "naut furajer": "naut furajer", "naut": "naut",
    "mustar": "mustar",
}

INTENT_SELL = ("vand", "vindem", "ofer", "oferim", "disponibil", "am de vanzare", "de vanzare")
INTENT_BUY = ("cumpar", "cumparam", "caut", "cautam", "achizitionam", "solicit")


def detect_intent(text):
    """Return 'offer' (sell) or 'request' (buy) from RO verbs; default offer."""
    t = text.lower()
    if any(w in t for w in INTENT_BUY):
        return "request"
    if any(w in t for w in INTENT_SELL):
        return "offer"
    return "offer"


def detect_grain(text):
    t = text.lower()
    for term in sorted(GRAIN_TERMS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(term) + r"\b", t):
            return GRAIN_TERMS[term]
    return None


def extract_tons(text):
    """Grain is priced/traded in tons. Return float tons (also fills quantity_kg)."""
    t = text.lower()
    m = re.search(r"(\d+[.,]?\d*)\s*(?:to|tone|tona|t)\b", t)
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.search(r"(\d+[.,]?\d*)\s*(?:vagoane|vagon)\b", t)  # 1 vagon ~ 60 t
    if m:
        return float(m.group(1).replace(",", ".")) * 60.0
    return None


def extract_price_ton(text):
    """Return (currency, price_per_ton). Grain quotes are per-ton (eur/to, lei/to)."""
    t = text.lower()
    pats = [
        (r"(\d+[.,]?\d*)\s*(?:eur|euro|€)\s*/?\s*(?:to|tona|t)\b", "EUR"),
        (r"(\d+[.,]?\d*)\s*(?:ron|lei)\s*/?\s*(?:to|tona|t)\b", "RON"),
        (r"pret\s*[:=]?\s*(\d+[.,]?\d*)\s*(?:eur|euro)", "EUR"),
        (r"pret\s*[:=]?\s*(\d+[.,]?\d*)\s*(?:ron|lei)", "RON"),
        (r"(\d{3,4})\s*(?:ron|lei)\b", "RON"),
        (r"(\d{2,4})\s*(?:eur|euro)\b", "EUR"),
    ]
    for pat, cur in pats:
        m = re.search(pat, t)
        if m:
            return cur, float(m.group(1).replace(",", "."))
    return None, None


def extract_grain_quality(text):
    """Grain quality = humidity/protein/hectoliter, not F&V class. Return dict."""
    t = text.lower()
    q = {}
    m = re.search(r"umiditate\s*[:=]?\s*(\d+[.,]?\d*)|umidit\.?\s*(\d+[.,]?\d*)|(\d+[.,]?\d*)\s*%?\s*umiditate", t)
    if m:
        val = next((g for g in m.groups() if g), None)
        if val:
            q["humidity_pct"] = float(val.replace(",", "."))
    m = re.search(r"proteina\s*[:=]?\s*(\d+[.,]?\d*)|proteine\s*(\d+[.,]?\d*)", t)
    if m:
        val = next((g for g in m.groups() if g), None)
        if val:
            q["protein_pct"] = float(val.replace(",", "."))
    m = re.search(r"(?:hl|hectolitric|masa\s*hectolitrica)\s*[:=]?\s*(\d+[.,]?\d*)", t)
    if m:
        q["hectoliter"] = float(m.group(1).replace(",", "."))
    return q


def extract_phone(text):
    m = re.search(r"(\+?4?0?7\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3})", text)
    if m:
        return re.sub(r"[\s.\-]", "", m.group(1))
    return None


_CALLLIST = None


def load_calllist(path=CALLLIST_PATH):
    """Contact base: {normalized_phone: {cui,name}} from the 4653-CUI call-list."""
    global _CALLLIST
    if _CALLLIST is not None:
        return _CALLLIST
    _CALLLIST = {}
    if not os.path.exists(path):
        return _CALLLIST
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ph = re.sub(r"[\s.\-]", "", (row.get("phone") or "").strip())
            if ph:
                _CALLLIST[ph] = {"cui": row.get("cui", ""), "name": row.get("name", "")}
    return _CALLLIST


def _match_trader(phone):
    if not phone:
        return None
    cl = load_calllist()
    variants = {phone}
    if phone.startswith("+40"):
        variants.add("0" + phone[3:])
    elif phone.startswith("40"):
        variants.add("0" + phone[2:])
    elif phone.startswith("0"):
        variants.add("+4" + phone)
    for v in variants:
        if v in cl:
            return cl[v]
    return None


def parse_grain_message(text, channel="whatsapp", from_phone=None, msg_id=None):
    """Parse one free-text RO grain WA/SMS message into a ledger offer dict."""
    intent = detect_intent(text)
    product = detect_grain(text)
    tons = extract_tons(text)
    currency, price = extract_price_ton(text)
    quality = extract_grain_quality(text)
    origin = fv.extract_origin(text)  # reuse county list from F&V extractor
    phone = from_phone or extract_phone(text)
    trader = _match_trader(phone)

    filled = sum(1 for v in (product, tons, price) if v is not None)
    completeness = "complete" if filled >= 3 else "partial"

    return {
        "offer_id": f"cer_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}",
        "source_email_id": msg_id,
        "extracted_at": datetime.now().isoformat(),
        "product_ro": product or "cereale",
        "product_en": product or "grain",
        "category": "cereal",
        "quality_class": None,
        "grain_quality": quality or None,
        "quantity_kg": (tons * 1000.0) if tons is not None else None,
        "quantity_tons": tons,
        "price_per_unit": price,
        "price_basis": "per_ton",
        "currency": currency or "EUR",
        "origin": origin,
        "delivery_terms": fv.extract_delivery_terms(text),
        "completeness": completeness,
        "context": text[:800].lower(),
        "raw_snippet": text[:200],
        "supplier_email": "",
        "from_email": "",
        "channel": channel,
        "entry_type": intent,
        "internal_only": True,
        "contact_phone": phone,
        "trader_cui": (trader or {}).get("cui"),
        "trader_name": (trader or {}).get("name"),
    }


def ingest(text, channel="whatsapp", from_phone=None, msg_id=None, store=True):
    offer = parse_grain_message(text, channel=channel, from_phone=from_phone, msg_id=msg_id)
    if store:
        fv.append_to_ledger([offer])  # same path as F&V: JSONL + PG dual-write
    return offer


def main():
    ap = argparse.ArgumentParser(description="GATED cereale WA/SMS intake -> ledger.")
    ap.add_argument("--from-text", help="Free-text grain message to parse.")
    ap.add_argument("--from-file", help="File with one grain message per line.")
    ap.add_argument("--channel", default="whatsapp", choices=["whatsapp", "sms"])
    ap.add_argument("--phone", help="Sender phone (else parsed from text).")
    ap.add_argument("--store", action="store_true", help="Write to ledger (default: dry parse-only).")
    ap.add_argument("--demo", action="store_true", help="Parse 3 sample RO messages, print only.")
    args = ap.parse_args()

    if args.demo:
        samples = [
            "vand grau 500t umiditate 13 pret 195 eur/to Ialomita",
            "Ofer porumb boabe 120 tone, umiditate 14.5, 850 lei/to, jud Dolj, 0722123456",
            "cumparam floarea soarelui 300 to proteina 44 pret 380 euro Constanta",
        ]
        out = [parse_grain_message(s, channel="whatsapp") for s in samples]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        print("\nNOTE: --demo never stores. Use --store to write to ledger.", file=sys.stderr)
        return 0

    texts = []
    if args.from_text:
        texts = [args.from_text]
    elif args.from_file:
        with open(args.from_file, "r", encoding="utf-8") as f:
            texts = [ln.strip() for ln in f if ln.strip()]
    else:
        ap.error("provide --from-text, --from-file or --demo")

    results = []
    for t in texts:
        results.append(ingest(t, channel=args.channel, from_phone=args.phone, store=args.store))
    print(json.dumps({"parsed": len(results), "stored": bool(args.store),
                      "offers": results}, indent=2, ensure_ascii=False))
    if not args.store:
        print("\nNOTE: dry parse-only. Add --store to write to ledger.", file=sys.stderr)
    print("\nINBOUND WA HOOKUP (Tudor OK needed): whatsapp-connector is send-only; "
          "wiring its receive webhook to call ingest() is the go-live step.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
