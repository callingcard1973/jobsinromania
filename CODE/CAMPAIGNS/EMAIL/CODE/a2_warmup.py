#!/usr/bin/env python3
"""Warmup script for A2 SMTP domains. Send test emails to own accounts.
Start 5/day, +5/day, max 50/day. State in a2_warmup_state.json.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/a2_warmup.py

Cron: 0 9 * * * python3 /opt/ACTIVE/INFRA/SKILLS/a2_warmup.py
"""
import smtplib, json, random
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime, date

STATE_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/a2_warmup_state.json")

A2_SMTP = "nl1-cl8-ats1.a2hosting.com"
A2_PORT = 465  # SSL

# A2 domain senders to warm up
A2_SENDERS = [
    {"email": "office@interjob.ro", "password": ""},      # Fill from .env
    {"email": "office@buildjobs.eu", "password": ""},
    {"email": "office@careworkers.eu", "password": ""},
    {"email": "office@electricjobs.eu", "password": ""},
    {"email": "office@factoryjobs.eu", "password": ""},
    {"email": "office@farmworkers.eu", "password": ""},
    {"email": "office@horecaworkers.eu", "password": ""},
    {"email": "office@mechanicjobs.eu", "password": ""},
    {"email": "office@warehouseworkers.eu", "password": ""},
]

# Load passwords from .env if available
ENV_FILE = Path("/opt/EMAIL/CAMPAIGNS/.env")
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            # Match A2_PASS_domain format
            for s in A2_SENDERS:
                dom = s["email"].split("@")[1].replace(".", "_")
                if k.strip() == f"A2_PASS_{dom}":
                    s["password"] = v.strip().strip('"')

# Recipients (own accounts, guaranteed opens)
WARMUP_TARGETS = [
    "manpower.dristor@gmail.com",
    "elena.manpower.dristor@gmail.com",
    "expatsinromania@gmail.com",
    "transport.work@zohomail.com",
    "workers.europe@zohomail.eu",
]

SUBJECTS = [
    "InterJob - Weekly Recruitment Update",
    "Team Sync - Available Candidates Report",
    "Market Update - European Construction Sector",
    "Status - Worker Placement Pipeline",
    "Follow-up - Partnership Discussion",
    "Briefing - New Employer Inquiries",
]

BODIES = [
    "Hi team,\n\nQuick update on our ongoing recruitment activities.\n\nBest,\nInterJob Team",
    "Hello,\n\nSharing the latest pipeline status.\n\nRegards,\nInterJob Recruitment",
    "Team,\n\nWeekly summary attached.\n\nBest regards,\nInterJob Operations",
]

INCREASE_PER_DAY = 5
START_LIMIT = 5
MAX_LIMIT = 50


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"day": 0, "history": {}, "senders": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_daily_limit(state):
    today = date.today().isoformat()
    history = state.get("history", {})
    days_active = len(history)
    limit = min(START_LIMIT + days_active * INCREASE_PER_DAY, MAX_LIMIT)
    return limit


def send_warmup_email(sender_email, sender_pass, to_email):
    """Send a single warmup email via A2 SMTP SSL."""
    msg = MIMEText(random.choice(BODIES), "plain", "utf-8")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = random.choice(SUBJECTS)

    with smtplib.SMTP_SSL(A2_SMTP, A2_PORT) as server:
        server.login(sender_email, sender_pass)
        server.send_message(msg)
    return True


def main():
    state = load_state()
    today = date.today().isoformat()

    if today in state.get("history", {}):
        print(f"Already ran today ({today}). Skipping.")
        return

    limit = get_daily_limit(state)
    print(f"A2 Warmup Day {len(state.get('history', {})) + 1}: limit={limit}/sender")

    active_senders = [s for s in A2_SENDERS if s["password"]]
    if not active_senders:
        print("ERROR: No sender passwords configured. Set A2_PASS_domain in .env")
        return

    total_sent = 0
    day_stats = {}

    for sender in active_senders:
        sent = 0
        targets = WARMUP_TARGETS.copy()
        random.shuffle(targets)

        for target in targets:
            if sent >= limit:
                break
            try:
                send_warmup_email(sender["email"], sender["password"], target)
                sent += 1
                total_sent += 1
                print(f"  {sender['email']} -> {target} OK")
            except Exception as e:
                print(f"  {sender['email']} -> {target} FAIL: {e}")

        day_stats[sender["email"]] = sent
        state.setdefault("senders", {})[sender["email"]] = {
            "total_sent": state.get("senders", {}).get(sender["email"], {}).get("total_sent", 0) + sent,
            "last_sent": today,
        }

    state.setdefault("history", {})[today] = {
        "limit": limit,
        "sent": total_sent,
        "by_sender": day_stats,
    }
    save_state(state)
    print(f"Done. Sent {total_sent} warmup emails (limit {limit}/sender, "
          f"{len(active_senders)} senders).")


if __name__ == "__main__":
    main()
