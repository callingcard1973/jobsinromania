#!/usr/bin/env python3
"""
Node-RED Flow Health Checker

Validates all scheduled flows to catch broken scripts BEFORE they fail.
Run daily or after any Node-RED changes.

Usage:
    python3 nodered_health_check.py           # Check all scheduled flows
    python3 nodered_health_check.py --fix     # Disable broken flows
    python3 nodered_health_check.py --alert   # Send Telegram alert if issues
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime

NODERED_URL = "http://localhost:1880/flows"

# Scripts that are known to be deprecated/removed
DEPRECATED_SCRIPTS = [
    'anofm_construct_pipeline.py',
    'db_campaign_sender.py',  # Missing campaign_contacts table
]


def get_flows():
    """Fetch Node-RED flows."""
    try:
        resp = requests.get(NODERED_URL, timeout=5)
        return resp.json()
    except:
        return []


def check_script_exists(cmd):
    """Check if script in command exists."""
    parts = cmd.split()
    for i, part in enumerate(parts):
        if part.endswith('.py') or part.endswith('.sh'):
            script_path = part
            if not script_path.startswith('/'):
                continue
            if not os.path.exists(script_path):
                return False, f"Script not found: {script_path}"
            # Check for deprecated scripts
            for dep in DEPRECATED_SCRIPTS:
                if dep in script_path:
                    return False, f"Deprecated script: {dep}"
    return True, "OK"


def check_db_connection(cmd):
    """Check if DB-dependent scripts can connect."""
    if 'psql' in cmd or 'pg_dump' in cmd:
        # Check postgres is running
        result = subprocess.run(['pg_isready'], capture_output=True, timeout=5)
        if result.returncode != 0:
            return False, "PostgreSQL not ready"
    return True, "OK"


def validate_flow(flow_info):
    """Validate a single flow."""
    issues = []
    cmd = flow_info['command']

    # Check script exists
    ok, msg = check_script_exists(cmd)
    if not ok:
        issues.append(msg)

    # Check DB if needed
    ok, msg = check_db_connection(cmd)
    if not ok:
        issues.append(msg)

    return issues


def get_scheduled_flows():
    """Get all scheduled exec flows."""
    data = get_flows()
    if not data:
        return []

    exec_nodes = {n.get('id'): n for n in data if n.get('type') == 'exec'}
    scheduled = []

    for node in data:
        if node.get('type') == 'inject' and node.get('crontab'):
            for wire_group in node.get('wires', []):
                for wire_id in wire_group:
                    if wire_id in exec_nodes:
                        exec_node = exec_nodes[wire_id]
                        scheduled.append({
                            'inject_id': node.get('id'),
                            'inject_name': node.get('name'),
                            'cron': node.get('crontab'),
                            'exec_id': exec_node.get('id'),
                            'exec_name': exec_node.get('name'),
                            'command': exec_node.get('command', '')
                        })
    return scheduled


def disable_flow(inject_id, flows_data):
    """Disable a flow by clearing its crontab."""
    for node in flows_data:
        if node.get('id') == inject_id:
            node['crontab'] = ''
            node['name'] = f"DISABLED: {node.get('name', '')}"
            return True
    return False


def send_alert(message):
    """Send Telegram alert."""
    try:
        from alerting import send_telegram
        send_telegram(message)
    except:
        print(f"Alert: {message}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--fix', action='store_true', help='Disable broken flows')
    parser.add_argument('--alert', action='store_true', help='Send Telegram alert')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args()

    scheduled = get_scheduled_flows()
    results = []
    broken = []

    for flow in scheduled:
        issues = validate_flow(flow)
        status = 'OK' if not issues else 'BROKEN'
        results.append({
            'name': flow['inject_name'],
            'cron': flow['cron'],
            'command': flow['command'][:60],
            'status': status,
            'issues': issues
        })
        if issues:
            broken.append(flow)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    # Print report
    print("=== NODE-RED HEALTH CHECK ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Total scheduled: {len(scheduled)}")
    print(f"Broken: {len(broken)}")
    print()

    if broken:
        print("BROKEN FLOWS:")
        for flow in broken:
            issues = validate_flow(flow)
            print(f"  - {flow['inject_name']} ({flow['cron']})")
            print(f"    Command: {flow['command'][:50]}...")
            for issue in issues:
                print(f"    ERROR: {issue}")
            print()

        if args.fix:
            print("Disabling broken flows...")
            data = get_flows()
            for flow in broken:
                disable_flow(flow['inject_id'], data)
            resp = requests.post(NODERED_URL, json=data,
                headers={'Content-Type': 'application/json',
                         'Node-RED-Deployment-Type': 'full'})
            print(f"Deploy: {resp.status_code}")

        if args.alert:
            msg = f"Node-RED Health: {len(broken)} broken flows\n"
            for flow in broken[:3]:
                msg += f"- {flow['inject_name']}\n"
            send_alert(msg)
    else:
        print("All flows OK")


if __name__ == '__main__':
    main()
