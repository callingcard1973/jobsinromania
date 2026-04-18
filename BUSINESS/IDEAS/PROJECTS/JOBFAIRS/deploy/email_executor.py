#!/usr/bin/env python3
"""Email Executor — executes approved email actions.
Called by Telegram bot when Tudor types /approve_eXXX or /skip_eXXX."""
import json, smtplib, sqlite3, psycopg2, os
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pathlib import Path

QUEUE = Path("/opt/ACTIVE/INFRA/GOVERNOR/email_queue.json")
APPLICANT_DB = "/opt/ACTIVE/OPENDATA/DATA/master_applicants.db"
LOG = "/home/tudor/.logs/email_executor.log"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def load_env():
    env = {}
    with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
        for l in f:
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1)
                env[k] = v
    return env


def load_queue():
    if QUEUE.exists():
        return json.loads(QUEUE.read_text())
    return {}


def save_queue(queue):
    QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))


def send_reply(to, subject, body_text, env):
    msg = MIMEText(body_text)
    msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    msg["From"] = "Tudor - InterJob Solutions <manpower.dristor@gmail.com>"
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
        smtp.login("manpower.dristor@gmail.com",
                    env["GMAIL_MANPOWERDRISTOR_APP_PASSWORD"])
        smtp.send_message(msg)
    return True


def add_dnc(email_addr, reason, months):
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        expires = (datetime.now() + timedelta(days=months * 30)).strftime("%Y-%m-%d")
        cur.execute("""INSERT INTO dnc (email, reason, expires_at)
            VALUES (%s, %s, %s) ON CONFLICT (email)
            DO UPDATE SET reason=%s, expires_at=%s""",
            (email_addr, reason, expires, reason, expires))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        log(f"DNC error: {e}")
        return False


def add_followup(email_addr, company, reason, days):
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        fdate = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute("""INSERT INTO followup (email, company, reason, followup_date)
            VALUES (%s, %s, %s, %s)""",
            (email_addr, company, reason, fdate))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        log(f"Followup error: {e}")
        return False


def add_applicant(email_addr, name, details):
    try:
        conn = sqlite3.connect(APPLICANT_DB)
        cur = conn.cursor()
        cur.execute("""INSERT OR IGNORE INTO applicants
            (email, name, skills, source)
            VALUES (?, ?, ?, ?)""",
            (email_addr, name, details, "email_processor"))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log(f"Applicant error: {e}")
        return False


def move_to_folder(email_addr, folder, env):
    """Move emails from sender to Gmail label."""
    import imaplib
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login("manpower.dristor@gmail.com",
                    env["GMAIL_MANPOWERDRISTOR_APP_PASSWORD"])
        imap.select("INBOX")
        try:
            imap.create(folder)
        except Exception:
            pass
        _, nums = imap.search(None, f'(FROM "{email_addr}")')
        if nums[0]:
            for n in nums[0].split():
                imap.copy(n, folder)
                imap.store(n, "+FLAGS", r"(\Seen)")
        imap.logout()
        return True
    except Exception as e:
        log(f"Move error: {e}")
        return False


def execute(eid, action="approve"):
    queue = load_queue()
    item = queue.get(eid)
    if not item:
        return f"Email {eid} not found in queue"
    if item["status"] != "pending":
        return f"Already {item['status']}"

    env = load_env()
    em = item["email"]
    prop = item["proposal"]
    sender = em["sender"]
    subject = em["subject"]
    results = []

    if action == "skip":
        item["status"] = "skipped"
        save_queue(queue)
        return f"Skipped {sender}"

    # Execute proposed action
    act = prop.get("action", "archive")
    reply_text = prop.get("reply_text", "")
    category = prop.get("category", "")

    if reply_text and act in ("reply", "followup", "dnc"):
        try:
            send_reply(sender, subject, reply_text, env)
            results.append("Reply sent")
        except Exception as e:
            results.append(f"Reply FAILED: {e}")

    if act == "dnc":
        months = prop.get("dnc_months", 3) or 3
        add_dnc(sender, f"{category}: {prop.get('summary','')}",  months)
        results.append(f"DNC {months}mo")

    if act == "followup":
        days = prop.get("followup_days", 90) or 90
        company = re.search(r"pentru (.+?)( /|$)", subject)
        comp = company.group(1) if company else subject[:50]
        add_followup(sender, comp, prop.get("summary", ""), days)
        results.append(f"Follow-up {days}d")

    if act == "applicant" or category == "WORKER_APPLICATION":
        add_applicant(sender, sender.split("@")[0], em.get("body", "")[:200])
        move_to_folder(sender, "APPLICANTS", env)
        results.append("Added to applicants + moved")

    item["status"] = "approved"
    item["executed"] = datetime.now().isoformat()
    item["results"] = results
    save_queue(queue)
    log(f"Executed {eid}: {sender} -> {', '.join(results)}")
    return f"Done: {', '.join(results)}"


import re

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        eid = sys.argv[1]
        act = sys.argv[2] if len(sys.argv) > 2 else "approve"
        print(execute(eid, act))
