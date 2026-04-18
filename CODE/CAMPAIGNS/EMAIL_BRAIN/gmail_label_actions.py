#!/usr/bin/env python3
"""Gmail Label Actions — your labels become commands. Every 10 min via cron.
SOLONET → solonet draft. APPLICANTS → applicant DB. LATER → follow-up 7d.
IMPORTANT → flag. UNSUBSCRIBE → permanent DNC. Any new label = extensible."""
import imaplib, email, re, os, json, psycopg2, sqlite3, requests
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

TOKEN = "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8"
CHAT = "547047851"
STATE = Path("/opt/ACTIVE/INFRA/GOVERNOR/gmail_labels_state.json")
LOG = "/home/tudor/.logs/gmail_labels.log"
APPLICANT_DB = "/opt/ACTIVE/OPENDATA/DATA/master_applicants.db"

ACCOUNTS = [
    ("manpower.dristor@gmail.com", "GMAIL_MANPOWERDRISTOR_APP_PASSWORD"),
    ("elena.manpower.dristor@gmail.com", "GMAIL_ELENA_APP_PASSWORD"),
]

LABEL_ACTIONS = {
    "SOLONET": "solonet",
    "APPLICANTS": "applicant",
    "LATER": "followup_7d",
    "IMPORTANT": "flag",
    "DNC": "dnc_permanent",
    "UNSUBSCRIBE": "dnc_permanent",
}

OWN_DOMAINS = {"brevo.com", "google.com", "googlemail.com", "buildjobs.eu",
    "interjob.ro", "cifn.eu", "factoryjobs.eu", "careworkers.eu",
    "zohomail.com", "zohomail.eu", "seicarescu.com", "mailrelay.com",
    "mivromania.info", "expatsinromania.org", "bppltd.co.uk"}


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


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"seen": {}}


def save_state(state):
    for k in state.get("seen", {}):
        state["seen"][k] = state["seen"][k][-200:]
    STATE.write_text(json.dumps(state))


def get_sender(msg):
    m = re.search(r"<([^>]+)>", msg.get("From", ""))
    return m.group(1).lower() if m else msg.get("From", "")[:100].lower()


def decode_subj(msg):
    d = decode_header(msg.get("Subject", ""))
    return " ".join(
        p.decode(e or "utf-8", errors="replace") if isinstance(p, bytes) else p
        for p, e in d)[:200]


def get_body(msg):
    plain, html = "", ""
    for part in (msg.walk() if msg.is_multipart() else [msg]):
        ct = part.get_content_type()
        try:
            text = part.get_payload(decode=True).decode(errors="replace")
        except Exception:
            continue
        if ct == "text/plain" and not plain:
            plain = text[:500]
        elif ct == "text/html" and not html:
            html = re.sub(r"<[^>]+>", " ", text)
            html = re.sub(r"\s+", " ", html).strip()[:500]
    return plain or html or ""


def is_own(sender):
    domain = sender.split("@")[1] if "@" in sender else ""
    return any(domain.endswith(d) for d in OWN_DOMAINS)


def action_solonet(sender, subject, body):
    try:
        from solonet_pipeline import create_draft
        company = ""
        m = re.search(r"pentru (.+?)( /| $|\r)", subject)
        if m:
            company = m.group(1).strip()
        create_draft(sender, company or sender.split("@")[0],
            "", body[:200], "", "", subject, body)
    except Exception as e:
        log(f"Solonet error: {e}")


def action_applicant(sender, subject, body):
    try:
        conn = sqlite3.connect(APPLICANT_DB)
        cur = conn.cursor()
        name = ""
        for line in body.split("\n")[:5]:
            if any(w in line.lower() for w in ["name:", "my name", "i am"]):
                name = line.strip()[:100]
                break
        cur.execute("INSERT OR IGNORE INTO applicants (email, name, skills, source) VALUES (?, ?, ?, ?)",
            (sender, name or sender.split("@")[0], subject[:200], "gmail_label"))
        conn.commit()
        conn.close()
        # Also add to cv_vault
        try:
            dbc = psycopg2.connect(host="/var/run/postgresql",
                dbname="interjob_master", user="tudor", password="scraper123")
            dc = dbc.cursor()
            dc.execute("INSERT INTO cv_vault (filename, name, email, skills, source, date_added) VALUES (%s,%s,%s,%s,%s,CURRENT_DATE) ON CONFLICT DO NOTHING",
                (f"auto_{sender.replace('@','_')}.pdf", name or sender, sender, subject[:200], "gmail_label"))
            dbc.commit()
            dc.close()
            dbc.close()
        except Exception:
            pass
        alert(f"👷 <b>APPLICANT</b> (Gmail label)\nFrom: {sender}\nSubj: {subject[:60]}")
    except Exception as e:
        log(f"Applicant error: {e}")


def action_followup(sender, subject, days=7):
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur = conn.cursor()
        fdate = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute("CREATE TABLE IF NOT EXISTS followup (id SERIAL PRIMARY KEY, email VARCHAR(255), company VARCHAR(255), reason TEXT, followup_date DATE, status VARCHAR(50) DEFAULT 'pending', created_at TIMESTAMP DEFAULT NOW())")
        cur.execute("INSERT INTO followup (email, company, reason, followup_date) VALUES (%s, %s, %s, %s)",
            (sender, sender.split("@")[0], f"Gmail LATER label. Subj: {subject[:80]}", fdate))
        conn.commit()
        cur.close()
        conn.close()
        alert(f"📅 <b>FOLLOW-UP</b> in {days}d\n{sender}\n{subject[:60]}")
    except Exception as e:
        log(f"Follow-up error: {e}")


def action_dnc(sender, subject):
    try:
        conn = psycopg2.connect(host="/var/run/postgresql",
            dbname="interjob_master", user="tudor", password="scraper123")
        cur = conn.cursor()
        cur.execute("INSERT INTO master_dnc (email, reason, source) VALUES (%s, %s, 'unsubscribe') ON CONFLICT DO NOTHING",
            (sender, f"Gmail DNC label. Subj: {subject[:80]}"))
        conn.commit()
        cur.close()
        conn.close()
        bl = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")
        with open(bl, "a") as f:
            f.write(sender + "\n")
    except Exception as e:
        log(f"DNC error: {e}")


def action_flag(sender, subject):
    alert(f"⭐ <b>IMPORTANT</b>\n{sender}\n{subject[:80]}")


ACTIONS = {
    "solonet": action_solonet,
    "applicant": action_applicant,
    "followup_7d": lambda s, subj, body: action_followup(s, subj, 7),
    "flag": lambda s, subj, body: action_flag(s, subj),
    "dnc_permanent": lambda s, subj, body: action_dnc(s, subj),
}


def scan_labels(account, pwd_env, state):
    env = {}
    with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
        for l in f:
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1)
                env[k] = v.strip().strip('"')
    pwd = env.get(pwd_env, "")
    if not pwd:
        return 0
    total = 0
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(account, pwd)
        for label, action_key in LABEL_ACTIONS.items():
            try:
                imap.create(label)
            except Exception:
                pass
            s, _ = imap.select(label)
            if s != "OK":
                continue
            since = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
            _, nums = imap.search(None, f'(SINCE "{since}")')
            if not nums[0]:
                continue
            seen_key = f"{account}_{label}"
            for num in nums[0].split()[-20:]:
                _, data = imap.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                msg_id = msg.get("Message-ID", num.decode())
                if msg_id in state.get("seen", {}).get(seen_key, []):
                    continue
                state.setdefault("seen", {}).setdefault(seen_key, []).append(msg_id)
                sender = get_sender(msg)
                if is_own(sender):
                    continue
                subject = decode_subj(msg)
                body = get_body(msg)
                action_fn = ACTIONS.get(action_key)
                if action_fn:
                    action_fn(sender, subject, body)
                    total += 1
                    log(f"{label}: {sender} -> {action_key}")
        imap.logout()
    except Exception as e:
        log(f"Label scan error {account}: {e}")
    return total


def main():
    state = load_state()
    total = 0
    for account, pwd_env in ACCOUNTS:
        total += scan_labels(account, pwd_env, state)
    save_state(state)
    if total:
        log(f"Processed {total} labeled emails")


if __name__ == "__main__":
    main()
