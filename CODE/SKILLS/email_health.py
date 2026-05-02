#!/usr/bin/env python3
"""
Email Health Dashboard - Analyze send logs from PostgreSQL
Usage: python3 email_health.py [days]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import psycopg2
from datetime import datetime, timedelta

DB = {'host':'raspi','database':'email_sender','user':'tudor','password':'scraper123'}

def get_stats(days=7):
    """Return email stats as dict for dashboard integration."""
    stats = {
        'status_breakdown': {},
        'total': 0,
        'bounce_rate': 0,
        'ok': 0,
        'failed': 0,
        'top_domains': [],
        'templates': [],
        'daily_sends': []
    }

    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()

        # Status breakdown
        cur.execute(f"""
            SELECT status, COUNT(*) FROM send_log
            WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
            GROUP BY status ORDER BY COUNT(*) DESC
        """)
        for status, cnt in cur.fetchall():
            stats['status_breakdown'][status] = cnt
            stats['total'] += cnt

        # Bounce rate
        cur.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE status='OK') as ok,
                COUNT(*) FILTER (WHERE status IN ('bounced','failed','error')) as failed
            FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
        """)
        ok, failed = cur.fetchone()
        stats['ok'] = ok or 0
        stats['failed'] = failed or 0
        stats['bounce_rate'] = (failed*100//(ok+failed)) if (ok and failed and (ok+failed)>0) else 0

        # Top domains
        cur.execute(f"""
            SELECT SPLIT_PART(email,'@',2) as domain,
                   COUNT(*) FILTER (WHERE status='OK') as ok,
                   COUNT(*) as total
            FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
            GROUP BY domain ORDER BY total DESC LIMIT 10
        """)
        for domain, ok, total in cur.fetchall():
            rate = ok*100//total if total>0 else 0
            stats['top_domains'].append({'domain': domain, 'ok': ok, 'total': total, 'rate': rate})

        # Templates
        cur.execute(f"""
            SELECT template_name, COUNT(*) as cnt,
                   COUNT(*) FILTER (WHERE status='OK') as ok
            FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
            AND template_name IS NOT NULL
            GROUP BY template_name ORDER BY cnt DESC LIMIT 5
        """)
        for tpl, cnt, ok in cur.fetchall():
            rate = ok*100//cnt if cnt>0 else 0
            stats['templates'].append({'template': tpl, 'count': cnt, 'ok': ok, 'rate': rate})

        # Daily trend
        cur.execute(f"""
            SELECT DATE(sent_at_utc) as day, COUNT(*)
            FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
            GROUP BY day ORDER BY day DESC LIMIT 7
        """)
        for day, cnt in cur.fetchall():
            stats['daily_sends'].append({'date': str(day), 'count': cnt})

        cur.close()
        conn.close()
    except Exception as e:
        stats['error'] = str(e)

    return stats

def dashboard(days=7):
    print(f"\n{'='*60}\nEMAIL HEALTH DASHBOARD (Last {days} days)\n{'='*60}\n")
    
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    
    # Overall stats
    cur.execute(f"""
        SELECT status, COUNT(*) FROM send_log 
        WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
        GROUP BY status ORDER BY COUNT(*) DESC
    """)
    print("STATUS BREAKDOWN:")
    total = 0
    for status, cnt in cur.fetchall():
        print(f"  {status}: {cnt}")
        total += cnt
    print(f"  TOTAL: {total}")
    
    # Bounce rate
    cur.execute(f"""
        SELECT 
            COUNT(*) FILTER (WHERE status='OK') as ok,
            COUNT(*) FILTER (WHERE status IN ('bounced','failed','error')) as failed
        FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
    """)
    ok, failed = cur.fetchone()
    bounce_rate = failed*100//(ok+failed) if (ok+failed)>0 else 0
    print(f"\nBOUNCE RATE: {bounce_rate}% ({failed}/{ok+failed})")
    
    # By domain
    cur.execute(f"""
        SELECT SPLIT_PART(email,'@',2) as domain, 
               COUNT(*) FILTER (WHERE status='OK') as ok,
               COUNT(*) as total
        FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
        GROUP BY domain ORDER BY total DESC LIMIT 10
    """)
    print(f"\nTOP DOMAINS:")
    for domain, ok, total in cur.fetchall():
        rate = ok*100//total if total>0 else 0
        print(f"  {domain}: {ok}/{total} ({rate}%)")
    
    # By template
    cur.execute(f"""
        SELECT template_name, COUNT(*) as cnt,
               COUNT(*) FILTER (WHERE status='OK') as ok
        FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
        AND template_name IS NOT NULL
        GROUP BY template_name ORDER BY cnt DESC LIMIT 5
    """)
    print(f"\nTEMPLATE PERFORMANCE:")
    for tpl, cnt, ok in cur.fetchall():
        rate = ok*100//cnt if cnt>0 else 0
        print(f"  {tpl}: {ok}/{cnt} ({rate}%)")
    
    # Daily trend
    cur.execute(f"""
        SELECT DATE(sent_at_utc) as day, COUNT(*) 
        FROM send_log WHERE sent_at_utc > NOW() - INTERVAL '{days} days'
        GROUP BY day ORDER BY day DESC LIMIT 7
    """)
    print(f"\nDAILY SENDS:")
    for day, cnt in cur.fetchall():
        print(f"  {day}: {cnt}")
    
    cur.close()
    conn.close()
    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv)>1 else 7
    dashboard(days)
