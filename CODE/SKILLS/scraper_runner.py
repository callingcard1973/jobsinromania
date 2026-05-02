#!/usr/bin/env python3
"""
Scraper Runner - Wrapper that runs scrapers with Telegram failure alerts.

Usage:
    python3 scraper_runner.py NORWAY
    python3 scraper_runner.py --all              # Run all stale scrapers
    python3 scraper_runner.py --cron-install      # Install nightly cron schedule
    python3 scraper_runner.py --cron-remove       # Remove scraper cron entries

Features:
- Runs scraper, checks exit code and output
- Sends Telegram alert on failure
- Creates per-scraper log in /opt/ACTIVE/INFRA/LOGS/scrapers/
- Prevents duplicate runs (pgrep check)
- Staggered cron schedule for all 17 scrapers
"""

import os
import sys
import re
import subprocess
import json
import argparse
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# LLM validation (optional)
try:
    sys.path.insert(0, '/opt/ACTIVE/LLM/MEMORY/llm_tasks')
    from validate_after_scraper import validate_scraper_output
    HAS_LLM_VALIDATOR = True
except ImportError:
    HAS_LLM_VALIDATOR = False

LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/scrapers')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Scraper definitions: name -> (directory, command, timeout_hours)
SCRAPERS = {
    'ACHIZITII_PUBLICE': ('/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/DATA_GOV_RO', 'scrape_achizitii.py --year 2025', 2),
    'ANOFM': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM', 'anofm_scraper.py', 2),
    'CQC': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK/CQC', 'cqc_scraper.py', 3),
    'DENMARK': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK', 'danish_scraper.py --headless --max-clicks 100', 4),
    'DSVSA': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/DSVSA', 'scraper.py', 2),
    'EURES': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES', 'eures_scraper.py 1 9999 50 de,nl,be,at,ch,lu 1 LAST_WEEK', 8),
    'EURES_AGENCIES': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES', 'eures_agencies_scraper.py 1 500 50 at,be,bg,ch,cy,cz,de,dk,ee,es,fi,fr,gr,hr,hu,ie,is,it,li,lt,lu,lv,mt,nl,no,pl,pt,ro,se,si,sk 1 LAST_WEEK', 6),
    'FINLAND': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND', 'duunitori_scraper.py', 3),
    'GERMANY': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/GERMANY', 'bundesagentur_scraper.py', 4),
    'MALTA': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/MALTA', 'malta_accommodation_scraper.py', 2),
    'MOLDOVA': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/MOLDOVA', 'scrape_rabota.py', 2),
    'NORTH_MACEDONIA': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORTH_MACEDONIA', 'run_scraper.py', 2),
    'NORWAY': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY', 'arbeidsplassen_scraper.py', 6),
    'POLAND': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/POLAND', 'kraz_scraper.py', 3),
    'RECYCLING': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/RECYCLING', 'recycling_jobs_scraper.py', 3),
    'SWEDEN': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SWEDEN', 'sweden_scraper.py', 4),
    'UK': ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK', 'run_uk_scraper.py', 12),
}

# Staggered cron schedule (HH:MM, spread across night/early morning)
CRON_SCHEDULE = {
    'EURES':             '00 22',   # 22:00 - longest runner, start first
    'EURES_AGENCIES':    '30 22',   # 22:00 - also long, different data
    'NORWAY':            '30 22',   # 22:30
    'GERMANY':           '00 23',   # 23:00
    'SWEDEN':            '30 23',   # 23:30
    'UK':                '00 0',    # 00:00
    'DENMARK':           '30 0',    # 00:30
    'FINLAND':           '00 1',    # 01:00
    'POLAND':            '30 1',    # 01:30
    'CQC':               '00 2',    # 02:00
    'RECYCLING':         '30 2',    # 02:30
    'ANOFM':             '00 3',    # 03:00
    'ACHIZITII_PUBLICE': '30 3',    # 03:30
    'DSVSA':             '00 4',    # 04:00
    'MOLDOVA':           '30 4',    # 04:30
    'MALTA':             '00 5',    # 05:00
    'NORTH_MACEDONIA':   '30 5',    # 05:30
}


def send_telegram(message: str):
    """Send Telegram alert."""
    try:
        from dotenv import load_dotenv
        load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')
        token = os.getenv('TELEGRAM_GROUPS_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID', '547047851')
        if not token:
            print("WARNING: No Telegram bot token found")
            return
        import requests
        resp = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
            },
            timeout=10
        )
        if resp.status_code == 200:
            print(f"Telegram alert sent")
        else:
            print(f"Telegram error: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"Telegram send failed: {e}")


def get_running_pids(scraper_name: str) -> list:
    """Get PIDs of running scraper processes."""
    info = SCRAPERS.get(scraper_name)
    if not info:
        return []
    script = info[1].split()[0]
    pids = []
    try:
        result = subprocess.run(['pgrep', '-af', script], capture_output=True, text=True, timeout=5)
        for line in result.stdout.strip().split('\n'):
            if line.strip() and 'pgrep' not in line and 'scraper_runner' not in line:
                try:
                    pids.append(int(line.strip().split()[0]))
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    return pids


def get_process_age_hours(pid: int) -> float:
    """Get how long a process has been running in hours."""
    try:
        result = subprocess.run(
            ['ps', '-o', 'etimes=', '-p', str(pid)],
            capture_output=True, text=True, timeout=5
        )
        elapsed_secs = int(result.stdout.strip())
        return elapsed_secs / 3600.0
    except Exception:
        return 0.0


def kill_stale_process(scraper_name: str, pid: int, age_hours: float) -> bool:
    """Kill a stale scraper process."""
    try:
        subprocess.run(['kill', str(pid)], timeout=5)
        print(f"  Killed stale {scraper_name} (PID {pid}, running {age_hours:.1f}h)")
        send_telegram(f"\u26a0\ufe0f Killed stale {scraper_name} (PID {pid}, was running {age_hours:.1f}h)")
        import time
        time.sleep(2)
        # Force kill if still alive
        try:
            subprocess.run(['kill', '-9', str(pid)], timeout=5, capture_output=True)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"  Failed to kill PID {pid}: {e}")
        return False


def is_running(scraper_name: str) -> bool:
    """Check if scraper is already running. Kills stale processes (>2x timeout)."""
    info = SCRAPERS.get(scraper_name)
    if not info:
        return False
    timeout_h = info[2]
    max_age_h = timeout_h * 2  # Kill if running longer than 2x timeout

    pids = get_running_pids(scraper_name)
    if not pids:
        return False

    # Check if any running process is stale
    all_killed = True
    for pid in pids:
        age_h = get_process_age_hours(pid)
        if age_h > max_age_h:
            print(f"  {scraper_name} PID {pid} is stale ({age_h:.1f}h > {max_age_h}h max)")
            kill_stale_process(scraper_name, pid, age_h)
        else:
            all_killed = False
            print(f"  {scraper_name} PID {pid} still running ({age_h:.1f}h, max {max_age_h}h)")

    return not all_killed


def run_scraper(scraper_name: str) -> dict:
    """Run a scraper and return results."""
    if scraper_name not in SCRAPERS:
        return {'success': False, 'error': f'Unknown scraper: {scraper_name}'}

    work_dir, cmd_args, timeout_h = SCRAPERS[scraper_name]
    script = cmd_args.split()[0]

    # Check if already running
    if is_running(scraper_name):
        msg = f'{scraper_name} already running, skipping'
        print(msg)
        return {'success': True, 'skipped': True, 'message': msg}

    # Prepare log file
    today = date.today().strftime('%Y%m%d')
    log_dir = LOG_DIR / f'restart_{today}'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f'{scraper_name}.log'

    full_cmd = f'set -a; source /opt/ACTIVE/SCRAPERS/EUROPE/.env 2>/dev/null; set +a; cd {work_dir} && nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 {cmd_args}'
    start_time = datetime.now()
    print(f"[{start_time:%H:%M:%S}] Starting {scraper_name}: {full_cmd}")

    try:
        with open(log_file, 'w') as lf:
            lf.write(f"=== {scraper_name} started at {start_time} ===\n")
            lf.write(f"Command: {full_cmd}\n\n")
            lf.flush()

            proc = subprocess.run(
                full_cmd,
                shell=True,
                stdout=lf,
                stderr=subprocess.STDOUT,
                timeout=timeout_h * 3600,
            )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        exit_code = proc.returncode

        with open(log_file, 'a') as lf:
            lf.write(f"\n=== Finished at {end_time} (exit code: {exit_code}, duration: {duration:.0f}s) ===\n")

        # Read last 10 lines for context
        try:
            tail = subprocess.run(['tail', '-10', str(log_file)], capture_output=True, text=True, timeout=5)
            tail_text = tail.stdout.strip()
        except Exception:
            tail_text = "(could not read log tail)"

        result = {
            'success': exit_code == 0,
            'exit_code': exit_code,
            'duration_s': duration,
            'log_file': str(log_file),
            'tail': tail_text,
        }

        # LLM validation for successful runs
        if exit_code == 0 and HAS_LLM_VALIDATOR:
            try:
                valid = validate_scraper_output(scraper_name, quiet=True)
                if not valid:
                    send_telegram(f"⚠️ <b>VALIDATION WARNING: {scraper_name}</b>\nScraper succeeded but output validation found issues.")
                result['validated'] = valid
            except Exception as ve:
                print(f"  Validation skipped: {ve}")

        if exit_code != 0:
            msg = (
                f"<b>SCRAPER FAILED: {scraper_name}</b>\n"
                f"Exit code: {exit_code}\n"
                f"Duration: {duration:.0f}s\n"
                f"Log: {log_file}\n\n"
                f"<pre>{tail_text[-500:]}</pre>"
            )
            send_telegram(msg)

        print(f"[{end_time:%H:%M:%S}] {scraper_name}: exit={exit_code}, {duration:.0f}s")
        return result

    except subprocess.TimeoutExpired:
        duration = timeout_h * 3600
        msg = (
            f"<b>SCRAPER TIMEOUT: {scraper_name}</b>\n"
            f"Exceeded {timeout_h}h limit\n"
            f"Log: {log_file}"
        )
        send_telegram(msg)
        # Kill the process
        subprocess.run(f'pkill -f "{script}"', shell=True, capture_output=True)
        return {'success': False, 'error': 'timeout', 'duration_s': duration}

    except Exception as e:
        msg = (
            f"<b>SCRAPER ERROR: {scraper_name}</b>\n"
            f"Exception: {e}"
        )
        send_telegram(msg)
        return {'success': False, 'error': str(e)}


def install_cron():
    """Install nightly staggered cron schedule."""
    # Read existing crontab
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        existing = result.stdout
    except Exception:
        existing = ''

    # Remove old scraper_runner entries
    lines = [l for l in existing.split('\n') if 'scraper_runner.py' not in l]

    # Add header
    lines.append('')
    lines.append('# === Nightly Scraper Schedule (auto-generated by scraper_runner.py) ===')

    # Add entries for each scraper
    for name, schedule in sorted(CRON_SCHEDULE.items(), key=lambda x: x[1]):
        minute, hour = schedule.split()
        lines.append(
            f'{minute} {hour} * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/scraper_runner.py {name} '
            f'>> /opt/ACTIVE/INFRA/LOGS/scrapers/cron_{name.lower()}.log 2>&1'
        )

    lines.append('# === End Scraper Schedule ===')
    lines.append('')

    new_crontab = '\n'.join(lines)

    # Install
    proc = subprocess.run(['crontab', '-'], input=new_crontab, capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"Installed cron schedule for {len(CRON_SCHEDULE)} scrapers")
        for name, schedule in sorted(CRON_SCHEDULE.items(), key=lambda x: x[1]):
            minute, hour = schedule.split()
            print(f"  {hour}:{minute.zfill(2)} - {name}")
    else:
        print(f"Failed to install crontab: {proc.stderr}")


def remove_cron():
    """Remove scraper_runner cron entries."""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        existing = result.stdout
    except Exception:
        print("No crontab found")
        return

    lines = [l for l in existing.split('\n')
             if 'scraper_runner.py' not in l
             and 'Nightly Scraper Schedule' not in l
             and 'End Scraper Schedule' not in l]

    # Remove consecutive blank lines
    clean = []
    for l in lines:
        if l.strip() == '' and clean and clean[-1].strip() == '':
            continue
        clean.append(l)

    subprocess.run(['crontab', '-'], input='\n'.join(clean), capture_output=True, text=True)
    print("Removed scraper_runner cron entries")


def main():
    parser = argparse.ArgumentParser(description='Run scrapers with failure alerts')
    parser.add_argument('scraper', nargs='?', help='Scraper name (e.g. NORWAY)')
    parser.add_argument('--all', action='store_true', help='Run all scrapers that are stale (>48h)')
    parser.add_argument('--cron-install', action='store_true', help='Install nightly cron schedule')
    parser.add_argument('--cron-remove', action='store_true', help='Remove scraper cron entries')
    parser.add_argument('--list', action='store_true', help='List available scrapers')
    args = parser.parse_args()

    if args.cron_install:
        install_cron()
        return

    if args.cron_remove:
        remove_cron()
        return

    if args.list:
        print("Available scrapers:")
        for name in sorted(SCRAPERS):
            running = "RUNNING" if is_running(name) else ""
            print(f"  {name:25s} {running}")
        return

    if args.all:
        # Find stale scrapers and run them
        try:
            sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
            from static_dashboard_pure import get_scrapers
            scrapers = get_scrapers()
            stale = [s for s in scrapers if s['age_h'] > 48 and s['name'] in SCRAPERS]
        except Exception as e:
            print(f"Could not load scraper status: {e}")
            stale = []

        if not stale:
            print("No stale scrapers found")
            return

        print(f"Found {len(stale)} stale scrapers")
        results = {}
        for s in stale:
            name = s['name']
            print(f"\n{'='*60}")
            result = run_scraper(name)
            results[name] = result

        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY:")
        ok = sum(1 for r in results.values() if r.get('success'))
        fail = sum(1 for r in results.values() if not r.get('success') and not r.get('skipped'))
        skip = sum(1 for r in results.values() if r.get('skipped'))
        print(f"  OK: {ok}, Failed: {fail}, Skipped: {skip}")
        return

    if args.scraper:
        name = args.scraper.upper()
        if name not in SCRAPERS:
            print(f"Unknown scraper: {name}")
            print(f"Available: {', '.join(sorted(SCRAPERS))}")
            sys.exit(1)
        result = run_scraper(name)
        sys.exit(0 if result.get('success') else 1)

    parser.print_help()


if __name__ == '__main__':
    main()
