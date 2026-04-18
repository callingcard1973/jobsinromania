#!/usr/bin/env python3
"""Send test emails for eu_projects_info campaign via Mailrelay."""
import os, sys, psycopg2, requests
sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED")
from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/.env")

# Get one real contact
conn = psycopg2.connect(host="localhost", dbname="european_funds", user="tudor", password="tudor")
cur = conn.cursor()
cur.execute("SELECT * FROM proiecte WHERE email IS NOT NULL AND beneficiar != '' LIMIT 1")
cols = [d[0] for d in cur.description]
row = cur.fetchone()
contact = dict(zip(cols, row))
cur.close()
conn.close()

# Read and render template
with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/eu_projects_info/template1.txt") as f:
    tpl = f.read()
lines = tpl.strip().split("\n")
subject = lines[0].replace("Subject: ", "")
body = "\n".join(lines[1:]).strip()

for key, val in contact.items():
    subject = subject.replace("{" + str(key) + "}", str(val or ""))
    body = body.replace("{" + str(key) + "}", str(val or ""))
body = body.replace("{unsubscribe_url}", "https://interjob.ro/unsubscribe.php?email=test")

print("SUBJECT:", subject)
print("BODY:", body[:300], "...")
print()

# Send via Mailrelay
api_key = os.environ.get("MAILRELAY_API_KEY", "")
base = os.environ.get("MAILRELAY_API_URL", "https://expatsinromania.ipzmarketing.com")
if not base.endswith("/api/v1"):
    base = base.rstrip("/") + "/api/v1"
h = {"X-Auth-Token": api_key, "Content-Type": "application/json"}

for email in ["apaminerala@yahoo.com", "fruitnature4@gmail.com"]:
    # Ensure subscriber exists
    # Search subscriber
    r = requests.get(base + "/subscribers", headers=h, params={"q[email_eq]": email}, timeout=10)
    subs = r.json() if r.status_code == 200 and r.text.strip().startswith("[") else []
    if not subs:
        # Create subscriber
        requests.post(base + "/subscribers", headers=h, json={
            "name": email.split("@")[0], "email": email,
            "group_ids": [1], "status": "active"}, timeout=10)
        r = requests.get(base + "/subscribers", headers=h, params={"q[email_eq]": email}, timeout=10)
        subs = r.json() if r.status_code == 200 and r.text.strip().startswith("[") else []
    if not subs:
        print(email + ": NO SUBSCRIBER")
        continue
    sid = subs[0]["id"]

    # Build HTML
    html = "<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>"
    html += body.replace("\n", "<br>")
    html += "</div><p><a href='[unsubscribe_url]'>Unsubscribe</a></p>"

    # Create temp group for this recipient, add subscriber to it
    grp = requests.post(base + "/groups", headers=h, json={
        "name": "send_" + email.replace("@", "_at_")[:30]}, timeout=10)
    if grp.status_code == 201:
        gid = grp.json()["id"]
    else:
        # Group might already exist, find it
        gl = requests.get(base + "/groups", headers=h, timeout=10)
        gid = next((g["id"] for g in gl.json() if g["name"].startswith("send_" + email.split("@")[0])), 1)
    # Add subscriber to group
    requests.patch(base + "/subscribers/" + str(sid), headers=h, json={"group_ids": [gid]}, timeout=10)

    camp = {"subject": subject, "sender_id": 1, "html": html,
            "target": "groups", "group_ids": [gid]}
    r2 = requests.post(base + "/campaigns", headers=h, json=camp, timeout=15)
    if r2.status_code != 201:
        print(email + ": CAMPAIGN FAIL " + str(r2.status_code) + " " + r2.text[:100])
        continue
    cid = r2.json()["id"]
    r3 = requests.post(base + "/campaigns/" + str(cid) + "/send_all", headers=h,
                       json={"target": "groups", "group_ids": [1]}, timeout=15)
    if r3.status_code == 200:
        print(email + ": SENT (campaign " + str(cid) + ")")
    else:
        print(email + ": SEND FAIL " + str(r3.status_code) + " " + r3.text[:100])
