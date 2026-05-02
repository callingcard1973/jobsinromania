#!/usr/bin/env python3
"""
LLM-Enhanced Reply Classifier
Uses local LLM (laptop 32GB preferred) for accurate email reply classification.

Categories:
- interested: Want more info, ready to engage
- not_interested: Polite decline, not now
- unsubscribe: Explicit opt-out request (-> DNC)
- wrong_person: Not the right contact, forwarded
- auto_reply: Out of office, vacation, auto-responder
- bounce: Delivery failure (-> DNC)
- spam_complaint: Marked as spam (-> DNC immediately)
- question: Has questions but unclear intent
- other: Uncategorized

Usage:
    # Classify single reply
    python3 reply_classifier.py --text "Yes, I'm interested in your workers"

    # Classify from file
    python3 reply_classifier.py --file reply.txt

    # Process inbox (scan unread)
    python3 reply_classifier.py --scan --mailbox office@factoryjobs.eu

    # Process all mailboxes
    python3 reply_classifier.py --scan-all

Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Optional, Dict, Tuple

# Add paths
sys.path.insert(0, '/opt/ACTIVE/LLM')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from AI.lmstudio_client import get_laptop_client, query_fast, is_lmstudio_available, LMStudioClient
from alerting import send_telegram

# Local raspibig client (faster, always available)
_local_client = None

def get_local_client():
    """Get local raspibig LM Studio client with short timeout."""
    global _local_client
    if _local_client is None or not _local_client.is_connected:
        _local_client = LMStudioClient(host='http://127.0.0.1:1234', timeout=15, auto_connect=True)
    return _local_client if _local_client.is_connected else None

# Simplified classification prompt (shorter = faster on local LLM)
CLASSIFY_PROMPT = """Classify email reply. Answer with ONE category only.

Categories:
- interested (wants info/workers)
- not_interested (polite no)
- unsubscribe (remove from list)
- auto_reply (out of office)
- bounce (delivery failed)
- other

Email: {body}

Category:"""

# Fallback keywords when LLM unavailable
POSITIVE_KW = ["interested", "yes", "want", "details", "price", "when", "how many", "available", "cv", "workers"]
NEGATIVE_KW = ["no thanks", "not interested", "not now", "decline"]
UNSUBSCRIBE_KW = ["unsubscribe", "stop", "remove", "opt out", "gdpr", "delete my", "no more"]
AUTO_REPLY_KW = ["out of office", "vacation", "automatic reply", "auto-reply", "away from"]
BOUNCE_KW = ["mailer-daemon", "delivery failed", "undeliverable", "address rejected", "mailbox full"]
WRONG_PERSON_KW = ["wrong person", "no longer", "left company", "retired", "forward to"]


def classify_with_llm(subject: str, body: str) -> Optional[Dict]:
    """Classify reply using local LLM (raspibig). Fast, no external API."""
    # Use local raspibig only (no external tokens)
    client = get_local_client()
    if not client:
        return None

    # Truncate body to save tokens (shorter = faster)
    body_truncated = body[:500] if len(body) > 500 else body

    prompt = CLASSIFY_PROMPT.format(body=body_truncated)

    try:
        # Use local model with short response
        result = client.query(
            prompt,
            model="llama-3.2-3b-instruct",
            temperature=0.1,
            max_tokens=20  # Just need one word
        )

        if result:
            # Parse simple word response
            result = result.strip().lower()
            # Extract category from response
            valid_categories = ["interested", "not_interested", "unsubscribe", "auto_reply", "bounce", "other"]
            category = "other"
            for cat in valid_categories:
                if cat in result:
                    category = cat
                    break

            # Map category to action
            action_map = {
                "interested": "notify_sales",
                "not_interested": "ignore",
                "unsubscribe": "add_dnc",
                "auto_reply": "ignore",
                "bounce": "add_dnc",
                "other": "manual_review",
            }

            return {
                "category": category,
                "confidence": 0.8,
                "reason": f"LLM: {result[:30]}",
                "action": action_map.get(category, "manual_review")
            }
    except Exception as e:
        print(f"  [WARN] LLM classification error: {e}")

    return None


def classify_with_keywords(subject: str, body: str) -> Dict:
    """Fallback classification using keywords."""
    text = f"{subject} {body}".lower()

    # Check in order of priority
    if any(kw in text for kw in BOUNCE_KW):
        return {"category": "bounce", "confidence": 0.7, "reason": "keyword match", "action": "add_dnc"}

    if any(kw in text for kw in UNSUBSCRIBE_KW):
        return {"category": "unsubscribe", "confidence": 0.8, "reason": "keyword match", "action": "add_dnc"}

    if any(kw in text for kw in AUTO_REPLY_KW):
        return {"category": "auto_reply", "confidence": 0.8, "reason": "keyword match", "action": "ignore"}

    if any(kw in text for kw in WRONG_PERSON_KW):
        return {"category": "wrong_person", "confidence": 0.6, "reason": "keyword match", "action": "manual_review"}

    if any(kw in text for kw in NEGATIVE_KW):
        return {"category": "not_interested", "confidence": 0.6, "reason": "keyword match", "action": "ignore"}

    if any(kw in text for kw in POSITIVE_KW):
        return {"category": "interested", "confidence": 0.6, "reason": "keyword match", "action": "notify_sales"}

    return {"category": "other", "confidence": 0.3, "reason": "no keywords matched", "action": "manual_review"}


def classify_reply(subject: str, body: str, use_llm: bool = True) -> Dict:
    """
    Classify an email reply.

    Returns dict with: category, confidence, reason, action
    """
    result = None

    if use_llm:
        result = classify_with_llm(subject, body)
        if result:
            result["method"] = "llm"

    if not result:
        result = classify_with_keywords(subject, body)
        result["method"] = "keywords"

    return result


def process_classification(email_addr: str, result: Dict, subject: str) -> str:
    """Process classification result and take action."""
    category = result.get("category", "other")
    action = result.get("action", "manual_review")
    confidence = result.get("confidence", 0)

    log_msg = f"[{category.upper()}] {email_addr} - {result.get('reason', 'N/A')} (conf: {confidence:.0%})"

    if action == "notify_sales" and confidence >= 0.6:
        # Send Telegram notification for interested leads
        msg = f"🔥 INTERESTED LEAD\n\nFrom: {email_addr}\nSubject: {subject[:50]}\nConfidence: {confidence:.0%}\n\nReason: {result.get('reason', 'N/A')}"
        try:
            send_telegram(msg)
        except Exception as e:
            print(f"  [WARN] Telegram notification failed: {e}")

    elif action == "add_dnc":
        # Add to DNC list
        dnc_file = "/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt"
        try:
            with open(dnc_file, "a") as f:
                f.write(f"{email_addr.lower()}\n")
            log_msg += " -> Added to DNC"
        except Exception as e:
            log_msg += f" -> DNC failed: {e}"

    return log_msg


def classify_text(text: str, subject: str = "No subject") -> Dict:
    """Classify text input (for testing)."""
    return classify_reply(subject, text)


# IMAP inbox scanning
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv

load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

# Mailbox configurations
A2_PASSWORD = os.getenv("A2_EMAIL_PASSWORD", "")

# A2 Hosting mailboxes (may have connectivity issues)
A2_MAILBOXES = {
    "office@factoryjobs.eu": ("mail.factoryjobs.eu", A2_PASSWORD),
    "office@buildjobs.eu": ("mail.buildjobs.eu", A2_PASSWORD),
    "office@warehouseworkers.eu": ("mail.warehouseworkers.eu", A2_PASSWORD),
    "office@careworkers.eu": ("mail.careworkers.eu", A2_PASSWORD),
    "office@mivromania.info": ("mail.mivromania.info", A2_PASSWORD),
    "office@horecaworkers.eu": ("mail.horecaworkers.eu", A2_PASSWORD),
}

# Gmail accounts (more reliable)
GMAIL_MAILBOXES = {
    "manpower.dristor@gmail.com": ("imap.gmail.com", "tbdh pycf vbxo eung"),
    "manpowerdristor@gmail.com": ("imap.gmail.com", "dmrsuqiudvqtrpzu"),
}

# Combined
MAILBOXES = {**GMAIL_MAILBOXES, **A2_MAILBOXES}


def decode_mime_header(header):
    """Decode MIME header to string."""
    if not header:
        return ""
    decoded = decode_header(header)
    parts = []
    for data, charset in decoded:
        if isinstance(data, bytes):
            parts.append(data.decode(charset or 'utf-8', errors='ignore'))
        else:
            parts.append(data)
    return ' '.join(parts)


def get_email_body(msg):
    """Extract plain text body from email."""
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
    return body[:3000]  # Limit body size


def scan_mailbox(email_addr: str, limit: int = 10, mark_read: bool = False, recent: bool = False) -> list:
    """Scan mailbox for replies and classify them."""
    if email_addr not in MAILBOXES:
        print(f"Unknown mailbox: {email_addr}")
        return []

    server, password = MAILBOXES[email_addr]
    results = []

    try:
        mail = imaplib.IMAP4_SSL(server, 993, timeout=30)
        mail.login(email_addr, password)
        mail.select("INBOX")

        # Search for messages
        if recent:
            # Get recent emails (last N regardless of read status)
            status, messages = mail.search(None, "ALL")
        else:
            # Get unread only
            status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            return results

        msg_ids = messages[0].split()[-limit:]  # Get last N unread

        for msg_id in msg_ids:
            status, data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(data[0][1])

            # Extract headers
            from_addr = decode_mime_header(msg.get("From", ""))
            subject = decode_mime_header(msg.get("Subject", ""))
            body = get_email_body(msg)

            # Extract email from From header
            from_email = from_addr
            if "<" in from_addr and ">" in from_addr:
                from_email = from_addr.split("<")[1].split(">")[0]

            # Classify
            result = classify_reply(subject, body)
            result["from"] = from_email
            result["subject"] = subject[:100]
            result["mailbox"] = email_addr

            # Process action
            log_msg = process_classification(from_email, result, subject)
            print(f"  {log_msg}")

            results.append(result)

            # Mark as read if requested
            if mark_read:
                mail.store(msg_id, '+FLAGS', '\\Seen')

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"Error scanning {email_addr}: {e}")

    return results


def scan_all_mailboxes(limit_per_box: int = 5, recent: bool = False) -> dict:
    """Scan all configured mailboxes."""
    all_results = {}

    print(f"\n=== Scanning {len(MAILBOXES)} mailboxes ===\n")

    for email_addr in MAILBOXES:
        print(f"\n[{email_addr}]")
        results = scan_mailbox(email_addr, limit=limit_per_box, recent=recent)
        all_results[email_addr] = results

        # Summary
        if results:
            categories = {}
            for r in results:
                cat = r.get("category", "other")
                categories[cat] = categories.get(cat, 0) + 1
            print(f"  Summary: {categories}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="LLM-Enhanced Reply Classifier")
    parser.add_argument("--text", help="Classify text directly")
    parser.add_argument("--subject", default="No subject", help="Email subject")
    parser.add_argument("--file", help="Read reply from file")
    parser.add_argument("--no-llm", action="store_true", help="Use keyword matching only")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--scan", help="Scan specific mailbox for unread replies")
    parser.add_argument("--scan-all", action="store_true", help="Scan all mailboxes")
    parser.add_argument("--limit", type=int, default=10, help="Max emails to process per mailbox")
    parser.add_argument("--mark-read", action="store_true", help="Mark processed emails as read")
    parser.add_argument("--recent", action="store_true", help="Process recent emails (not just unread)")
    parser.add_argument("--list-mailboxes", action="store_true", help="List available mailboxes")

    args = parser.parse_args()

    # List mailboxes
    if args.list_mailboxes:
        print("Available mailboxes:")
        for mb in MAILBOXES:
            print(f"  - {mb}")
        return

    # Scan modes
    if args.scan_all:
        results = scan_all_mailboxes(limit_per_box=args.limit, recent=args.recent)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        return

    if args.scan:
        results = scan_mailbox(args.scan, limit=args.limit, mark_read=args.mark_read, recent=args.recent)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        return

    # Single text classification
    if args.text:
        body = args.text
    elif args.file:
        with open(args.file, "r") as f:
            body = f.read()
    else:
        # Read from stdin
        print("Enter email body (Ctrl+D to finish):")
        body = sys.stdin.read()

    # Classify
    result = classify_reply(args.subject, body, use_llm=not args.no_llm)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n=== Classification Result ===")
        print(f"Category: {result.get('category', 'unknown').upper()}")
        print(f"Confidence: {result.get('confidence', 0):.0%}")
        print(f"Reason: {result.get('reason', 'N/A')}")
        print(f"Action: {result.get('action', 'manual_review')}")
        print(f"Method: {result.get('method', 'unknown')}")


if __name__ == "__main__":
    main()
