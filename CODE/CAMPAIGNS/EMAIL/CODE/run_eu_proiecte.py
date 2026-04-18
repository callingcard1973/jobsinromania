#!/usr/bin/env python3
"""Send EU Proiecte campaign via Mailrelay. Standalone, no dependencies on send_campaign.py."""
import os, sys, json, psycopg2, time
from pathlib import Path
from dotenv import load_dotenv
from send_mailrelay import get_api, ensure_group, sync_subscribers, send_campaign

load_dotenv("/opt/ACTIVE/EMAIL/.env")

CONFIG = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/eu_projects_info.json"
TEMPLATE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/eu_projects_info/template1.txt"
STATE_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/state/proiecte.json"

with open(CONFIG) as f:
    cfg = json.load(f)

sector = cfg["sectors"]["PROIECTE"]
if not sector.get("enabled"):
    print("Campaign disabled"); sys.exit(0)

daily_limit = int(sys.argv[1]) if len(sys.argv) > 1 else sector.get("daily_limit", 100)

# Load state
state = {"daily_count": 0, "total_sent": 0}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        state = json.load(f)
    from datetime import date
    if state.get("last_reset") != str(date.today()):
        state["daily_count"] = 0
        state["last_reset"] = str(date.today())

remaining = daily_limit - state.get("daily_count", 0)
if remaining <= 0:
    print(f"Daily limit reached ({daily_limit})"); sys.exit(0)

# Get unsent contacts
db = cfg["db"]
tbl = cfg["tables"]
conn = psycopg2.connect(**db)
cur = conn.cursor()
cur.execute(f"""
    SELECT * FROM {tbl['contacts']}
    WHERE ({tbl['col_campaign_status']} IS NULL OR {tbl['col_campaign_status']} = 'pending')
      AND {tbl['col_email']} IS NOT NULL AND {tbl['col_email']} != ''
    ORDER BY id LIMIT %s
""", (remaining,))
cols = [d[0] for d in cur.description]
contacts = [dict(zip(cols, r)) for r in cur.fetchall()]
cur.close()
conn.close()

if not contacts:
    print("No pending contacts"); sys.exit(0)

print(f"Found {len(contacts)} contacts, sending {min(len(contacts), remaining)}")

# Load and render template
with open(TEMPLATE) as f:
    tpl = f.read()
lines = tpl.strip().split("\n")
subject_tpl = lines[0].replace("Subject: ", "")
body_tpl = "\n".join(lines[1:]).strip()

# Mailrelay: sync subscribers and send
key, base = get_api()
campaign_name = cfg.get("campaign_name", "eu_proiecte")
group_name = "campaign_" + campaign_name[:30].replace(" ", "_").lower()
gid = ensure_group(key, base, group_name)
if not gid:
    print("ERROR: cannot create Mailrelay group"); sys.exit(1)

batch = contacts[:remaining]
print(f"Syncing {len(batch)} subscribers...")
sub_map = sync_subscribers(key, base, gid, batch)
print(f"Synced {len(sub_map)} subscribers")

if not sub_map:
    print("No subscribers synced"); sys.exit(1)

# Render with first contact for subject (Mailrelay sends same subject to all)
subject = subject_tpl
body = body_tpl
for k, v in batch[0].items():
    subject = subject.replace("{" + str(k) + "}", str(v or ""))
# Body: use generic (per-recipient personalization not supported in batch)
html = "<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>"
html += body.replace("\n", "<br>") + "</div>"
html = html.replace("{unsubscribe_url}", "https://interjob.ro/unsubscribe.php?email=test")

ok, msg = send_campaign(key, base, gid, subject, html)
if ok:
    print(f"SENT campaign {msg} to {len(sub_map)} recipients")
    # Mark as sent in DB
    conn = psycopg2.connect(**db)
    cur = conn.cursor()
    for email in sub_map:
        cur.execute(f"UPDATE {tbl['contacts']} SET {tbl['col_campaign_status']}='sent' WHERE LOWER({tbl['col_email']})=%s", (email,))
    conn.commit()
    cur.close()
    conn.close()
    # Update state
    state["daily_count"] += len(sub_map)
    state["total_sent"] = state.get("total_sent", 0) + len(sub_map)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    print(f"State: {state['daily_count']}/{daily_limit} today, {state['total_sent']} total")
else:
    print(f"FAILED: {msg}")
