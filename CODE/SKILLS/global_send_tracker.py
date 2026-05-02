#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Global Send Tracker v2 -- PostgreSQL-backed cross-campaign dedup.

Usage as module:
    from global_send_tracker import was_recently_sent, log_send
    if was_recently_sent(email, days=14):
        skip...
    log_send(email, 'CAMPAIGN_NAME', 'sender@example.com')

Usage as CLI:
    python3 global_send_tracker.py --stats
    python3 global_send_tracker.py --check user@example.com
"""
import os
import sys
import argparse
from datetime import date, timedelta

import psycopg2

DB_CFG = {
    'host': 'localhost',
    'dbname': 'email_sender',
    'user': 'tudor',
    'password': 'tudor',
}

_conn = None

def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(**DB_CFG)
        _conn.autocommit = True
    return _conn


def was_recently_sent(email, days=14):
    """Check if email was sent by ANY campaign in last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM global_sends WHERE LOWER(email) = LOWER(%s) AND sent_date >= %s LIMIT 1",
        (email.strip(), cutoff)
    )
    return cur.fetchone() is not None


def get_send_info(email, days=14):
    """Get most recent send info for an email."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT sent_date, campaign, sender FROM global_sends WHERE LOWER(email) = LOWER(%s) AND sent_date >= %s ORDER BY sent_date DESC LIMIT 1",
        (email.strip(), cutoff)
    )
    row = cur.fetchone()
    if row:
        return {'date': str(row[0]), 'campaign': row[1], 'sender': row[2]}
    return None


def log_send(email, campaign, sender):
    """Log a send to the global tracker."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO global_sends (email, campaign, sender, sent_date)
        VALUES (LOWER(%s), %s, %s, CURRENT_DATE)
        ON CONFLICT (LOWER(email), campaign)
        DO UPDATE SET sent_date = CURRENT_DATE, sender = EXCLUDED.sender
    """, (email.strip(), campaign, sender))



def ab_report(days=30):
    """Show A/B template performance by campaign/sector."""
    conn = _get_conn()
    cur = conn.cursor()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    # Join send_logs with reply data
    for db_name, log_table in [('norway_emails', 'norway_send_log'), ('denmark_emails', 'denmark_send_log'), ('romania_emails', 'send_log')]:
        try:
            src = psycopg2.connect(host='localhost', dbname=db_name, user='tudor', password='tudor')
            scur = src.cursor()
            scur.execute(f"""
                SELECT campaign, template_num, COUNT(*) as sent,
                       SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced
                FROM {log_table}
                WHERE sent_at >= %s AND template_num IS NOT NULL
                GROUP BY campaign, template_num
                ORDER BY campaign, template_num
            """, (cutoff,))
            rows = scur.fetchall()
            if rows:
                print(f"\n{db_name}:")
                for campaign, tpl, sent, bounced in rows:
                    print(f"  {campaign} tpl#{tpl}: {sent} sent, {bounced} bounced")
            src.close()
        except Exception as e:
            print(f"  {db_name}: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stats', action='store_true')
    p.add_argument('--check', type=str)
    p.add_argument('--ab-report', type=int, nargs='?', const=30)
    args = p.parse_args()

    conn = _get_conn()
    cur = conn.cursor()

    if args.ab_report is not None:
        ab_report(args.ab_report)
        return

    if args.check:
        info = get_send_info(args.check, days=14)
        if info:
            print(f"Found: {info}")
        else:
            print("Not found in last 14 days")
        return

    cur.execute("SELECT COUNT(*), COUNT(DISTINCT email) FROM global_sends")
    total, unique = cur.fetchone()
    cutoff = (date.today() - timedelta(days=14)).isoformat()
    cur.execute("SELECT COUNT(DISTINCT email) FROM global_sends WHERE sent_date >= %s", (cutoff,))
    recent = cur.fetchone()[0]
    cur.execute("SELECT campaign, COUNT(*) FROM global_sends GROUP BY campaign ORDER BY count DESC LIMIT 10")
    top = cur.fetchall()

    print(f"Global sends: {total} total, {unique} unique emails")
    print(f"Last 14 days: {recent} unique emails")
    print("Top campaigns:")
    for c, n in top:
        print(f"  {c}: {n}")


if __name__ == '__main__':
    main()
