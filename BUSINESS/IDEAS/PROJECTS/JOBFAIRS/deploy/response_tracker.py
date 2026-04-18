#!/usr/bin/env python3
"""Response Tracker — monitors IMAP inboxes for campaign replies.
Checks every 5 min via cron. Alerts Tudor on Telegram. Logs to DB.
Applies to: NORWAY_VIRGIL, ANOFM, any campaign with reply_to."""
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

INBOXES = [
    {
        "name": "seicarescu",
        "host": "imap.zoho.eu", "port": 993,
        "user": "tudor@seicarescu.com",
        "password_env": "ZOHO_SEICARESCU_PASSWORD",
        "campaigns": ["NORWAY_VIRGIL"],
    },
    {
        "name": "manpower_dristor",
        "host": "imap.gmail.com", "port": 993,
        "user": "manpower.dristor@gmail.com",
        "password_env": "GMAIL_MANPOWERDRISTOR_APP_PASSWORD",
        "campaigns": ["ANOFM", "HARGHITA", "DELIVERY"],
    },
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def alert(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10)
    except Exception:
        pass


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_check": {}, "seen_ids": []}


def save_state(state):
    state["seen_ids"] = state["seen_ids"][-500:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def decode_subject(msg):
    subject = msg.get("Subject", "")
    decoded = decode_header(subject)
    parts = []
    for part, enc in decoded:
        if isinstance(part, bytes):
            parts.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return " ".join(parts)[:200]


def get_sender(msg):
    frm = msg.get("From", "")
    match = re.search(r'<([^>]+)>', frm)
    return match.group(1) if match else frm[:100]


def classify_response(subject, body_text):
    text = (subject + " " + body_text).lower()
    if any(w in text for w in ["interested", "tell me more", "send info",
                                "yes", "when", "how many", "contact me"]):
        return "INTERESTED"
    if any(w in text for w in ["not interested", "no thanks", "remove",
                                "unsubscribe", "stop"]):
        return "NOT_INTERESTED"
    if any(w in text for w in ["out of office", "automatic reply", "auto-reply",
                                "vacation", "away from"]):
        return "AUTO_REPLY"
    if any(w in text for w in ["delivery failed", "undeliverable", "mailer-daemon"]):
        return "BOUNCE"
    return "UNKNOWN"


def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors="replace")
                except Exception:
                    pass
                break
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="replace")
        except Exception:
            pass
    return body[:1000]


def save_response_db(sender, subject, category, campaign, inbox_name):
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO campaign_responses (sender_email, subject, category, campaign, inbox, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (sender, subject[:200], category, campaign, inbox_name))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"DB error: {e}")


def check_inbox(inbox_cfg, state):
    name = inbox_cfg["name"]
    password = os.environ.get(inbox_cfg["password_env"], "")
    if not password:
        env_file = "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env"
        try:
            with open(env_file) as f:
                for line in f:
                    if line.startswith(inbox_cfg["password_env"] + "="):
                        password = line.strip().split("=", 1)[1]
        except Exception:
            pass
    if not password:
        log(f"{name}: no password for {inbox_cfg['password_env']}")
        return 0

    new_count = 0
    try:
        imap = imaplib.IMAP4_SSL(inbox_cfg["host"], inbox_cfg["port"])
        imap.login(inbox_cfg["user"], password)
        imap.select("INBOX")
        since = (datetime.now() - timedelta(hours=6)).strftime("%d-%b-%Y")
        _, msg_nums = imap.search(None, f'(SINCE "{since}")')
        if not msg_nums[0]:
            imap.logout()
            return 0
        for num in msg_nums[0].split()[-20:]:
            _, data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            msg_id = msg.get("Message-ID", num.decode())
            if msg_id in state.get("seen_ids", []):
                continue
            state.setdefault("seen_ids", []).append(msg_id)
            sender = get_sender(msg)
            subject = decode_subject(msg)
            body = get_body(msg)
            category = classify_response(subject, body)
            campaigns = ", ".join(inbox_cfg["campaigns"])
            if category == "AUTO_REPLY" or category == "BOUNCE":
                log(f"{name}: {category} from {sender}")
                continue
            new_count += 1
            icon = {"INTERESTED": "🟢", "NOT_INTERESTED": "🔴", "UNKNOWN": "📩"}.get(category, "📩")
            alert(f"{icon} <b>{category}</b> — {campaigns}\n"
                  f"From: {sender}\n"
                  f"Subject: {subject[:100]}\n"
                  f"Preview: {body[:200]}")
            save_response_db(sender, subject, category, campaigns, name)
            log(f"{name}: {category} from {sender} — {subject[:50]}")
        imap.logout()
    except Exception as e:
        log(f"{name}: IMAP error — {e}")
    return new_count


def ensure_db_table():
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS campaign_responses (
                id SERIAL PRIMARY KEY,
                sender_email VARCHAR(255),
                subject VARCHAR(255),
                category VARCHAR(50),
                campaign VARCHAR(100),
                inbox VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(sender_email, subject)
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"DB table creation error: {e}")


def main():
    ensure_db_table()
    state = load_state()
    total = 0
    for inbox in INBOXES:
        total += check_inbox(inbox, state)
    save_state(state)
    if total > 0:
        log(f"Total new responses: {total}")


if __name__ == "__main__":
    main()
