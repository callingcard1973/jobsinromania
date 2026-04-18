#!/usr/bin/env python3
"""Email Processor — Ollama classifies, drafts reply, Tudor approves via Telegram.
Runs every 10 min via cron. No cloud LLM tokens used."""
import os, json, imaplib, email, re, smtplib, sqlite3, requests, psycopg2
from datetime import datetime, timedelta
from email.header import decode_header
from email.mime.text import MIMEText
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3-4b"
TOKEN = "8546618948:AAG0neoQA-kNq0M2GrZX7J-dGXNvEJEOK9w"
CHAT = "547047851"
STATE = Path("/opt/ACTIVE/INFRA/GOVERNOR/email_processor_state.json")
LOG = "/home/tudor/.logs/email_processor.log"
QUEUE = Path("/opt/ACTIVE/INFRA/GOVERNOR/email_queue.json")
APPLICANT_DB = "/opt/ACTIVE/OPENDATA/DATA/master_applicants.db"

OWN = {"manpower.dristor@gmail.com", "manpowersearchromania@gmail.com",
       "tudor@seicarescu.com", "office@buildjobs.eu", "office@cifn.eu",
       "workers.europe@zohomail.eu", "campaigns@m.brevo.com",
       "elena.manpower.dristor@gmail.com", "info@mailrelay.com",
       "office@interjob.ro", "office@bppltd.co.uk", "no-reply@brevo.com"}

INBOX_CFG = {"host": "imap.gmail.com", "port": 993,
             "user": "manpower.dristor@gmail.com",
             "password_env": "GMAIL_MANPOWERDRISTOR_APP_PASSWORD"}


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


def decode_subj(msg):
    d = decode_header(msg.get("Subject", ""))
    return " ".join(p.decode(e or "utf-8", errors="replace") if isinstance(p, bytes) else p for p, e in d)[:200]


def get_sender(msg):
    m = re.search(r"<([^>]+)>", msg.get("From", ""))
    return m.group(1).lower() if m else msg.get("From", "")[:100].lower()


def get_body(msg):
    for part in (msg.walk() if msg.is_multipart() else [msg]):
        if part.get_content_type() == "text/plain":
            try:
                return part.get_payload(decode=True).decode(errors="replace")[:500]
            except Exception:
                pass
    return ""


def ask_ollama(prompt):
    try:
        r = requests.post(OLLAMA, json={"model": MODEL, "prompt": prompt,
            "stream": False}, timeout=30)
        if r.status_code == 200:
            return r.json().get("response", "")[:800]
    except Exception:
        pass
    return ""


def sklearn_classify(text):
    """Fast sklearn classification — instant, no LLM needed."""
    try:
        import pickle
        with open("/opt/ACTIVE/EMAIL/ORDERS/models/email_classifier.pkl", "rb") as f:
            models = pickle.load(f)
        intent = models["intent"].predict([text])[0]
        confidence = max(models["intent"].predict_proba([text])[0]) * 100
        priority = models["priority"].predict([text])[0]
        folder = models["folder"].predict([text])[0]
        return {"intent": intent, "confidence": confidence,
                "priority": priority, "folder": folder}
    except Exception:
        return None


INTENT_MAP = {"application": "WORKER_APPLICATION", "campaign_reply": "INTERESTED",
    "inquiry": "QUESTION", "bounce": "AUTO_REPLY", "auto_reply": "AUTO_REPLY",
    "spam": "SPAM", "newsletter": "SPAM", "other": "UNKNOWN"}


def classify_and_draft(sender, subject, body):
    text = f"Subject: {subject}\n\n{body[:400]}"

    # Step 1: sklearn (instant, free)
    sk = sklearn_classify(text)
    category = INTENT_MAP.get(sk["intent"], "UNKNOWN") if sk else "UNKNOWN"
    confidence = sk["confidence"] if sk else 0

    # Step 2: if high confidence sklearn, skip Ollama for classification
    # but still use Ollama to draft reply
    if confidence >= 60 and category in ("AUTO_REPLY", "SPAM"):
        return {"category": category, "action": "archive",
                "reply_text": "", "dnc_months": 0, "followup_days": 0,
                "summary": f"sklearn:{sk['intent']}@{confidence:.0f}%"}

    # Step 3: Ollama for draft reply + refine category if sklearn unsure
    prompt = f"""/no_think
You are an email assistant for InterJob, a European recruitment agency.
Classify this email and draft a short reply.

From: {sender}
Subject: {subject}
Body: {body[:400]}

sklearn pre-classification: {category} ({confidence:.0f}% confidence)

Reply ONLY in this JSON format:
{{"category": "NOT_INTERESTED|POSITION_FILLED|INTERESTED|WORKER_APPLICATION|AUTO_REPLY|SPAM|QUESTION",
 "action": "reply|archive|dnc|applicant|followup",
 "reply_text": "the draft reply text in the language of the original email",
 "dnc_months": 0,
 "followup_days": 0,
 "summary": "one line summary"}}"""
    raw = ask_ollama(prompt)
    try:
        # Extract JSON from response
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"category": "UNKNOWN", "action": "archive",
            "reply_text": "", "summary": raw[:100], "dnc_months": 0, "followup_days": 0}


def send_telegram_proposal(email_data, proposal):
    cat = proposal.get("category", "?")
    action = proposal.get("action", "?")
    summary = proposal.get("summary", "")
    reply = proposal.get("reply_text", "")[:200]
    icons = {"INTERESTED": "🟢", "NOT_INTERESTED": "🔴", "POSITION_FILLED": "🟡",
             "WORKER_APPLICATION": "👷", "QUESTION": "❓", "SPAM": "🗑", "AUTO_REPLY": "🤖"}
    icon = icons.get(cat, "📩")

    text = (f"{icon} <b>{cat}</b>\n"
            f"From: {email_data['sender']}\n"
            f"Subj: {email_data['subject'][:60]}\n"
            f"Summary: {summary}\n"
            f"Action: {action}\n")
    if reply:
        text += f"\n<b>Draft reply:</b>\n<i>{reply}</i>\n"
    text += f"\n/approve_{email_data['id']} — send reply + execute\n/skip_{email_data['id']} — skip this email"

    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"seen_ids": []}


def save_state(state):
    state["seen_ids"] = state["seen_ids"][-200:]
    STATE.write_text(json.dumps(state))


def load_queue():
    if QUEUE.exists():
        try:
            return json.loads(QUEUE.read_text())
        except Exception:
            pass
    return {}


def save_queue(queue):
    QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))


def main():
    env = load_env()
    state = load_state()
    queue = load_queue()
    password = env.get(INBOX_CFG["password_env"], "")
    if not password:
        log("No password")
        return

    try:
        imap = imaplib.IMAP4_SSL(INBOX_CFG["host"], INBOX_CFG["port"])
        imap.login(INBOX_CFG["user"], password)
        imap.select("INBOX")
        since = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
        _, nums = imap.search(None, f'(SINCE "{since}" UNSEEN)')
        if not nums[0]:
            imap.logout()
            return

        processed = 0
        for num in nums[0].split()[-10:]:
            _, data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            msg_id = msg.get("Message-ID", num.decode())
            if msg_id in state.get("seen_ids", []):
                continue

            sender = get_sender(msg)
            if sender in OWN:
                state.setdefault("seen_ids", []).append(msg_id)
                continue

            subject = decode_subj(msg)
            body = get_body(msg)
            state.setdefault("seen_ids", []).append(msg_id)

            # Classify with Ollama
            proposal = classify_and_draft(sender, subject, body)
            eid = f"e{int(datetime.now().timestamp())}{processed}"

            email_data = {"id": eid, "sender": sender, "subject": subject,
                          "body": body, "msg_num": num.decode(), "msg_id": msg_id}

            # Save to queue for approval
            queue[eid] = {"email": email_data, "proposal": proposal,
                          "status": "pending", "created": datetime.now().isoformat()}

            # Send Telegram proposal
            send_telegram_proposal(email_data, proposal)
            log(f"Proposed: {sender} -> {proposal.get('category')} ({proposal.get('action')})")
            processed += 1

        imap.logout()
        save_state(state)
        save_queue(queue)
        if processed:
            log(f"Processed {processed} new emails")

    except Exception as e:
        log(f"Error: {e}")


if __name__ == "__main__":
    main()
