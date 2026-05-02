#!/usr/bin/env python3
"""Monitor orders.csv for new COMANDA entries, send Telegram alert.
Run via cron every 30 min on raspibig.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/telegram_comanda_alert.py

Cron: */30 * * * * python3 /opt/ACTIVE/INFRA/SKILLS/telegram_comanda_alert.py
"""
import csv, json, requests
from pathlib import Path
from datetime import datetime

BOT_TOKEN = "8546618948:AAG0neoQA-kNq0M2GrZX7J-dGXNvEJEOK9w"
# Get chat ID: send /start to bot, then GET https://api.telegram.org/bot<TOKEN>/getUpdates
CHAT_ID = None  # Set after first /start — or auto-detect below

ORDERS_CSV = Path("/opt/ACTIVE/EMAIL/ORDERS/orders.csv")
STATE_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/comanda_alert_state.json")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"alerted_ids": [], "chat_id": None}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def get_chat_id(state):
    """Auto-detect chat ID from recent /start messages."""
    if state.get("chat_id"):
        return state["chat_id"]
    if CHAT_ID:
        return CHAT_ID
    try:
        r = requests.get(f"{API_URL}/getUpdates", timeout=10)
        data = r.json()
        for update in reversed(data.get("result", [])):
            msg = update.get("message", {})
            if msg.get("text", "").startswith("/start"):
                cid = msg["chat"]["id"]
                state["chat_id"] = cid
                return cid
    except Exception as e:
        print(f"ERROR getting chat_id: {e}")
    return None


def read_orders():
    """Read orders.csv and return COMANDA rows."""
    if not ORDERS_CSV.exists():
        print(f"orders.csv not found at {ORDERS_CSV}")
        return []
    comandas = []
    with open(ORDERS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            obs = row.get("D. Observații", row.get("Observații", ""))
            if "COMANDA" in obs.upper():
                comandas.append(row)
    return comandas


def make_message_id(row):
    """Create unique ID for a COMANDA row."""
    company = row.get("Denumire companie", "").strip()
    email = row.get("Email", "").strip()
    ts = row.get("Timestamp", "").strip()
    return f"{ts}|{company}|{email}"


def format_alert(row):
    """Format Telegram message for a COMANDA."""
    company = row.get("Denumire companie", "N/A")
    contact = row.get("Nume persoană de contact", "N/A")
    phone = row.get("Telefon", "N/A")
    email = row.get("Email", "N/A")
    location = row.get("Localitate / Județ / Locația de lucru", "N/A")
    positions = row.get("Tip poziții", "N/A")
    count = row.get("Număr persoane necesare", "N/A")
    obs = row.get("D. Observații", row.get("Observații", ""))

    msg = (
        f"🔔 *COMANDA NOUA*\n\n"
        f"🏢 *{company}*\n"
        f"👤 Contact: {contact}\n"
        f"📞 Telefon: {phone}\n"
        f"📧 Email: {email}\n"
        f"📍 Locatie: {location}\n"
        f"💼 Pozitii: {positions}\n"
        f"👥 Nr. persoane: {count}\n"
        f"📝 {obs}"
    )
    return msg


def send_telegram(chat_id, text):
    """Send message via Telegram bot."""
    try:
        r = requests.post(
            f"{API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        return r.json().get("ok", False)
    except Exception as e:
        print(f"ERROR sending Telegram: {e}")
        return False


def main():
    state = load_state()
    chat_id = get_chat_id(state)
    if not chat_id:
        print("No chat_id found. Send /start to the bot first.")
        save_state(state)
        return

    comandas = read_orders()
    alerted = set(state.get("alerted_ids", []))
    new_count = 0

    for row in comandas:
        mid = make_message_id(row)
        if mid in alerted:
            continue
        msg = format_alert(row)
        if send_telegram(chat_id, msg):
            alerted.add(mid)
            new_count += 1
            print(f"ALERT sent: {row.get('Denumire companie', '?')}")
        else:
            print(f"FAILED to alert: {row.get('Denumire companie', '?')}")

    state["alerted_ids"] = list(alerted)
    state["chat_id"] = chat_id
    state["last_run"] = datetime.now().isoformat()
    state["last_new"] = new_count
    save_state(state)
    print(f"Done. {new_count} new alerts sent, {len(comandas)} total COMENZIs.")


if __name__ == "__main__":
    main()
