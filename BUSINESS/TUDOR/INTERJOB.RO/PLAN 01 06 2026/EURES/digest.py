#!/usr/bin/env python3
"""Print the EURES outreach daily digest (per-sender sent/cap/bounces/queue)."""
import os
import json
import psycopg2

BASE = '/opt/ACTIVE/EURES'
DB = {'dbname': 'interjob_master', 'user': 'tudor'}


def main():
    senders = json.load(open(os.path.join(BASE, 'senders.json')))
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    print("=== EURES OUTREACH DIGEST ===")
    grand = 0
    for dom, cfg in senders.items():
        cur.execute("SELECT count(*) FILTER (WHERE sent_at::date=current_date), "
                    "count(*) FILTER (WHERE status='bounced'), "
                    "count(*) FILTER (WHERE status='opted_out') FROM eures_send_log WHERE sender_domain=%s", (dom,))
        sent_today, bounced, opted = cur.fetchone()
        cur.execute("SELECT count(*) FROM eures_audience_sendable a LEFT JOIN eures_send_log s "
                    "ON s.email=a.email WHERE a.sender_domain=%s AND s.email IS NULL", (dom,))
        queue = cur.fetchone()[0]
        grand += sent_today
        flag = 'ON' if cfg.get('enabled') else 'off'
        print(f"  {dom:26} [{flag:3}] sent_today={sent_today:4} cap={cfg['max_daily_cap']:4} "
              f"bounced={bounced:4} optout={opted:4} queue={queue}")
    cur.execute("SELECT count(*) FROM eures_audience_sendable")
    aud = cur.fetchone()[0]
    print(f"  audience_total={aud}  sent_today_all={grand}")
    cur.close()
    conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
