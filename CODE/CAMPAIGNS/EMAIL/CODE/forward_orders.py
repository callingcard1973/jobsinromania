#!/usr/bin/env python3
"""Forward extracted orders to solonet.vacancy@gmail.com with CC to owner.
Reads orders.csv, formats each order as email, sends via Gmail SMTP.
[AI: Claude Code]

Usage:
    python3 forward_orders.py --preview       # Show what would be sent
    python3 forward_orders.py --send          # Actually send
    python3 forward_orders.py --send --id 3   # Send specific row only
"""
import csv, json, smtplib, sys, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

DIR = Path(__file__).parent
CSV_F = DIR / "orders.csv"
SENT_F = DIR / "orders_sent.json"
LOG_F = DIR / "orders_forward.log"

# Config
TO = "solonet.vacancy@gmail.com"
CC = "manpower.dristor@gmail.com"
FROM_EMAIL = "manpower.dristor@gmail.com"
FROM_PASS = "tbdh pycf vbxo eung"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 587

# Skip these in Observatii
SKIP_NOTES = ["NU ESTE COMANDA", "SKIP", "REGEX FALLBACK"]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_F, "a", encoding="utf-8") as f: f.write(line + "\n")

def load_sent():
    if SENT_F.exists():
        return json.loads(SENT_F.read_text(encoding="utf-8"))
    return {"sent": []}

def save_sent(state):
    SENT_F.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def load_orders():
    if not CSV_F.exists():
        log("No orders.csv found"); return []
    rows = []
    with open(CSV_F, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            row["_row_id"] = i + 1
            rows.append(row)
    return rows

def should_skip(row):
    obs = (row.get("Observații", "") or "").upper()
    return any(s in obs for s in SKIP_NOTES)

def format_email(row):
    """Format order as readable email body."""
    fields = [
        ("Companie", row.get("Denumire companie", "")),
        ("Persoana contact", row.get("Nume persoană de contact", "")),
        ("Functie", row.get("Funcție (HR / Admin / Manager etc.)", "")),
        ("Localitate", row.get("Localitate / Județ / Locația de lucru", "")),
        ("Telefon", row.get("Telefon", "")),
        ("Email", row.get("Email", "")),
        ("Nr persoane", row.get("Număr persoane necesare", "")),
        ("Tip pozitii", row.get("Tip poziții", "")),
        ("Gen preferat", row.get("Gen preferat", "")),
        ("Tip contract", row.get("Tip contract", "")),
        ("Cand incepe", row.get("Când doriți să înceapă?", "")),
        ("Cazare", row.get("Condiții cazare", "")),
        ("Salariu", row.get("Salariu / beneficii", "")),
        ("Observatii", row.get("Observații", "")),
        ("Sursa email", row.get("From Email", "")),
    ]
    lines = []
    for label, val in fields:
        if val and val.strip():
            lines.append(f"{label}: {val}")
    body = "\n".join(lines)
    company = row.get("Denumire companie", "") or row.get("From Email", "")
    obs = row.get("Observații", "")
    # Extract classification tag [COMANDA] / [INTERESAT] / [PARTENER]
    tag_m = __import__("re").search(r"\[(COMANDA|INTERESAT|PARTENER|DE VERIFICAT)\]", obs)
    tag = tag_m.group(1) if tag_m else "CERERE"
    subject = f"[{tag}] {company}" if company else f"[{tag}] Cerere personal noua"
    return subject, body

def send_email(subject, body, smtp=None):
    """Send one email. Returns True on success."""
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO
    msg["Cc"] = CC
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        if smtp is None:
            smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            smtp.starttls()
            smtp.login(FROM_EMAIL, FROM_PASS)
            smtp.sendmail(FROM_EMAIL, [TO, CC], msg.as_string())
            smtp.quit()
        else:
            smtp.sendmail(FROM_EMAIL, [TO, CC], msg.as_string())
        return True
    except Exception as e:
        log(f"  SMTP error: {e}")
        return False

def main():
    preview = "--preview" in sys.argv
    send = "--send" in sys.argv
    row_id = None
    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        row_id = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else None

    if not preview and not send:
        print("Usage: python3 forward_orders.py --preview | --send [--id N]")
        return

    orders = load_orders()
    state = load_sent()
    sent_ids = set(state["sent"])

    valid = [r for r in orders if not should_skip(r)]
    log(f"Orders: {len(orders)} total, {len(valid)} valid, {len(sent_ids)} already sent")

    smtp = None
    if send:
        try:
            smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            smtp.starttls()
            smtp.login(FROM_EMAIL, FROM_PASS)
            log("SMTP connected")
        except Exception as e:
            log(f"SMTP login failed: {e}"); return

    count = 0
    for row in valid:
        rid = str(row["_row_id"])
        if row_id and int(rid) != row_id: continue
        if rid in sent_ids and not row_id: continue
        subject, body = format_email(row)
        if preview:
            log(f"  [PREVIEW] Row {rid}: {subject}")
            print(f"---\nTo: {TO}\nCc: {CC}\nSubject: {subject}\n\n{body}\n")
        elif send:
            ok = send_email(subject, body, smtp)
            if ok:
                state["sent"].append(rid)
                count += 1
                log(f"  SENT Row {rid}: {subject}")
            else:
                log(f"  FAILED Row {rid}: {subject}")

    if send and smtp:
        smtp.quit()
        save_sent(state)
    log(f"Done. {'Previewed' if preview else 'Sent'} {count} orders.")

if __name__ == "__main__":
    main()
