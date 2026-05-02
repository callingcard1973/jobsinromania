#!/usr/bin/env python3
"""
Email Reply Classifier — FIXED for keyword matching without LLM dependency.
Categories: interested, not_interested, unsubscribe, auto_reply, bounce, question, other
"""

import os
import sys
import json
import argparse
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from pathlib import Path

# Gmail credentials (hardcoded for this script)
GMAIL_ACCOUNTS = {
    "manpower.dristor@gmail.com": "tbdh pycf vbxo eung",
    "manpowerdristor@gmail.com": "dmrsuqiudvqtrpzu",
}

# Keyword categories (priority order)
BOUNCE_KW = ["mailer-daemon", "delivery failed", "undeliverable", "address rejected", "mailbox full", "returned mail"]
UNSUBSCRIBE_KW = ["unsubscribe", "stop", "remove", "opt out", "gdpr", "delete my", "no more"]
AUTO_REPLY_KW = ["out of office", "vacation", "automatic reply", "auto-reply", "away from", "returning"]
WRONG_PERSON_KW = ["wrong person", "no longer", "left company", "retired", "forward to"]
NEGATIVE_KW = ["no thanks", "not interested", "not now", "decline", "not suitable"]
POSITIVE_KW = ["interested", "yes", "want", "details", "price", "when", "how many", "available", "cv", "workers", "send cv"]

DNC_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")


def classify_keywords(subject: str, body: str) -> dict:
    """Classify using keyword matching only."""
    text = f"{subject} {body}".lower()

    if any(kw in text for kw in BOUNCE_KW):
        return {"category": "bounce", "confidence": 0.8, "action": "add_dnc", "reason": "bounce keyword"}
    if any(kw in text for kw in UNSUBSCRIBE_KW):
        return {"category": "unsubscribe", "confidence": 0.9, "action": "add_dnc", "reason": "unsubscribe keyword"}
    if any(kw in text for kw in AUTO_REPLY_KW):
        return {"category": "auto_reply", "confidence": 0.85, "action": "skip", "reason": "auto-reply keyword"}
    if any(kw in text for kw in WRONG_PERSON_KW):
        return {"category": "wrong_person", "confidence": 0.7, "action": "skip", "reason": "wrong person keyword"}
    if any(kw in text for kw in NEGATIVE_KW):
        return {"category": "not_interested", "confidence": 0.7, "action": "skip", "reason": "negative keyword"}
    if any(kw in text for kw in POSITIVE_KW):
        return {"category": "interested", "confidence": 0.6, "action": "notify", "reason": "positive keyword"}

    return {"category": "other", "confidence": 0.3, "action": "manual_review", "reason": "no keywords matched"}


def decode_mime(header):
    """Decode MIME header."""
    if not header:
        return ""
    decoded = decode_header(header)
    parts = []
    for data, charset in decoded:
        try:
            if isinstance(data, bytes):
                parts.append(data.decode(charset or 'utf-8', errors='ignore'))
            else:
                parts.append(str(data))
        except:
            pass
    return ''.join(parts)


def get_body(msg):
    """Extract email body."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = str(msg.get_payload())
    return body[:2000]


def process_inbox(email_addr: str, password: str, limit: int = 20) -> list:
    """Scan Gmail inbox and classify replies."""
    results = []

    print(f"\n[{email_addr}] Scanning...")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
        mail.login(email_addr, password)
        mail.select("INBOX")

        # Get unread messages
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            print(f"  No unread messages")
            return results

        msg_ids = messages[0].split()[-limit:]
        print(f"  Found {len(msg_ids)} unread messages")

        for msg_id in msg_ids:
            status, data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(data[0][1])

            from_addr = decode_mime(msg.get("From", ""))
            subject = decode_mime(msg.get("Subject", ""))
            body = get_body(msg)

            # Extract email from From header
            from_email = from_addr
            if "<" in from_addr and ">" in from_addr:
                from_email = from_addr.split("<")[1].split(">")[0]

            # Classify
            result = classify_keywords(subject, body)
            result["from"] = from_email
            result["subject"] = subject[:60]
            result["method"] = "keyword"

            # Log result
            print(f"  [{result['category'].upper()}] {from_email} — {result['reason']}")

            # Add to DNC if needed
            if result["action"] == "add_dnc":
                try:
                    DNC_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(DNC_FILE, "a") as f:
                        f.write(f"{from_email.lower()}\n")
                    print(f"    → Added to DNC")
                except Exception as e:
                    print(f"    → DNC error: {e}")

            results.append(result)

            # Mark as read
            mail.store(msg_id, '+FLAGS', '\\Seen')

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"  Error: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Email Reply Classifier (Fixed)")
    parser.add_argument("--text", help="Classify text directly")
    parser.add_argument("--subject", default="No subject", help="Email subject")
    parser.add_argument("--scan", help="Scan Gmail mailbox")
    parser.add_argument("--scan-all", action="store_true", help="Scan all accounts")
    parser.add_argument("--limit", type=int, default=20, help="Max emails to process")

    args = parser.parse_args()

    # Direct text classification
    if args.text:
        result = classify_keywords(args.subject, args.text)
        print(f"\nCategory: {result['category'].upper()}")
        print(f"Confidence: {result['confidence']:.0%}")
        print(f"Action: {result['action']}")
        return

    # Scan Gmail
    if args.scan_all:
        for email_addr, password in GMAIL_ACCOUNTS.items():
            process_inbox(email_addr, password, args.limit)
        return

    if args.scan:
        if args.scan in GMAIL_ACCOUNTS:
            process_inbox(args.scan, GMAIL_ACCOUNTS[args.scan], args.limit)
        else:
            print(f"Unknown account: {args.scan}")
        return

    print("Usage: --text STRING | --scan EMAIL | --scan-all")


if __name__ == "__main__":
    main()
