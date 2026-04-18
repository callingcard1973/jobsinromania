#!/usr/bin/env python3
"""Bounce Cleaner — automated. Runs weekly via cron.
1. Pulls bounced emails from ALL Brevo accounts
2. Pulls bounces from Gmail mailer-daemon messages
3. Adds to master blacklist
4. Cleans ALL campaign CSVs (removes bounced rows)
5. Cleans PostgreSQL campaign tables
6. Reports via Telegram
No tokens. Pure API + IMAP + file ops."""
import os, re, csv, json, requests, imaplib, email, psycopg2
from pathlib import Path
from datetime import datetime
from glob import glob

TOKEN = "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8"
CHAT = "547047851"
BLACKLIST = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")
LOG = "/home/tudor/.logs/bounce_cleaner.log"
BREVO_API = "https://api.brevo.com/v3"
CSV_DIRS = [
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs",
    "/opt/ACTIVE/EMAIL/CAMPAIGNS",
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def alert(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


def load_env():
    env = {}
    with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
        for l in f:
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1)
                env[k] = v.strip().strip('"')
    return env


def load_blacklist():
    bl = set()
    if BLACKLIST.exists():
        for line in BLACKLIST.read_text().splitlines():
            e = line.strip().lower()
            if "@" in e:
                bl.add(e)
    return bl


def save_blacklist(bl):
    BLACKLIST.parent.mkdir(parents=True, exist_ok=True)
    BLACKLIST.write_text("\n".join(sorted(bl)) + "\n")


def pull_brevo_bounces(env):
    """Pull blocked/bounced contacts from all Brevo accounts."""
    new = set()
    keys = [k for k in env if k.startswith("BREVO_") and k.endswith("_API_KEY")]
    for key_name in keys:
        key = env[key_name]
        if not key:
            continue
        try:
            for offset in range(0, 2000, 50):
                r = requests.get(f"{BREVO_API}/contacts",
                    headers={"api-key": key},
                    params={"limit": 50, "offset": offset, "modifiedSince": "2026-01-01T00:00:00Z"},
                    timeout=15)
                if r.status_code != 200:
                    break
                contacts = r.json().get("contacts", [])
                if not contacts:
                    break
                for c in contacts:
                    if c.get("emailBlacklisted"):
                        new.add(c["email"].lower())
        except Exception:
            pass
        # Also get hard bounces from stats
        try:
            r = requests.get(f"{BREVO_API}/smtp/statistics/events",
                headers={"api-key": key},
                params={"event": "hardBounces", "limit": 100}, timeout=15)
            if r.status_code == 200:
                for ev in r.json().get("events", []):
                    new.add(ev.get("email", "").lower())
        except Exception:
            pass
    return new


def pull_gmail_bounces(env):
    """Extract bounced emails from Gmail mailer-daemon messages."""
    new = set()
    accounts = [
        ("manpower.dristor@gmail.com", env.get("GMAIL_MANPOWERDRISTOR_APP_PASSWORD", "")),
        ("elena.manpower.dristor@gmail.com", env.get("GMAIL_ELENA_APP_PASSWORD", "")),
    ]
    for user, pwd in accounts:
        if not pwd:
            continue
        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            imap.login(user, pwd)
            imap.select("INBOX")
            _, nums = imap.search(None, '(FROM "mailer-daemon")')
            if nums[0]:
                for num in nums[0].split()[-50:]:
                    _, data = imap.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    body = ""
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="replace")
                            break
                    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", body)
                    for e in emails:
                        if e.lower() not in ("mailer-daemon@googlemail.com",):
                            new.add(e.lower())
            imap.logout()
        except Exception:
            pass
    return new


def clean_csvs(blacklist):
    """Remove bounced emails from all campaign CSVs."""
    cleaned = 0
    for d in CSV_DIRS:
        for csv_path in glob(f"{d}/**/*.csv", recursive=True):
            try:
                with open(csv_path, encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    if not reader.fieldnames:
                        continue
                    email_col = None
                    for col in reader.fieldnames:
                        if "email" in col.lower():
                            email_col = col
                            break
                    if not email_col:
                        continue
                    rows = list(reader)
                before = len(rows)
                rows = [r for r in rows if r.get(email_col, "").lower() not in blacklist]
                removed = before - len(rows)
                if removed > 0:
                    with open(csv_path, "w", newline="", encoding="utf-8") as f:
                        w = csv.DictWriter(f, fieldnames=reader.fieldnames)
                        w.writeheader()
                        w.writerows(rows)
                    cleaned += removed
                    log(f"CSV: {csv_path} — removed {removed}")
            except Exception:
                pass
    return cleaned


def clean_db_tables(blacklist):
    """Add bounced emails to DNC tables in PostgreSQL."""
    added = 0
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        # Add to norway_virgil DNC
        for e in blacklist:
            cur.execute("INSERT INTO norway_virgil_dnc (email, reason) VALUES (%s, 'bounce') ON CONFLICT DO NOTHING", (e,))
            added += cur.rowcount
        # Mark in master_emails
        bl_list = list(blacklist)[:5000]
        if bl_list:
            cur.execute("UPDATE master_emails SET is_bounced=TRUE WHERE LOWER(email) IN %s AND is_bounced IS NOT TRUE",
                (tuple(bl_list),))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"DB error: {e}")
    return added


def main():
    env = load_env()
    bl = load_blacklist()
    initial = len(bl)

    # Pull new bounces
    brevo = pull_brevo_bounces(env)
    gmail = pull_gmail_bounces(env)
    new = (brevo | gmail) - bl
    bl.update(new)
    save_blacklist(bl)

    # Clean
    csv_cleaned = clean_csvs(bl)
    db_added = clean_db_tables(new) if new else 0

    # Report
    msg = (f"Blacklist: {initial} -> {len(bl)} (+{len(new)})\n"
           f"Brevo: {len(brevo)}, Gmail: {len(gmail)}\n"
           f"CSVs cleaned: {csv_cleaned} rows\n"
           f"DB DNC added: {db_added}")
    log(msg)
    if new:
        alert(f"🧹 <b>BOUNCE CLEANER</b>\n{msg}")


if __name__ == "__main__":
    main()
