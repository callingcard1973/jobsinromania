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
            command = parts[5]

            # Extract cron name from command (e.g., press_review.py -> press_review)
            cron_name = command.split("/")[-1].split(".")[0]

            # Build readable schedule
            if minute == "*" and hour == "*":
                schedule = "Every minute"
            elif minute == "*/30":
                schedule = "Every 30 min"
            elif hour == "*":
                schedule = f"Every hour at :{minute} min"
            elif weekday != "*":
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                schedule = f"Specific days at {hour}:{minute:0>2}"
            else:
                schedule = f"{hour}:{minute:0>2} UTC"

            crons[cron_name] = {
                "schedule": schedule,
                "command": command,
                "line": line,
            }

        return crons
    except Exception as e:
        print(f"[ERROR] Error reading crontab: {e}")
        return {}

def send_email(subject: str, body: str, is_alert: bool = False):
    """Send email alert"""
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg["Subject"] = f"{'[ALERT]' if is_alert else '[REPORT]'}: {subject}"

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.send_message(msg)
        return True
    except smtplib.SMTPException as e:
        print(f"[FAIL] Email failed (SMTP): {e}")
        return False
    except OSError as e:
        print(f"[FAIL] Email failed (connection): {e}")
        return False

def send_telegram(message: str):
    """Send Telegram alert"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Telegram skipped: credentials not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"[FAIL] Telegram failed: {e}")
        return False

def check_cron_status(cron_name: str) -> bool:
    """Check if a cron ran successfully in last 90 minutes via syslog"""
    try:
        cutoff_time = datetime.now() - timedelta(minutes=90)
        syslog = Path("/var/log/syslog")

        if not syslog.exists():
            return False  # Can't verify; assume OK rather than flood alerts

        # Read last 2000 lines only (avoids full-file scan of large syslog)
        result = subprocess.run(
            ["tail", "-n", "2000", str(syslog)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Debian cron logs: Jun  8 09:30:01 raspibig CRON[12345]: (tudor) CMD (...)
        for line in result.stdout.splitlines():
            if "CRON" in line and cron_name in line:
                # Parse syslog timestamp: "Jun  8 09:30:01"
                try:
                    line_time = datetime.strptime(
                        f"{datetime.now().year} {line[:15]}", "%Y %b %d %H:%M:%S"
                    )
                    if line_time > cutoff_time:
                        return True
                except ValueError:
                    pass

        return False
    except subprocess.TimeoutExpired:
        print(f"⚠️  Timeout checking {cron_name}")
        return False
    except OSError as e:
        print(f"⚠️  Error checking {cron_name}: {e}")
        return False

def rotate_history_if_needed():
    """Keep history file under 5 MB - rotates on each run if needed"""
    path = Path(CRON_HISTORY_FILE)
    max_bytes = 5 * 1024 * 1024  # 5 MB
    if path.exists() and path.stat().st_size > max_bytes:
        archive = path.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        path.rename(archive)
        # Keep only last 7 archives
        archives = sorted(path.parent.glob("cron_history.*.log"))
        for old in archives[:-7]:
            old.unlink()

def monitor_crons():
    """Check all active crons and alert on failures"""
    timestamp = datetime.now().isoformat()
    failed_crons = []

    # Rotate history log if needed
    rotate_history_if_needed()

    # Auto-detect all crons from crontab
    all_crons = get_all_crons()

    if not all_crons:
        print(f"[{timestamp}] No active crons found in crontab")
        return True

    print(f"[{timestamp}] Checking {len(all_crons)} crons...")

    for cron_name, cron_info in all_crons.items():
        status = check_cron_status(cron_name)

        if not status:
            failed_crons.append((cron_name, cron_info["schedule"]))
            print(f"  ❌ {cron_name}: FAILED ({cron_info['schedule']})")
        else:
            print(f"  ✅ {cron_name}: OK")

    # Log status
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(CRON_STATUS_FILE, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "failed": [{"name": c[0], "schedule": c[1]} for c in failed_crons],
            "total_checked": len(all_crons),
            "total_failed": len(failed_crons),
            "all_crons": list(all_crons.keys()),
        }, f, indent=2)

    # Append to history
    with open(CRON_HISTORY_FILE, "a") as f:
        f.write(f"[{timestamp}] Failed: {len(failed_crons)}/{len(all_crons)}\n")
        for cron_name, desc in failed_crons:
            f.write(f"  - {cron_name}: {desc}\n")

    # Alert on failures
    if failed_crons:
        alert_msg = f"[CRON FAILURES] ({len(failed_crons)}/{len(all_crons)} down)\n\n"
        for cron_name, schedule in failed_crons:
            alert_msg += f"[FAIL] {cron_name}\n   Schedule: {schedule}\n"
        alert_msg += f"\nCheck: {RASPIBIG_IP}:{LOG_DIR}/cron_history.log"

        # Send alerts
        print(f"\n🚨 Alerting on {len(failed_crons)} failures...")
        send_email(f"Cron Failures ({len(failed_crons)}/{len(all_crons)})", alert_msg, is_alert=True)
        send_telegram(alert_msg)

    return len(failed_crons) == 0

def send_daily_digest():
    """Generate and send daily digest of cron status"""
    timestamp = datetime.now().isoformat()

    if not Path(CRON_HISTORY_FILE).exists():
        return

    with open(CRON_HISTORY_FILE, "r") as f:
        history = f.readlines()

    # Summarize last 24 hours
    cutoff = datetime.now() - timedelta(hours=24)
    recent = [line for line in history if line[:19] > cutoff.isoformat()]

    digest = f"Daily Cron Report - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    digest += f"Total checks: {len(recent)}\n"
    digest += f"Period: Last 24 hours\n\n"
    digest += f"Details:\n"
    digest += "".join(recent[-20:]) if recent else "No failures detected.\n"

    send_email("Daily Cron Report", digest, is_alert=False)
    send_telegram(f"📊 Daily Cron Digest:\n\n{digest[:500]}...")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--daily-digest":
        send_daily_digest()
    else:
        success = monitor_crons()
        sys.exit(0 if success else 1)
