"""
Step 33: Daily campaign readiness report
Runs at 07:00, outputs HTML digest + sends to Telegram.
Deploy: cron on raspibig or laptop.

Usage: python step33_daily_report.py
"""

import asyncpg
import asyncio
import datetime
from pathlib import Path

DB = dict(user="tudor", password="tudor", host="127.0.0.1", port=5433, database="interjob_master")
OUT_DIR = Path(__file__).parent
TELEGRAM_TOKEN = None  # Set from env: TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT = None   # Set from env: TELEGRAM_CHAT_ID


async def get_stats(conn):
    stats = {}

    # Contactable by country+tier
    stats["by_country"] = await conn.fetch("""
        SELECT country,
          COUNT(*) FILTER (WHERE lead_score >= 60) AS tier_a,
          COUNT(*) FILTER (WHERE lead_score >= 40 AND lead_score < 60) AS tier_b,
          COUNT(*) FILTER (WHERE lead_score >= 20 AND lead_score < 40) AS tier_c,
          COUNT(*) total_contactable
        FROM companies_clean
        WHERE (email IS NOT NULL AND email!='' OR enriched_email IS NOT NULL AND enriched_email!='')
          AND (is_insolvent IS NULL OR is_insolvent=false)
          AND country IN ('NO','RO','BG','PL','DK','FI','FR','DE')
        GROUP BY country ORDER BY total_contactable DESC
    """)

    # MX check progress
    stats["mx"] = await conn.fetchrow("""
        SELECT
          COUNT(*) FILTER (WHERE mx_valid=true) AS valid,
          COUNT(*) FILTER (WHERE mx_valid=false) AS invalid,
          COUNT(*) FILTER (WHERE mx_valid IS NULL) AS unknown,
          COUNT(*) total
        FROM master_emails
    """)

    # New responses in last 24h
    stats["responses"] = await conn.fetch("""
        SELECT category, COUNT(*) AS count
        FROM campaign_responses
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY category ORDER BY count DESC
    """)

    # DNC growth
    stats["dnc"] = await conn.fetchval("SELECT COUNT(*) FROM dnc_list")

    # Warm leads pending
    stats["warm"] = await conn.fetchval("""
        SELECT COUNT(*) FROM campaign_responses
        WHERE category IN ('INTERESTED','REPLY')
          AND sender_email NOT IN (SELECT email FROM dnc_list)
    """)

    return stats


def render_html(stats) -> str:
    date = datetime.date.today().isoformat()
    rows = "".join(
        f"<tr><td>{r['country']}</td><td>{r['tier_a']}</td><td>{r['tier_b']}</td>"
        f"<td>{r['tier_c']}</td><td><b>{r['total_contactable']:,}</b></td></tr>"
        for r in stats["by_country"]
    )
    mx = stats["mx"]
    resp = "".join(f"<li>{r['category']}: {r['count']}</li>" for r in stats["responses"])

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Daily Report {date}</title>
<style>body{{font-family:monospace;background:#111;color:#eee;padding:20px}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:6px 12px;border:1px solid #333}}
th{{background:#222}}h2{{color:#4af}}</style></head><body>
<h1>InterJob DB Report — {date}</h1>
<h2>Contactable Companies by Country</h2>
<table><tr><th>Country</th><th>A (60+)</th><th>B (40-59)</th><th>C (20-39)</th><th>Total</th></tr>
{rows}</table>
<h2>Email Quality</h2>
<p>MX Valid: <b>{mx['valid']:,}</b> | Invalid: {mx['invalid']:,} | Unknown: {mx['unknown']:,} | Total: {mx['total']:,}</p>
<h2>Last 24h Responses</h2><ul>{resp or '<li>None</li>'}</ul>
<p>Warm leads pending: <b>{stats['warm']}</b> | DNC total: {stats['dnc']:,}</p>
</body></html>"""


async def main():
    pool = await asyncpg.create_pool(**DB)
    async with pool.acquire() as conn:
        stats = await get_stats(conn)
    await pool.close()

    html = render_html(stats)
    out = OUT_DIR / f"daily_report_{datetime.date.today()}.html"
    out.write_text(html, encoding="utf-8")
    print(f"Report -> {out.name}")

    # Telegram digest (plain text)
    mx = stats["mx"]
    warm = stats["warm"]
    top = stats["by_country"][:5]
    msg = f"InterJob Daily {datetime.date.today()}\n"
    msg += f"MX valid: {mx['valid']:,} | Unknown: {mx['unknown']:,}\n"
    msg += f"Warm leads: {warm}\n"
    msg += "Top contactable:\n"
    for r in top:
        msg += f"  {r['country']}: {r['total_contactable']:,} (A:{r['tier_a']})\n"

    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        import urllib.request, json
        data = json.dumps({"chat_id": TELEGRAM_CHAT, "text": msg}).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=data, timeout=10
        )
        print("Telegram sent")
    else:
        print(msg)


if __name__ == "__main__":
    asyncio.run(main())
