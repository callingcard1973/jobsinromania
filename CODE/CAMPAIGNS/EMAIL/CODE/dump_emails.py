#!/usr/bin/env python3
"""Dump filtered emails to JSON for external LLM processing."""
import imaplib, email, json, ssl, re, sys
from email.header import decode_header
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT = SCRIPT_DIR / "raw_emails.json"

ACCOUNTS = [
    {"email": "manpower.dristor@gmail.com", "password": "tbdh pycf vbxo eung", "imap_server": "imap.gmail.com", "imap_port": 993},
    {"email": "elena.manpower.dristor@gmail.com", "password": "wmfnpikkcierkmrq", "imap_server": "imap.gmail.com", "imap_port": 993},
]

SKIP_SENDERS = {
    "elena.manpower.dristor@gmail.com", "manpower.dristor@gmail.com", "manpowerdristor@gmail.com",
    "noreply@interjob.ro", "elena@interjob.ro", "office@interjob.ro", "tudor@interjob.ro",
    "office@seicarescu.com", "tudor@seicarescu.com", "office@mivromania.info",
    "mailer-daemon@", "noreply@", "no-reply@", "notifications@", "newsletter@",
    "@brevosend.com", "@5099400.brevosend.com", "@t.brevo.com", "account-alerts@",
    "@supabase.com", "@zohomail.com", "@zohocorp.com", "transport.work@", "workers.europe@",
    "@jobteam.dk", "support@contactsplus.com", "info@google.com", "accounts.google.com",
}

SKIP_SUBJECTS = re.compile(
    r"(out of office|automatic reply|autoreply|automatische antwort|auto response|r.ponse automatique|"
    r"delivery.*(fail|status)|undeliver|returned mail|vacation|absence|mailer.daemon|"
    r"dezabonare|unsubscribe|campaign alert|stalled campaign|"
    r"smtp test|security alert|verify a new ip|welcome to brevo|new smtp key|"
    r"getting started with|lock down your|going to be paused|has been paused|thank you for your message)", re.I)

APPLICANT_SUBJECTS = re.compile(
    r"(job application|application for|job search|farm worker position|hotel job|looking for.*job|"
    r"seeking.*employment|application for employment|ans.gning)", re.I)

def decode_h(v):
    if not v: return ""
    parts = decode_header(v)
    r = []
    for p, c in parts:
        r.append(p.decode(c or "utf-8", errors="replace") if isinstance(p, bytes) else p)
    return " ".join(r)

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                p = part.get_payload(decode=True)
                if p: return p.decode(part.get_content_charset() or "utf-8", errors="replace")
            elif ct == "text/html":
                p = part.get_payload(decode=True)
                if p:
                    h = p.decode(part.get_content_charset() or "utf-8", errors="replace")
                    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
                    return re.sub(r"<[^>]+>", "", h)
    else:
        p = msg.get_payload(decode=True)
        if p: return p.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return ""

def extract_email(f):
    m = re.search(r"<([^>]+)>", f)
    if m: return m.group(1).lower()
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", f)
    return m.group().lower() if m else f.lower()

def should_skip(sender):
    s = sender.lower()
    return any(skip in s for skip in SKIP_SENDERS)

results = []
for acct in ACCOUNTS:
    print(f"Scanning {acct['email']}...")
    ctx = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL(acct["imap_server"], acct["imap_port"], ssl_context=ctx)
    imap.login(acct["email"], acct["password"])
    imap.select("INBOX", readonly=True)
    _, ids = imap.search(None, '(SINCE "01-Jan-2025")')
    if not ids[0]:
        imap.logout()
        continue
    all_ids = ids[0].split()
    print(f"  {len(all_ids)} messages")
    for mid in all_ids:
        _, hd = imap.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
        hm = email.message_from_bytes(hd[0][1])
        frm = decode_h(hm.get("From", ""))
        subj = decode_h(hm.get("Subject", ""))
        sender = extract_email(frm)
        if should_skip(sender): continue
        if SKIP_SUBJECTS.search(subj): continue
        if APPLICANT_SUBJECTS.search(subj): continue
        _, fd = imap.fetch(mid, "(RFC822)")
        fm = email.message_from_bytes(fd[0][1])
        body = get_body(fm)
        if not body.strip(): continue
        results.append({"from": frm, "sender_email": sender, "subject": subj, "body": body[:2000], "account": acct["email"]})
        try:
            print(f"  + {sender} | {subj[:60]}")
        except UnicodeEncodeError:
            print(f"  + {sender} | (unicode subject)")

    imap.logout()

OUTPUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nDumped {len(results)} emails to {OUTPUT}")
