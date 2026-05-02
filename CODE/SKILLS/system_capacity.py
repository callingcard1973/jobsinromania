#!/usr/bin/env python3
"""
System Capacity Skill - Monitor raspibig health and email capacity

Checks:
- CPU, Memory, Disk usage
- Running processes (scrapers, campaigns)
- Email contacts remaining per campaign
- Daily send capacity vs usage

Usage:
    system_capacity.py              # Full report
    system_capacity.py --health     # System health only
    system_capacity.py --email      # Email capacity only
    system_capacity.py --alert      # Only show problems
"""
import os
import sys
import json
import psutil
import subprocess
from datetime import datetime
from pathlib import Path
from glob import glob

# Thresholds
CPU_WARN = 70
CPU_CRIT = 90
MEM_WARN = 70
MEM_CRIT = 85
DISK_WARN = 80
DISK_CRIT = 90

# Paths
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
BLACKLIST_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt"

# Brevo daily limits
BREVO_SENDERS = {
    "AGRI": ("mivromania.info", 290),
    "ANOFM": ("interjob.ro", 290),
    "POLAND": ("expatsinromania.org", 290),
    "FACTORY_EU": ("buildjobs.eu", 290),
    "TOURISM_RO": ("mivromania.online", 290),
    "HORECA2026": ("factoryjobs.eu", 290),
    "CAREWORKERS": ("careworkers.eu", 290),
    "CIFN_NEPAL": ("cifn.info", 290),
    "CONSTRUCTION_RO": ("seicarescu.com", 290),
}


def get_system_health():
    """Get CPU, memory, disk usage."""
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Load average
    load1, load5, load15 = os.getloadavg()

    # Temperature (Raspberry Pi)
    temp = None
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            temp = int(f.read()) / 1000
    except:
        pass

    return {
        'cpu_percent': cpu,
        'cpu_status': 'CRIT' if cpu > CPU_CRIT else 'WARN' if cpu > CPU_WARN else 'OK',
        'mem_percent': mem.percent,
        'mem_used_gb': mem.used / (1024**3),
        'mem_total_gb': mem.total / (1024**3),
        'mem_status': 'CRIT' if mem.percent > MEM_CRIT else 'WARN' if mem.percent > MEM_WARN else 'OK',
        'disk_percent': disk.percent,
        'disk_free_gb': disk.free / (1024**3),
        'disk_status': 'CRIT' if disk.percent > DISK_CRIT else 'WARN' if disk.percent > DISK_WARN else 'OK',
        'load_1m': load1,
        'load_5m': load5,
        'load_15m': load15,
        'temp_c': temp,
    }


def get_running_processes():
    """Get running scrapers and campaign processes."""
    scrapers = []
    campaigns = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'scraper' in cmdline.lower() or 'anofm' in cmdline.lower():
                scrapers.append({
                    'pid': proc.info['pid'],
                    'cmd': cmdline[-60:],
                    'cpu': proc.info['cpu_percent'],
                    'mem': proc.info['memory_percent'],
                })
            elif 'send_' in cmdline or 'campaign' in cmdline.lower():
                campaigns.append({
                    'pid': proc.info['pid'],
                    'cmd': cmdline[-60:],
                    'cpu': proc.info['cpu_percent'],
                    'mem': proc.info['memory_percent'],
                })
        except:
            pass

    return scrapers, campaigns


def get_campaign_capacity():
    """Get email capacity for each campaign."""
    campaigns = {}
    today = datetime.now().strftime('%Y-%m-%d')

    for campaign, (sender, daily_limit) in BREVO_SENDERS.items():
        campaign_dir = CAMPAIGNS_DIR / campaign
        if not campaign_dir.exists():
            continue

        # Find state file
        state_files = list(campaign_dir.glob("*.json")) + list(campaign_dir.glob(".*.json"))
        state = {}
        for sf in state_files:
            try:
                with open(sf) as f:
                    state = json.load(f)
                break
            except:
                pass

        # Get sent count
        sent_list = state.get('sent', state.get('sent_emails', []))
        if isinstance(sent_list, dict):
            sent_list = list(sent_list.keys())
        total_sent = len(sent_list)

        # Get today's sent
        daily_sent = state.get('daily_sent', 0)
        last_date = state.get('last_date', '')
        if last_date != today:
            daily_sent = 0

        # Get remaining contacts
        remaining = 0
        for pattern in ['contacts/*.csv', 'segments/*.csv', '*.csv']:
            for csv_file in campaign_dir.glob(pattern):
                if '.bak' in str(csv_file):
                    continue
                try:
                    with open(csv_file) as f:
                        lines = len(f.readlines()) - 1  # minus header
                        remaining += max(0, lines)
                except:
                    pass

        remaining = max(0, remaining - total_sent)

        campaigns[campaign] = {
            'sender': sender,
            'daily_limit': daily_limit,
            'daily_sent': daily_sent,
            'daily_remaining': daily_limit - daily_sent,
            'total_sent': total_sent,
            'contacts_remaining': remaining,
            'days_left': remaining // daily_limit if daily_limit else 0,
        }

    return campaigns


def get_email_summary():
    """Get overall email capacity summary."""
    campaigns = get_campaign_capacity()

    total_daily_limit = sum(c['daily_limit'] for c in campaigns.values())
    total_daily_sent = sum(c['daily_sent'] for c in campaigns.values())
    total_remaining = sum(c['contacts_remaining'] for c in campaigns.values())

    # DNC count
    dnc_count = 0
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE) as f:
            dnc_count = len([l for l in f if l.strip()])

    return {
        'total_daily_limit': total_daily_limit,
        'total_daily_sent': total_daily_sent,
        'total_daily_available': total_daily_limit - total_daily_sent,
        'total_contacts_remaining': total_remaining,
        'dnc_count': dnc_count,
        'campaigns': campaigns,
    }


def print_health_report(health, scrapers, campaigns):
    """Print system health report."""
    print("=" * 60)
    print("SYSTEM HEALTH")
    print("=" * 60)

    # CPU
    status = health['cpu_status']
    icon = '!' if status != 'OK' else ' '
    print(f"{icon} CPU:  {health['cpu_percent']:5.1f}%  [{status}]")
    print(f"  Load: {health['load_1m']:.2f} / {health['load_5m']:.2f} / {health['load_15m']:.2f}")

    # Memory
    status = health['mem_status']
    icon = '!' if status != 'OK' else ' '
    print(f"{icon} MEM:  {health['mem_percent']:5.1f}%  [{status}]  ({health['mem_used_gb']:.1f}/{health['mem_total_gb']:.1f} GB)")

    # Disk
    status = health['disk_status']
    icon = '!' if status != 'OK' else ' '
    print(f"{icon} DISK: {health['disk_percent']:5.1f}%  [{status}]  ({health['disk_free_gb']:.1f} GB free)")

    # Temperature
    if health['temp_c']:
        temp_status = 'WARN' if health['temp_c'] > 70 else 'OK'
        icon = '!' if temp_status != 'OK' else ' '
        print(f"{icon} TEMP: {health['temp_c']:5.1f}C  [{temp_status}]")

    # Running processes
    print(f"\nRunning: {len(scrapers)} scrapers, {len(campaigns)} campaigns")


def print_email_report(email):
    """Print email capacity report."""
    print("\n" + "=" * 60)
    print("EMAIL CAPACITY")
    print("=" * 60)

    print(f"Daily limit:     {email['total_daily_limit']:,}")
    print(f"Sent today:      {email['total_daily_sent']:,}")
    print(f"Available today: {email['total_daily_available']:,}")
    print(f"Contacts left:   {email['total_contacts_remaining']:,}")
    print(f"DNC list:        {email['dnc_count']:,}")

    print("\n{:<15} {:>8} {:>8} {:>10} {:>8}".format(
        "CAMPAIGN", "TODAY", "AVAIL", "REMAINING", "DAYS"))
    print("-" * 55)

    for name, c in sorted(email['campaigns'].items()):
        print("{:<15} {:>5}/{:<3} {:>8} {:>10,} {:>8}".format(
            name[:15],
            c['daily_sent'],
            c['daily_limit'],
            c['daily_remaining'],
            c['contacts_remaining'],
            c['days_left']
        ))


def print_alert_report(health, email):
    """Print only problems."""
    problems = []

    if health['cpu_status'] != 'OK':
        problems.append(f"CPU {health['cpu_percent']:.0f}% [{health['cpu_status']}]")
    if health['mem_status'] != 'OK':
        problems.append(f"MEM {health['mem_percent']:.0f}% [{health['mem_status']}]")
    if health['disk_status'] != 'OK':
        problems.append(f"DISK {health['disk_percent']:.0f}% [{health['disk_status']}]")
    if health['temp_c'] and health['temp_c'] > 70:
        problems.append(f"TEMP {health['temp_c']:.0f}C")

    # Low email capacity
    if email['total_daily_available'] < 100:
        problems.append(f"Email capacity low: {email['total_daily_available']}")

    # Campaigns running out
    for name, c in email['campaigns'].items():
        if c['contacts_remaining'] < 100 and c['contacts_remaining'] > 0:
            problems.append(f"{name}: only {c['contacts_remaining']} contacts left")

    if problems:
        print("ALERTS:")
        for p in problems:
            print(f"  ! {p}")
    else:
        print("OK - No problems detected")

    return len(problems)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='System Capacity Monitor')
    parser.add_argument('--health', action='store_true', help='Health only')
    parser.add_argument('--email', action='store_true', help='Email only')
    parser.add_argument('--alert', action='store_true', help='Alerts only')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args()

    health = get_system_health()
    scrapers, campaigns = get_running_processes()
    email = get_email_summary()

    if args.json:
        print(json.dumps({
            'health': health,
            'scrapers': len(scrapers),
            'campaigns': len(campaigns),
            'email': email,
        }, indent=2))
        return

    print(f"RASPIBIG CAPACITY - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if args.alert:
        sys.exit(print_alert_report(health, email))

    if args.health or not args.email:
        print_health_report(health, scrapers, campaigns)

    if args.email or not args.health:
        print_email_report(email)

    # Quick summary
    print("\n" + "=" * 60)
    ok = health['cpu_status'] == 'OK' and health['mem_status'] == 'OK' and health['disk_status'] == 'OK'
    capacity = email['total_daily_available']
    print(f"STATUS: {'OK' if ok else 'CHECK NEEDED'} | Email capacity: {capacity:,}/day | Contacts: {email['total_contacts_remaining']:,}")


if __name__ == "__main__":
    main()
