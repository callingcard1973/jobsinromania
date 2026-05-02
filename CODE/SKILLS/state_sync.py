#!/usr/bin/env python3
"""
State Sync - Sync critical state files to raspi for failover.

Syncs:
- Campaign state files
- Scraper progress
- Node-RED flows
- Redis dump
- Configuration

Usage:
    python3 state_sync.py              # Full sync
    python3 state_sync.py --quick      # Quick sync (state only)
    python3 state_sync.py --status     # Check sync status
    python3 state_sync.py --restore    # Restore from raspi (failover)
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

# Configuration
RASPI_HOST = 'raspi'
RASPI_USER = 'tudor'
SYNC_DIR = '/opt/ACTIVE/INFRA/SYNC_STATE'  # Local staging
RASPI_SYNC_DIR = '/opt/ACTIVE/INFRA/SYNC_STATE'  # Remote destination

# What to sync
SYNC_ITEMS = {
    'campaign_states': {
        'source': '/opt/ACTIVE/EMAIL/CAMPAIGNS/*/state.json',
        'glob': True,
        'priority': 'high',
    },
    'campaign_states_hidden': {
        'source': '/opt/ACTIVE/EMAIL/CAMPAIGNS/*/.*.json',
        'glob': True,
        'priority': 'high',
    },
    'scraper_progress': {
        'source': '/opt/ACTIVE/OPENDATA/DATA/scraper_progress/',
        'priority': 'medium',
    },
    'nodered_flows': {
        'source': '/home/tudor/.node-red/flows.json',
        'priority': 'high',
    },
    'redis_dump': {
        'source': '/tmp/redis_dump.rdb',
        'cmd': 'redis-cli BGSAVE && sleep 2 && sudo cp /var/lib/redis/dump.rdb /tmp/redis_dump.rdb 2>/dev/null && sudo chmod 644 /tmp/redis_dump.rdb',
        'priority': 'high',
    },
    'email_env': {
        'source': '/opt/ACTIVE/EMAIL/CAMPAIGNS/.env',
        'priority': 'high',
    },
    'blacklist': {
        'source': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt',
        'priority': 'medium',
    },
    'crontab': {
        'source': '/tmp/crontab_backup.txt',
        'cmd': 'crontab -l > /tmp/crontab_backup.txt',
        'priority': 'low',
    },
}

STATUS_FILE = Path('/opt/ACTIVE/INFRA/SYNC_STATE/last_sync.json')

def run(cmd, check=True):
    """Run shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        return False
    return True

def sync_item(name, config):
    """Sync a single item to raspi."""
    source = config['source']

    # Run pre-command if needed
    if 'cmd' in config:
        run(config['cmd'], check=False)

    # Handle glob patterns
    if config.get('glob'):
        # Use rsync with glob
        cmd = f"rsync -avz --include='*/' --include='{Path(source).name}' --exclude='*' {Path(source).parent}/ {RASPI_USER}@{RASPI_HOST}:{RASPI_SYNC_DIR}/{name}/"
    else:
        # Direct rsync
        if Path(source).is_dir():
            cmd = f"rsync -avz {source}/ {RASPI_USER}@{RASPI_HOST}:{RASPI_SYNC_DIR}/{name}/"
        else:
            cmd = f"rsync -avz {source} {RASPI_USER}@{RASPI_HOST}:{RASPI_SYNC_DIR}/{name}/"

    return run(cmd, check=False)

def full_sync():
    """Sync all items to raspi."""
    print(f"[{datetime.now():%H:%M}] Starting full state sync to raspi...")

    # Ensure remote dir exists
    run(f"ssh {RASPI_USER}@{RASPI_HOST} 'mkdir -p {RASPI_SYNC_DIR}'", check=False)

    results = {}
    for name, config in SYNC_ITEMS.items():
        print(f"  Syncing {name}...", end=' ')
        success = sync_item(name, config)
        results[name] = success
        print("OK" if success else "FAILED")

    # Save status
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    status = {
        'last_sync': datetime.now().isoformat(),
        'results': results,
        'success': all(results.values()),
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n[{datetime.now():%H:%M}] Sync completed with errors: {', '.join(failed)}")
        return False
    else:
        print(f"\n[{datetime.now():%H:%M}] Sync completed successfully")
        return True

def quick_sync():
    """Sync only high-priority items."""
    print(f"[{datetime.now():%H:%M}] Quick sync (high priority only)...")

    run(f"ssh {RASPI_USER}@{RASPI_HOST} 'mkdir -p {RASPI_SYNC_DIR}'", check=False)

    for name, config in SYNC_ITEMS.items():
        if config.get('priority') == 'high':
            print(f"  Syncing {name}...", end=' ')
            success = sync_item(name, config)
            print("OK" if success else "FAILED")

    print(f"[{datetime.now():%H:%M}] Quick sync done")
    return True

def check_status():
    """Check sync status."""
    print(f"\n=== STATE SYNC STATUS ===\n")

    # Check last sync
    if STATUS_FILE.exists():
        status = json.loads(STATUS_FILE.read_text())
        last_sync = datetime.fromisoformat(status['last_sync'])
        age = datetime.now() - last_sync

        print(f"Last sync: {last_sync:%Y-%m-%d %H:%M}")
        print(f"Age: {age.total_seconds() / 3600:.1f} hours")
        print(f"Status: {'OK' if status['success'] else 'FAILED'}")

        if age > timedelta(hours=2):
            print("\n⚠️  WARNING: Sync is stale (>2 hours)")

        print(f"\nResults:")
        for name, success in status.get('results', {}).items():
            print(f"  {'✓' if success else '✗'} {name}")
    else:
        print("No sync status found. Run: python3 state_sync.py")

    # Check raspi connectivity
    print(f"\nRaspi connectivity: ", end='')
    result = subprocess.run(f"ssh {RASPI_USER}@{RASPI_HOST} 'echo OK'", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("OK")
    else:
        print("FAILED")

    # Check remote files
    print(f"\nRemote state directory:")
    subprocess.run(f"ssh {RASPI_USER}@{RASPI_HOST} 'ls -la {RASPI_SYNC_DIR}/ 2>/dev/null || echo \"Not found\"'", shell=True)

def restore_from_raspi():
    """Restore state from raspi (failover scenario)."""
    print(f"[{datetime.now():%H:%M}] RESTORING STATE FROM RASPI...")
    print("⚠️  This will overwrite local state files!")

    # Confirm
    confirm = input("Type 'RESTORE' to confirm: ")
    if confirm != 'RESTORE':
        print("Aborted")
        return False

    # Create backup first
    backup_dir = f"/opt/ACTIVE/INFRA/BACKUPS/pre_restore_{datetime.now():%Y%m%d_%H%M%S}"
    run(f"mkdir -p {backup_dir}")

    for name, config in SYNC_ITEMS.items():
        source = config['source']
        if not config.get('glob') and Path(source).exists():
            run(f"cp -r {source} {backup_dir}/", check=False)

    print(f"Backup created at: {backup_dir}")

    # Restore from raspi
    for name, config in SYNC_ITEMS.items():
        if config.get('priority') != 'high':
            continue

        source = config['source']
        print(f"  Restoring {name}...", end=' ')

        if config.get('glob'):
            # Can't easily restore glob patterns
            print("SKIP (glob)")
            continue

        if Path(source).is_dir():
            cmd = f"rsync -avz {RASPI_USER}@{RASPI_HOST}:{RASPI_SYNC_DIR}/{name}/ {source}/"
        else:
            Path(source).parent.mkdir(parents=True, exist_ok=True)
            cmd = f"rsync -avz {RASPI_USER}@{RASPI_HOST}:{RASPI_SYNC_DIR}/{name}/* {source}"

        success = run(cmd, check=False)
        print("OK" if success else "FAILED")

    print(f"\n[{datetime.now():%H:%M}] Restore completed")
    send_telegram(f"🔄 STATE RESTORED FROM RASPI\n\nBackup at: {backup_dir}")
    return True

def main():
    if len(sys.argv) < 2:
        full_sync()
    elif sys.argv[1] == '--quick':
        quick_sync()
    elif sys.argv[1] == '--status':
        check_status()
    elif sys.argv[1] == '--restore':
        restore_from_raspi()
    else:
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()
