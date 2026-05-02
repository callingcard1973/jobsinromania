#!/usr/bin/env python3
"""
Local Decision Engine - Handles routine GO/NO-GO decisions locally
Reduces Claude API calls for predictable decisions
"""
import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

CONTEXT_DIR = Path('/tmp/claude_context')

def check_disk_space(threshold_gb=5):
    """Check if disk has enough space."""
    result = subprocess.run(['df', '-BG', '/opt'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    if len(lines) >= 2:
        parts = lines[1].split()
        available = int(parts[3].replace('G', ''))
        return {
            'decision': 'GO' if available >= threshold_gb else 'NO-GO',
            'reason': f'{available}GB available' if available >= threshold_gb else f'Only {available}GB available (need {threshold_gb}GB)',
            'available_gb': available
        }
    return {'decision': 'UNKNOWN', 'reason': 'Could not parse disk space'}

def check_site_up(url):
    """Check if target site is responding."""
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '-m', '10', url],
            capture_output=True, text=True, timeout=15
        )
        status = int(result.stdout.strip())
        return {
            'decision': 'GO' if 200 <= status < 400 else 'NO-GO',
            'reason': f'HTTP {status}',
            'status_code': status
        }
    except Exception as e:
        return {'decision': 'NO-GO', 'reason': str(e)}

def check_last_run(data_dir, max_hours=24):
    """Check when data directory was last modified."""
    data_path = Path(data_dir)
    if not data_path.exists():
        return {'decision': 'GO', 'reason': 'Directory does not exist yet'}

    # Find most recent file
    files = list(data_path.glob('**/*'))
    if not files:
        return {'decision': 'GO', 'reason': 'No files in directory'}

    newest = max(files, key=lambda p: p.stat().st_mtime if p.is_file() else 0)
    age = datetime.now() - datetime.fromtimestamp(newest.stat().st_mtime)
    hours = age.total_seconds() / 3600

    return {
        'decision': 'GO' if hours >= max_hours else 'NO-GO',
        'reason': f'Last run {hours:.1f}h ago' if hours >= max_hours else f'Only {hours:.1f}h since last run (wait {max_hours}h)',
        'hours_since': round(hours, 1),
        'newest_file': str(newest)
    }

def check_campaign_ready(campaign_dir):
    """Check if campaign has contacts and template."""
    camp_path = Path(campaign_dir)

    checks = {
        'contacts': False,
        'template': False,
        'contact_count': 0,
        'issues': []
    }

    # Check contacts
    contacts_dir = camp_path / 'contacts'
    if contacts_dir.exists():
        csvs = list(contacts_dir.glob('*.csv'))
        if csvs:
            # Count rows in first CSV
            import csv
            with open(csvs[0], 'r') as f:
                checks['contact_count'] = sum(1 for _ in f) - 1  # minus header
            checks['contacts'] = checks['contact_count'] > 0
            if checks['contact_count'] < 10:
                checks['issues'].append(f'Only {checks["contact_count"]} contacts')
        else:
            checks['issues'].append('No CSV files in contacts/')
    else:
        checks['issues'].append('No contacts/ directory')

    # Check template
    templates_dir = camp_path / 'templates'
    if templates_dir.exists():
        templates = list(templates_dir.glob('*.txt'))
        if templates:
            checks['template'] = True
            # Check ASCII
            with open(templates[0], 'rb') as f:
                content = f.read()
                if any(b > 127 for b in content):
                    checks['issues'].append('Template contains non-ASCII characters')
        else:
            checks['issues'].append('No template files')
    else:
        checks['issues'].append('No templates/ directory')

    return {
        'decision': 'GO' if checks['contacts'] and checks['template'] and not checks['issues'] else 'NO-GO',
        'reason': 'Campaign ready' if not checks['issues'] else '; '.join(checks['issues']),
        **checks
    }

def check_machine_reachable(host):
    """Check if machine is reachable via ping."""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', host],
            capture_output=True, timeout=5
        )
        return {
            'decision': 'GO' if result.returncode == 0 else 'NO-GO',
            'reason': f'{host} reachable' if result.returncode == 0 else f'{host} unreachable'
        }
    except Exception as e:
        return {'decision': 'NO-GO', 'reason': str(e)}

def scraper_preflight(scraper_name, data_dir, target_url=None):
    """Full preflight check for scraper."""
    results = {
        'scraper': scraper_name,
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }

    # Disk space
    results['checks']['disk'] = check_disk_space()

    # Last run
    results['checks']['last_run'] = check_last_run(data_dir)

    # Site up (if URL provided)
    if target_url:
        results['checks']['site'] = check_site_up(target_url)

    # Overall decision
    all_go = all(c['decision'] == 'GO' for c in results['checks'].values())
    results['decision'] = 'GO' if all_go else 'NO-GO'

    if not all_go:
        failed = [k for k, v in results['checks'].items() if v['decision'] != 'GO']
        results['reason'] = f"Failed checks: {', '.join(failed)}"
    else:
        results['reason'] = 'All checks passed'

    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: local_decision.py <command> [args]")
        print("\nCommands:")
        print("  disk [threshold_gb]     - Check disk space")
        print("  site <url>              - Check if site is up")
        print("  lastrun <dir> [hours]   - Check last run time")
        print("  campaign <dir>          - Check campaign readiness")
        print("  ping <host>             - Check machine reachable")
        print("  scraper <name> <dir> [url] - Full preflight")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'disk':
        threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        result = check_disk_space(threshold)
    elif cmd == 'site':
        result = check_site_up(sys.argv[2])
    elif cmd == 'lastrun':
        hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24
        result = check_last_run(sys.argv[2], hours)
    elif cmd == 'campaign':
        result = check_campaign_ready(sys.argv[2])
    elif cmd == 'ping':
        result = check_machine_reachable(sys.argv[2])
    elif cmd == 'scraper':
        url = sys.argv[4] if len(sys.argv) > 4 else None
        result = scraper_preflight(sys.argv[2], sys.argv[3], url)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    print(json.dumps(result, indent=2))

    # Exit code based on decision
    sys.exit(0 if result.get('decision') == 'GO' else 1)

if __name__ == '__main__':
    main()
