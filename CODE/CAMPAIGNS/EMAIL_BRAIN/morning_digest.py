#!/usr/bin/env python3
"""Morning Digest — 07:00 daily Telegram summary. Covers items 5,7,3,4,6."""
import os, psycopg2, requests, sqlite3
from datetime import datetime, timedelta

TOKEN = "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8"
CHAT = "547047851"
LOG = "/home/tudor/.logs/morning_digest.log"


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] {msg}\n")


def get_responses_24h():
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""SELECT category, COUNT(*) FROM campaign_responses
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY category ORDER BY count DESC""")
        return dict(cur.fetchall())
    except Exception:
        return {}


def get_solonet_status():
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) FROM solonet_orders GROUP BY status")
        return dict(cur.fetchall())
    except Exception:
        return {}


def get_followups_due():
    """Item 3: check follow-ups due today."""
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        cur.execute("""SELECT email, company, reason FROM followup
            WHERE followup_date <= CURRENT_DATE AND status='pending'""")
        return cur.fetchall()
    except Exception:
        return []


def get_response_rates():
    """Item 4: response rate by campaign."""
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        cur.execute("""SELECT campaign, COUNT(*) as sent FROM send_log
            GROUP BY campaign ORDER BY sent DESC LIMIT 10""")
        sends = dict(cur.fetchall())
        cur.close()
        conn.close()
        conn2 = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur2 = conn2.cursor()
        cur2.execute("""SELECT campaign, COUNT(*) FROM campaign_responses
            WHERE category IN ('INTERESTED','REPLY')
            GROUP BY campaign""")
        replies = dict(cur2.fetchall())
        cur2.close()
        conn2.close()
        rates = {}
        for camp, sent in sends.items():
            resp = replies.get(camp, 0)
            if sent > 0:
                rates[camp] = f"{resp}/{sent} ({resp/sent*100:.1f}%)"
        return rates
    except Exception:
        return {}


def get_dnc_24h():
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM master_dnc WHERE created_at > NOW() - INTERVAL '24 hours'")
        return cur.fetchone()[0]
    except Exception:
        return 0


def get_workers_24h():
    try:
        conn = sqlite3.connect("/opt/ACTIVE/OPENDATA/DATA/master_applicants.db")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM applicants WHERE created_at > datetime('now', '-1 day')")
        return cur.fetchone()[0]
    except Exception:
        return 0


def get_cv_count():
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cv_vault")
        return cur.fetchone()[0]
    except Exception:
        return 0


def send_followup_reminders(due):
    """Item 3: send Telegram reminders for due follow-ups."""
    for email, company, reason in due:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "parse_mode": "HTML",
                  "text": f"📅 <b>FOLLOW-UP DUE</b>\n{company or email}\n{reason[:80]}"},
            timeout=10)


def process_unsubscribes():
    """Item 5: auto-DNC unsubscribe responses."""
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("""SELECT sender_email, subject FROM campaign_responses
            WHERE category='NOT_INTERESTED'
            AND (LOWER(subject) LIKE '%unsubscri%' OR LOWER(subject) LIKE '%stop%'
                 OR LOWER(subject) LIKE '%remove%' OR LOWER(subject) LIKE '%dezabona%')
            AND sender_email NOT IN (SELECT email FROM master_dnc)""")
        unsubs = cur.fetchall()
        for email, subj in unsubs:
            cur.execute("INSERT INTO master_dnc (email, reason, source) VALUES (%s, %s, 'unsubscribe') ON CONFLICT DO NOTHING",
                (email, f"Unsubscribe: {subj[:80]}"))
        conn.commit()
        cur.close()
        conn.close()
        return len(unsubs)
    except Exception:
        return 0


def main():
    responses = get_responses_24h()
    solonet = get_solonet_status()
    followups = get_followups_due()
    rates = get_response_rates()
    new_dnc = get_dnc_24h()
    new_workers = get_workers_24h()
    cv_count = get_cv_count()
    new_unsubs = process_unsubscribes()

    # Send follow-up reminders
    if followups:
        send_followup_reminders(followups)

    # Build digest
    lines = ["📋 <b>MORNING DIGEST</b>", ""]

    # Responses
    r_str = ", ".join(f"{k}: {v}" for k, v in responses.items()) if responses else "none"
    lines.append(f"📬 Responses 24h: {r_str}")

    # Solonet
    s_str = ", ".join(f"{k}: {v}" for k, v in solonet.items()) if solonet else "none"
    lines.append(f"🏢 Solonet: {s_str}")

    # Follow-ups
    lines.append(f"📅 Follow-ups due: {len(followups)}")

    # Workers + CVs
    lines.append(f"👷 New workers: {new_workers} | CV vault: {cv_count}")

    # DNC
    lines.append(f"🚫 New DNC: {new_dnc} | Unsubscribes: {new_unsubs}")

    # Top response rates
    if rates:
        top = list(rates.items())[:5]
        lines.append("")
        lines.append("📊 Response rates:")
        for camp, rate in top:
            lines.append(f"  {camp}: {rate}")

    msg = "\n".join(lines)
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT, "text": msg, "parse_mode": "HTML"}, timeout=10)
    log(msg.replace("<b>", "").replace("</b>", ""))


if __name__ == "__main__":
    main()
