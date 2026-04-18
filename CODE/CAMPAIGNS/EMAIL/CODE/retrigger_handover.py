#!/usr/bin/env python3
"""Read handovers.csv, find new contacts, add to campaign contact list for re-sending.
Marks processed in handovers_processed.json.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/retrigger_handover.py
"""
import csv, json
from pathlib import Path
from datetime import datetime

HANDOVERS_CSV = Path("/opt/ACTIVE/EMAIL/ORDERS/handovers.csv")
STATE_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/handovers_processed.json")
CONTACT_LIST = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/retrigger_contacts.csv")

# Campaign config directory for sector-based routing
CAMPAIGN_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed": {}, "stats": {"total": 0, "added": 0}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def read_handovers():
    """Read handovers.csv and return rows with valid emails."""
    if not HANDOVERS_CSV.exists():
        print(f"handovers.csv not found at {HANDOVERS_CSV}")
        return []
    rows = []
    with open(HANDOVERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = row.get("Email", row.get("email", "")).strip().lower()
            if email and "@" in email:
                row["_email"] = email
                rows.append(row)
    return rows


def load_existing_contacts():
    """Load already-queued retrigger contacts."""
    if not CONTACT_LIST.exists():
        return set()
    existing = set()
    with open(CONTACT_LIST, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing.add(row.get("email", "").strip().lower())
    return existing


def append_contact(row):
    """Append a contact to the retrigger CSV."""
    write_header = not CONTACT_LIST.exists()
    fields = ["email", "name", "company", "phone", "source", "added_at"]
    with open(CONTACT_LIST, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "email": row["_email"],
            "name": row.get("Name", row.get("name", "")),
            "company": row.get("Company", row.get("company", "")),
            "phone": row.get("Phone", row.get("phone", "")),
            "source": "handover_retrigger",
            "added_at": datetime.now().isoformat(),
        })


def make_id(row):
    ts = row.get("Timestamp", row.get("timestamp", ""))
    return f"{ts}|{row['_email']}"


def main():
    state = load_state()
    processed = state.get("processed", {})
    existing = load_existing_contacts()

    handovers = read_handovers()
    new_count = 0

    for row in handovers:
        hid = make_id(row)
        if hid in processed:
            continue

        email = row["_email"]
        if email in existing:
            processed[hid] = {"email": email, "status": "already_in_list",
                              "at": datetime.now().isoformat()}
            continue

        append_contact(row)
        existing.add(email)
        processed[hid] = {"email": email, "status": "added",
                          "at": datetime.now().isoformat()}
        new_count += 1
        print(f"ADDED: {email} ({row.get('Company', row.get('company', '?'))})")

    state["processed"] = processed
    state["stats"]["total"] = len(processed)
    state["stats"]["added"] += new_count
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    print(f"Done. {new_count} new contacts added, {len(processed)} total processed.")


if __name__ == "__main__":
    main()
