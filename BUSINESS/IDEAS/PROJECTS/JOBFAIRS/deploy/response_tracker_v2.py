#!/usr/bin/env python3
"""Response Tracker v2 — matches responses to actual campaigns via send_log.
Checks IMAP every 5 min. Telegram alert on real replies. Logs to DB."""
import os
import sys
import json
import imaplib
import email
import re
import requests
import psycopg2
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

TELEGRAM_TOKEN = "8546618948:AAG0neoQA-kNq0M2GrZX7J-dGXNvEJEOK9w"
CHAT_ID = "547047851"
STATE_FILE = Path("/opt/ACTIVE/INFRA/GOVERNOR/response_tracker_state.json")
LOG = "/home/tudor/.logs/response_tracker.log"

from response_tracker_inboxes import INBOXES, OWN_EMAILS
from worker_router import is_worker_application, process_worker
from solonet_pipeline import create_draft as solonet_draft

SCAN_HOURS = int(os.environ.get("RESPONSE_SCAN_HOURS", "168"))  # 7 days default


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def alert(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"seen_ids": []}


def save_state(state):
    state["seen_ids"] = state["seen_ids"][-500:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def decode_subject(msg):
    decoded = decode_header(msg.get("Subject", ""))
    return " ".join(p.decode(e or "utf-8", errors="replace") if isinstance(p, bytes) else p for p, e in decoded)[:200]

def get_sender(msg):
    m = re.search(r'<([^>]+)>', msg.get("From", ""))
    return m.group(1).lower() if m else msg.get("From", "")[:100].lower()

def get_body(msg):
    for part in (msg.walk() if msg.is_multipart() else [msg]):
        if part.get_content_type() == "text/plain":
            try:
                return part.get_payload(decode=True).decode(errors="replace")[:1000]
            except Exception:
                pass
    return ""


def match_campaign(sender_email):
    """Check which campaign contacted this sender — checks email_sender DB first."""
    # Primary: email_sender database (unified send log)
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        cur.execute("SELECT campaign FROM send_log WHERE LOWER(email)=%s ORDER BY sent_at_utc DESC LIMIT 1",
            (sender_email.lower(),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass
    # Fallback: interjob_master send_log tables
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        for campaign, table in CAMPAIGN_LOGS.items():
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE LOWER(email)=%s",
                    (sender_email.lower(),))
                if cur.fetchone()[0] > 0:
                    cur.close()
                    conn.close()
                    return campaign
            except Exception:
                conn.rollback()
        cur.close()
        conn.close()
    except Exception:
        pass
    return "UNKNOWN"


def classify(subject, body):
    text = (subject + " " + body).lower()
    # Bounce
    if any(w in text for w in ["delivery failed", "undeliverable", "mailer-daemon", "550 ", "mailbox not found"]):
        return "BOUNCE"
    # Auto-reply
    if any(w in text for w in ["out of office", "automatic reply", "auto-reply", "vacation",
                                "away from", "autosvar", "fravær", "ikke på kontoret"]):
        return "AUTO_REPLY"
    # Not interested
    if any(w in text for w in ["not interested", "no thanks", "remove me", "unsubscribe",
                                "stop sending", "ikke interessert", "nu suntem interesati",
                                "nu ne intereseaza", "nu avem nevoie"]):
        return "NOT_INTERESTED"
    # Interested (strong signals)
    if any(w in text for w in ["interested", "tell me more", "send info", "contact me",
                                "yes please", "when is", "how many workers",
                                "suntem interesati", "ne intereseaza", "avem nevoie",
                                "da, dorim", "cand puteti"]):
        return "INTERESTED"
    # RE: to our subject = they replied = likely interested
    if subject.lower().startswith("re:") or subject.lower().startswith("sv:"):
        if any(w in text for w in ["workers", "muncitori", "recruitment", "staff",
                                    "positions", "posturi", "angajare"]):
            return "INTERESTED"
    # Any RE: response that's not auto/bounce = at minimum they engaged
    if subject.lower().startswith(("re:", "sv:", "fw:", "fwd:")):
        return "REPLY"
    return "UNKNOWN"


def _log_solonet_conversation(sender, subject, body, msg_id):
    """Log every email in adrian.craciunescu inbox to solonet_conversations."""
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        direction = "from_solonet" if "solonet" in sender or "adrian" in sender else "from_client"
        # Match to order by sender email
        order_id = None
        cur.execute("SELECT id FROM solonet_orders WHERE contact_email=%s LIMIT 1", (sender,))
        row = cur.fetchone()
        if row:
            order_id = row[0]
            if direction == "from_client":
                cur.execute("UPDATE solonet_orders SET status='responded', responded_at=NOW() WHERE id=%s AND status='sent'", (order_id,))
        cur.execute("""INSERT INTO solonet_conversations
            (order_id, direction, sender_email, recipient_email, subject, body_preview, message_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (message_id) DO NOTHING""",
            (order_id, direction, sender, "adrian.craciunescu@buildjobs.eu",
             subject[:255], body[:500], msg_id))
        conn.commit()
        cur.close()
        conn.close()
        log(f"solonet_conv: {direction} {sender} re: {subject[:40]}")
    except Exception as e:
        log(f"solonet_conv error: {e}")


def save_response_db(sender, subject, category, campaign, inbox):
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""INSERT INTO campaign_responses
            (sender_email, subject, category, campaign, inbox, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW()) ON CONFLICT DO NOTHING""",
            (sender, subject[:200], category, campaign, inbox))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"DB error: {e}")


def check_inbox(inbox_cfg, state):
    name = inbox_cfg["name"]
    password = ""
    try:
        with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
            for line in f:
                if line.startswith(inbox_cfg["password_env"] + "="):
                    password = line.strip().split("=", 1)[1]
    except Exception:
        pass
    if not password:
        log(f"{name}: no password")
        return 0

    new_count = 0
    try:
        imap = imaplib.IMAP4_SSL(inbox_cfg["host"], inbox_cfg["port"])
        imap.login(inbox_cfg["user"], password)
        imap.select("INBOX")
        since = (datetime.now() - timedelta(hours=SCAN_HOURS)).strftime("%d-%b-%Y")
        _, msg_nums = imap.search(None, f'(SINCE "{since}")')
        if not msg_nums[0]:
            imap.logout()
            return 0

        for num in msg_nums[0].split()[-50:]:
            _, data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            msg_id = msg.get("Message-ID", num.decode())
            if msg_id in state.get("seen_ids", []):
                continue
            state.setdefault("seen_ids", []).append(msg_id)

            sender = get_sender(msg)
            if sender in OWN_EMAILS:
                continue

            subject = decode_subject(msg)
            body = get_body(msg)
            category = classify(subject, body)
            campaign = match_campaign(sender)

            if category in ("AUTO_REPLY", "BOUNCE"):
                log(f"{name}: {category} from {sender}")
                continue

            # Route workers to applicant pipeline
            if is_worker_application(sender, name, category):
                process_worker(sender, name, subject, body)
                continue

            # Solonet conversation tracker — log ALL emails in/out of adrian.craciunescu inbox
            if name == "solonet_tracker":
                _log_solonet_conversation(sender, subject, body, msg_id)
                continue

            # Route Romanian employer leads to solonet pipeline
            if category in ("INTERESTED", "REPLY") and sender.endswith(".ro"):
                company = ""
                m = re.search(r"pentru (.+?)( /| $)", subject)
                if m:
                    company = m.group(1)
                solonet_draft(sender, company or sender.split("@")[0],
                    "", body[:200], "", campaign, subject, body)

            new_count += 1
            icons = {"INTERESTED": "🟢", "REPLY": "📩", "NOT_INTERESTED": "🔴", "UNKNOWN": "❓"}
            icon = icons.get(category, "❓")
            alert(f"{icon} <b>{category}</b> — {campaign}\n"
                  f"From: {sender}\nSubject: {subject[:80]}\n"
                  f"Preview: {body[:150]}")
            save_response_db(sender, subject, category, campaign, name)
            log(f"{name}: {category} [{campaign}] from {sender}")

        imap.logout()
    except Exception as e:
        log(f"{name}: IMAP error — {e}")
    return new_count


def ensure_db():
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS campaign_responses (
            id SERIAL PRIMARY KEY, sender_email VARCHAR(255),
            subject VARCHAR(255), category VARCHAR(50),
            campaign VARCHAR(100), inbox VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(sender_email, subject))""")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"DB error: {e}")


def main():
    ensure_db()
    state = load_state()
    total = 0
    for inbox in INBOXES:
        total += check_inbox(inbox, state)
    save_state(state)
    if total:
        log(f"New responses: {total}")


if __name__ == "__main__":
    main()
