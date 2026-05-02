#!/usr/bin/env python3
"""
Dashboard Campaign Register

Automatically registers raspi campaigns with the pipeline dashboard.
Can be run manually or triggered when a new campaign is created.

Usage:
    python3 dashboard_campaign_register.py --scan          # Scan raspi for new campaigns
    python3 dashboard_campaign_register.py --add NAME      # Add specific campaign
    python3 dashboard_campaign_register.py --list          # List registered campaigns
    python3 dashboard_campaign_register.py --sync          # Sync all from raspi

Example:
    python3 dashboard_campaign_register.py --scan --auto-add
    python3 dashboard_campaign_register.py --add LUCIAN_ANOFM --path /opt/EMAIL/CAMPAIGNS/LUCIAN/
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
PIPELINE_JSON = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/pipeline.json"
RASPI_HOST = "192.168.100.20"
RASPI_CAMPAIGNS_DIR = "/opt/EMAIL/CAMPAIGNS"
DASHBOARD_SERVICE = "pipeline-dashboard.service"


def load_pipeline_config():
    """Load pipeline.json config."""
    with open(PIPELINE_JSON) as f:
        return json.load(f)


def save_pipeline_config(config):
    """Save pipeline.json config."""
    # Backup first
    backup = f"{PIPELINE_JSON}.bak"
    with open(PIPELINE_JSON) as f:
        with open(backup, 'w') as b:
            b.write(f.read())

    with open(PIPELINE_JSON, 'w') as f:
        json.dump(config, f, indent=2)


def run_ssh(cmd, timeout=10):
    """Run command on raspi via SSH."""
    full_cmd = f"ssh -o ConnectTimeout=5 {RASPI_HOST} '{cmd}'"
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"


def restart_dashboard():
    """Restart the pipeline dashboard service."""
    result = subprocess.run(['sudo', 'systemctl', 'restart', DASHBOARD_SERVICE],
                          capture_output=True, text=True)
    return result.returncode == 0


def scan_raspi_campaigns():
    """Scan raspi for campaign directories."""
    success, output, error = run_ssh(f"ls -d {RASPI_CAMPAIGNS_DIR}/*/")
    if not success:
        print(f"Failed to scan raspi: {error}")
        return []

    campaigns = []
    for line in output.strip().split('\n'):
        if not line:
            continue
        path = line.rstrip('/')
        name = os.path.basename(path)

        # Check if it has a sender script
        success2, scripts, _ = run_ssh(f"ls {path}/*_sender.py 2>/dev/null || echo ''")
        if not scripts.strip():
            continue

        # Get script name
        script_name = os.path.basename(scripts.strip().split('\n')[0]) if scripts.strip() else None

        # Check for status.json
        success3, status_content, _ = run_ssh(f"cat {path}/status.json 2>/dev/null || echo ''")
        has_status = bool(status_content.strip() and status_content.strip().startswith('{'))

        # Try to parse status for more info
        status_data = {}
        if has_status:
            try:
                status_data = json.loads(status_content)
            except:
                pass

        campaigns.append({
            'name': name.lower(),
            'path': f"{path}/",
            'script': script_name,
            'has_status': has_status,
            'status_data': status_data
        })

    return campaigns


def get_registered_campaigns():
    """Get campaigns already registered in dashboard."""
    config = load_pipeline_config()
    return config.get('raspi_campaigns', {})


def detect_campaign_config(campaign_info):
    """Auto-detect campaign configuration from status.json or script."""
    status = campaign_info.get('status_data', {})
    path = campaign_info['path']

    # Defaults
    config = {
        'host': RASPI_HOST,
        'path': path,
        'script': campaign_info.get('script', 'sender.py'),
        'status_file': 'status.json',
        'business_hours': '8:00-18:00 Mon-Fri',
        'senders': {
            'gmail': {'email': 'unknown', 'limit': 100},
            'brevo': {'email': 'unknown', 'limit': 290}
        },
        'cron': '40 8,12,16 * * *',
        'daily_capacity': 390,
        'registered_date': datetime.now().strftime('%Y-%m-%d')
    }

    # Override from status.json if available
    if status:
        if 'gmail_limit' in status:
            config['senders']['gmail']['limit'] = status['gmail_limit']
        if 'brevo_limit' in status:
            config['senders']['brevo']['limit'] = status['brevo_limit']
        if 'business_hours' in status:
            config['business_hours'] = status['business_hours']
        config['daily_capacity'] = status.get('gmail_limit', 100) + status.get('brevo_limit', 290)

    return config


def add_campaign(name, path=None, config=None, auto_detect=True):
    """Add a campaign to the dashboard."""
    pipeline = load_pipeline_config()

    if 'raspi_campaigns' not in pipeline:
        pipeline['raspi_campaigns'] = {}

    # Normalize name
    name_key = name.lower().replace(' ', '_').replace('-', '_')

    if name_key in pipeline['raspi_campaigns']:
        print(f"Campaign {name_key} already registered")
        return False

    # Build config
    if config:
        camp_config = config
    elif auto_detect and path:
        # Scan for info
        campaigns = scan_raspi_campaigns()
        found = None
        for c in campaigns:
            if c['path'].rstrip('/') == path.rstrip('/'):
                found = c
                break
        if found:
            camp_config = detect_campaign_config(found)
        else:
            camp_config = {
                'host': RASPI_HOST,
                'path': path,
                'script': f"{name_key}_sender.py",
                'status_file': 'status.json',
                'business_hours': '8:00-18:00 Mon-Fri',
                'senders': {
                    'gmail': {'email': 'unknown', 'limit': 100},
                    'brevo': {'email': 'unknown', 'limit': 290}
                },
                'cron': '40 8,12,16 * * *',
                'daily_capacity': 390,
                'registered_date': datetime.now().strftime('%Y-%m-%d')
            }
    else:
        print("Need --path or --config to add campaign")
        return False

    pipeline['raspi_campaigns'][name_key] = camp_config
    save_pipeline_config(pipeline)
    print(f"Added campaign: {name_key}")
    return True


def sync_campaigns(auto_add=False, dry_run=False):
    """Sync raspi campaigns with dashboard."""
    print("Scanning raspi for campaigns...")
    raspi_campaigns = scan_raspi_campaigns()

    print(f"Found {len(raspi_campaigns)} campaigns on raspi:")
    for c in raspi_campaigns:
        status_icon = "✓" if c['has_status'] else "✗"
        print(f"  [{status_icon}] {c['name']}: {c['path']}")

    registered = get_registered_campaigns()
    print(f"\nCurrently registered: {len(registered)}")
    for name in registered:
        print(f"  {name}")

    # Find new campaigns
    new_campaigns = []
    for c in raspi_campaigns:
        name_key = c['name'].lower().replace(' ', '_').replace('-', '_')
        if name_key not in registered:
            new_campaigns.append(c)

    if not new_campaigns:
        print("\nNo new campaigns to register")
        return

    print(f"\nNew campaigns found: {len(new_campaigns)}")
    for c in new_campaigns:
        print(f"  {c['name']}: {c['path']}")

    if auto_add and not dry_run:
        print("\nAuto-adding campaigns...")
        for c in new_campaigns:
            config = detect_campaign_config(c)
            add_campaign(c['name'], config=config)

        print("\nRestarting dashboard...")
        if restart_dashboard():
            print("Dashboard restarted successfully")
        else:
            print("Failed to restart dashboard (may need sudo)")
    elif dry_run:
        print("\n[DRY RUN] Would add these campaigns")
    else:
        print("\nUse --auto-add to register these campaigns")


def list_campaigns():
    """List all registered raspi campaigns."""
    config = load_pipeline_config()
    raspi_camps = config.get('raspi_campaigns', {})

    if not raspi_camps:
        print("No raspi campaigns registered")
        return

    print(f"Registered raspi campaigns ({len(raspi_camps)}):")
    print("-" * 70)

    for name, cfg in raspi_camps.items():
        print(f"\n{name.upper()}")
        print(f"  Path: {cfg.get('path', 'N/A')}")
        print(f"  Script: {cfg.get('script', 'N/A')}")
        print(f"  Business hours: {cfg.get('business_hours', 'N/A')}")
        print(f"  Daily capacity: {cfg.get('daily_capacity', 'N/A')}")
        print(f"  Cron: {cfg.get('cron', 'N/A')}")

        # Check if online
        success, status, _ = run_ssh(f"cat {cfg.get('path', '')}{cfg.get('status_file', 'status.json')} 2>/dev/null")
        if success and status:
            try:
                data = json.loads(status)
                gmail = data.get('gmail_today', 0)
                brevo = data.get('brevo_today', 0)
                remaining = data.get('remaining', '?')
                print(f"  Status: ONLINE (Gmail: {gmail}, Brevo: {brevo}, Remaining: {remaining})")
            except:
                print("  Status: ONLINE (status parse error)")
        else:
            print("  Status: OFFLINE")


def remove_campaign(name):
    """Remove a campaign from the dashboard."""
    config = load_pipeline_config()
    name_key = name.lower().replace(' ', '_').replace('-', '_')

    if name_key not in config.get('raspi_campaigns', {}):
        print(f"Campaign {name_key} not found")
        return False

    del config['raspi_campaigns'][name_key]
    save_pipeline_config(config)
    print(f"Removed campaign: {name_key}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Dashboard Campaign Register')
    parser.add_argument('--scan', action='store_true', help='Scan raspi for campaigns')
    parser.add_argument('--sync', action='store_true', help='Sync raspi campaigns with dashboard')
    parser.add_argument('--list', action='store_true', help='List registered campaigns')
    parser.add_argument('--add', metavar='NAME', help='Add a campaign')
    parser.add_argument('--remove', metavar='NAME', help='Remove a campaign')
    parser.add_argument('--path', help='Campaign path on raspi')
    parser.add_argument('--auto-add', action='store_true', help='Auto-add new campaigns')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--restart', action='store_true', help='Restart dashboard service')
    args = parser.parse_args()

    if args.scan:
        campaigns = scan_raspi_campaigns()
        print(f"Found {len(campaigns)} campaigns on raspi:")
        for c in campaigns:
            status_icon = "✓" if c['has_status'] else "✗"
            print(f"  [{status_icon}] {c['name']}: {c['path']} ({c.get('script', 'no script')})")
        return

    if args.sync:
        sync_campaigns(auto_add=args.auto_add, dry_run=args.dry_run)
        return

    if args.list:
        list_campaigns()
        return

    if args.add:
        success = add_campaign(args.add, path=args.path)
        if success and not args.dry_run:
            print("\nRestarting dashboard...")
            if restart_dashboard():
                print("Dashboard restarted successfully")
            else:
                print("Failed to restart dashboard (may need sudo)")
        return

    if args.remove:
        success = remove_campaign(args.remove)
        if success:
            print("\nRestarting dashboard...")
            if restart_dashboard():
                print("Dashboard restarted successfully")
            else:
                print("Failed to restart dashboard (may need sudo)")
        return

    if args.restart:
        print("Restarting dashboard...")
        if restart_dashboard():
            print("Dashboard restarted successfully")
        else:
            print("Failed to restart dashboard (may need sudo)")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
