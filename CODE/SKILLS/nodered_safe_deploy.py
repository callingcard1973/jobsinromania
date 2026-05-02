#!/usr/bin/env python3
"""
Safe Node-RED flow deployment - NEVER replaces, only adds.
"""
import json
import requests
import sys
from datetime import datetime
from pathlib import Path

NODERED_URL = "http://localhost:1880"
BACKUP_DIR = Path("/opt/ACTIVE/INFRA/BACKUPS/nodered")

def backup_flows():
    """Always backup before any change."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    r = requests.get(f"{NODERED_URL}/flows")
    if r.ok:
        backup_file = BACKUP_DIR / f"flows_{datetime.now():%Y%m%d_%H%M%S}.json"
        backup_file.write_text(json.dumps(r.json(), indent=2))
        print(f"Backup: {backup_file}")
        return True
    return False

def add_flow(new_flow_json):
    """Add flow WITHOUT replacing existing ones."""
    # 1. Backup first
    if not backup_flows():
        print("ERROR: Could not backup flows")
        return False
    
    # 2. Get existing flows
    r = requests.get(f"{NODERED_URL}/flows")
    if not r.ok:
        print("ERROR: Could not get existing flows")
        return False
    
    existing = r.json()
    print(f"Existing nodes: {len(existing)}")
    
    # 3. Load new flow
    if isinstance(new_flow_json, str):
        new_flow = json.loads(new_flow_json)
    else:
        new_flow = new_flow_json
    
    # 4. Check for ID conflicts
    existing_ids = {f.get('id') for f in existing}
    for node in new_flow:
        if node.get('id') in existing_ids:
            print(f"ERROR: ID conflict: {node.get('id')}")
            return False
    
    # 5. Merge and deploy
    combined = existing + new_flow
    r = requests.post(
        f"{NODERED_URL}/flows",
        json=combined,
        headers={"Node-RED-Deployment-Type": "full"}
    )
    
    if r.ok:
        print(f"SUCCESS: Added {len(new_flow)} nodes")
        return True
    else:
        print(f"ERROR: {r.text}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: nodered_safe_deploy.py <flow.json>")
        print("       nodered_safe_deploy.py --backup")
        sys.exit(1)
    
    if sys.argv[1] == "--backup":
        backup_flows()
    else:
        flow_file = Path(sys.argv[1])
        if flow_file.exists():
            add_flow(flow_file.read_text())
        else:
            print(f"File not found: {flow_file}")
