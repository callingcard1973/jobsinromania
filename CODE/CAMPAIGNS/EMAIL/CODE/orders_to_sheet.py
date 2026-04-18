#!/usr/bin/env python3
"""Read orders.csv, format as HTML table, create Gmail draft to
expatsinromania@gmail.com with the table.
Uses fruitnature4@gmail.com IMAP to create draft.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/orders_to_sheet.py
"""
import csv, json, imaplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, date

GMAIL_EMAIL = "fruitnature4@gmail.com"
GMAIL_PASS = "mosv ghia ptwc xasr"
IMAP_SERVER = "imap.gmail.com"

TO_EMAIL = "expatsinromania@gmail.com"
ORDERS_CSV = Path("/opt/ACTIVE/EMAIL/ORDERS/orders.csv")
STATE_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/orders_sheet_state.json")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"drafts_created": [], "last_rows_hash": ""}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def read_orders():
    """Read orders.csv and return rows."""
    if not ORDERS_CSV.exists():
        print(f"orders.csv not found at {ORDERS_CSV}")
        return [], []
    with open(ORDERS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def make_html_table(headers, rows):
    """Format orders as styled HTML table."""
    # Select key columns for readability
    key_cols = [
        "Timestamp", "Denumire companie", "Nume persoană de contact",
        "Telefon", "Email", "Localitate / Județ / Locația de lucru",
        "Tip poziții", "Număr persoane necesare", "D. Observații",
    ]
    # Use key cols if available, else all headers
    display_cols = [c for c in key_cols if c in headers] or headers

    style = """
    <style>
      table { border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 12px; }
      th { background: #2c3e50; color: white; padding: 8px 6px; text-align: left; }
      td { padding: 6px; border: 1px solid #ddd; }
      tr:nth-child(even) { background: #f8f9fa; }
      tr:hover { background: #e8f4f8; }
      .comanda { background: #d4edda !important; font-weight: bold; }
      .interesat { background: #fff3cd !important; }
      .partener { background: #cce5ff !important; }
      h2 { color: #2c3e50; }
      .stats { margin-bottom: 15px; color: #555; }
    </style>
    """

    # Count stats
    comanda = sum(1 for r in rows if "COMANDA" in r.get("D. Observații", "").upper())
    interesat = sum(1 for r in rows if "INTERESAT" in r.get("D. Observații", "").upper())
    partener = sum(1 for r in rows if "PARTENER" in r.get("D. Observații", "").upper())

    html = f"""{style}
    <h2>InterJob Orders Report - {date.today().isoformat()}</h2>
    <div class="stats">
      Total: {len(rows)} | COMENZI: {comanda} | INTERESATI: {interesat} | PARTENERI: {partener}
    </div>
    <table>
    <tr>{''.join(f'<th>{c}</th>' for c in display_cols)}</tr>
    """

    for row in rows:
        obs = row.get("D. Observații", "").upper()
        cls = ""
        if "COMANDA" in obs:
            cls = ' class="comanda"'
        elif "INTERESAT" in obs:
            cls = ' class="interesat"'
        elif "PARTENER" in obs:
            cls = ' class="partener"'

        cells = "".join(f"<td>{row.get(c, '')}</td>" for c in display_cols)
        html += f"<tr{cls}>{cells}</tr>\n"

    html += "</table>"
    return html


def rows_hash(rows):
    """Simple hash of row count + last row to detect changes."""
    if not rows:
        return "empty"
    last = rows[-1]
    return f"{len(rows)}|{last.get('Email', '')}|{last.get('Timestamp', '')}"


def create_gmail_draft(subject, html_body):
    """Create a draft in Gmail via IMAP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = subject

    # Plain text fallback
    plain = "See HTML version for the orders table."
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Connect via IMAP and save to Drafts
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(GMAIL_EMAIL, GMAIL_PASS)

    # Gmail uses [Gmail]/Drafts
    draft_folder = "[Gmail]/Drafts"
    imap.select(draft_folder)

    raw = msg.as_bytes()
    imap.append(draft_folder, "\\Draft", None, raw)
    imap.logout()
    return True


def main():
    state = load_state()
    headers, rows = read_orders()

    if not rows:
        print("No orders found.")
        return

    # Check if data changed since last draft
    current_hash = rows_hash(rows)
    if current_hash == state.get("last_rows_hash", ""):
        print("No new orders since last draft. Skipping.")
        return

    # Build HTML table
    html = make_html_table(headers, rows)

    # Create draft
    subject = f"InterJob Orders Report - {date.today().isoformat()} ({len(rows)} entries)"
    try:
        create_gmail_draft(subject, html)
        state["last_rows_hash"] = current_hash
        state["drafts_created"].append({
            "date": datetime.now().isoformat(),
            "rows": len(rows),
            "subject": subject,
        })
        # Keep only last 50 draft records
        state["drafts_created"] = state["drafts_created"][-50:]
        save_state(state)
        print(f"Draft created: {subject}")
        print(f"  Rows: {len(rows)}, To: {TO_EMAIL}")
    except Exception as e:
        print(f"ERROR creating draft: {e}")


if __name__ == "__main__":
    main()
