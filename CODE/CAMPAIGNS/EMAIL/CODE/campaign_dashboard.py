#!/usr/bin/env python3
"""Generate HTML dashboard: campaigns, sends, bounces, orders, pipeline stats.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/campaign_dashboard.py
Output: /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/dashboard.html
"""
import csv, json, os, glob
from pathlib import Path
from datetime import datetime, date

import psycopg2

DB_PARAMS = dict(dbname="anofm", user="tudor", password="tudor", host="localhost")
ORDERS_CSV = Path("/opt/ACTIVE/EMAIL/ORDERS/orders.csv")
BOUNCES_LOG = Path("/opt/ACTIVE/EMAIL/ORDERS/bounces.log")
CONTACTS_CSV = Path("/opt/ACTIVE/EMAIL/ORDERS/contacts.csv")
CAMPAIGN_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/")
OUTPUT = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/dashboard.html")


def query_sends_today():
    """Query send_log for today's stats."""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        today = date.today().isoformat()
        cur.execute(
            "SELECT campaign, sender, method, status, COUNT(*) "
            "FROM send_log WHERE sent_at::date = %s GROUP BY campaign, sender, method, status "
            "ORDER BY COUNT(*) DESC", (today,))
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM send_log WHERE sent_at::date = %s", (today,))
        total = cur.fetchone()[0]
        cur.execute(
            "SELECT campaign, COUNT(*) FROM send_log WHERE sent_at::date = %s "
            "GROUP BY campaign ORDER BY COUNT(*) DESC", (today,))
        by_campaign = cur.fetchall()
        conn.close()
        return {"total": total, "breakdown": rows, "by_campaign": by_campaign}
    except Exception as e:
        return {"total": 0, "breakdown": [], "by_campaign": [], "error": str(e)}


def count_orders():
    if not ORDERS_CSV.exists():
        return {"total": 0, "comanda": 0, "interesat": 0}
    total = comanda = interesat = 0
    with open(ORDERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            obs = row.get("D. Observații", row.get("Observații", "")).upper()
            if "COMANDA" in obs:
                comanda += 1
            elif "INTERESAT" in obs:
                interesat += 1
    return {"total": total, "comanda": comanda, "interesat": interesat}


def count_bounces():
    if not BOUNCES_LOG.exists():
        return 0
    return sum(1 for _ in open(BOUNCES_LOG, encoding="utf-8"))


def count_contacts():
    if not CONTACTS_CSV.exists():
        return 0
    return sum(1 for _ in open(CONTACTS_CSV, encoding="utf-8")) - 1


def list_campaigns():
    if not CAMPAIGN_DIR.exists():
        return []
    return [f.stem for f in CAMPAIGN_DIR.glob("*.json")]


def generate_html(sends, orders, bounces, contacts, campaigns):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    camp_rows = "".join(f"<tr><td>{c}</td></tr>" for c in campaigns) or "<tr><td>No configs found</td></tr>"
    send_rows = "".join(
        f"<tr><td>{r[0]}</td><td>{r[1]}</td></tr>"
        for r in sends.get("by_campaign", [])
    ) or "<tr><td colspan='2'>No sends today</td></tr>"
    breakdown_rows = "".join(
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
        for r in sends.get("breakdown", [])[:20]
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Campaign Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#1a1a2e; color:#e0e0e0; font-family:monospace; padding:20px; }}
  h1 {{ color:#00d4ff; margin-bottom:10px; }}
  h2 {{ color:#ff6b6b; margin:20px 0 8px; }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin:15px 0; }}
  .card {{ background:#16213e; border:1px solid #0f3460; border-radius:8px; padding:15px; text-align:center; }}
  .card .num {{ font-size:2em; color:#00d4ff; font-weight:bold; }}
  .card .label {{ color:#a0a0a0; font-size:0.9em; }}
  table {{ width:100%; border-collapse:collapse; margin:10px 0; }}
  th,td {{ padding:6px 10px; border:1px solid #0f3460; text-align:left; }}
  th {{ background:#0f3460; color:#00d4ff; }}
  tr:nth-child(even) {{ background:#16213e; }}
  .err {{ color:#ff6b6b; }}
  .ts {{ color:#666; font-size:0.8em; margin-top:20px; }}
</style></head><body>
<h1>InterJob Email Campaign Dashboard</h1>
<div class="grid">
  <div class="card"><div class="num">{sends['total']}</div><div class="label">Sends Today</div></div>
  <div class="card"><div class="num">{orders['comanda']}</div><div class="label">COMENZI</div></div>
  <div class="card"><div class="num">{orders['interesat']}</div><div class="label">INTERESATI</div></div>
  <div class="card"><div class="num">{bounces}</div><div class="label">Bounces</div></div>
</div>
<div class="grid">
  <div class="card"><div class="num">{orders['total']}</div><div class="label">Total Orders</div></div>
  <div class="card"><div class="num">{contacts}</div><div class="label">Contacts</div></div>
  <div class="card"><div class="num">{len(campaigns)}</div><div class="label">Campaigns</div></div>
  <div class="card"><div class="num">{"OK" if not sends.get("error") else "ERR"}</div><div class="label">DB Status</div></div>
</div>
{f'<p class="err">DB Error: {sends["error"]}</p>' if sends.get("error") else ""}
<h2>Sends by Campaign (Today)</h2>
<table><tr><th>Campaign</th><th>Count</th></tr>{send_rows}</table>
<h2>Detailed Breakdown</h2>
<table><tr><th>Campaign</th><th>Sender</th><th>Method</th><th>Status</th><th>Count</th></tr>
{breakdown_rows}</table>
<h2>Active Campaigns</h2>
<table><tr><th>Config</th></tr>{camp_rows}</table>
<p class="ts">Generated: {now}</p>
</body></html>"""
    return html


def main():
    sends = query_sends_today()
    orders = count_orders()
    bounces = count_bounces()
    contacts = count_contacts()
    campaigns = list_campaigns()

    html = generate_html(sends, orders, bounces, contacts, campaigns)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Dashboard saved to {OUTPUT}")
    print(f"Sends today: {sends['total']}, Orders: {orders['total']} "
          f"(COMENZI: {orders['comanda']}), Bounces: {bounces}")


if __name__ == "__main__":
    main()
