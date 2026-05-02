#!/usr/bin/env python3
"""Zoho warmup: send daily emails to own accounts + known good recipients.
Run daily via cron. Starts at 5/day, increases +5/day, max 250/day.
"""
import smtplib, json, os, random
from email.mime.text import MIMEText
from datetime import datetime, date
from pathlib import Path

STATE_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/zoho_warmup_state.json")

ZOHO_EMAIL = "workers.europe@zohomail.eu"
ZOHO_PASS = "Mu59U3Lfa3Dw"
ZOHO_SMTP = "smtp.zoho.eu"
ZOHO_PORT = 587

# Own accounts to warm up with (guaranteed opens)
WARMUP_TARGETS = [
    "manpower.dristor@gmail.com",
    "elena.manpower.dristor@gmail.com",
    "expatsinromania@gmail.com",
    "office@interjob.ro",
    "office@buildjobs.eu",
    "office@careworkers.eu",
    "office@mivromania.info",
    "transport.work@zohomail.com",
    "office@nepalezi.com",
    "office@electricjobs.eu",
]

SUBJECTS = [
    "Status update - InterJob recruitment pipeline",
    "Weekly digest - European worker placement",
    "Team sync - Available candidates report",
    "Market update - Construction sector Romania",
    "Follow-up - Recruitment partnership progress",
    "Update - Campaign performance metrics",
    "Briefing - New employer requests this week",
    "Status - Worker availability update",
]

BODIES = [
    "Hi team,\n\nQuick update on our recruitment activities this week.\n\nBest,\nWorkers Europe Team",
    "Hello,\n\nSharing the latest status on our European placement pipeline.\n\nRegards,\nInterJob Workers Europe",
    "Team,\n\nPlease find below the weekly summary of our operations.\n\nBest regards,\nWorkers Europe",
]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"day": 0, "daily_limit": 5, "total_sent": 0, "last_date": None}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def send_warmup(target, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = ZOHO_EMAIL
    msg["To"] = target
    msg["Subject"] = subject
    try:
        s = smtplib.SMTP(ZOHO_SMTP, ZOHO_PORT)
        s.starttls()
        s.login(ZOHO_EMAIL, ZOHO_PASS)
        s.sendmail(ZOHO_EMAIL, [target], msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print(f"  FAIL {target}: {e}")
        return False

def main():
    state = load_state()
    today = str(date.today())

    if state["last_date"] == today:
        print(f"Already ran today ({state['daily_limit']} sent)")
        return

    # Increase daily limit
    if state["last_date"] and state["last_date"] != today:
        state["day"] += 1
        state["daily_limit"] = min(5 + state["day"] * 5, 250)

    limit = state["daily_limit"]
    print(f"Warmup day {state['day']}: sending {limit} emails")

    sent = 0
    targets = WARMUP_TARGETS * (limit // len(WARMUP_TARGETS) + 1)
    random.shuffle(targets)

    for target in targets[:limit]:
        subject = random.choice(SUBJECTS)
        body = random.choice(BODIES)
        if send_warmup(target, subject, body):
            sent += 1
            print(f"  OK [{sent}/{limit}] {target}")

    state["last_date"] = today
    state["total_sent"] += sent
    save_state(state)
    print(f"\nDone: {sent}/{limit} sent. Total: {state['total_sent']}")

if __name__ == "__main__":
    main()
