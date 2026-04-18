#!/usr/bin/env python3
"""Add EU Funding pipeline to Node-RED on raspibig."""
import requests
import json
import uuid

NR = "http://localhost:1880"

# Get existing flows
flows = requests.get(f"{NR}/flows").json()

# Create new tab
tab_id = str(uuid.uuid4()).replace("-", "")[:16]
tab = {
    "id": tab_id,
    "type": "tab",
    "label": "EU Funding Pipeline",
    "disabled": False,
    "info": "Daily scrape + cleanup + export for EU funding leads"
}

# Cron trigger: 02:00, 09:00, 16:00
cron_id = str(uuid.uuid4()).replace("-", "")[:16]
cron_node = {
    "id": cron_id,
    "type": "inject",
    "z": tab_id,
    "name": "Daily 02:00 09:00 16:00",
    "props": [{"p": "payload"}],
    "repeat": "",
    "crontab": "00 02,09,16 * * *",
    "once": False,
    "onceDelay": 0.1,
    "topic": "",
    "payload": "scrape",
    "payloadType": "str",
    "x": 150,
    "y": 100,
    "wires": [[str(uuid.uuid4()).replace("-", "")[:16]]]
}

# Scraper exec node
scrape_id = cron_node["wires"][0][0]
scrape_node = {
    "id": scrape_id,
    "type": "exec",
    "z": tab_id,
    "command": "cd /opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/SCRAPER_beneficiar.fonduri-ue && python3 beneficiar_fonduri_ue_scraper.py --both --workers 30",
    "addpay": "",
    "append": "",
    "useSpawn": "false",
    "timer": "1800",
    "winHide": False,
    "oldrc": False,
    "name": "Scrape --both",
    "x": 400,
    "y": 100,
    "wires": [[str(uuid.uuid4()).replace("-", "")[:16]], [], []]
}

# Cleanup exec node
cleanup_id = scrape_node["wires"][0][0]
cleanup_node = {
    "id": cleanup_id,
    "type": "exec",
    "z": tab_id,
    "command": "python3 /opt/ACTIVE/INFRA/SKILLS/eu_funding_cleanup.py",
    "addpay": "",
    "append": "",
    "useSpawn": "false",
    "timer": "300",
    "winHide": False,
    "oldrc": False,
    "name": "Cleanup DB",
    "x": 650,
    "y": 100,
    "wires": [[str(uuid.uuid4()).replace("-", "")[:16]], [], []]
}

# Export exec node
export_id = cleanup_node["wires"][0][0]
export_node = {
    "id": export_id,
    "type": "exec",
    "z": tab_id,
    "command": "python3 /opt/ACTIVE/INFRA/SKILLS/eu_funding_export_2w.py",
    "addpay": "",
    "append": "",
    "useSpawn": "false",
    "timer": "300",
    "winHide": False,
    "oldrc": False,
    "name": "Export 2w CSV",
    "x": 900,
    "y": 100,
    "wires": [[str(uuid.uuid4()).replace("-", "")[:16]], [], []]
}

# Debug output
debug_id = export_node["wires"][0][0]
debug_node = {
    "id": debug_id,
    "type": "debug",
    "z": tab_id,
    "name": "Result",
    "active": True,
    "tosidebar": True,
    "console": False,
    "tostatus": True,
    "complete": "payload",
    "targetType": "msg",
    "statusVal": "payload",
    "statusType": "auto",
    "x": 1100,
    "y": 100,
    "wires": []
}

# Sunday fix-desc trigger
sun_cron_id = str(uuid.uuid4()).replace("-", "")[:16]
sun_cron = {
    "id": sun_cron_id,
    "type": "inject",
    "z": tab_id,
    "name": "Sunday 01:00 fix-desc",
    "props": [{"p": "payload"}],
    "repeat": "",
    "crontab": "00 01 * * 0",
    "once": False,
    "onceDelay": 0.1,
    "topic": "",
    "payload": "fix-desc",
    "payloadType": "str",
    "x": 150,
    "y": 200,
    "wires": [[str(uuid.uuid4()).replace("-", "")[:16]]]
}

fixdesc_id = sun_cron["wires"][0][0]
fixdesc_node = {
    "id": fixdesc_id,
    "type": "exec",
    "z": tab_id,
    "command": "cd /opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/SCRAPER_beneficiar.fonduri-ue && python3 beneficiar_fonduri_ue_scraper.py --fix-desc --workers 30",
    "addpay": "",
    "append": "",
    "useSpawn": "false",
    "timer": "3600",
    "winHide": False,
    "oldrc": False,
    "name": "Fix Descriptions",
    "x": 400,
    "y": 200,
    "wires": [[], [], []]
}

new_nodes = [tab, cron_node, scrape_node, cleanup_node, export_node, debug_node, sun_cron, fixdesc_node]
flows.extend(new_nodes)

r = requests.post(f"{NR}/flows", json=flows, headers={"Node-RED-Deployment-Type": "full"})
print(f"Deploy: {r.status_code}")
if r.status_code == 204:
    print("EU Funding Pipeline added to Node-RED!")
else:
    print(f"Error: {r.text[:200]}")
