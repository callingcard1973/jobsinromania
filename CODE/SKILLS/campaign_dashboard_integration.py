#!/usr/bin/env python3
"""
Campaign Dashboard Integration - Auto-integrate new campaigns

Auto-detects new campaign configs in UNIFIED/configs/ directory and:
1. Adds entry to pipeline.json
2. Creates nginx redirects
3. Restarts services (nginx, pipeline dashboard)

Usage:
  python3 campaign_dashboard_integration.py --status          # Current status
  python3 campaign_dashboard_integration.py --sync            # Sync configs to pipeline
  python3 campaign_dashboard_integration.py --check-nginx     # Verify nginx config
  python3 campaign_dashboard_integration.py --reload-nginx    # Reload nginx
  python3 campaign_dashboard_integration.py --dry-run         # Preview changes

Docs: /opt/ACTIVE/CLAUDE.md
"""

import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime

# Config paths
CONFIGS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs")
PIPELINE_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/pipeline.json")
NGINX_FILE = Path("/etc/nginx/sites-enabled/raspibig")
LOG_FILE = Path("/opt/ACTIVE/INFRA/LOGS/campaign_integration.log")

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().isoformat()
    msg = f"[{timestamp}] {message}"
    print(msg)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')

def read_pipeline():
    """Load pipeline.json"""
    with open(PIPELINE_FILE) as f:
        return json.load(f)

def write_pipeline(data):
    """Save pipeline.json with pretty formatting"""
    with open(PIPELINE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def read_config(config_file):
    """Load campaign config file"""
    with open(config_file) as f:
        return json.load(f)

def get_total_contacts(campaign_name, config):
    """Count contacts in campaign database"""
    db_info = config.get('db', {})
    table_name = config.get('tables', {}).get('contacts', f'{campaign_name}_contacts')

    host = db_info.get('host', 'localhost')
    dbname = db_info.get('dbname', 'interjob_master')
    user = db_info.get('user', 'tudor')
    password = db_info.get('password', 'tudor')

    try:
        cmd = [
            'psql', '-h', host, '-U', user, '-d', dbname,
            '-tc', f'SELECT COUNT(*) as count FROM {table_name};'
        ]
        env = {'PGPASSWORD': password}
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

        if result.returncode == 0:
            count = int(result.stdout.strip())
            return count
        else:
            log(f"  WARNING: Could not count contacts for {campaign_name}: {result.stderr}")
            return 0
    except Exception as e:
        log(f"  WARNING: Error counting contacts for {campaign_name}: {e}")
        return 0

def get_existing_campaigns(pipeline):
    """Get list of campaign names currently in pipeline.json"""
    return set(pipeline.get('campaigns', {}).keys())

def get_config_campaigns():
    """Get list of campaign configs available"""
    campaigns = {}

    if not CONFIGS_DIR.exists():
        log(f"ERROR: Config directory {CONFIGS_DIR} does not exist")
        return campaigns

    for config_file in sorted(CONFIGS_DIR.glob('*.json')):
        campaign_name = config_file.stem
        try:
            config = read_config(config_file)
            campaigns[campaign_name] = {
                'file': config_file,
                'config': config,
                'campaign_name': campaign_name
            }
        except Exception as e:
            log(f"  WARNING: Could not load config {config_file}: {e}")

    return campaigns

def build_campaign_entry(campaign_name, config):
    """Build pipeline.json campaign entry"""
    db_info = config.get('db', {})
    tables = config.get('tables', {})

    # Count total contacts
    total_contacts = get_total_contacts(campaign_name, config)

    # Estimate daily capacity (conservative: 90-200 emails/day for most campaigns)
    daily_limit = config.get('sectors', {}).get('ALL', {}).get('daily_limit', 90)

    entry = {
        "config": f"/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/{campaign_name}.json",
        "service": f"campaign-{campaign_name}",
        "db": {
            "host": db_info.get('host', 'localhost'),
            "dbname": db_info.get('dbname', 'interjob_master'),
            "user": db_info.get('user', 'tudor'),
            "password": db_info.get('password', 'tudor')
        },
        "tables": {
            "contacts": tables.get('contacts', f'{campaign_name}_contacts'),
            "send_log": tables.get('send_log', f'{campaign_name}_send_log'),
            "responses": tables.get('responses', f'{campaign_name}_responses'),
            "dnc": tables.get('dnc', f'{campaign_name}_dnc'),
            "conversions": tables.get('conversions', 'conversions')
        },
        "total_contacts": total_contacts,
        "daily_capacity": daily_limit,
        "status_column": "campaign_status"
    }

    return entry

def sync_pipeline(dry_run=False):
    """Sync campaign configs to pipeline.json"""
    log("Starting campaign sync...")

    pipeline = read_pipeline()
    existing = get_existing_campaigns(pipeline)
    configs = get_config_campaigns()

    new_campaigns = set(configs.keys()) - existing
    removed_campaigns = existing - set(configs.keys())

    if not new_campaigns and not removed_campaigns:
        log("  No changes needed")
        return True

    # Add new campaigns
    for campaign_name in sorted(new_campaigns):
        log(f"  Adding campaign: {campaign_name}")
        config = configs[campaign_name]['config']
        entry = build_campaign_entry(campaign_name, config)

        if not dry_run:
            pipeline['campaigns'][campaign_name] = entry
            log(f"    ✓ Added with {entry['total_contacts']} contacts, {entry['daily_capacity']}/day capacity")

    # Warn about removed campaigns (don't auto-delete)
    for campaign_name in sorted(removed_campaigns):
        log(f"  WARNING: Campaign {campaign_name} in pipeline but config missing")

    if not dry_run and new_campaigns:
        write_pipeline(pipeline)
        log(f"  Saved pipeline.json with {len(new_campaigns)} new campaign(s)")

    return True

def update_nginx(dry_run=False):
    """Add nginx redirects for new campaigns"""
    log("Updating nginx configuration...")

    pipeline = read_pipeline()
    campaigns = list(pipeline.get('campaigns', {}).keys())

    # Read current nginx config
    if not NGINX_FILE.exists():
        log(f"ERROR: Nginx config {NGINX_FILE} not found")
        return False

    with open(NGINX_FILE) as f:
        nginx_content = f.read()

    # Check which redirects are missing
    missing_redirects = []
    for campaign in campaigns:
        location_pattern = f"location = /{campaign}/"
        if location_pattern not in nginx_content:
            missing_redirects.append(campaign)

    if not missing_redirects:
        log("  No missing redirects")
        return True

    # Build new redirects
    new_redirects = []
    for campaign in missing_redirects:
        new_redirects.append(f"    location = /{campaign}/ {{ return 302 /pipeline/campaign/{campaign}; }}")
        new_redirects.append(f"    location = /{campaign}  {{ return 302 /pipeline/campaign/{campaign}; }}")

    redirect_block = '\n'.join(new_redirects)

    # Find insertion point (after the comments about redirects)
    redirect_comment = "# Redirects: old campaign URLs -> pipeline"
    if redirect_comment not in nginx_content:
        log("ERROR: Could not find redirect comment in nginx config")
        return False

    # Insert new redirects before the "Executori dashboard" comment
    executori_comment = "# Executori dashboard"
    if executori_comment not in nginx_content:
        log("ERROR: Could not find executori comment in nginx config")
        return False

    new_content = nginx_content.replace(
        executori_comment,
        redirect_block + "\n\n    " + executori_comment
    )

    if not dry_run:
        # Backup original
        backup_file = NGINX_FILE.with_suffix('.bak')
        with open(backup_file, 'w') as f:
            f.write(nginx_content)
        log(f"  Backed up to {backup_file}")

        # Write new config
        with open(NGINX_FILE, 'w') as f:
            f.write(new_content)

        # Test config
        result = subprocess.run(['sudo', 'nginx', '-t'], capture_output=True, text=True)
        if result.returncode != 0:
            log(f"ERROR: Nginx config validation failed:")
            log(result.stderr)
            # Restore backup
            with open(backup_file) as f:
                with open(NGINX_FILE, 'w') as out:
                    out.write(f.read())
            log(f"  Restored from backup")
            return False

        log(f"  Nginx config OK")
        log(f"  Added redirects for: {', '.join(missing_redirects)}")
    else:
        log(f"  Would add redirects for: {', '.join(missing_redirects)}")

    return True

def reload_nginx(dry_run=False):
    """Reload nginx"""
    log("Reloading nginx...")

    if dry_run:
        log("  (dry-run) Would run: sudo systemctl reload nginx")
        return True

    result = subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], capture_output=True, text=True)
    if result.returncode == 0:
        log("  ✓ Nginx reloaded")
        return True
    else:
        log(f"ERROR: Failed to reload nginx: {result.stderr}")
        return False

def check_nginx():
    """Verify nginx redirects are correct"""
    log("Checking nginx configuration...")

    with open(NGINX_FILE) as f:
        nginx_content = f.read()

    pipeline = read_pipeline()
    campaigns = list(pipeline.get('campaigns', {}).keys())

    found = []
    missing = []

    for campaign in campaigns:
        location_pattern = f"location = /{campaign}/"
        if location_pattern in nginx_content:
            found.append(campaign)
        else:
            missing.append(campaign)

    log(f"  Found redirects: {len(found)}")
    for c in found:
        log(f"    ✓ {c}")

    if missing:
        log(f"  Missing redirects: {len(missing)}")
        for c in missing:
            log(f"    ✗ {c}")
        return False

    return True

def status():
    """Show current status"""
    log("Campaign Integration Status")
    log("=" * 50)

    pipeline = read_pipeline()
    configs = get_config_campaigns()

    existing = get_existing_campaigns(pipeline)
    new = set(configs.keys()) - existing

    log(f"Pipeline campaigns: {len(existing)}")
    log(f"Config files: {len(configs)}")

    if new:
        log(f"\nNew campaigns ready to sync:")
        for c in sorted(new):
            config = configs[c]['config']
            contacts = get_total_contacts(c, config)
            log(f"  + {c}: {contacts} contacts")
    else:
        log("\nAll campaigns synced")

    log("\nNginx redirects status:")
    with open(NGINX_FILE) as f:
        nginx_content = f.read()

    for campaign in sorted(existing):
        location_pattern = f"location = /{campaign}/"
        status = "✓" if location_pattern in nginx_content else "✗"
        log(f"  {status} {campaign}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Campaign Dashboard Integration')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--sync', action='store_true', help='Sync configs to pipeline')
    parser.add_argument('--check-nginx', action='store_true', help='Check nginx config')
    parser.add_argument('--reload-nginx', action='store_true', help='Reload nginx')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')

    args = parser.parse_args()

    if args.status:
        status()
    elif args.sync:
        if sync_pipeline(dry_run=args.dry_run) and not args.dry_run:
            if update_nginx(dry_run=False) and reload_nginx(dry_run=False):
                log("✓ Sync complete and nginx reloaded")
            else:
                log("✗ Nginx update failed")
        elif args.dry_run:
            update_nginx(dry_run=True)
            log("(dry-run) No changes applied")
    elif args.check_nginx:
        check_nginx()
    elif args.reload_nginx:
        reload_nginx(dry_run=args.dry_run)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
