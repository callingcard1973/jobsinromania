#!/usr/bin/env python3
"""Query send_log + global_sends for analytics: sends per day, per campaign,
per method, bounce rate per sender. Output to analytics.json + print report.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/campaign_analytics.py
"""
import json
from pathlib import Path
from datetime import datetime, timedelta

import psycopg2

ANOFM_DB = dict(dbname="anofm", user="tudor", password="tudor", host="localhost")
SENDER_DB = dict(dbname="email_sender", user="tudor", password="tudor", host="localhost")
OUTPUT = Path("/opt/ACTIVE/INFRA/SKILLS/analytics.json")


def safe_query(db_params, query, params=None):
    """Execute query, return rows or empty list on error."""
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        return rows, cols
    except Exception as e:
        print(f"DB error ({db_params['dbname']}): {e}")
        return [], []


def sends_per_day(days=30):
    """Sends per day from send_log (last N days)."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows, _ = safe_query(ANOFM_DB,
        "SELECT sent_at::date AS day, COUNT(*) "
        "FROM send_log WHERE sent_at >= %s "
        "GROUP BY day ORDER BY day DESC", (cutoff,))
    return [{"date": str(r[0]), "count": r[1]} for r in rows]


def sends_per_campaign():
    """Total sends per campaign."""
    rows, _ = safe_query(ANOFM_DB,
        "SELECT campaign, COUNT(*), "
        "MIN(sent_at)::date, MAX(sent_at)::date "
        "FROM send_log GROUP BY campaign ORDER BY COUNT(*) DESC")
    return [{"campaign": r[0], "count": r[1],
             "first": str(r[2]), "last": str(r[3])} for r in rows]


def sends_per_method():
    """Sends by method (brevo, gmail, zoho, etc.)."""
    rows, _ = safe_query(ANOFM_DB,
        "SELECT method, COUNT(*) FROM send_log "
        "GROUP BY method ORDER BY COUNT(*) DESC")
    return [{"method": r[0], "count": r[1]} for r in rows]


def sends_per_sender():
    """Sends by sender address."""
    rows, _ = safe_query(ANOFM_DB,
        "SELECT sender, COUNT(*), "
        "SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) AS bounces "
        "FROM send_log GROUP BY sender ORDER BY COUNT(*) DESC")
    result = []
    for r in rows:
        total = r[1]
        bounced = r[2] or 0
        result.append({
            "sender": r[0],
            "total": total,
            "bounced": bounced,
            "bounce_rate": round(bounced / total * 100, 2) if total > 0 else 0,
        })
    return result


def bounce_rate_per_campaign():
    """Bounce rate by campaign."""
    rows, _ = safe_query(ANOFM_DB,
        "SELECT campaign, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) AS bounced, "
        "SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent "
        "FROM send_log GROUP BY campaign ORDER BY COUNT(*) DESC")
    result = []
    for r in rows:
        total = r[1]
        bounced = r[2] or 0
        result.append({
            "campaign": r[0],
            "total": total,
            "sent": r[3] or 0,
            "bounced": bounced,
            "bounce_rate": round(bounced / total * 100, 2) if total > 0 else 0,
        })
    return result


def global_sends_stats():
    """Stats from email_sender.global_sends."""
    rows, _ = safe_query(SENDER_DB,
        "SELECT COUNT(*), "
        "COUNT(DISTINCT email), "
        "MIN(sent_at)::date, MAX(sent_at)::date "
        "FROM global_sends")
    if rows:
        r = rows[0]
        return {"total": r[0], "unique_emails": r[1],
                "first": str(r[2]), "last": str(r[3])}
    return {}


def main():
    print("Generating campaign analytics...")

    daily = sends_per_day(30)
    by_campaign = sends_per_campaign()
    by_method = sends_per_method()
    by_sender = sends_per_sender()
    bounces = bounce_rate_per_campaign()
    global_stats = global_sends_stats()

    analytics = {
        "generated": datetime.now().isoformat(),
        "summary": {
            "total_sends_30d": sum(d["count"] for d in daily),
            "avg_per_day": round(sum(d["count"] for d in daily) / max(len(daily), 1), 1),
            "campaigns_active": len(by_campaign),
            "methods_used": len(by_method),
        },
        "global_sends": global_stats,
        "sends_per_day": daily,
        "sends_per_campaign": by_campaign,
        "sends_per_method": by_method,
        "sends_per_sender": by_sender,
        "bounce_rate_per_campaign": bounces,
    }

    OUTPUT.write_text(json.dumps(analytics, indent=2, ensure_ascii=False))

    # Print report
    print(f"\n{'='*60}")
    print(f"CAMPAIGN ANALYTICS REPORT")
    print(f"{'='*60}")
    s = analytics["summary"]
    print(f"Total sends (30d):  {s['total_sends_30d']:>8,}")
    print(f"Average per day:    {s['avg_per_day']:>8}")
    print(f"Active campaigns:   {s['campaigns_active']:>8}")

    if global_stats:
        print(f"\nGlobal sends:  {global_stats['total']:>8,} "
              f"({global_stats['unique_emails']:,} unique)")

    print(f"\n--- Sends per Campaign ---")
    for c in by_campaign[:15]:
        print(f"  {c['campaign']:30s} {c['count']:>6,}  ({c['first']} - {c['last']})")

    print(f"\n--- Sends per Method ---")
    for m in by_method:
        print(f"  {m['method']:20s} {m['count']:>8,}")

    print(f"\n--- Bounce Rate per Sender ---")
    for s in by_sender[:10]:
        print(f"  {s['sender']:35s} {s['total']:>6,} sent, "
              f"{s['bounced']:>4} bounced ({s['bounce_rate']}%)")

    print(f"\nFull analytics: {OUTPUT}")


if __name__ == "__main__":
    main()
