#!/usr/bin/env python3
"""Worker Router — auto-routes worker applications to applicant DB + sends apply link.
Called by response_tracker when a worker application is detected."""
import os
import re
import json
import smtplib
import sqlite3
import requests
import psycopg2
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

MASTER_DB = "/opt/ACTIVE/OPENDATA/DATA/master_applicants.db"
LOG = "/home/tudor/.logs/worker_router.log"
TELEGRAM_TOKEN = "8546618948:AAG0neoQA-kNq0M2GrZX7J-dGXNvEJEOK9w"
CHAT_ID = "547047851"

# Job site inboxes (workers apply here, not employers)
JOB_SITE_INBOXES = {
    "meatworkers", "buildjobs", "interjob", "careworkers",
    "factoryjobs", "electricjobs", "warehouseworkers",
    "farmworkers", "horecaworkers2026", "meatworkers",
}

# Free email = likely worker, corporate = likely employer
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "mail.com", "protonmail.com", "live.com",
    "yahoo.fr", "yahoo.co.uk", "hotmail.co.uk", "msn.com",
}

AUTO_REPLY_TEMPLATE = """Dear applicant,

Thank you for your interest in working in Europe.

To process your application, please fill out our form:
https://interjob.ro/apply.html

Please include:
- Full name and nationality
- Phone number (WhatsApp preferred)
- Work experience (years and type)
- Languages spoken
- Preferred country and job type

We will review your application within 48 hours.

Best regards,
InterJob European Recruitment
interjob.ro
"""


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def is_worker_application(sender_email, inbox_name, category):
    """Detect if this is a worker applying (not an employer responding)."""
    domain = sender_email.split("@")[1] if "@" in sender_email else ""
    if inbox_name not in JOB_SITE_INBOXES:
        return False
    if domain in FREE_EMAIL_DOMAINS:
        return True
    if category == "INTERESTED" and domain in FREE_EMAIL_DOMAINS:
        return True
    return False


def add_to_applicant_db(email, name="", subject="", inbox=""):
    """Add worker to master applicants SQLite database."""
    try:
        conn = sqlite3.connect(MASTER_DB)
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE, name TEXT, phone TEXT, nationality TEXT,
            skills TEXT, source TEXT, cv_path TEXT, status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""INSERT OR IGNORE INTO applicants (email, name, source, skills)
            VALUES (?, ?, ?, ?)""",
            (email, name, f"auto:{inbox}", subject[:200]))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log(f"SQLite error: {e}")
        return False


def add_to_cv_vault(email, name, nationality, skills):
    """Add worker to cv_vault table for matching."""
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        fname = f"auto_{email.replace('@','_')}.pdf"
        cur.execute("""INSERT INTO cv_vault (filename, name, email, nationality, skills, source, date_added)
            VALUES (%s, %s, %s, %s, %s, 'auto_ingest', CURRENT_DATE)
            ON CONFLICT (filename) DO NOTHING""",
            (fname, name[:255], email, nationality or "??", skills or "general"))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def save_worker_to_pg(email, name, subject, inbox):
    """Save to PostgreSQL campaign_responses with worker tag."""
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""INSERT INTO campaign_responses
            (sender_email, subject, category, campaign, inbox, created_at)
            VALUES (%s, %s, 'WORKER_APPLICATION', %s, %s, NOW())
            ON CONFLICT DO NOTHING""",
            (email, subject[:200], f"WORKER_{inbox.upper()}", inbox))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"PG error: {e}")


def send_auto_reply(to_email, inbox_name):
    """Send apply form link to worker. Uses A2 SMTP."""
    env = {}
    try:
        with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
            for l in f:
                if "=" in l and not l.startswith("#"):
                    k, v = l.strip().split("=", 1)
                    env[k] = v
    except Exception:
        return False

    sender = f"office@interjob.ro"
    password = env.get("A2_EMAIL_PASSWORD", "")
    if not password:
        log(f"No A2 password for auto-reply to {to_email}")
        return False

    msg = MIMEText(AUTO_REPLY_TEMPLATE)
    msg["Subject"] = "Your application - next steps"
    msg["From"] = f"InterJob Recruitment <{sender}>"
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("nl1-cl8-ats1.a2hosting.com", 465, timeout=15) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        log(f"Auto-reply sent to {to_email}")
        return True
    except Exception as e:
        log(f"SMTP error replying to {to_email}: {e}")
        return False


def alert_telegram(email, inbox, subject):
    """Notify Tudor of new worker application."""
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "parse_mode": "HTML",
                  "text": f"👷 <b>WORKER APPLICATION</b>\n"
                          f"From: {email}\nInbox: {inbox}\n"
                          f"Subject: {subject[:80]}\n"
                          f"Auto-reply sent with apply form link"},
            timeout=10)
    except Exception:
        pass


def process_worker(sender_email, inbox_name, subject="", body=""):
    """Full pipeline: DB + auto-reply + alert."""
    name = ""
    # Try to extract name from body
    for line in body.split("\n")[:5]:
        if any(w in line.lower() for w in ["name:", "my name", "i am"]):
            name = line.strip()[:100]
            break

    added = add_to_applicant_db(sender_email, name, subject, inbox_name)
    save_worker_to_pg(sender_email, name or sender_email, subject, inbox_name)
    add_to_cv_vault(sender_email, name or sender_email, "", subject[:200])
    sent = send_auto_reply(sender_email, inbox_name)
    alert_telegram(sender_email, inbox_name, subject)

    log(f"Worker {sender_email} from {inbox_name}: db={'OK' if added else 'SKIP'} reply={'OK' if sent else 'FAIL'}")
    return added
