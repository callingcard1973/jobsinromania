#!/usr/bin/env python3
"""Polls IMAP (Yahoo/Gmail) for F&V offer emails."""

import imaplib
import email
import json
import argparse
import os
import re
from datetime import datetime, timedelta
from email.utils import parseaddr

PROVIDERS = {
    "yahoo": {"host": "imap.mail.yahoo.com", "port": 993},
    "gmail": {"host": "imap.gmail.com", "port": 993},
}

FV_KEYWORDS = [
    "oferta", "ofert", "pret", "pre", "disponibil", "stoc", "livrare",
    "rosii", "tomate", "castraveti", "ardei", "ceapa", "usturoi", "cartofi",
    "morcovi", "varza", "conopida", "brocoli", "salata", "spanac", "vinete",
    "dovlecei", "fasole", "mazare", "porumb", "ciuperci", "pepene",
    "struguri", "mere", "pere", "prune", "capsuni", "zmeura", "afine",
    "cirese", "visine", "caise", "piersici", "nectarine", "gutui", "nuci",
    "kg", "tone", "paleti", "cutii", "ladite", "bigbag", "europalet",
    "container", "camion", "extra", "clasa", "calitate", "globalgap",
    "banane", "portocale", "lamai", "kiwi", "avocado", "mango", "ananas",
    "conserve", "bulion", "pasta", "muraturi", "zacusca", "gem", "dulceata",
    "compot", "sirop", "suc", "industrial",
]
LEDGER_PATH = os.path.join(os.path.dirname(__file__), "..", "DATA", "offers_ledger.jsonl")
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "DATA", "raw_emails")

def _bare_email(s):
    addr = parseaddr(s or "")[1].strip().lower()
    return addr if "@" in addr else ""

def _decode_part(part):
    raw = part.get_payload(decode=True)
    return raw.decode("utf-8", errors="ignore") if raw else ""

def load_processed_ids(ledger_path):
    ids = set()
    if not os.path.exists(ledger_path):
        return ids
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                sid = json.loads(line).get("source_email_id")
            except json.JSONDecodeError:
                continue
            if sid:
                ids.add(sid)
    return ids

def fetch_fv_emails(email_addr, app_password, days=7, save_raw=False, limit=50, provider="yahoo"):
    results = {"batch_id": datetime.now().strftime("%Y-%m-%d-%H%M"), "provider": provider, "new_offers": 0, "offers": []}
    os.makedirs(RAW_DIR, exist_ok=True)

    cfg = PROVIDERS.get(provider, PROVIDERS["yahoo"])
    imap = imaplib.IMAP4_SSL(cfg["host"], cfg["port"])
    imap.login(email_addr, app_password)
    imap.select("INBOX")

    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    status, messages = imap.search(None, "SINCE", since_date)

    processed_ids = load_processed_ids(LEDGER_PATH)
    msg_ids = messages[0].split()[-limit:] if messages[0] else []
    for msg_id in msg_ids:
        status, msg_data = imap.fetch(msg_id, "(RFC822)")
        if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        email_id = msg.get("Message-ID", str(msg_id))
        subject = msg.get("Subject", "?")
        sender = msg.get("From", "?")
        date = msg.get("Date", "?")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = _decode_part(part)
                    break
        else:
            body = _decode_part(msg)

        body_lower = body.lower()
        matched_keywords = [kw for kw in FV_KEYWORDS if kw in body_lower or kw in subject.lower()]
        if not matched_keywords:
            continue

        has_pricing = any(w in body for w in ["EUR", "RON", "/kg", "/ton", "\u20ac", "euro", "lei"])

        if email_id in processed_ids:
            continue

        results["new_offers"] += 1
        body_path = ""
        if save_raw:
            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", email_id[:30])
            body_path = os.path.join(RAW_DIR, f'{results["batch_id"]}_{safe_name}.txt')
            with open(body_path, "w", encoding="utf-8") as f:
                f.write(body)

        results["offers"].append({
            "email_id": email_id,
            "from": sender,
            "supplier_email": _bare_email(sender),
            "date": date,
            "subject": subject,
            "fv_keywords_found": matched_keywords[:10],
            "has_pricing": has_pricing,
            "body_length": len(body),
            "body_path": body_path
        })

    imap.close()
    imap.logout()
    results["total_fetched"] = len(results["offers"])
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FV Email Poller")
    parser.add_argument("--email", default="apaminerala@yahoo.com")
    parser.add_argument("--password", required=True, help="IMAP app password")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--save-raw", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--provider", choices=["yahoo", "gmail"], default="yahoo")
    args = parser.parse_args()

    result = fetch_fv_emails(args.email, args.password, args.days, args.save_raw, args.limit, args.provider)
    print(json.dumps(result, indent=2, ensure_ascii=False))
