#!/usr/bin/env python3
"""
Failover Manager - Automatic failover between raspibig and raspi.

RASPIBIG (primary): Runs scrapers, campaigns, Odoo
RASPI (standby): Takes over if raspibig down >10 min

Usage:
    # On raspibig - check status
    python3 failover_manager.py --status

    # On raspi - monitor and auto-failover
    python3 failover_manager.py --monitor

    # Manual failover to raspi
    python3 failover_manager.py --failover raspi

    # Manual failback to raspibig
    python3 failover_manager.py --failback

    # Test failover (dry run)
    python3 failover_manager.py --test
"""
import os
import sys
import json
import socket
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import time

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

# Configuration
RASPIBIG_IP = '192.168.100.21'
RASPI_IP = '192.168.100.20'
CURRENT_HOST = socket.gethostname()

# Failover settings
HEALTH_CHECK_INTERVAL = 60  # seconds
FAILOVER_THRESHOLD = 10  # minutes down before failover
FAILBACK_THRESHOLD = 5   # minutes up before failback

# State files
STATE_FILE = Path('/opt/ACTIVE/INFRA/SYNC_STATE/failover_state.json')
HEARTBEAT_FILE = Path('/opt/ACTIVE/INFRA/SYNC_STATE/heartbeat.json')

# Services to manage
CAMPAIGN_CRONS = [
    '0 9 * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND_AGENCIES/send_poland_brevo.py',
    '0 10 * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/TRANSPORT_EU/send_transport_brevo.py',
    '0 11 * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/send_factory_brevo.py',
    '0 12 * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/TOURISM_RO/send_tourism_brevo.py',
]

SCRAPER_CRONS = [
    '30 2 * * * /opt/ACTIVE/INFRA/SKILLS/backup_scheduler.sh denmark',
    '30 3 * * * /opt/ACTIVE/INFRA/SKILLS/backup_scheduler.sh sweden',
    '30 4 * * * /opt/ACTIVE/INFRA/SKILLS/backup_scheduler.sh norway',
]


def run(cmd, check=True):
    """Run shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def is_host_up(host, timeout=5):
    """Check if host is reachable."""
    success, _, _ = run(f"ping -c 1 -W {timeout} {host}")
    return success


def check_services(host):
    """Check if critical services are running on host."""
    if host == CURRENT_HOST or (host == 'raspibig' and CURRENT_HOST == 'raspibig'):
        # Local check
        checks = {
            'nodered': run("systemctl is-active nodered")[0],
            'postgresql': run("systemctl is-active postgresql")[0],
            'docker': run("docker ps -q | head -1")[0],
        }
    else:
        # Remote check
        checks = {
            'nodered': run(f"ssh {host} 'systemctl is-active nodered'")[0],
            'postgresql': run(f"ssh {host} 'systemctl is-active postgresql'")[0],
            'docker': run(f"ssh {host} 'docker ps -q | head -1'")[0],
        }
    return checks


def write_heartbeat():
    """Write heartbeat file (run on primary)."""
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'host': CURRENT_HOST,
        'timestamp': datetime.now().isoformat(),
        'epoch': time.time(),
        'services': check_services(CURRENT_HOST),
    }
    HEARTBEAT_FILE.write_text(json.dumps(data, indent=2))

    # Also sync to raspi
    run(f"rsync -az {HEARTBEAT_FILE} raspi:/opt/ACTIVE/INFRA/SYNC_STATE/")


def read_heartbeat(remote=False):
    """Read heartbeat from primary."""
    if remote:
        # Read from raspibig
        success, stdout, _ = run(f"ssh raspibig 'cat /opt/ACTIVE/INFRA/SYNC_STATE/heartbeat.json 2>/dev/null'")
        if success and stdout:
            return json.loads(stdout)
        return None
    else:
        if HEARTBEAT_FILE.exists():
            return json.loads(HEARTBEAT_FILE.read_text())
        return None


def get_state():
    """Get current failover state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        'mode': 'normal',  # normal, failover, failback_pending
        'primary': 'raspibig',
        'active': 'raspibig',
        'last_check': None,
        'failover_time': None,
        'down_since': None,
    }


def save_state(state):
    """Save failover state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state['last_check'] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def activate_standby():
    """Activate raspi as active node."""
    print("[FAILOVER] Activating raspi as primary...")

    # 1. Restore state from sync
    print("  Restoring campaign states...")
    run("rsync -az /opt/ACTIVE/INFRA/SYNC_STATE/campaign_states/ /opt/ACTIVE/EMAIL/CAMPAIGNS/")
    run("rsync -az /opt/ACTIVE/INFRA/SYNC_STATE/campaign_states_hidden/ /opt/ACTIVE/EMAIL/CAMPAIGNS/")

    # 2. Restore Node-RED flows
    print("  Restoring Node-RED flows...")
    run("cp /opt/ACTIVE/INFRA/SYNC_STATE/nodered_flows/flows.json ~/.node-red/flows.json")
    run("sudo systemctl restart nodered")

    # 3. Enable campaign crons
    print("  Enabling campaign crons...")
    success, current_cron, _ = run("crontab -l")
    if success:
        new_cron = current_cron
        for cron in CAMPAIGN_CRONS:
            if cron not in new_cron:
                new_cron += f"\n# FAILOVER ENABLED\n{cron}"
        run(f"echo '{new_cron}' | crontab -")

    # 4. Start watchdog
    print("  Starting watchdog...")
    run("nohup /opt/ACTIVE/INFRA/SKILLS/watchdog.sh > /opt/ACTIVE/INFRA/LOGS/watchdog.log 2>&1 &")

    print("[FAILOVER] Raspi is now ACTIVE")
    return True


def deactivate_standby():
    """Deactivate raspi, return to standby."""
    print("[FAILBACK] Deactivating raspi, returning to standby...")

    # 1. Disable campaign crons
    print("  Disabling campaign crons...")
    success, current_cron, _ = run("crontab -l")
    if success:
        new_cron = '\n'.join(
            line for line in current_cron.split('\n')
            if '# FAILOVER ENABLED' not in line and not any(c in line for c in CAMPAIGN_CRONS)
        )
        run(f"echo '{new_cron}' | crontab -")

    # 2. Sync state back to raspibig
    print("  Syncing state back to raspibig...")
    run("rsync -az /opt/ACTIVE/EMAIL/CAMPAIGNS/*/*.json raspibig:/opt/ACTIVE/EMAIL/CAMPAIGNS/")

    print("[FAILBACK] Raspi is now STANDBY")
    return True


def do_failover(dry_run=False):
    """Execute failover to raspi."""
    state = get_state()

    if state['active'] == 'raspi':
        print("Already in failover mode")
        return False

    msg = f"🚨 FAILOVER INITIATED\n\nRaspibig down, activating raspi\nTime: {datetime.now():%Y-%m-%d %H:%M}"
    print(msg)

    if dry_run:
        print("[DRY RUN] Would activate raspi")
        return True

    send_telegram(msg)

    if CURRENT_HOST == 'raspi':
        activate_standby()
    else:
        # Remote activation
        run("ssh raspi '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/failover_manager.py --activate'")

    state['mode'] = 'failover'
    state['active'] = 'raspi'
    state['failover_time'] = datetime.now().isoformat()
    save_state(state)

    send_telegram(f"✅ FAILOVER COMPLETE\n\nRaspi is now active\nCampaigns and monitoring resumed")
    return True


def do_failback(dry_run=False):
    """Execute failback to raspibig."""
    state = get_state()

    if state['active'] == 'raspibig':
        print("Already on raspibig")
        return False

    msg = f"🔄 FAILBACK INITIATED\n\nRaspibig recovered, returning control\nTime: {datetime.now():%Y-%m-%d %H:%M}"
    print(msg)

    if dry_run:
        print("[DRY RUN] Would deactivate raspi")
        return True

    send_telegram(msg)

    if CURRENT_HOST == 'raspi':
        deactivate_standby()
    else:
        run("ssh raspi '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/failover_manager.py --deactivate'")

    state['mode'] = 'normal'
    state['active'] = 'raspibig'
    state['failover_time'] = None
    state['down_since'] = None
    save_state(state)

    send_telegram(f"✅ FAILBACK COMPLETE\n\nRaspibig is now active\nRaspi returned to standby")
    return True


def monitor_loop():
    """Main monitoring loop (run on raspi)."""
    # Unbuffered output
    sys.stdout.reconfigure(line_buffering=True)

    print(f"[{datetime.now():%H:%M}] Starting failover monitor on {CURRENT_HOST}")
    print(f"  Primary: raspibig ({RASPIBIG_IP})")
    print(f"  Failover threshold: {FAILOVER_THRESHOLD} minutes")
    print(f"  Check interval: {HEALTH_CHECK_INTERVAL} seconds")
    print()
    sys.stdout.flush()

    consecutive_failures = 0
    consecutive_successes = 0

    while True:
        state = get_state()

        # Check raspibig health
        is_up = is_host_up(RASPIBIG_IP)
        services_ok = False

        if is_up:
            services = check_services('raspibig')
            services_ok = all(services.values())

        healthy = is_up and services_ok

        if healthy:
            consecutive_failures = 0
            consecutive_successes += 1

            if state['down_since']:
                state['down_since'] = None
                save_state(state)

            # Check for failback
            if state['active'] == 'raspi' and consecutive_successes >= FAILBACK_THRESHOLD:
                print(f"[{datetime.now():%H:%M}] Raspibig recovered for {FAILBACK_THRESHOLD}+ minutes")
                do_failback()
                consecutive_successes = 0
            else:
                print(f"[{datetime.now():%H:%M}] Raspibig: OK", flush=True)
        else:
            consecutive_successes = 0
            consecutive_failures += 1

            if not state['down_since']:
                state['down_since'] = datetime.now().isoformat()
                save_state(state)

            down_minutes = consecutive_failures
            print(f"[{datetime.now():%H:%M}] Raspibig: DOWN ({down_minutes} min)")

            # Check for failover
            if state['active'] == 'raspibig' and consecutive_failures >= FAILOVER_THRESHOLD:
                print(f"[{datetime.now():%H:%M}] Raspibig down for {FAILOVER_THRESHOLD}+ minutes")
                do_failover()
                consecutive_failures = 0

        time.sleep(HEALTH_CHECK_INTERVAL)


def show_status():
    """Show current failover status."""
    state = get_state()

    print(f"\n=== FAILOVER STATUS ({datetime.now():%H:%M}) ===\n")
    print(f"Current host: {CURRENT_HOST}")
    print(f"Mode: {state['mode']}")
    print(f"Active node: {state['active']}")
    print(f"Last check: {state.get('last_check', 'Never')}")

    if state.get('failover_time'):
        print(f"Failover since: {state['failover_time']}")
    if state.get('down_since'):
        print(f"Down since: {state['down_since']}")

    print(f"\n--- Host Status ---")

    # Check raspibig
    print(f"\nRaspibig ({RASPIBIG_IP}):")
    if is_host_up(RASPIBIG_IP):
        print(f"  Ping: OK")
        services = check_services('raspibig')
        for svc, ok in services.items():
            print(f"  {svc}: {'OK' if ok else 'DOWN'}")
    else:
        print(f"  Ping: DOWN")

    # Check raspi
    print(f"\nRaspi ({RASPI_IP}):")
    if is_host_up(RASPI_IP):
        print(f"  Ping: OK")
        if CURRENT_HOST == 'raspi':
            services = check_services('raspi')
        else:
            services = check_services('raspi')
        for svc, ok in services.items():
            print(f"  {svc}: {'OK' if ok else 'DOWN'}")
    else:
        print(f"  Ping: DOWN")

    # Heartbeat
    print(f"\n--- Heartbeat ---")
    hb = read_heartbeat()
    if hb:
        age = time.time() - hb.get('epoch', 0)
        print(f"  Last: {hb.get('timestamp', 'Unknown')}")
        print(f"  Age: {age:.0f} seconds")
        print(f"  Host: {hb.get('host', 'Unknown')}")
    else:
        print(f"  No heartbeat found")

    print()


def main():
    if len(sys.argv) < 2:
        show_status()
        return

    cmd = sys.argv[1]

    if cmd == '--status':
        show_status()

    elif cmd == '--monitor':
        monitor_loop()

    elif cmd == '--failover':
        target = sys.argv[2] if len(sys.argv) > 2 else 'raspi'
        if target == 'raspi':
            do_failover()
        else:
            print(f"Unknown target: {target}")

    elif cmd == '--failback':
        do_failback()

    elif cmd == '--test':
        print("=== DRY RUN TEST ===")
        print("\nTesting failover...")
        do_failover(dry_run=True)
        print("\nTesting failback...")
        do_failback(dry_run=True)
        print("\nTest complete")

    elif cmd == '--activate':
        activate_standby()

    elif cmd == '--deactivate':
        deactivate_standby()

    elif cmd == '--heartbeat':
        write_heartbeat()
        print("Heartbeat written")

    else:
        print(__doc__)


if __name__ == '__main__':
    main()
