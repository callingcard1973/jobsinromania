#!/usr/bin/env python3
"""
FreeScout Unread Alerts - Telegram notifications for unread conversations.
[AI: Claude Code]

Usage:
    python3 freescout_alerts.py                    # Check and alert
    python3 freescout_alerts.py --status           # Show unread count
    python3 freescout_alerts.py --list             # List unread conversations
    python3 freescout_alerts.py --test             # Send test alert
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import argparse
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# FreeScout config
FREESCOUT_URL = "http://localhost:8087"
FREESCOUT_DB_HOST = "localhost"
FREESCOUT_DB_NAME = "freescout"
FREESCOUT_DB_USER = "freescout"
FREESCOUT_DB_PASS = "freescout_pass_2026"
FREESCOUT_DB_PORT = 3307  # Docker mapped port

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '547047851')

# Alert thresholds
ALERT_IF_UNREAD_OVER = 0  # Alert if any unread
ALERT_IF_OLDEST_HOURS = 4  # Alert if oldest unread > 4 hours


def get_unread_conversations() -> List[Dict]:
    """Get unread conversations from FreeScout database."""
    try:
        import pymysql
        conn = pymysql.connect(
            host=FREESCOUT_DB_HOST,
            port=FREESCOUT_DB_PORT,
            user=FREESCOUT_DB_USER,
            password=FREESCOUT_DB_PASS,
            database=FREESCOUT_DB_NAME,
            charset='utf8mb4'
        )

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Get unread conversations (status=1 is active, user_updated_at is last customer reply)
        query = """
            SELECT
                c.id,
                c.number,
                c.subject,
                c.customer_email,
                c.created_at,
                c.user_updated_at,
                c.status,
                m.name as mailbox_name,
                m.email as mailbox_email
            FROM conversations c
            JOIN mailboxes m ON c.mailbox_id = m.id
            WHERE c.status = 1
              AND c.state = 1
              AND c.read_by_user IS NULL
            ORDER BY c.user_updated_at DESC
            LIMIT 50
        """

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return rows

    except ImportError:
        print("pymysql not installed, trying docker exec...")
        return get_unread_via_docker()
    except Exception as e:
        print(f"Database error: {e}")
        return get_unread_via_docker()


def get_unread_via_docker() -> List[Dict]:
    """Get unread conversations via docker exec."""
    import subprocess

    query = """
        SELECT
            c.id,
            c.number,
            SUBSTRING(c.subject, 1, 50) as subject,
            c.customer_email,
            c.created_at,
            c.user_updated_at,
            m.email as mailbox_email
        FROM conversations c
        JOIN mailboxes m ON c.mailbox_id = m.id
        WHERE c.status = 1
          AND c.state = 1
          AND (c.user_id IS NULL OR c.read_by_user IS NULL)
        ORDER BY c.user_updated_at DESC
        LIMIT 50;
    """

    cmd = f'docker exec freescout-db mariadb -u{FREESCOUT_DB_USER} -p{FREESCOUT_DB_PASS} {FREESCOUT_DB_NAME} -N -e "{query}"'

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Docker error: {result.stderr}")
            return []

        rows = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 7:
                    rows.append({
                        'id': parts[0],
                        'number': parts[1],
                        'subject': parts[2],
                        'customer_email': parts[3],
                        'created_at': parts[4],
                        'user_updated_at': parts[5],
                        'mailbox_email': parts[6]
                    })
        return rows
    except Exception as e:
        print(f"Docker exec error: {e}")
        return []


def send_telegram_alert(message: str) -> bool:
    """Send alert to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("No TELEGRAM_BOT_TOKEN configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        r = requests.post(url, data=data, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def format_alert_message(conversations: List[Dict]) -> str:
    """Format alert message for Telegram."""
    count = len(conversations)

    msg = f"📬 <b>FreeScout: {count} Unread Conversation{'s' if count != 1 else ''}</b>\n\n"

    for i, c in enumerate(conversations[:10], 1):
        mailbox = c.get('mailbox_email', '').split('@')[0] if c.get('mailbox_email') else '?'
        subject = c.get('subject', 'No subject')[:40]
        customer = c.get('customer_email', '?')[:30]
        number = c.get('number', '?')

        msg += f"{i}. <b>#{number}</b> [{mailbox}]\n"
        msg += f"   {subject}\n"
        msg += f"   From: {customer}\n\n"

    if count > 10:
        msg += f"<i>... and {count - 10} more</i>\n\n"

    msg += f"🔗 <a href='http://raspibig:8087/'>Open FreeScout</a>"

    return msg


def check_and_alert(force: bool = False) -> Dict:
    """Check for unread conversations and send alert if needed."""
    conversations = get_unread_conversations()
    count = len(conversations)

    result = {
        'unread_count': count,
        'alerted': False,
        'conversations': conversations
    }

    if count > ALERT_IF_UNREAD_OVER or force:
        if conversations:
            msg = format_alert_message(conversations)
            if send_telegram_alert(msg):
                result['alerted'] = True
                print(f"Alert sent: {count} unread conversations")
            else:
                print("Failed to send alert")
        elif force:
            send_telegram_alert("✅ FreeScout: No unread conversations")
            result['alerted'] = True
    else:
        print(f"No alert needed: {count} unread (threshold: >{ALERT_IF_UNREAD_OVER})")

    return result


def print_status():
    """Print current unread status."""
    conversations = get_unread_conversations()
    count = len(conversations)

    print(f"\n=== FreeScout Unread Status ===")
    print(f"Unread conversations: {count}")
    print(f"Alert threshold: >{ALERT_IF_UNREAD_OVER}")
    print(f"FreeScout URL: {FREESCOUT_URL}")

    if conversations:
        print(f"\nOldest unread:")
        c = conversations[-1] if conversations else None
        if c:
            print(f"  #{c.get('number')} - {c.get('subject', '')[:50]}")
            print(f"  From: {c.get('customer_email')}")
            print(f"  Date: {c.get('user_updated_at') or c.get('created_at')}")


def print_list():
    """Print list of unread conversations."""
    conversations = get_unread_conversations()

    print(f"\n=== Unread Conversations ({len(conversations)}) ===\n")

    for c in conversations:
        number = c.get('number', '?')
        subject = c.get('subject', 'No subject')[:50]
        customer = c.get('customer_email', '?')
        mailbox = c.get('mailbox_email', '?')
        date = c.get('user_updated_at') or c.get('created_at')

        print(f"#{number} [{mailbox}]")
        print(f"  Subject: {subject}")
        print(f"  From: {customer}")
        print(f"  Date: {date}")
        print()


def main():
    parser = argparse.ArgumentParser(description='FreeScout Unread Alerts')
    parser.add_argument('--status', action='store_true', help='Show unread status')
    parser.add_argument('--list', action='store_true', help='List unread conversations')
    parser.add_argument('--test', action='store_true', help='Send test alert')
    parser.add_argument('--force', action='store_true', help='Force send alert even if no unread')
    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.list:
        print_list()
    elif args.test:
        send_telegram_alert("🧪 FreeScout Alert Test - Working!")
        print("Test alert sent")
    else:
        result = check_and_alert(force=args.force)
        if not args.force:
            print(f"Unread: {result['unread_count']}, Alerted: {result['alerted']}")


if __name__ == '__main__':
    main()
