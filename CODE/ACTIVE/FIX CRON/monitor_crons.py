#!/usr/bin/env python3
"""
Cron Monitoring System - Alerts on failures via email, Telegram, and daily digest
Deployed to raspibig: /opt/ACTIVE/INFRA/monitor_crons.py
Runs every 30 minutes to detect failures
Daily digest at 08:00 UTC
"""

import os
import sys
import json
import smtplib
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

RASPIBIG_IP = "192.168.100.21"
LOG_DIR = "/opt/ACTIVE/INFRA/LOGS"
CRON_STATUS_FILE = f"{LOG_DIR}/cron_status.json"
CRON_HISTORY_FILE = f"{LOG_DIR}/cron_history.log"

# Email config
SMTP_HOST = "127.0.0.1"
SMTP_PORT = 25
EMAIL_FROM = "monitor@raspibig.local"
EMAIL_TO = "fruitnature4@gmail.com"

# Telegram config (from environment - required)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_all_crons() -> dict:
    """Auto-detect all active crons from crontab"""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        crons = {}

        for line in result.stdout.split("\n"):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse cron line: minute hour day month weekday command
            parts = line.split(None, 5)
            if len(parts) < 6:
                continue

            minute, hour, day, month, weekday = parts[:5]
            command = " ".join(parts[5:])

            # Name = last path component of the full command line (log filename takes priority
            # over script name when >> redirect is present — matches the actual log file checked)
            cron_name = command.split("/")[-1].split(".")[0].split(" ")[0]
            # Skip duplicates (e.g. same script with two cron schedules writing same log)
            if cron_name in crons:
                continue

            # Build readable schedule
            if minute == "*" and hour == "*":
                schedule = "Every minute"
            elif minute == "*/30":
                schedule = "Every 30 min"
            elif hour == "*":
                schedule = f"Every hour at :{minute} min"
            elif day != "*":
                schedule = f"Monthly on day {day} at {hour}:{minute:0>2} UTC"
            elif weekday != "*":
                schedule = f"Specific days at {hour}:{minute:0>2}"
            else:
                schedule = f"{hour}:{minute:0>2} UTC"

            # Skip empty cron names
            if not cron_name:
                continue
            crons[cron_name] = {
                "schedule": schedule,
                "command": command,
                "line": line,
            }

        return crons
    except Exception as e:
        print(f"❌ Error reading crontab: {e}")
        return {}

def send_email(subject: str, body: str, is_alert: bool = False):
    """Send email alert"""
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg["Subject"] = f"{'🚨 ALERT' if is_alert else 'ℹ️ Report'}: {subject}"

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.send_message(msg)
        return True
    except smtplib.SMTPException as e:
        print(f"❌ Email failed (SMTP): {e}")
        return False
    except OSError as e:
        print(f"❌ Email failed (connection): {e}")
        return False

def send_telegram(message: str):
    """Send Telegram alert"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram skipped: credentials not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"❌ Telegram failed: {e}")
        return False

def check_cron_status(cron_name: str, schedule: str = "") -> bool:
    """Success = cron log updated within its expected cadence window."""
    sched = schedule.lower()
    if "hour" in sched or ":*/" in sched or "min" in sched:
        window = timedelta(hours=2, minutes=30)
    elif "monthly" in sched:
        window = timedelta(days=33)
    elif "specific days" in sched:
        window = timedelta(days=7, hours=2)
    else:
        window = timedelta(hours=26)
    log = Path(f"{LOG_DIR}/{cron_name}.log")
    if not log.exists():
        return False
    return datetime.fromtimestamp(log.stat().st_mtime) > datetime.now() - window

def monitor_crons():
    """Check all active crons and alert on failures"""
    timestamp = datetime.now().isoformat()
    failed_crons = []

    all_crons = get_all_crons()

    if not all_crons:
        print(f"[{timestamp}] No active crons found in crontab")
        return True

    print(f"[{timestamp}] Checking {len(all_crons)} crons...")

    for cron_name, cron_info in all_crons.items():
        status = check_cron_status(cron_name, cron_info.get("schedule", ""))

        if not status:
            failed_crons.append((cron_name, cron_info["schedule"]))
            print(f"  ❌ {cron_name}: FAILED ({cron_info['schedule']})")
        else:
            print(f"  ✅ {cron_name}: OK")

    os.makedirs(LOG_DIR, exist_ok=True)
    tmp = CRON_STATUS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "failed": [{"name": c[0], "schedule": c[1]} for c in failed_crons],
            "total_checked": len(all_crons),
            "total_failed": len(failed_crons),
            "all_crons": list(all_crons.keys()),
        }, f, indent=2)
    os.replace(tmp, CRON_STATUS_FILE)

    cutoff_7d = datetime.now() - timedelta(days=7)
    history_path = Path(CRON_HISTORY_FILE)
    if history_path.exists():
        lines = history_path.read_text().splitlines(keepends=True)
        lines = [l for l in lines if l[:19] >= cutoff_7d.isoformat() or l.startswith("  -")]
        history_path.write_text("".join(lines))
    with open(CRON_HISTORY_FILE, "a") as f:
        f.write(f"[{timestamp}] Failed: {len(failed_crons)}/{len(all_crons)}\n")
        for cron_name, desc in failed_crons:
            f.write(f"  - {cron_name}: {desc}\n")

    if failed_crons:
        alert_msg = f"⏰ Cron Failures ({len(failed_crons)}/{len(all_crons)} down)\n\n"
        for cron_name, schedule in failed_crons:
            alert_msg += f"❌ {cron_name}\n   Schedule: {schedule}\n"
        alert_msg += f"\nCheck: {RASPIBIG_IP}:{LOG_DIR}/cron_history.log"
        print(f"\n🚨 Alerting on {len(failed_crons)} failures...")
        send_email(f"Cron Failures ({len(failed_crons)}/{len(all_crons)})", alert_msg, is_alert=True)
        send_telegram(alert_msg)

    return len(failed_crons) == 0

def send_daily_digest():
    """Generate and send daily digest of cron status"""
    if not Path(CRON_HISTORY_FILE).exists():
        return

    with open(CRON_HISTORY_FILE, "r") as f:
        history = f.readlines()

    cutoff = datetime.now() - timedelta(hours=24)
    recent = [line for line in history if line[:19] > cutoff.isoformat()]

    digest = f"Daily Cron Report - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    digest += f"Total checks: {len(recent)}\n"
    digest += f"Period: Last 24 hours\n\n"
    digest += "".join(recent[-20:]) if recent else "No failures detected.\n"

    send_email("Daily Cron Report", digest, is_alert=False)
    send_telegram(f"📊 Daily Cron Digest:\n\n{digest[:500]}...")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--daily-digest":
        send_daily_digest()
    else:
        success = monitor_crons()
        sys.exit(0 if success else 1)
