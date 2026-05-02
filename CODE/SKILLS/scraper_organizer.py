#!/usr/bin/env python3
"""
Scraper & Download Organizer - Unified status across both machines
CLI tool + HTML dashboard generator
"""

import subprocess
import json
import os
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Configuration
MACHINES = {
    'raspibig': {'host': 'localhost', 'name': 'raspibig', 'ip': '192.168.100.21'},
    'raspi': {'host': 'raspi', 'name': 'raspi', 'ip': '192.168.100.20'}
}

SCRAPER_PATTERNS = [
    'eures_scraper',
    'scraper.py',
    'WORLD_CRAWLER',
    'EURES'
]

DOWNLOAD_DIRS = {
    'raspibig': [
        '/opt/DATA/WORLD_CRAWLER',
        '/opt/DATA/GERMANY',
        '/opt/DATA/EUROSTAT',
        '/opt/DATA/EURES',
        '/mnt/hdd/SCRAPER_DATA'
    ],
    'raspi': [
        '/opt/DATA/EURES',
        '/opt/DATA/WORLD_CRAWLER'
    ]
}

HTML_OUTPUT = '/opt/DATA/scraper_dashboard.html'
JSON_OUTPUT = '/opt/DATA/scraper_status.json'


def run_cmd(cmd: str, host: str = 'localhost', timeout: int = 30) -> str:
    """Run command locally or via SSH"""
    try:
        if host == 'localhost':
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            # Use double quotes and escape for SSH
            result = subprocess.run(['ssh', host, cmd], capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def get_memory(host: str) -> Dict:
    """Get memory stats"""
    output = run_cmd("free -b | grep Mem", host)
    if 'ERROR' in output:
        return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}

    parts = output.split()
    if len(parts) >= 4:
        total = int(parts[1])
        used = int(parts[2])
        return {
            'total': total,
            'used': used,
            'free': total - used,
            'percent': round(used / total * 100, 1) if total > 0 else 0
        }
    return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}


def get_scrapers(host: str) -> List[Dict]:
    """Get running scrapers"""
    scrapers = []
    # Pattern to detect scrapers - works with SSH list args
    cmd = "ps aux | grep -iE 'eures_scraper|scraper.py|WORLD_CRAWLER' | grep -v grep | grep python"
    output = run_cmd(cmd, host)

    for line in output.split('\n'):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 10:
            cmd_full = ' '.join(parts[10:]) if len(parts) > 10 else parts[-1]
            # Extract scraper name
            name = 'unknown'
            if 'eures_scraper' in cmd_full.lower():
                # Extract countries from command args
                for p in parts:
                    if ',' in p and len(p) >= 5 and p[0].isalpha():
                        countries = p[:25] + ('...' if len(p) > 25 else '')
                        name = f"EURES ({countries})"
                        break
                else:
                    name = 'EURES'
            elif 'scraper.py' in cmd_full:
                # Extract country code from path
                if '/countries/' in cmd_full:
                    idx = cmd_full.find('/countries/')
                    name = f"WORLD_CRAWLER ({cmd_full[idx+11:idx+13]})"
                else:
                    name = 'WORLD_CRAWLER'
            elif 'firefox' in cmd_full.lower() or 'playwright' in cmd_full.lower():
                continue  # Skip browser processes

            if name == 'unknown':
                continue  # Skip unidentified processes

            scrapers.append({
                'pid': parts[1],
                'cpu': parts[2],
                'mem': parts[3],
                'name': name,
                'started': f"{parts[8]} {parts[9]}" if len(parts) > 9 else parts[8]
            })

    return scrapers


def get_downloads(host: str, dirs: List[str]) -> List[Dict]:
    """Get download directory stats"""
    downloads = []

    for dir_path in dirs:
        cmd = f"du -sh {dir_path} 2>/dev/null && find {dir_path} -type f 2>/dev/null | wc -l"
        output = run_cmd(cmd, host)

        if output and 'ERROR' not in output:
            lines = output.strip().split('\n')
            if len(lines) >= 2:
                size = lines[0].split()[0] if lines[0] else '0'
                files = lines[1].strip() if len(lines) > 1 else '0'
                downloads.append({
                    'path': dir_path,
                    'size': size,
                    'files': files
                })

    return downloads


def get_systemd_status(host: str, service: str) -> Dict:
    """Get systemd service status"""
    cmd = f"systemctl is-active {service} 2>/dev/null && systemctl show {service} --property=ActiveEnterTimestamp 2>/dev/null"
    output = run_cmd(cmd, host)

    if 'active' in output:
        return {'status': 'running', 'since': output.split('=')[-1] if '=' in output else 'unknown'}
    return {'status': 'stopped', 'since': ''}


def collect_all_status() -> Dict:
    """Collect status from all machines"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'machines': {}
    }

    for machine_id, machine in MACHINES.items():
        host = machine['host']

        machine_status = {
            'name': machine['name'],
            'ip': machine['ip'],
            'memory': get_memory(host),
            'scrapers': get_scrapers(host),
            'downloads': get_downloads(host, DOWNLOAD_DIRS.get(machine_id, [])),
            'eures_service': get_systemd_status(host, 'eures-scraper')
        }

        status['machines'][machine_id] = machine_status

    return status


def print_cli_status(status: Dict):
    """Print CLI status"""
    print("\n" + "=" * 60)
    print("  SCRAPER & DOWNLOAD ORGANIZER")
    print("  " + status['timestamp'])
    print("=" * 60)

    for machine_id, machine in status['machines'].items():
        print(f"\n{'─' * 60}")
        print(f"  {machine['name'].upper()} ({machine['ip']})")
        print(f"{'─' * 60}")

        # Memory
        mem = machine['memory']
        mem_bar = '█' * int(mem['percent'] / 5) + '░' * (20 - int(mem['percent'] / 5))
        print(f"  Memory: [{mem_bar}] {mem['percent']}%")
        print(f"          {mem['used'] // (1024**3):.1f}G / {mem['total'] // (1024**3):.1f}G")

        # EURES Service
        eures = machine['eures_service']
        status_icon = '🟢' if eures['status'] == 'running' else '🔴'
        print(f"\n  EURES Service: {status_icon} {eures['status']}")

        # Scrapers
        scrapers = machine['scrapers']
        print(f"\n  Running Scrapers: {len(scrapers)}")
        for s in scrapers[:5]:  # Show max 5
            print(f"    PID {s['pid']:>6} | CPU {s['cpu']:>5}% | MEM {s['mem']:>5}% | {s['name']}")
        if len(scrapers) > 5:
            print(f"    ... and {len(scrapers) - 5} more")

        # Downloads
        downloads = machine['downloads']
        print(f"\n  Downloads:")
        for d in downloads:
            print(f"    {d['size']:>8} | {d['files']:>6} files | {d['path']}")

    print("\n" + "=" * 60)


def generate_html(status: Dict) -> str:
    """Generate HTML dashboard"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Scraper Dashboard</title>
    <meta http-equiv="refresh" content="60">
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Courier New', monospace;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 {
            color: #00ff88;
            margin-bottom: 10px;
            font-size: 24px;
        }
        .timestamp { color: #888; margin-bottom: 20px; }
        .machines { display: flex; gap: 20px; flex-wrap: wrap; }
        .machine {
            background: #16213e;
            border: 1px solid #0f3460;
            border-radius: 8px;
            padding: 20px;
            flex: 1;
            min-width: 400px;
        }
        .machine h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .section { margin-bottom: 15px; }
        .section-title {
            color: #888;
            font-size: 12px;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        .memory-bar {
            background: #333;
            border-radius: 4px;
            height: 20px;
            overflow: hidden;
        }
        .memory-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #00d4ff);
            transition: width 0.3s;
        }
        .memory-fill.warning { background: linear-gradient(90deg, #ffaa00, #ff6600); }
        .memory-fill.danger { background: linear-gradient(90deg, #ff4444, #ff0000); }
        .status { display: flex; align-items: center; gap: 8px; }
        .dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .dot.green { background: #00ff88; box-shadow: 0 0 8px #00ff88; }
        .dot.red { background: #ff4444; box-shadow: 0 0 8px #ff4444; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td {
            padding: 6px 8px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        th { color: #888; }
        .num { text-align: right; }
        .path { color: #888; font-size: 11px; }
    </style>
</head>
<body>
    <h1>SCRAPER & DOWNLOAD ORGANIZER</h1>
    <div class="timestamp">Last updated: """ + status['timestamp'] + """</div>

    <div class="machines">
"""

    for machine_id, machine in status['machines'].items():
        mem = machine['memory']
        mem_class = ''
        if mem['percent'] > 80:
            mem_class = 'danger'
        elif mem['percent'] > 60:
            mem_class = 'warning'

        eures = machine['eures_service']
        eures_dot = 'green' if eures['status'] == 'running' else 'red'

        html += f"""
        <div class="machine">
            <h2>{machine['name'].upper()} <span style="color:#888">({machine['ip']})</span></h2>

            <div class="section">
                <div class="section-title">Memory</div>
                <div class="memory-bar">
                    <div class="memory-fill {mem_class}" style="width: {mem['percent']}%"></div>
                </div>
                <div style="margin-top:5px">{mem['percent']}% - {mem['used'] // (1024**3):.1f}G / {mem['total'] // (1024**3):.1f}G</div>
            </div>

            <div class="section">
                <div class="section-title">EURES Service</div>
                <div class="status">
                    <div class="dot {eures_dot}"></div>
                    <span>{eures['status']}</span>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Running Scrapers ({len(machine['scrapers'])})</div>
                <table>
                    <tr><th>PID</th><th>CPU</th><th>MEM</th><th>Name</th></tr>
"""

        for s in machine['scrapers'][:8]:
            html += f"""                    <tr>
                        <td>{s['pid']}</td>
                        <td class="num">{s['cpu']}%</td>
                        <td class="num">{s['mem']}%</td>
                        <td>{s['name']}</td>
                    </tr>
"""

        html += """                </table>
            </div>

            <div class="section">
                <div class="section-title">Downloads</div>
                <table>
                    <tr><th>Size</th><th>Files</th><th>Path</th></tr>
"""

        for d in machine['downloads']:
            html += f"""                    <tr>
                        <td class="num">{d['size']}</td>
                        <td class="num">{d['files']}</td>
                        <td class="path">{d['path']}</td>
                    </tr>
"""

        html += """                </table>
            </div>
        </div>
"""

    html += """    </div>
</body>
</html>"""

    return html


def main():
    import sys

    # Collect status
    status = collect_all_status()

    # Save JSON
    with open(JSON_OUTPUT, 'w') as f:
        json.dump(status, f, indent=2)

    # Generate HTML
    html = generate_html(status)
    with open(HTML_OUTPUT, 'w') as f:
        f.write(html)

    # CLI output
    if '--json' in sys.argv:
        print(json.dumps(status, indent=2))
    elif '--html' in sys.argv:
        print(f"HTML dashboard: {HTML_OUTPUT}")
    else:
        print_cli_status(status)
        print(f"\nDashboard: {HTML_OUTPUT}")
        print(f"JSON: {JSON_OUTPUT}")


if __name__ == '__main__':
    main()
