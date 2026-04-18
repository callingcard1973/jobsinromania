#!/usr/bin/env python3
"""PostHog analytics Telegram command + morning digest."""
import requests
from datetime import date, timedelta
from telegram import Update
from telegram.ext import ContextTypes

POSTHOG_KEY = "phx_ZKBT7BuYJ2UQZZVJN62uqp95U5nrYZK79auQzCxc7Ad7n64i"
POSTHOG_PROJECT = "377581"
POSTHOG_HOST = "https://us.posthog.com"

def _ph_query(sql):
    r = requests.post(
        f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT}/query/",
        json={"query": {"kind": "HogQLQuery", "query": sql}},
        headers={"Authorization": f"Bearer {POSTHOG_KEY}"},
        timeout=20,
    )
    if r.status_code != 200:
        return None, f"API error {r.status_code}"
    return r.json().get("results", []), None

def _pg(sql):
    import subprocess
    r = subprocess.run(["psql", "-d", "interjob_master", "-t", "-c", sql],
                       capture_output=True, text=True, timeout=10)
    return (r.stdout + r.stderr).strip()

def build_report(days=1):
    today = date.today().isoformat()
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    label = "TODAY" if days == 1 else f"LAST {days}d"
    lines = [f"POSTHOG — {label} ({since}):"]

    # Pageviews + visitors
    rows, _ = _ph_query(f"""
        SELECT count() AS pv, count(DISTINCT distinct_id) AS vis
        FROM events WHERE event='$pageview' AND toDate(timestamp)>='{since}'
    """)
    if rows:
        lines.append(f"\nViews: {rows[0][0]:,}  Visitors: {rows[0][1]:,}")

    # Top 5 sites
    rows, _ = _ph_query(f"""
        SELECT replaceRegexpAll(properties.$host,'^www\\.','') AS s, count() v
        FROM events WHERE event='$pageview' AND toDate(timestamp)>='{since}'
        GROUP BY s ORDER BY v DESC LIMIT 5
    """)
    if rows:
        lines.append("\nTop sites:")
        for s, v in rows:
            lines.append(f"  {s}: {v:,}")

    # Top campaigns (UTM)
    rows, _ = _ph_query(f"""
        SELECT properties.utm_campaign AS c, count() v
        FROM events WHERE event='$pageview' AND toDate(timestamp)>='{since}'
          AND properties.utm_campaign IS NOT NULL AND properties.utm_campaign!=''
        GROUP BY c ORDER BY v DESC LIMIT 8
    """)
    if rows:
        lines.append("\nCampaign clicks:")
        for c, v in rows:
            lines.append(f"  {c}: {v:,}")

    # Apply funnel
    rows, _ = _ph_query(f"""
        SELECT event, count() n FROM events
        WHERE event IN ('apply_page_view','apply_submitted')
          AND toDate(timestamp)>='{since}'
        GROUP BY event ORDER BY event
    """)
    if rows:
        lines.append("\nApply funnel:")
        for ev, n in rows:
            label_e = "viewed" if "view" in ev else "submitted"
            lines.append(f"  {label_e}: {n:,}")

    # Replies from PostHog events (employer_replied + campaign_response)
    rows, _ = _ph_query(f"""
        SELECT properties.campaign AS c,
               countIf(properties.category='INTERESTED') AS interested,
               countIf(properties.category='NOT_INTERESTED') AS unsub,
               count() AS total
        FROM events
        WHERE event IN ('employer_replied','campaign_response')
          AND toDate(timestamp)>='{since}'
          AND properties.campaign IS NOT NULL
        GROUP BY c ORDER BY interested DESC LIMIT 8
    """)
    if rows:
        lines.append("\nEmail replies:")
        for c, interested, unsub, total in rows:
            parts = []
            if interested: parts.append(f"{interested} INTERESTED")
            if unsub: parts.append(f"{unsub} unsub")
            lines.append(f"  {c}: {' | '.join(parts) or str(total)}")

    # Catalog sent
    rows, _ = _ph_query(f"""
        SELECT properties.sector AS s, count() n
        FROM events WHERE event='catalog_sent' AND toDate(timestamp)>='{since}'
        GROUP BY s ORDER BY n DESC
    """)
    if rows:
        lines.append("\nCataloage trimise:")
        for s, n in rows:
            lines.append(f"  {s}: {n}")

    # Placements/revenue
    try:
        r = _pg(f"SELECT COUNT(*), COALESCE(SUM(revenue_eur),0) FROM solonet_orders WHERE status='placed' AND created_at::date>='{since}'")
        if r.strip() and r.strip() != "0 |    0":
            lines.append(f"\nPlacements: {r.strip()}")
    except Exception:
        pass

    return "\n".join(lines)

async def cmd_posthog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/posthog [days] — analytics report. Default: today."""
    days = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 1
    await update.message.reply_text("Fetching...")
    report = build_report(days)
    await update.message.reply_text(report[:4000])

async def send_posthog_digest(context):
    """Morning digest — called by JobQueue at 07:00."""
    import os
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    report_today = build_report(days=1)
    report_week = build_report(days=7)
    msg = report_today + "\n\n---\n" + report_week
    await context.bot.send_message(chat_id=chat_id, text=msg[:4000])
