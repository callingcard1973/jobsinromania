#!/usr/bin/env python3
"""
Disk Guardian - Proactive disk space management

Features:
1. Monitors disk usage on raspi and raspibig
2. Sends Telegram alerts at warning (80%) and critical (90%) thresholds
3. Auto-triggers cleanup when disk exceeds threshold
4. Runs every hour via cron
5. Prevents backup accumulation

Thresholds:
- 70%: Info (logged only)
- 80%: Warning (Telegram alert)
- 90%: Critical (Telegram alert + auto-cleanup)
- 95%: Emergency (aggressive cleanup + loud alerts)
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuration
MACHINES = {
    'raspibig': {'host': 'localhost', 'ip': '192.168.100.21'},
    'raspi': {'host': 'raspi', 'ip': '192.168.100.20'}
}

THRESHOLDS = {
    'info': 70,
    'warning': 80,
    'critical': 90,
    'emergency': 95
}

STATE_FILE = Path("/opt/LOGS/disk_guardian_state.json")
LOG_FILE = Path("/opt/LOGS/disk_guardian.log")
CLEANER_SCRIPT = "/opt/ACTIVE/INFRA/SKILLS/system_cleaner.py"

# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')


def log(msg: str, level: str = 'INFO'):
    """Log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


def run_cmd(cmd: str, host: str = 'localhost', timeout: int = 30) -> str:
    """Run command locally or via SSH"""
    try:
        if host == 'localhost':
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(['ssh', host, cmd], capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def get_disk_usage(host: str) -> dict:
    """Get disk usage for root filesystem"""
    output = run_cmd("df -B1 / | tail -1", host)
    if 'ERROR' in output:
        return {'percent': 0, 'used': 0, 'avail': 0, 'total': 0}

    parts = output.split()
    if len(parts) >= 5:
        return {
            'total': int(parts[1]),
            'used': int(parts[2]),
            'avail': int(parts[3]),
            'percent': int(parts[4].replace('%', ''))
        }
    return {'percent': 0, 'used': 0, 'avail': 0, 'total': 0}


def format_bytes(b: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(b) < 1024.0:
            return f"{b:.1f}{unit}"
        b /= 1024.0
    return f"{b:.1f}PB"


def send_telegram(message: str) -> bool:
    """Send Telegram alert"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        # Try to load from common locations
        env_files = ['/opt/EMAIL/.env', '/opt/ACTIVE/INFRA/.env', '/home/tudor/.env']
        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    with open(env_file) as f:
                        for line in f:
                            if line.startswith('TELEGRAM_BOT_TOKEN='):
                                token = line.split('=', 1)[1].strip().strip('"\'')
                            elif line.startswith('TELEGRAM_CHAT_ID='):
                                chat_id = line.split('=', 1)[1].strip().strip('"\'')
                    if token and chat_id:
                        break
                except:
                    pass
        else:
            log("No Telegram credentials found", "WARNING")
            return False
    else:
        token = TELEGRAM_BOT_TOKEN
        chat_id = TELEGRAM_CHAT_ID

    try:
        import urllib.request
        import urllib.parse

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }).encode()

        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log(f"Telegram send failed: {e}", "ERROR")
        return False


def load_state() -> dict:
    """Load previous state"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {'alerts_sent': {}, 'last_cleanup': {}}


def save_state(state: dict):
    """Save state"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Failed to save state: {e}", "ERROR")


def run_cleanup(machine: str, host: str, aggressive: bool = False) -> bool:
    """Run cleanup script"""
    log(f"Running cleanup on {machine} (aggressive={aggressive})", "INFO")

    cmd = f"python3 {CLEANER_SCRIPT}"
    if machine == 'raspi':
        cmd += " --raspi"
    elif machine == 'raspibig':
        cmd += " --raspibig"

    if host == 'localhost':
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    else:
        result = subprocess.run(['ssh', host, cmd], capture_output=True, text=True, timeout=300)

    if aggressive and machine == 'raspi':
        # Extra aggressive cleanup for raspi
        aggressive_cmds = [
            "find /opt/BACKUPS -name '*.gz' -mtime +3 -delete",
            "find /opt/LOGS -name '*.log' -mtime +3 -delete",
            "find /tmp -type f -mtime +1 -delete 2>/dev/null",
            "sudo journalctl --vacuum-time=1d",
        ]
        for cmd in aggressive_cmds:
            run_cmd(cmd, host)

    return result.returncode == 0


def check_machine(machine: str, config: dict, state: dict) -> dict:
    """Check a single machine and take action if needed"""
    host = config['host']
    disk = get_disk_usage(host)
    percent = disk['percent']

    result = {
        'machine': machine,
        'percent': percent,
        'avail': disk['avail'],
        'level': 'ok',
        'action': None
    }

    # Determine severity level
    if percent >= THRESHOLDS['emergency']:
        result['level'] = 'emergency'
    elif percent >= THRESHOLDS['critical']:
        result['level'] = 'critical'
    elif percent >= THRESHOLDS['warning']:
        result['level'] = 'warning'
    elif percent >= THRESHOLDS['info']:
        result['level'] = 'info'

    # Check if we already alerted for this level today
    today = datetime.now().strftime("%Y-%m-%d")
    alert_key = f"{machine}_{result['level']}_{today}"
    already_alerted = state['alerts_sent'].get(alert_key, False)

    # Take action based on level
    if result['level'] == 'emergency':
        # Emergency: aggressive cleanup + loud alert
        if not already_alerted:
            msg = (f"🚨 <b>EMERGENCY: {machine.upper()}</b>\n"
                   f"Disk at {percent}% ({format_bytes(disk['avail'])} free)\n"
                   f"Running aggressive cleanup...")
            send_telegram(msg)
            state['alerts_sent'][alert_key] = True

        run_cleanup(machine, host, aggressive=True)
        result['action'] = 'aggressive_cleanup'

    elif result['level'] == 'critical':
        # Critical: auto cleanup + alert
        if not already_alerted:
            msg = (f"⚠️ <b>CRITICAL: {machine.upper()}</b>\n"
                   f"Disk at {percent}% ({format_bytes(disk['avail'])} free)\n"
                   f"Running auto-cleanup...")
            send_telegram(msg)
            state['alerts_sent'][alert_key] = True

        run_cleanup(machine, host, aggressive=False)
        result['action'] = 'auto_cleanup'

    elif result['level'] == 'warning':
        # Warning: alert only
        if not already_alerted:
            msg = (f"⚡ <b>WARNING: {machine.upper()}</b>\n"
                   f"Disk at {percent}% ({format_bytes(disk['avail'])} free)\n"
                   f"Consider running cleanup.")
            send_telegram(msg)
            state['alerts_sent'][alert_key] = True
        result['action'] = 'alert_sent'

    elif result['level'] == 'info':
        log(f"{machine}: {percent}% disk usage", "INFO")

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Disk Guardian - Proactive disk management')
    parser.add_argument('--check', action='store_true', help='Check disk usage (default)')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--test-alert', action='store_true', help='Send test Telegram alert')
    parser.add_argument('--force-cleanup', action='store_true', help='Force cleanup regardless of disk level')
    parser.add_argument('--cron', action='store_true', help='Quiet mode for cron')
    args = parser.parse_args()

    if args.test_alert:
        if send_telegram("🧪 Disk Guardian test alert - everything is working!"):
            print("Test alert sent successfully")
        else:
            print("Failed to send test alert")
        return

    if args.status:
        print("\n=== DISK GUARDIAN STATUS ===\n")
        for machine, config in MACHINES.items():
            disk = get_disk_usage(config['host'])
            level = 'OK'
            if disk['percent'] >= THRESHOLDS['emergency']:
                level = '🚨 EMERGENCY'
            elif disk['percent'] >= THRESHOLDS['critical']:
                level = '⚠️ CRITICAL'
            elif disk['percent'] >= THRESHOLDS['warning']:
                level = '⚡ WARNING'

            print(f"{machine.upper():12} {disk['percent']:3}% ({format_bytes(disk['avail']):>8} free) {level}")
        print()
        return

    if args.force_cleanup:
        for machine, config in MACHINES.items():
            run_cleanup(machine, config['host'], aggressive=False)
        return

    # Default: check and act
    state = load_state()
    results = []

    for machine, config in MACHINES.items():
        result = check_machine(machine, config, state)
        results.append(result)

        if not args.cron and result['level'] != 'ok':
            log(f"{machine}: {result['percent']}% - {result['level']} - action: {result['action']}")

    save_state(state)

    # Summary for non-cron mode
    if not args.cron:
        print("\n=== DISK GUARDIAN CHECK ===")
        for r in results:
            status = '✓' if r['level'] == 'ok' else '!'
            print(f"  {status} {r['machine']:12} {r['percent']:3}% ({format_bytes(r['avail']):>8} free)")
        print()


if __name__ == '__main__':
    main()
