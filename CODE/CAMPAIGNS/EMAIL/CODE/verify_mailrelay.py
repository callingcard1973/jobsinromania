#!/usr/bin/env python3
"""Full Mailrelay verification: account, sender, subscribers, test send."""
import os, requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/.env")

key = os.environ.get("MAILRELAY_API_KEY", "")
base = os.environ.get("MAILRELAY_API_URL", "").rstrip("/")
if not base.endswith("/api/v1"):
    base += "/api/v1"
h = {"X-Auth-Token": key, "Content-Type": "application/json"}

print("=== ACCOUNT ===")
r = requests.get(base + "/package", headers=h, timeout=10)
p = r.json()
print("Plan:", p.get("package_type"), "| Used:", p.get("usage"), "/", p.get("limit"),
      "| Subs:", p.get("subscribers_usage"), "/", p.get("subscribers_limit"))

print("\n=== SENDER ===")
r = requests.get(base + "/senders", headers=h, timeout=10)
for s in r.json():
    print(s.get("email"), "confirmed=" + str(s.get("confirmed")))

print("\n=== GROUPS ===")
r = requests.get(base + "/groups", headers=h, timeout=10)
for g in r.json():
    print(g.get("name"), "(" + str(g.get("subscribers_count")) + " subs)")

print("\n=== SUBSCRIBERS ===")
r = requests.get(base + "/subscribers", headers=h, timeout=10)
for s in r.json():
    print(s.get("email"), "status=" + str(s.get("status")))

print("\n=== TEST SEND ===")
html = "<p>Mailrelay verify " + datetime.now().isoformat() + "</p>"
html += '<p><a href="[unsubscribe_url]">Unsubscribe</a></p>'
r = requests.post(base + "/campaigns", headers=h, json={
    "subject": "Mailrelay Verify " + datetime.now().strftime("%H:%M"),
    "sender_id": 1, "html": html, "target": "groups", "group_ids": [1]
}, timeout=15)
print("Campaign:", r.status_code)
if r.status_code == 201:
    cid = r.json()["id"]
    r2 = requests.post(base + "/campaigns/" + str(cid) + "/send_all",
                       headers=h, json={"target": "groups", "group_ids": [1]}, timeout=15)
    if r2.status_code == 200:
        print("SENT to all group 1 subscribers")
    else:
        print("FAIL:", r2.status_code, r2.text[:150])
else:
    print("FAIL:", r.text[:150])
