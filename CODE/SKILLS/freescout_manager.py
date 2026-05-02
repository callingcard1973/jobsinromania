#!/usr/bin/env python3
"""
FreeScout Manager Skill
Manages FreeScout helpdesk: mailboxes, conversations, auto-response.

Usage:
    python3 freescout_manager.py status
    python3 freescout_manager.py mailboxes
    python3 freescout_manager.py add-mailbox email@domain.com "Display Name"
    python3 freescout_manager.py conversations [--limit N]
    python3 freescout_manager.py fetch-emails
    python3 freescout_manager.py test-imap email@domain.com
"""

import sys
import os
import argparse
import subprocess
import pymysql
from datetime import datetime
from typing import Optional, Dict, List

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# A2 Hosting credentials
A2_PASSWORD = os.getenv('A2_EMAIL_PASSWORD', 'Romania1973')


def get_db_ip() -> str:
    """Get FreeScout DB container IP."""
    result = subprocess.run(
        ['docker', 'inspect', '-f', '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}', 'freescout-db'],
        capture_output=True, text=True
    )
    return result.stdout.strip() or '172.18.0.2'


def get_db():
    """Get FreeScout DB connection."""
    return pymysql.connect(
        host=get_db_ip(),
        user='freescout',
        password='freescout_pass_2026',
        database='freescout',
        charset='utf8mb4'
    )


def cmd_status():
    """Show FreeScout status."""
    db = get_db()
    cursor = db.cursor()

    stats = {}
    queries = {
        'mailboxes': "SELECT COUNT(*) FROM mailboxes",
        'auto_reply': "SELECT COUNT(*) FROM mailboxes WHERE auto_reply_enabled = 1",
        'conversations': "SELECT COUNT(*) FROM conversations",
        'customers': "SELECT COUNT(*) FROM customers",
        'open': "SELECT COUNT(*) FROM conversations WHERE status = 1",
        'pending': "SELECT COUNT(*) FROM conversations WHERE status = 2",
        'closed': "SELECT COUNT(*) FROM conversations WHERE status = 3",
    }

    for key, query in queries.items():
        cursor.execute(query)
        stats[key] = cursor.fetchone()[0]

    db.close()

    print(f"""
FreeScout Status
================
URL:           http://raspibig:8087
Admin:         tudor@interjob.ro / admin123

Mailboxes:     {stats['mailboxes']} ({stats['auto_reply']} with auto-reply)
Conversations: {stats['conversations']} total
  - Open:      {stats['open']}
  - Pending:   {stats['pending']}
  - Closed:    {stats['closed']}
Customers:     {stats['customers']}
""")


def cmd_mailboxes():
    """List all mailboxes."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, name, email, auto_reply_enabled,
               (SELECT COUNT(*) FROM conversations WHERE mailbox_id = mailboxes.id) as conv_count
        FROM mailboxes
        ORDER BY email
    """)

    print(f"{'ID':>3} {'Email':<40} {'Name':<25} {'AR':>2} {'Conv':>5}")
    print("-" * 80)

    for row in cursor.fetchall():
        mid, name, email, ar, conv = row
        print(f"{mid:>3} {email:<40} {name[:25]:<25} {ar:>2} {conv:>5}")

    db.close()


def cmd_add_mailbox(email: str, name: str, enable_auto_reply: bool = True):
    """Add a new mailbox."""
    domain = email.split('@')[1]
    db = get_db()
    cursor = db.cursor()

    # Check if exists
    cursor.execute("SELECT id FROM mailboxes WHERE email = %s", (email,))
    if cursor.fetchone():
        print(f"Mailbox {email} already exists")
        db.close()
        return

    # Auto-reply template
    ar_subject = "Re: {%subject%} [#{%conversation_number%}]"
    ar_message = """Buna ziua,

Mesajul dumneavoastra a fost primit si inregistrat cu numarul #{%conversation_number%}.

Vom raspunde in cel mai scurt timp posibil.

---
{%mailbox.name%}
"""

    is_system = any(x in email for x in ['dmarc', 'noreply', 'unsubscribe'])
    auto_reply = 0 if is_system else (1 if enable_auto_reply else 0)

    cursor.execute("""
        INSERT INTO mailboxes (
            name, email,
            in_server, in_port, in_username, in_password, in_protocol, in_encryption, in_validate_cert,
            out_method,
            auto_reply_enabled, auto_reply_subject, auto_reply_message,
            from_name, ticket_status, ticket_assignee, template,
            created_at, updated_at
        ) VALUES (
            %s, %s,
            %s, 993, %s, %s, 1, 1, 1,
            1,
            %s, %s, %s,
            1, 2, 2, 1,
            NOW(), NOW()
        )
    """, (
        name[:40], email,
        f"mail.{domain}", email, A2_PASSWORD,
        auto_reply, ar_subject if auto_reply else None, ar_message if auto_reply else None
    ))

    db.commit()
    print(f"Added mailbox: {email} (ID: {cursor.lastrowid})")
    db.close()


def cmd_conversations(limit: int = 20):
    """List recent conversations."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT c.id, c.number, c.subject, c.status, c.customer_email, m.email as mailbox,
               c.created_at
        FROM conversations c
        LEFT JOIN mailboxes m ON c.mailbox_id = m.id
        ORDER BY c.created_at DESC
        LIMIT %s
    """, (limit,))

    status_map = {1: 'Open', 2: 'Pending', 3: 'Closed'}

    print(f"{'#':>5} {'Subject':<35} {'Status':<8} {'Customer':<25}")
    print("-" * 80)

    for row in cursor.fetchall():
        cid, num, subj, status, cust, mbox, created = row
        subj_short = (subj[:32] + '...') if subj and len(subj) > 35 else (subj or 'No subject')
        cust_short = (cust[:22] + '...') if cust and len(cust) > 25 else (cust or 'Unknown')
        print(f"{num:>5} {subj_short:<35} {status_map.get(status, '?'):<8} {cust_short:<25}")

    db.close()


def cmd_test_imap(email: str):
    """Test IMAP connection for a mailbox."""
    import imaplib

    domain = email.split('@')[1]
    server = f"mail.{domain}"

    print(f"Testing IMAP connection to {server}...")

    try:
        imap = imaplib.IMAP4_SSL(server, 993)
        imap.login(email, A2_PASSWORD)
        imap.select('INBOX')
        status, msgs = imap.search(None, 'UNSEEN')
        unread = len(msgs[0].split()) if msgs[0] else 0
        print(f"Success: {unread} unread emails")
        imap.logout()
    except Exception as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="FreeScout Manager")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    subparsers.add_parser('status', help='Show status')
    subparsers.add_parser('mailboxes', help='List mailboxes')

    add_mb = subparsers.add_parser('add-mailbox', help='Add mailbox')
    add_mb.add_argument('email', help='Email address')
    add_mb.add_argument('name', help='Display name')
    add_mb.add_argument('--no-auto-reply', action='store_true')

    conv = subparsers.add_parser('conversations', help='List conversations')
    conv.add_argument('--limit', type=int, default=20)

    test = subparsers.add_parser('test-imap', help='Test IMAP connection')
    test.add_argument('email', help='Email to test')

    args = parser.parse_args()

    if args.command == 'status':
        cmd_status()
    elif args.command == 'mailboxes':
        cmd_mailboxes()
    elif args.command == 'add-mailbox':
        cmd_add_mailbox(args.email, args.name, not args.no_auto_reply)
    elif args.command == 'conversations':
        cmd_conversations(args.limit)
    elif args.command == 'test-imap':
        cmd_test_imap(args.email)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
