#!/usr/bin/env python3
"""Trash-to-DNC — if Tudor deletes email from Gmail, sender goes to DNC 3 months.
Scans Gmail Trash folder every 10 min. Marks in DB with reason 'deleted_by_tudor'.
Runs via cron on raspibig."""
import imaplib, email, re, os, psycopg2, json, requests
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

TOKEN = "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8"
CHAT = "547047851"
STATE = Path("/opt/ACTIVE/INFRA/GOVERNOR/trash_dnc_state.json")
LOG = "/home/tudor/.logs/trash_dnc.log"
DNC_MONTHS = 3

OWN_DOMAINS = {"brevo.com", "mailrelay.com", "google.com", "googlemail.com",
    "buildjobs.eu", "interjob.ro", "cifn.eu", "factoryjobs.eu",
    "careworkers.eu", "meatworkers.eu", "electricjobs.eu", "warehouseworkers.eu",
    "horecaworkers.eu", "farmworkers.eu", "mivromania.info", "mivromania.com",
    "mivromania.online", "expatsinromania.org", "zohomail.com", "zohomail.eu",
    "seicarescu.com", "bppltd.co.uk", "agroevolution.com", "cifn.info",
    "nepalezi.com", "cumparlegume.com", "internaltransfers.eu",
    "horecaworkers2026.com", "horecaworkers2026.eu", "horecaworkers2026.online"}

OWN_EMAILS = {"manpower.dristor@gmail.com", "manpowersearchromania@gmail.com",
    "elena.manpower.dristor@gmail.com", "casafaurbucuresti@gmail.com",
    "cumparlegume@gmail.com", "expatsinromania@gmail.com",
    "pamintstrabun@gmail.com", "lucian.bpandp@gmail.com"}

ACCOUNTS = [
    ("manpower.dristor@gmail.com", "GMAIL_MANPOWERDRISTOR_APP_PASSWORD"),
    ("elena.manpower.dristor@gmail.com", "GMAIL_ELENA_APP_PASSWORD"),
]

SOLONET_FOLDER = "SOLONET"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"seen_trash_ids": []}

def save_state(state):
    state["seen_trash_ids"] = state["seen_trash_ids"][-500:]
    STATE.write_text(json.dumps(state))

def get_sender(msg):
    m = re.search(r"<([^>]+)>", msg.get("From", ""))
    return m.group(1).lower() if m else msg.get("From", "")[:100].lower()

def decode_subj(msg):
    d = decode_header(msg.get("Subject", ""))
    return " ".join(
        p.decode(e or "utf-8", errors="replace") if isinstance(p, bytes) else p
        for p, e in d)[:200]

def add_dnc(sender, subject):
    """Add to ALL DNC tables + blacklist. One deletion = blocked everywhere."""
    expires = (datetime.now() + timedelta(days=DNC_MONTHS * 30)).strftime("%Y-%m-%d")
    reason = f"Deleted by Tudor {datetime.now().strftime('%Y-%m-%d')}. Subj: {subject[:80]}"
    try:
        # 1. email_sender.dnc (master)
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        cur.execute("""INSERT INTO dnc (email, reason, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET reason=%s, expires_at=%s""",
            (sender, reason, expires, reason, expires))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"email_sender DNC error: {e}")

    try:
        # 2. ALL interjob_master DNC tables
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%_dnc'")
        dnc_tables = [r[0] for r in cur.fetchall()]
        for tbl in dnc_tables:
            try:
                cur.execute(f"INSERT INTO {tbl} (email, reason) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (sender, reason[:255]))
            except Exception:
                conn.rollback()
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"interjob DNC error: {e}")
    return True

def add_to_blacklist(sender):
    """Also add to master blacklist for CSV cleaning."""
    bl_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")
    try:
        existing = set()
        if bl_file.exists():
            existing = set(bl_file.read_text().splitlines())
        if sender not in existing:
            with open(bl_file, "a") as f:
                f.write(sender + "\n")
    except Exception:
        pass

def scan_trash(account, password_env, state):
    """Scan Gmail Trash for recently deleted emails."""
    env = {}
    with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
        for l in f:
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1)
                env[k] = v.strip().strip('"')

    pwd = env.get(password_env, "")
    if not pwd:
        return 0

    added = 0
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(account, pwd)
        imap.select("[Gmail]/Trash")
        since = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
        _, nums = imap.search(None, f'(SINCE "{since}")')
        if not nums[0]:
            imap.logout()
            return 0

        for num in nums[0].split()[-30:]:
            _, data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            msg_id = msg.get("Message-ID", num.decode())
            if msg_id in state.get("seen_trash_ids", []):
                continue
            state.setdefault("seen_trash_ids", []).append(msg_id)

            sender = get_sender(msg)
            domain = sender.split("@")[1] if "@" in sender else ""
            is_own = sender in OWN_EMAILS or any(domain.endswith(d) for d in OWN_DOMAINS)
            if is_own or not sender or "@" not in sender:
                continue

            # Skip workers (they're in applicant DB, not spam)
            try:
                import sqlite3
                adb = sqlite3.connect("/opt/ACTIVE/OPENDATA/DATA/master_applicants.db")
                ac = adb.cursor()
                ac.execute("SELECT COUNT(*) FROM applicants WHERE email=?", (sender,))
                is_worker = ac.fetchone()[0] > 0
                ac.close()
                adb.close()
                if is_worker:
                    continue
            except Exception:
                pass

            subject = decode_subj(msg)
            if add_dnc(sender, subject):
                add_to_blacklist(sender)
                added += 1
                log(f"DNC {DNC_MONTHS}mo: {sender} (deleted, subj: {subject[:50]})")

        imap.logout()
    except Exception as e:
        log(f"IMAP error {account}: {e}")
    return added

def scan_solonet_folder(account, password_env, state):
    """Scan Gmail SOLONET folder — emails moved here = assigned to Adrian."""
    env = {}
    with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
        for l in f:
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1)
                env[k] = v.strip().strip('"')
    pwd = env.get(password_env, "")
    if not pwd:
        return 0
    added = 0
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(account, pwd)
        try:
            imap.create(SOLONET_FOLDER)
        except Exception:
            pass
        status, _ = imap.select(SOLONET_FOLDER)
        if status != "OK":
            imap.logout()
            return 0
        since = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
        _, nums = imap.search(None, f'(SINCE "{since}")')
        if not nums[0]:
            imap.logout()
            return 0
        for num in nums[0].split()[-20:]:
            _, data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            msg_id = msg.get("Message-ID", num.decode())
            if msg_id in state.get("seen_solonet_ids", []):
                continue
            state.setdefault("seen_solonet_ids", []).append(msg_id)
            sender = get_sender(msg)
            domain = sender.split("@")[1] if "@" in sender else ""
            if any(domain.endswith(d) for d in OWN_DOMAINS) or sender in OWN_EMAILS:
                continue
            subject = decode_subj(msg)
            body = ""
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(errors="replace")[:500]
                    except Exception:
                        pass
                    break
            # Create solonet draft (enrichment handled by solonet_pipeline)
            try:
                from solonet_pipeline import create_draft
                company = ""
                m = re.search(r"pentru (.+?)( /| $|\r)", subject)
                if m:
                    company = m.group(1).strip()
                create_draft(sender, company or sender.split("@")[0],
                    "", body[:200], "", "", subject, body)
                added += 1
                log(f"SOLONET folder: {sender} -> draft created")
            except Exception as e:
                log(f"SOLONET draft error: {e}")
        imap.logout()
    except Exception as e:
        log(f"SOLONET scan error: {e}")
    return added

def main():
    state = load_state()
    total = 0
    solonet_total = 0
    for account, pwd_env in ACCOUNTS:
        total += scan_trash(account, pwd_env, state)
        solonet_total += scan_solonet_folder(account, pwd_env, state)
    # Keep seen_solonet_ids trimmed
    state["seen_solonet_ids"] = state.get("seen_solonet_ids", [])[-200:]
    save_state(state)
    if total:
        log(f"Added {total} deleted senders to DNC ({DNC_MONTHS} months)")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "parse_mode": "HTML",
                  "text": f"🗑 <b>TRASH->DNC</b>: {total} deleted senders added to DNC for {DNC_MONTHS} months"},
            timeout=10)

if __name__ == "__main__":
    main()
