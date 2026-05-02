#!/usr/bin/env python3
"""
Add Campaign to Dashboard - Quick campaign setup skill

Usage:
    python3 add_campaign_to_dash.py --name CAMPAIGN_NAME --contacts /path/to/contacts.csv --template /path/to/template.txt --sender a2_domain
    python3 add_campaign_to_dash.py --list  # List existing campaigns
    python3 add_campaign_to_dash.py --status CAMPAIGN_NAME  # Check campaign status

Examples:
    python3 add_campaign_to_dash.py --name meatworkers_pl --contacts /opt/.../contacts.csv --template /opt/.../template.txt --sender a2_meatworkers --limit 10
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

CONFIGS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")

def list_campaigns():
    """List all dashboard campaigns"""
    configs = sorted(CONFIGS_DIR.glob("*.json"))
    print(f"\n=== {len(configs)} CAMPAIGNS IN DASHBOARD ===\n")
    for c in configs:
        try:
            data = json.loads(c.read_text())
            name = data.get('campaign_name', c.stem)
            status = data.get('status', 'unknown')
            sender = data.get('sender', {})
            sender_type = sender.get('type', 'unknown') if isinstance(sender, dict) else 'unknown'
            total = data.get('metrics', {}).get('total_contacts', 0)
            print(f"  {name:30} | {status:10} | {sender_type:10} | {total:,} contacts")
        except:
            print(f"  {c.stem:30} | error reading config")
    print()

def check_status(name):
    """Check campaign status"""
    config_file = CONFIGS_DIR / f"{name}.json"
    if not config_file.exists():
        print(f"Campaign {name} not found in dashboard")
        return

    data = json.loads(config_file.read_text())
    print(f"\n=== {data.get('campaign_name', name)} ===")
    print(f"Status: {data.get('status', 'unknown')}")
    print(f"Sender: {data.get('sender', {}).get('email', 'unknown')}")
    print(f"Daily limit: {data.get('schedule', {}).get('daily_limit', 'unknown')}")
    print(f"Contacts: {data.get('metrics', {}).get('total_contacts', 0):,}")

    # Check contacts file
    db = data.get('db', {})
    if db.get('type') == 'csv' and db.get('file'):
        csv_file = Path(db['file'])
        if csv_file.exists():
            import csv
            with open(csv_file) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                sent = sum(1 for r in rows if r.get('sent') == '1')
                pending = len(rows) - sent
                print(f"Sent: {sent}, Pending: {pending}")
    print()

def create_campaign(name, contacts_csv, template_file, sender, limit=10, description=""):
    """Create a new campaign config"""

    # Validate inputs
    contacts_path = Path(contacts_csv)
    template_path = Path(template_file)

    if not contacts_path.exists():
        print(f"ERROR: Contacts file not found: {contacts_csv}")
        return False

    if not template_path.exists():
        print(f"ERROR: Template file not found: {template_file}")
        return False

    # Count contacts
    import csv
    with open(contacts_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        total = len(rows)

    # Detect sender type
    if sender.startswith('a2_'):
        sender_type = 'a2_smtp'
        domain = sender.replace('a2_', '') + '.eu'
        email = f"office@{domain}"
    elif sender.startswith('brevo_'):
        sender_type = 'brevo'
        domain = sender.replace('brevo_', '').replace('_', '.')
        email = f"office@{domain}"
    else:
        sender_type = 'unknown'
        email = sender
        domain = sender

    # Build config
    config = {
        "db": {
            "type": "csv",
            "file": str(contacts_path)
        },
        "campaign_name": name.upper(),
        "campaign_description": description or f"Campaign {name}",
        "templates_dir": str(template_path.parent) + "/",
        "logs_dir": str(template_path.parent.parent / "logs") + "/",
        "sender": {
            "type": sender_type,
            "email": email,
            "name": name.replace('_', ' ').title(),
            "daily_limit": limit
        },
        "template": {
            "file": template_path.name,
            "language": "EN"
        },
        "metrics": {
            "total_contacts": total
        },
        "schedule": {
            "enabled": True,
            "daily_limit": limit,
            "delay_seconds": 180,
            "run_time": "09:00"
        },
        "status": "active",
        "started": datetime.now().strftime("%Y-%m-%d"),
        "hide_charts": True
    }

    # Save config
    config_file = CONFIGS_DIR / f"{name}.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\n=== CAMPAIGN CREATED ===")
    print(f"Config: {config_file}")
    print(f"Name: {name.upper()}")
    print(f"Sender: {email} ({sender_type})")
    print(f"Contacts: {total:,}")
    print(f"Daily limit: {limit}")
    print(f"\nRestart dashboard to see changes:")
    print(f"  systemctl restart unified-dashboard")
    print()

    return True

def main():
    parser = argparse.ArgumentParser(description='Add campaign to dashboard')
    parser.add_argument('--list', action='store_true', help='List existing campaigns')
    parser.add_argument('--status', type=str, help='Check campaign status')
    parser.add_argument('--name', type=str, help='Campaign name')
    parser.add_argument('--contacts', type=str, help='Path to contacts CSV')
    parser.add_argument('--template', type=str, help='Path to template file')
    parser.add_argument('--sender', type=str, help='Sender ID (a2_domain or brevo_domain)')
    parser.add_argument('--limit', type=int, default=10, help='Daily send limit')
    parser.add_argument('--description', type=str, default='', help='Campaign description')

    args = parser.parse_args()

    if args.list:
        list_campaigns()
    elif args.status:
        check_status(args.status)
    elif args.name and args.contacts and args.template and args.sender:
        create_campaign(args.name, args.contacts, args.template, args.sender, args.limit, args.description)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
