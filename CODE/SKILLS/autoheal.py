#!/usr/bin/env python3
"""
Autoheal - Automatically fix common issues before alerting.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

LOG_FILE = Path('/opt/ACTIVE/INFRA/LOGS/autoheal.log')

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def run(cmd):
    """Run command and return success."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0

def heal_docker(container):
    """Restart a dead container."""
    log(f"HEALING: Restarting docker {container}")
    if run(f"docker start {container}"):
        log(f"  ✓ {container} started")
        return True
    else:
        log(f"  ✗ Failed to start {container}")
        return False

def heal_nodered():
    """Restart Node-RED."""
    log("HEALING: Restarting Node-RED")
    if run("sudo systemctl restart nodered"):
        log("  ✓ Node-RED restarted")
        return True
    else:
        log("  ✗ Failed to restart Node-RED")
        return False

def heal_postgres():
    """Restart PostgreSQL."""
    log("HEALING: Restarting PostgreSQL")
    if run("sudo systemctl restart postgresql"):
        log("  ✓ PostgreSQL restarted")
        return True
    else:
        log("  ✗ Failed to restart PostgreSQL")
        return False

def heal_campaign_lock():
    """Clear stale campaign lock (>2 hours old)."""
    lock_file = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK')
    if lock_file.exists():
        mtime = datetime.fromtimestamp(lock_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        if age_hours > 2:
            log(f"HEALING: Clearing stale campaign lock ({age_hours:.1f}h old)")
            lock_file.unlink()
            log("  ✓ Lock cleared")
            return True
    return False

def heal_disk():
    """Clean up old logs if disk >85%."""
    result = subprocess.run(['df', '--output=pcent', '/'], capture_output=True, text=True)
    usage = int(result.stdout.strip().split('\n')[1].replace('%', ''))
    
    if usage > 85:
        log(f"HEALING: Disk at {usage}%, cleaning old logs")
        # Delete logs older than 7 days
        run("find /opt/ACTIVE/INFRA/LOGS -name '*.log' -mtime +7 -delete")
        # Delete old backups
        run("find /opt/ACTIVE/INFRA/BACKUPS -type f -mtime +30 -delete")
        log("  ✓ Old logs cleaned")
        return True
    return False

def heal_stuck_scraper(name):
    """Kill and restart a stuck scraper."""
    log(f"HEALING: Restarting stuck scraper {name}")
    # Kill any existing process
    run(f"pkill -f '{name}'")
    time.sleep(2)
    # Don't auto-restart - just kill. Cron/Node-RED will restart on schedule.
    log(f"  ✓ Killed stuck {name}")
    return True

def check_heartbeats():
    """Check for stuck scrapers via heartbeat files."""
    import time as t
    heartbeat_dir = Path('/tmp/scraper_heartbeats')
    stuck = []

    if not heartbeat_dir.exists():
        return stuck

    now = t.time()
    for hb_file in heartbeat_dir.glob('*.heartbeat'):
        try:
            content = hb_file.read_text().strip().split('\n')
            timestamp = float(content[0])
            age_minutes = (now - timestamp) / 60

            if age_minutes > 15:  # 15 min stale = stuck
                stuck.append(hb_file.stem)
                # Clean up the heartbeat file
                hb_file.unlink()
        except:
            pass

    return stuck

def check_and_heal():
    """Main healing loop."""
    healed = []
    failed = []

    # 0. Stuck scrapers (heartbeat check)
    stuck_scrapers = check_heartbeats()
    for scraper in stuck_scrapers:
        if heal_stuck_scraper(scraper):
            healed.append(f"Stuck scraper: {scraper}")
        else:
            failed.append(f"Stuck scraper: {scraper}")

    # 1. Docker containers
    critical_containers = ['odoo', 'odoo-db', 'freescout', 'freescout-db']
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                          capture_output=True, text=True)
    running = result.stdout.strip().split('\n')
    
    for container in critical_containers:
        if container not in running:
            if heal_docker(container):
                healed.append(f"Docker: {container}")
            else:
                failed.append(f"Docker: {container}")
    
    # 2. Node-RED
    result = subprocess.run(['systemctl', 'is-active', 'nodered'], 
                          capture_output=True, text=True)
    if result.stdout.strip() != 'active':
        if heal_nodered():
            healed.append("Node-RED")
        else:
            failed.append("Node-RED")
    
    # 3. PostgreSQL
    result = subprocess.run(['systemctl', 'is-active', 'postgresql'], 
                          capture_output=True, text=True)
    if result.stdout.strip() != 'active':
        if heal_postgres():
            healed.append("PostgreSQL")
        else:
            failed.append("PostgreSQL")
    
    # 4. Campaign lock
    if heal_campaign_lock():
        healed.append("Campaign lock")
    
    # 5. Disk space
    if heal_disk():
        healed.append("Disk cleanup")
    
    return healed, failed

def main():
    healed, failed = check_and_heal()
    
    if healed:
        msg = f"🔧 AUTOHEAL ({datetime.now():%H:%M})\n\nFixed:\n"
        msg += "\n".join(f"✓ {h}" for h in healed)
        log(msg.replace('\n', ' | '))
        send_telegram(msg)
    
    if failed:
        msg = f"🚨 AUTOHEAL FAILED ({datetime.now():%H:%M})\n\nCould not fix:\n"
        msg += "\n".join(f"✗ {f}" for f in failed)
        log(msg.replace('\n', ' | '))
        send_telegram(msg)
        return 1
    
    if not healed and not failed:
        print(f"[{datetime.now():%H:%M}] All systems healthy, nothing to heal")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
