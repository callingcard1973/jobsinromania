#!/usr/bin/env python3
"""Add EBRD scraper watchdog to Node-RED."""
import requests
import json
import uuid

NR = "http://localhost:1880"

flows = requests.get(f"{NR}/flows").json()

tab_id = uuid.uuid4().hex[:16]
tab = {"id": tab_id, "type": "tab", "label": "EBRD Scraper", "disabled": False}

# Check every 5 min if scraper is running, restart if not
cron_id = uuid.uuid4().hex[:16]
cron = {
    "id": cron_id, "type": "inject", "z": tab_id,
    "name": "Every 5 min", "repeat": "300", "crontab": "",
    "once": True, "onceDelay": "10",
    "payload": "", "payloadType": "date",
    "x": 150, "y": 100,
    "wires": [[uuid.uuid4().hex[:16]]]
}

check_id = cron["wires"][0][0]
check = {
    "id": check_id, "type": "exec", "z": tab_id,
    "command": "pgrep -f ebrd_psd_scraper || (cd /opt/ACTIVE/SCRAPERS/EBRD && python3 -u ebrd_psd_scraper.py >> data/scrape.log 2>&1 &)",
    "addpay": "", "append": "", "useSpawn": "false",
    "timer": "10", "winHide": False, "oldrc": False,
    "name": "Check/Restart EBRD", "x": 400, "y": 100,
    "wires": [[uuid.uuid4().hex[:16]], [], []]
}

debug_id = check["wires"][0][0]
debug = {
    "id": debug_id, "type": "debug", "z": tab_id,
    "name": "Status", "active": True, "tosidebar": True,
    "console": False, "tostatus": True,
    "complete": "payload", "targetType": "msg",
    "x": 650, "y": 100, "wires": []
}

flows.extend([tab, cron, check, debug])
r = requests.post(f"{NR}/flows", json=flows, headers={"Node-RED-Deployment-Type": "full"})
print(f"Deploy: {r.status_code}")
if r.status_code == 204:
    print("EBRD Scraper watchdog added to Node-RED!")
