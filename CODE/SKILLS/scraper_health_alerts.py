#!/usr/bin/env python3
"""
Scraper Health Check Alerts

Monitors running scrapers and alerts if:
- Running > 2 hours with no output
- PID file exists but process is dead
- No output files created in expected time

Usage:
    python3 scraper_health_alerts.py          # Check all scrapers
    python3 scraper_health_alerts.py --alert  # Send Telegram alerts
    python3 scraper_health_alerts.py --fix    # Auto-fix stale PID files
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from alerting import send_telegram
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# Scraper definitions: name -> {pid_file, output_dir, max_runtime_hours}
SCRAPERS = {
    'OLX': {
        'pid_file': '/tmp/olx_scraper.pid',
        'output_dir': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/OLX_JOBS',
        'max_runtime_hours': 2,
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/OLX/olx_jobs_scraper.py',
    },
    'ANOFM': {
        'pid_file': '/tmp/anofm_scraper.pid',
        'output_dir': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM',
        'max_runtime_hours': 1,
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/anofm_scraper.py',
    },
    'DSVSA': {
        'pid_file': '/tmp/dsvsa_scraper.pid',
        'output_dir': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA',
        'max_runtime_hours': 4,  # Downloads large county files
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/DSVSA/scraper.py',
    },
    'IAJOB': {
        'pid_file': '/tmp/iajob_scraper.pid',
        'output_dir': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB',
        'max_runtime_hours': 1,
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/IAJOB/src/iajob_scraper.py',
    },
    'EURES': {
        'pid_file': '/tmp/eures_scraper.pid',
        'output_dir': '/opt/ACTIVE/OPENDATA/DATA/EURES',
        'max_runtime_hours': 6,  # Large EU-wide scrape
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/eures_scraper.py',
    },
    'DENMARK': {
        'pid_file': '/tmp/denmark_scraper.pid',
        'output_dir': '/opt/ACTIVE/OPENDATA/DATA/DENMARK',
        'max_runtime_hours': 2,
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/danish_scraper.py',
    },
    'FINLAND': {
        'pid_file': '/tmp/finland_scraper.pid',
        'output_dir': '/opt/ACTIVE/OPENDATA/DATA/FINLAND',
        'max_runtime_hours': 2,
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/tyomarkkinatori_requests.py',
    },
}


def is_process_running(pid: int) -> bool:
    """Check if a process is running by PID."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def get_pid_info(pid_file: str) -> dict:
    """Get PID file info: pid, running status, age."""
    pid_path = Path(pid_file)
    if not pid_path.exists():
        return {'exists': False}

    try:
        pid = int(pid_path.read_text().strip())
        mtime = datetime.fromtimestamp(pid_path.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600

        return {
            'exists': True,
            'pid': pid,
            'running': is_process_running(pid),
            'age_hours': age_hours,
            'started': mtime,
        }
    except (ValueError, OSError) as e:
        return {'exists': True, 'error': str(e)}


def get_latest_output(output_dir: str) -> dict:
    """Get info about most recent output file."""
    out_path = Path(output_dir)
    if not out_path.exists():
        return {'exists': False}

    # Find most recent CSV or JSON file (filter out symlinks and missing files)
    all_files = list(out_path.glob('*.csv')) + list(out_path.glob('*.json'))
    files = []
    for f in all_files:
        try:
            if f.exists() and f.is_file():
                files.append(f)
        except OSError:
            pass
    if not files:
        return {'exists': True, 'files': 0}

    latest = max(files, key=lambda f: f.stat().st_mtime)
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    size_mb = latest.stat().st_size / (1024 * 1024)

    return {
        'exists': True,
        'files': len(files),
        'latest': latest.name,
        'age_hours': age_hours,
        'size_mb': size_mb,
        'modified': mtime,
    }


def check_scraper(name: str, config: dict) -> dict:
    """Check health of a single scraper."""
    result = {
        'name': name,
        'status': 'OK',
        'issues': [],
        'pid_info': get_pid_info(config['pid_file']),
        'output_info': get_latest_output(config['output_dir']),
    }

    pid = result['pid_info']
    out = result['output_info']

    # Check 1: Stale PID file (process not running but PID file exists)
    if pid.get('exists') and not pid.get('running') and not pid.get('error'):
        result['issues'].append(f"Stale PID file (process {pid.get('pid')} not running)")
        result['status'] = 'WARN'

    # Check 2: Running too long without new output
    if pid.get('running'):
        runtime = pid.get('age_hours', 0)
        max_runtime = config.get('max_runtime_hours', 2)

        if runtime > max_runtime:
            result['issues'].append(f"Running {runtime:.1f}h (max: {max_runtime}h)")
            result['status'] = 'ALERT'

            # Check if output is being generated
            if out.get('exists') and out.get('age_hours', 999) < 0.5:
                result['issues'][-1] += " but output is fresh"
                result['status'] = 'WARN'

    # Check 3: No recent output (stale data)
    if out.get('exists') and out.get('age_hours', 0) > 48:
        hours = out.get('age_hours')
        result['issues'].append(f"No output in {hours:.0f}h")
        if result['status'] == 'OK':
            result['status'] = 'STALE'

    return result


def check_all_scrapers() -> list:
    """Check health of all configured scrapers."""
    results = []
    for name, config in SCRAPERS.items():
        results.append(check_scraper(name, config))
    return results


def fix_stale_pids():
    """Remove stale PID files (process not running)."""
    fixed = []
    for name, config in SCRAPERS.items():
        pid_info = get_pid_info(config['pid_file'])
        if pid_info.get('exists') and not pid_info.get('running') and not pid_info.get('error'):
            try:
                Path(config['pid_file']).unlink()
                fixed.append(f"{name}: removed {config['pid_file']}")
            except Exception as e:
                fixed.append(f"{name}: error removing - {e}")
    return fixed


def format_report(results: list) -> str:
    """Format health check results as text."""
    lines = ["=== Scraper Health Check ===", f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]

    # Count by status
    counts = {'OK': 0, 'WARN': 0, 'ALERT': 0, 'STALE': 0}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1

    lines.append(f"Status: {counts['OK']} OK, {counts['WARN']} WARN, {counts['ALERT']} ALERT, {counts['STALE']} STALE")
    lines.append("")

    # Details
    for r in results:
        pid = r['pid_info']
        out = r['output_info']

        status_icon = {'OK': '[OK]', 'WARN': '[!!]', 'ALERT': '[XX]', 'STALE': '[--]'}.get(r['status'], '[??]')

        line = f"{status_icon} {r['name']}"
        if pid.get('running'):
            line += f" (PID {pid.get('pid')}, {pid.get('age_hours', 0):.1f}h)"
        elif pid.get('exists'):
            line += " (stale PID)"
        else:
            line += " (not running)"

        lines.append(line)

        if out.get('latest'):
            lines.append(f"     Last output: {out['latest']} ({out['age_hours']:.1f}h ago, {out['size_mb']:.1f}MB)")

        for issue in r['issues']:
            lines.append(f"     ISSUE: {issue}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Scraper Health Check Alerts')
    parser.add_argument('--alert', action='store_true', help='Send Telegram alerts for issues')
    parser.add_argument('--fix', action='store_true', help='Auto-fix stale PID files')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    results = check_all_scrapers()
    report = format_report(results)

    print(report)

    # Fix stale PIDs
    if args.fix:
        print("\n=== Fixing Stale PIDs ===")
        fixed = fix_stale_pids()
        for f in fixed:
            print(f)
        if not fixed:
            print("No stale PIDs to fix")

    # Send alerts
    alerts = [r for r in results if r['status'] in ('ALERT', 'WARN')]
    if args.alert and alerts and TELEGRAM_AVAILABLE:
        alert_msg = "SCRAPER ALERT\n\n"
        for r in alerts:
            alert_msg += f"{r['status']}: {r['name']}\n"
            for issue in r['issues']:
                alert_msg += f"  - {issue}\n"

        send_telegram(alert_msg)
        print("\nTelegram alert sent")

    # Exit code based on severity
    if any(r['status'] == 'ALERT' for r in results):
        sys.exit(2)
    elif any(r['status'] in ('WARN', 'STALE') for r in results):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
