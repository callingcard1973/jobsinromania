#!/usr/bin/env python3
"""
Email Reply Classifier with Archive Action.
Scans replies, classifies, adds to DNC, and ARCHIVES non-interested emails.
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

GMAIL_ACCOUNTS = {
    "manpower.dristor@gmail.com": "tbdh pycf vbxo eung",
    "manpowerdristor@gmail.com": "dmrsuqiudvqtrpzu",
}

BOUNCE_KW = ["mailer-daemon", "delivery failed", "undeliverable", "address rejected", "mailbox full", "returned mail"]
UNSUBSCRIBE_KW = ["unsubscribe", "stop", "remove", "opt out", "gdpr", "delete my", "no more"]
AUTO_REPLY_KW = ["out of office", "vacation", "automatic reply", "auto-reply", "away from", "returning"]
WRONG_PERSON_KW = ["wrong person", "no longer", "left company", "retired", "forward to"]
NEGATIVE_KW = ["no thanks", "not interested", "not now", "decline", "not suitable"]
POSITIVE_KW = ["interested", "yes", "want", "details", "price", "when", "how many", "available", "cv", "workers", "send cv"]

DNC_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")


def classify_keywords(subject: str, body: str) -> dict:
    """Classify using keyword matching."""
    text = f"{subject} {body}".lower()

    if any(kw in text for kw in BOUNCE_KW):
        return {"category": "bounce", "confidence": 0.8, "archive": True, "reason": "bounce"}
    if any(kw in text for kw in UNSUBSCRIBE_KW):
        return {"category": "unsubscribe", "confidence": 0.9, "archive": True, "add_dnc": True, "reason": "unsubscribe"}
    if any(kw in text for kw in AUTO_REPLY_KW):
        return {"category": "auto_reply", "confidence": 0.85, "archive": True, "reason": "auto-reply"}
    if any(kw in text for kw in WRONG_PERSON_KW):
        return {"category": "wrong_person", "confidence": 0.7, "archive": True, "reason": "wrong person"}
    if any(kw in text for kw in NEGATIVE_KW):
        return {"category": "not_interested", "confidence": 0.7, "archive": True, "reason": "negative"}
    if any(kw in text for kw in POSITIVE_KW):
        return {"category": "interested", "confidence": 0.6, "archive": False, "reason": "positive", "keep": True}

    return {"category": "other", "confidence": 0.3, "archive": True, "reason": "unknown"}


def decode_mime(header):
    if not header: return ""
    decoded = decode_header(header)
    parts = []
    for data, charset in decoded:
        try:
            if isinstance(data, bytes):
                parts.append(data.decode(charset or 'utf-8', errors='ignore'))
            else:
                parts.append(str(data))
        except: pass
    return ''.join(parts)


def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except: pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = str(msg.get_payload())
    return body[:2000]


def move_to_archive(mail, msg_id):
    """Move email to All Mail or Archive label (it stays in Gmail but hidden from inbox)."""
    try:
        # In Gmail IMAP, we can remove INBOX label to archive
        mail.store(msg_id, '-FLAGS', '\\Inbox')
        return True
    except:
        return False


def process_inbox(email_addr: str, password: str, limit: int = 20, archive_mode: bool = True) -> dict:
    """Scan Gmail and classify/archive replies."""
    stats = {"total": 0, "interested": 0, "archived": 0, "dnc_added": 0, "errors": 0}

    print(f"\n[{email_addr}] Processing...")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
        mail.login(email_addr, password)
        mail.select("INBOX", readonly=False)

        status, messages = mail.search(None, "ALL")
        if status != "OK":
            print(f"  No messages")
            return stats

        msg_ids = messages[0].split()[-limit:]
        print(f"  Found {len(msg_ids)} total messages")

        for msg_id in msg_ids:
            try:
                status, data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(data[0][1])

                from_addr = decode_mime(msg.get("From", ""))
                subject = decode_mime(msg.get("Subject", ""))
                body = get_body(msg)

                from_email = from_addr
                if "<" in from_addr and ">" in from_addr:
                    from_email = from_addr.split("<")[1].split(">")[0]

                # Classify
                result = classify_keywords(subject, body)
                stats["total"] += 1

                # Archive if not interested
                if archive_mode and result.get("archive", True):
                    if move_to_archive(mail, msg_id):
                        stats["archived"] += 1
                        status_str = f"[{result['category'].upper():12}] {from_email[:35]:35} [ARCHIVED]"
                        print(f"  {status_str}")
                    else:
                        status_str = f"[{result['category'].upper():12}] {from_email[:35]:35} [ARCHIVE_FAILED]"
                        print(f"  {status_str}")
                else:
                    stats["interested"] += 1
                    status_str = f"[{result['category'].upper():12}] {from_email[:35]:35} [KEEP]"
                    print(f"  {status_str}")

                # Add to DNC if needed
                if result.get("add_dnc"):
                    try:
                        DNC_FILE.parent.mkdir(parents=True, exist_ok=True)
                        with open(DNC_FILE, "a") as f:
                            f.write(f"{from_email.lower()}\n")
                        stats["dnc_added"] += 1
                    except:
                        pass

            except Exception as e:
                print(f"  Error processing message: {e}")
                stats["errors"] += 1

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"  Connection error: {e}")
        stats["errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Email Classifier with Archive")
    parser.add_argument("--scan", help="Scan specific Gmail account")
    parser.add_argument("--scan-all", action="store_true", help="Scan all accounts")
    parser.add_argument("--limit", type=int, default=30, help="Max emails to process per account")
    parser.add_argument("--no-archive", action="store_true", help="Don't archive, just classify")

    args = parser.parse_args()

    if args.scan_all:
        all_stats = {}
        for email_addr, password in GMAIL_ACCOUNTS.items():
            all_stats[email_addr] = process_inbox(email_addr, password, args.limit, not args.no_archive)

        print(f"\n=== SUMMARY ===")
        for email_addr, stats in all_stats.items():
            print(f"{email_addr}: {stats['archived']} archived, {stats['interested']} kept")
        return

    if args.scan:
        if args.scan in GMAIL_ACCOUNTS:
            stats = process_inbox(args.scan, GMAIL_ACCOUNTS[args.scan], args.limit, not args.no_archive)
            print(f"\nStats: {stats}")
        else:
            print(f"Unknown account: {args.scan}")
        return

    print("Usage: --scan EMAIL | --scan-all [--no-archive] [--limit N]")


if __name__ == "__main__":
    main()
