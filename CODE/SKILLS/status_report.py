#!/usr/bin/env python3
"""
Status Report - Quick system status for raspi and raspibig
"""

import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

MACHINES = {
    'raspibig': {'host': 'localhost', 'ip': '192.168.100.21'},
    'raspi': {'host': 'raspi', 'ip': '192.168.100.20'}
}


def run_cmd(cmd: str, host: str = 'localhost', timeout: int = 15) -> str:
    """Run command locally or via SSH"""
    try:
        if host == 'localhost':
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(['ssh', host, cmd], capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def get_uptime(host: str) -> str:
    return run_cmd("uptime -p", host)


def get_load(host: str) -> str:
    output = run_cmd("cat /proc/loadavg", host)
    if output and 'ERROR' not in output:
        parts = output.split()
        return f"{parts[0]} {parts[1]} {parts[2]}" if len(parts) >= 3 else output
    return "N/A"


def get_memory(host: str) -> dict:
    output = run_cmd("free -b | grep Mem", host)
    if 'ERROR' in output:
        return {'total': 0, 'used': 0, 'percent': 0}
    parts = output.split()
    if len(parts) >= 3:
        total = int(parts[1])
        used = int(parts[2])
        return {
            'total': total,
            'used': used,
            'percent': round(used / total * 100, 1) if total > 0 else 0
        }
    return {'total': 0, 'used': 0, 'percent': 0}


def get_disk(host: str) -> dict:
    output = run_cmd("df -B1 / | tail -1", host)
    if 'ERROR' in output:
        return {'total': 0, 'used': 0, 'percent': 0}
    parts = output.split()
    if len(parts) >= 5:
        return {
            'total': int(parts[1]),
            'used': int(parts[2]),
            'percent': int(parts[4].replace('%', ''))
        }
    return {'total': 0, 'used': 0, 'percent': 0}


def get_temp(host: str) -> str:
    output = run_cmd("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null", host)
    if output and 'ERROR' not in output and output.isdigit():
        return f"{int(output) / 1000:.1f}C"
    return "N/A"


def get_services(host: str) -> dict:
    services = ['eures-scraper', 'postgresql', 'redis-server', 'docker']
    status = {}
    for svc in services:
        output = run_cmd(f"systemctl is-active {svc} 2>/dev/null", host)
        if output == 'active':
            status[svc] = 'running'
        elif 'ERROR' not in output:
            status[svc] = output
    return status


def get_processes(host: str) -> int:
    output = run_cmd("ps aux | wc -l", host)
    return int(output) - 1 if output.isdigit() else 0


def get_scrapers(host: str) -> list:
    cmd = "ps aux | grep -iE 'eures_scraper|scraper.py|WORLD_CRAWLER' | grep -v grep | grep python"
    output = run_cmd(cmd, host)
    scrapers = []
    for line in output.split('\n'):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 10:
            cmd_full = ' '.join(parts[10:]) if len(parts) > 10 else ''
            name = 'scraper'
            if 'eures_scraper' in cmd_full.lower():
                name = 'EURES'
            elif '/countries/' in cmd_full:
                idx = cmd_full.find('/countries/')
                name = f"WORLD ({cmd_full[idx+11:idx+13]})"
            scrapers.append({'pid': parts[1], 'cpu': parts[2], 'mem': parts[3], 'name': name})
    return scrapers


def format_bytes(b: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(b) < 1024.0:
            return f"{b:.1f}{unit}"
        b /= 1024.0
    return f"{b:.1f}PB"


def print_bar(percent: float, width: int = 20) -> str:
    filled = int(percent / 100 * width)
    return '[' + '█' * filled + '░' * (width - filled) + ']'


def generate_report(machine_filter: str = None):
    print("\n" + "=" * 60)
    print("  SYSTEM STATUS REPORT")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    machines = MACHINES
    if machine_filter:
        machines = {k: v for k, v in MACHINES.items() if k == machine_filter}

    for name, info in machines.items():
        host = info['host']
        print(f"\n{'─' * 60}")
        print(f"  {name.upper()} ({info['ip']})")
        print(f"{'─' * 60}")

        # Uptime & Load
        uptime = get_uptime(host)
        load = get_load(host)
        print(f"  Uptime: {uptime}")
        print(f"  Load:   {load}")

        # Temperature
        temp = get_temp(host)
        print(f"  Temp:   {temp}")

        # Memory
        mem = get_memory(host)
        mem_bar = print_bar(mem['percent'])
        print(f"\n  Memory: {mem_bar} {mem['percent']}%")
        print(f"          {format_bytes(mem['used'])} / {format_bytes(mem['total'])}")

        # Disk
        disk = get_disk(host)
        disk_bar = print_bar(disk['percent'])
        print(f"  Disk:   {disk_bar} {disk['percent']}%")
        print(f"          {format_bytes(disk['used'])} / {format_bytes(disk['total'])}")

        # Services
        services = get_services(host)
        print(f"\n  Services:")
        for svc, status in services.items():
            icon = '🟢' if status == 'running' else '🔴'
            print(f"    {icon} {svc}: {status}")

        # Scrapers
        scrapers = get_scrapers(host)
        print(f"\n  Scrapers: {len(scrapers)} running")
        for s in scrapers[:5]:
            print(f"    PID {s['pid']:>6} | CPU {s['cpu']:>5}% | {s['name']}")
        if len(scrapers) > 5:
            print(f"    ... and {len(scrapers) - 5} more")

        # Process count
        procs = get_processes(host)
        print(f"\n  Total processes: {procs}")

    print("\n" + "=" * 60)


def generate_json(machine_filter: str = None):
    machines = MACHINES
    if machine_filter:
        machines = {k: v for k, v in MACHINES.items() if k == machine_filter}

    report = {
        'timestamp': datetime.now().isoformat(),
        'machines': {}
    }

    for name, info in machines.items():
        host = info['host']
        report['machines'][name] = {
            'ip': info['ip'],
            'uptime': get_uptime(host),
            'load': get_load(host),
            'temp': get_temp(host),
            'memory': get_memory(host),
            'disk': get_disk(host),
            'services': get_services(host),
            'scrapers': get_scrapers(host),
            'processes': get_processes(host)
        }

    print(json.dumps(report, indent=2))


def main():
    import sys

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--json':
            generate_json(sys.argv[2] if len(sys.argv) > 2 else None)
        elif arg == '--raspi':
            generate_report('raspi')
        elif arg == '--raspibig':
            generate_report('raspibig')
        elif arg in ('-h', '--help'):
            print("Usage: status_report.py [OPTIONS]")
            print("")
            print("Options:")
            print("  (none)      Full report for both machines")
            print("  --raspi     Report for raspi only")
            print("  --raspibig  Report for raspibig only")
            print("  --json      Output as JSON")
            print("  --json raspi/raspibig  JSON for specific machine")
        else:
            print(f"Unknown option: {arg}")
            print("Use --help for usage")
    else:
        generate_report()


if __name__ == '__main__':
    main()
