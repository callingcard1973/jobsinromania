#!/usr/bin/env python3
"""Auto Follow-up — sends follow-up emails for due items. Daily 14:00 cron.
Drafts follow-up, sends via Gmail after Tudor approves (or auto if enabled)."""
import os, json, smtplib, psycopg2, requests
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

TOKEN = "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8"
CHAT = "547047851"
LOG = "/home/tudor/.logs/auto_followup.log"

FOLLOWUP_TEMPLATES = {
    "default": """Buna ziua,

Revin cu mesajul anterior referitor la disponibilitatea de personal.

Avem in continuare candidati disponibili rapid pentru pozitiile dumneavoastra.

Daca doriti sa discutam, va rog sa ne raspundeti sau sa ne contactati la +40 722 789 938.

Cu stima,
Tudor Seicarescu
InterJob Solutions Europe
cifn.eu""",

    "position_filled": """Buna ziua,

Va contactam sa verificam daca aveti noi pozitii deschise.

Data trecuta ne-ati informat ca postul s-a ocupat. Intre timp, am extins baza de candidati si avem personal disponibil rapid.

Daca aveti nevoie, suntem aici.

Cu stima,
Tudor Seicarescu
InterJob Solutions Europe""",
}


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] {msg}\n")


def load_env():
    env = {}
    with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
        for l in f:
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1)
                env[k] = v.strip().strip('"')
    return env


def get_due_followups():
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        cur.execute("""SELECT id, email, company, reason, followup_date
            FROM followup WHERE followup_date <= CURRENT_DATE AND status='pending'""")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception:
        return []


def send_followup(to_email, subject, body, env):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "Tudor InterJob <manpower.dristor@gmail.com>"
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
        smtp.login("manpower.dristor@gmail.com", env["GMAIL_MANPOWERDRISTOR_APP_PASSWORD"])
        smtp.send_message(msg)
    return True


def mark_sent(followup_id):
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        cur.execute("UPDATE followup SET status='sent' WHERE id=%s", (followup_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def main():
    due = get_due_followups()
    if not due:
        return

    env = load_env()
    for fid, email, company, reason, fdate in due:
        template = "position_filled" if "ocupat" in (reason or "").lower() else "default"
        body = FOLLOWUP_TEMPLATES[template]
        subject = f"Follow-up: {company or email}"

        # Send Telegram for approval
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "parse_mode": "HTML",
                  "text": f"📅 <b>FOLLOW-UP DUE</b>\n"
                          f"To: {email}\nCompany: {company}\n"
                          f"Reason: {(reason or '')[:80]}\n"
                          f"Due: {fdate}\n\n"
                          f"/followup_send_{fid} — send follow-up\n"
                          f"/followup_skip_{fid} — skip"},
            timeout=10)
        log(f"Follow-up due: {email} ({company}) — awaiting approval")


if __name__ == "__main__":
    main()
