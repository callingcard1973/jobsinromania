#!/usr/bin/env python3
"""
Gmail Draft Creator for InterJob Email Response System.

Reads pending drafts from PostgreSQL, creates Gmail drafts via IMAP APPEND.
You review in Gmail and hit Send (or delete to reject).

Usage:
    python3 gmail_drafter.py                 # Create drafts for pending responses
    python3 gmail_drafter.py --stats         # Show draft statistics
    python3 gmail_drafter.py --daemon        # Run every 15 min
"""

import json
import os
import imaplib
import argparse
import logging
import time
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

# --
CONFIG = json.loads((Path(__file__).parent / "config.json").read_text())
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "gmail_drafter.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("gmail_drafter")

# Gmail account for drafts review
GMAIL_ACCOUNT = "fruitnature4@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
IMAP_SERVER = "imap.gmail.com"

# Reply-from mapping: which account to reply from based on original recipient
REPLY_FROM = {
    "interjob.ro": "office@interjob.ro",
    "factoryjobs.eu": "office@factoryjobs.eu",
    "buildjobs.eu": "office@buildjobs.eu",
    "careworkers.eu": "office@careworkers.eu",
    "default": "office@interjob.ro",
}


def get_db():
    """Connect to PostgreSQL."""
    c = CONFIG["db"]
    kwargs = {"dbname": c["dbname"], "user": c["user"]}
    if c.get("host"):
        kwargs["host"] = c["host"]
        kwargs["port"] = c["port"]
    if c.get("password"):
        kwargs["password"] = c["password"]
    return psycopg2.connect(**kwargs)


def get_pending_drafts(conn, limit=20):
    """Get drafts awaiting Gmail push."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, email_dedup_key, from_addr, to_account, subject,
                   original_body, intent, language, draft_text
            FROM email_drafts
            WHERE status = 'pending' AND gmail_draft_id IS NULL
            ORDER BY created_at
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def build_reply_message(draft):
    """Build MIME message for Gmail draft."""
    reply_domain = (draft["to_account"] or "").split("@")[-1]
    from_addr = REPLY_FROM.get(reply_domain, REPLY_FROM["default"])

    subject = draft["subject"] or ""
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = MIMEText(draft["draft_text"], "plain", "utf-8")
    msg["From"] = from_addr
    msg["To"] = draft["from_addr"]
    msg["Subject"] = subject
    msg["X-InterJob-Intent"] = draft["intent"] or ""
    msg["X-InterJob-Draft-ID"] = str(draft["id"])

    return msg


def append_to_gmail_drafts(msg):
    """IMAP APPEND to Gmail Drafts folder. Returns UID or None."""
    if not GMAIL_APP_PASSWORD:
        log.error("GMAIL_APP_PASSWORD not set")
        return None

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_ACCOUNT, GMAIL_APP_PASSWORD)

        # Gmail drafts folder
        result, _ = mail.append(
            "[Gmail]/Drafts",
            "\\Draft",
            None,
            msg.as_bytes(),
        )
        mail.logout()

        if result == "OK":
            log.info(f"Draft appended to Gmail: {msg['To']}")
            return f"gmail-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        else:
            log.error(f"Gmail APPEND failed: {result}")
    except Exception as e:
        log.error(f"Gmail error: {e}")

    return None


def mark_draft_pushed(conn, draft_id, gmail_id):
    """Update draft status after Gmail push."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE email_drafts
            SET status = 'in_gmail', gmail_draft_id = %s, reviewed_at = NOW()
            WHERE id = %s
        """, (gmail_id, draft_id))
    conn.commit()


def process_drafts():
    """Push pending drafts to Gmail."""
    conn = get_db()
    drafts = get_pending_drafts(conn)

    if not drafts:
        log.info("No pending drafts")
        conn.close()
        return

    log.info(f"Pushing {len(drafts)} drafts to Gmail")
    pushed = 0

    for draft in drafts:
        msg = build_reply_message(draft)
        gmail_id = append_to_gmail_drafts(msg)

        if gmail_id:
            mark_draft_pushed(conn, draft["id"], gmail_id)
            pushed += 1

    conn.close()
    log.info(f"Done: {pushed}/{len(drafts)} pushed to Gmail")


def show_stats():
    """Show draft statistics."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT status, COUNT(*), MAX(created_at)
            FROM email_drafts
            GROUP BY status
            ORDER BY COUNT(*) DESC
        """)
        rows = cur.fetchall()

    conn.close()
    print("Draft Statistics:")
    print(f"  {'Status':<15} {'Count':>6}  {'Latest'}")
    print(f"  {'-'*15} {'-'*6}  {'-'*20}")
    for status, count, latest in rows:
        print(f"  {status:<15} {count:>6}  {latest}")


def main():
    parser = argparse.ArgumentParser(description="Gmail Draft Creator")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--daemon", action="store_true", help="Run every 15 min")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.daemon:
        log.info("Daemon mode (15 min interval)")
        while True:
            try:
                process_drafts()
            except Exception as e:
                log.error(f"Error: {e}")
            time.sleep(900)
    else:
        process_drafts()


if __name__ == "__main__":
    main()
