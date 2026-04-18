#!/usr/bin/env python3
"""Auto-reply to COMANDA entries in orders.csv via Gmail SMTP.
Sends: "Multumesc pentru raspuns. Va contactam in 24h."
Tracks replied in orders_replied.json.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/auto_reply_comanda.py

Cron: */30 * * * * python3 /opt/ACTIVE/INFRA/SKILLS/auto_reply_comanda.py
"""
import csv, json, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

GMAIL_EMAIL = "elena.manpower.dristor@gmail.com"
GMAIL_PASS = "wmfnpikkcierkmrq"
GMAIL_SMTP = "smtp.gmail.com"
GMAIL_PORT = 587

ORDERS_CSV = Path("/opt/ACTIVE/EMAIL/ORDERS/orders.csv")
STATE_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/orders_replied.json")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"replied": {}, "errors": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def row_id(row):
    return f"{row.get('Timestamp','')}|{row.get('Email','')}|{row.get('Denumire companie','')}"


def get_comanda_rows():
    """Read COMANDA rows from orders.csv."""
    if not ORDERS_CSV.exists():
        return []
    rows = []
    with open(ORDERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            obs = row.get("D. Observații", row.get("Observații", ""))
            if "COMANDA" in obs.upper():
                email = row.get("Email", "").strip()
                if email and "@" in email:
                    rows.append(row)
    return rows


def send_reply(to_email, company_name, contact_name):
    """Send auto-reply via Gmail SMTP."""
    name = contact_name if contact_name and contact_name != "N/A" else ""
    greeting = f"Stimate {name},\n\n" if name else "Buna ziua,\n\n"

    body = (
        f"{greeting}"
        f"Multumesc pentru raspunsul dumneavoastra"
        f"{' si interesul ' + company_name if company_name else ''}.\n\n"
        f"Va contactam in maxim 24 de ore pentru a discuta detaliile.\n\n"
        f"Cu respect,\n"
        f"Elena Seicarescu\n"
        f"InterJob - Recrutare Personal European\n"
        f"Tel: +40 799 974 158\n"
        f"Web: https://interjob.ro"
    )

    msg = MIMEMultipart()
    msg["From"] = f"Elena Seicarescu <{GMAIL_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "Re: Confirmare comanda recrutare - InterJob"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(GMAIL_SMTP, GMAIL_PORT) as server:
        server.starttls()
        server.login(GMAIL_EMAIL, GMAIL_PASS)
        server.send_message(msg)
    return True


def main():
    state = load_state()
    comandas = get_comanda_rows()
    replied = state.get("replied", {})
    new_replies = 0

    for row in comandas:
        rid = row_id(row)
        if rid in replied:
            continue

        email = row.get("Email", "").strip()
        company = row.get("Denumire companie", "").strip()
        contact = row.get("Nume persoană de contact", "").strip()

        try:
            send_reply(email, company, contact)
            replied[rid] = {
                "email": email,
                "company": company,
                "replied_at": datetime.now().isoformat(),
            }
            new_replies += 1
            print(f"REPLIED: {email} ({company})")
        except Exception as e:
            err = f"{datetime.now().isoformat()} | {email} | {e}"
            state.setdefault("errors", []).append(err)
            print(f"ERROR: {email} -> {e}")

    state["replied"] = replied
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    print(f"Done. {new_replies} new replies, {len(replied)} total replied.")


if __name__ == "__main__":
    main()
