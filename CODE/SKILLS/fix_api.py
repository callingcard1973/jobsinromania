#!/usr/bin/env python3
"""
Fix API Server for Dashboard v2

Runs on raspibig:8089, called by dashboard buttons via AJAX.

Features:
- CORS support for cross-port AJAX calls
- Scraper restart with duplicate detection (pgrep)
- Kill scraper, view logs, system load
- Restart all stale scrapers
- Async campaign feed (no timeout)
- Clear send lock

Usage:
    python3 fix_api.py --serve
    curl http://localhost:8089/fix/health_check
    curl http://localhost:8089/fixes
"""

import os
import re
import sys
import subprocess
import glob as globmod
import json
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from flask import Flask, jsonify
from telegram_fix_handler import FIX_COMMANDS, run_fix

app = Flask(__name__)


# --- CORS ---
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    return response


# --- Aliases: dashboard button names -> FIX_COMMANDS keys ---
FIX_ALIASES = {
    'feed_campaigns': 'campaign_low',
    'clear_lock': 'clear_lock',
    'disk_cleanup': 'disk_full',
    'restart_services': 'service_down',
}

# --- Scraper restart commands ---
SCRAPER_SCRIPTS = {
    'ACHIZITII_PUBLICE': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/DATA_GOV_RO && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 scrape_achizitii.py --year 2025 > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'ANOFM': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 anofm_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'CQC': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 cqc_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'DENMARK': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 danish_scraper.py --headless --max-clicks 100 > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'DSVSA': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/DSVSA && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'EURES': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES && nohup nice -n 19 cpulimit -l 50 -- /opt/ACTIVE/INFRA/venv/bin/python3 eures_scraper.py 1 9999 50 de,nl,be,at,ch,lu 1 LAST_WEEK > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'EURES_AGENCIES': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES && nohup nice -n 19 timeout 21600 /opt/ACTIVE/INFRA/venv/bin/python3 eures_agencies_scraper.py 1 500 50 at,be,bg,ch,cy,cz,de,dk,ee,es,fi,fr,gr,hr,hu,ie,is,it,li,lt,lu,lv,mt,nl,no,pl,pt,ro,se,si,sk 1 LAST_WEEK > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'FINLAND': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 duunitori_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'GERMANY': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/GERMANY && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 bundesagentur_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'MALTA': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/MALTA && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 malta_accommodation_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'MOLDOVA': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/MOLDOVA && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 scrape_rabota.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'NORTH_MACEDONIA': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORTH_MACEDONIA && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 run_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'NORWAY': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 arbeidsplassen_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'POLAND': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/POLAND && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 kraz_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'RECYCLING': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/RECYCLING && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 recycling_jobs_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'SWEDEN': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SWEDEN && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 sweden_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
    'UK': 'cd /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK && nohup nice -n 19 /opt/ACTIVE/INFRA/venv/bin/python3 run_uk_scraper.py > /opt/ACTIVE/INFRA/LOGS/fix_restart.log 2>&1 &',
}


def _get_script_search_term(scraper_name):
    """Extract script name from SCRAPER_SCRIPTS command for pgrep matching."""
    cmd = SCRAPER_SCRIPTS.get(scraper_name, '')
    m = re.search(r'python3\s+(\S+\.py)', cmd)
    return m.group(1) if m else scraper_name.lower()


def _find_running(search_term):
    """Find running processes matching search_term. Returns list of (pid, cmdline)."""
    try:
        check = subprocess.run(['pgrep', '-af', search_term], capture_output=True, text=True, timeout=5)
        return [(l.split()[0], l) for l in check.stdout.strip().split('\n')
                if l.strip() and 'pgrep' not in l]
    except Exception:
        return []


# --- Main fix route ---
@app.route('/fix/<fix_type>')
def api_fix(fix_type):
    """Run a fix command."""

    # --- Stop All Senders ---
    if fix_type == 'stop_all_senders':
        try:
            import subprocess as _sp
            results = []
            for svc in ['a2-warmup', 'brevo-warmup', 'capacity-maximizer']:
                _sp.run(['sudo', 'systemctl', 'stop', svc + '.service'], capture_output=True, text=True, timeout=10)
                _sp.run(['sudo', 'systemctl', 'disable', svc + '.service'], capture_output=True, text=True, timeout=10)
                results.append(f'{svc}: stopped+disabled')
            from pathlib import Path
            Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/PAUSED').write_text('PAUSED via dashboard')
            results.append('ANOFM: paused')
            r = _sp.run(['crontab', '-l'], capture_output=True, text=True)
            if r.returncode == 0:
                lines = r.stdout.strip().split('\n')
                new_lines = []
                for line in lines:
                    if not line.startswith('#') and ('anofm_sender' in line or 'send_to_banks' in line):
                        new_lines.append('#DASH_PAUSED ' + line)
                    else:
                        new_lines.append(line)
                _sp.run(['crontab', '-'], input='\n'.join(new_lines) + '\n', text=True)
                results.append('Crons paused')
            return jsonify({
                'success': True,
                'output': '\n'.join(results),
                'fix_name': 'Stop All Senders'
            })
        except Exception as e:
            return jsonify({'success': False, 'output': str(e), 'fix_name': 'Stop All Senders'})

    # --- Start All Senders ---
    if fix_type == 'start_all_senders':
        try:
            import subprocess as _sp
            results = []
            for svc in ['a2-warmup', 'brevo-warmup', 'capacity-maximizer']:
                _sp.run(['sudo', 'systemctl', 'enable', '--now', svc + '.service'], capture_output=True, text=True, timeout=10)
                results.append(f'{svc}: started+enabled')
            from pathlib import Path
            p = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/PAUSED')
            if p.exists():
                p.unlink()
            results.append('ANOFM: unpaused')
            r = _sp.run(['crontab', '-l'], capture_output=True, text=True)
            if r.returncode == 0:
                new_cron = r.stdout.replace('#DASH_PAUSED ', '').replace('#PAUSED_TODAY ', '')
                _sp.run(['crontab', '-'], input=new_cron, text=True)
                results.append('Crons restored')
            return jsonify({
                'success': True,
                'output': '\n'.join(results),
                'fix_name': 'Start All Senders'
            })
        except Exception as e:
            return jsonify({'success': False, 'output': str(e), 'fix_name': 'Start All Senders'})

    # --- Email Status ---
    if fix_type == 'email_status':
        try:
            import subprocess as _sp
            results = []
            for svc in ['a2-warmup', 'brevo-warmup', 'capacity-maximizer']:
                r = _sp.run(['systemctl', 'is-active', svc + '.service'], capture_output=True, text=True, timeout=5)
                status = r.stdout.strip()
                results.append(f'{svc}: {status}')
            from pathlib import Path
            anofm_paused = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/PAUSED').exists()
            results.append(f'ANOFM: {"PAUSED" if anofm_paused else "active"}')
            r = _sp.run(['pgrep', '-af', 'send_necalificati'], capture_output=True, text=True)
            necal_running = bool(r.stdout.strip())
            results.append(f'NECALIFICATI sender: {"RUNNING" if necal_running else "idle"}')
            r = _sp.run(['crontab', '-l'], capture_output=True, text=True)
            paused_crons = r.stdout.count('#DASH_PAUSED') + r.stdout.count('#PAUSED_TODAY')
            results.append(f'Paused cron entries: {paused_crons}')
            return jsonify({
                'success': True,
                'output': '\n'.join(results),
                'fix_name': 'Email Sender Status'
            })
        except Exception as e:
            return jsonify({'success': False, 'output': str(e), 'fix_name': 'Email Sender Status'})

        # --- Campaign Report ---
    if fix_type == 'campaign_report':
        try:
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/campaign_report.py'],
                capture_output=True, text=True, timeout=30
            )
            return jsonify({
                'success': result.returncode == 0,
                'output': result.stdout + result.stderr,
                'fix_name': 'Campaign Report'
            })
        except Exception as e:
            return jsonify({'success': False, 'output': str(e), 'fix_name': 'Campaign Report'})

    # --- Sender Health Check ---
    if fix_type == 'sender_healthcheck':
        try:
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/sender_healthcheck.py'],
                capture_output=True, text=True, timeout=120
            )
            return jsonify({
                'success': result.returncode == 0,
                'output': result.stdout + result.stderr,
                'fix_name': 'Sender Health Check'
            })
        except Exception as e:
            return jsonify({'success': False, 'output': str(e), 'fix_name': 'Sender Health Check'})

    # --- Sender Scores ---
    if fix_type == 'sender_scores':
        try:
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/campaign_report.py', '--score'],
                capture_output=True, text=True, timeout=30
            )
            return jsonify({
                'success': result.returncode == 0,
                'output': result.stdout + result.stderr,
                'fix_name': 'Sender Scores'
            })
        except Exception as e:
            return jsonify({'success': False, 'output': str(e), 'fix_name': 'Sender Scores'})

    # --- Scraper restart: restart_scraper:NAME ---
    if fix_type.startswith('restart_scraper:'):
        scraper_name = fix_type.split(':', 1)[1].upper()
        if scraper_name not in SCRAPER_SCRIPTS:
            return jsonify({
                'success': False,
                'output': f'Unknown scraper: {scraper_name}. Available: {", ".join(sorted(SCRAPER_SCRIPTS))}',
                'fix_name': f'Restart {scraper_name}'
            })
        search_term = _get_script_search_term(scraper_name)
        running = _find_running(search_term)
        if running:
            pids = [r[0] for r in running]
            return jsonify({
                'success': False,
                'output': f'{scraper_name} already running (PIDs: {", ".join(pids)}). Kill first or wait.',
                'fix_name': f'Restart {scraper_name}'
            })
        subprocess.Popen(SCRAPER_SCRIPTS[scraper_name], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({
            'success': True,
            'output': f'Started {scraper_name} scraper. Check /opt/ACTIVE/INFRA/LOGS/fix_restart.log for output.',
            'fix_name': f'Restart {scraper_name}'
        })

    # --- Kill scraper: kill_scraper:NAME ---
    if fix_type.startswith('kill_scraper:'):
        scraper_name = fix_type.split(':', 1)[1].upper()
        if scraper_name not in SCRAPER_SCRIPTS:
            return jsonify({
                'success': False,
                'output': f'Unknown scraper: {scraper_name}. Available: {", ".join(sorted(SCRAPER_SCRIPTS))}',
                'fix_name': f'Kill {scraper_name}'
            })
        search_term = _get_script_search_term(scraper_name)
        running = _find_running(search_term)
        if not running:
            return jsonify({
                'success': False,
                'output': f'{scraper_name} is not currently running.',
                'fix_name': f'Kill {scraper_name}'
            })
        killed = []
        for pid, _ in running:
            subprocess.run(['kill', pid], capture_output=True, timeout=5)
            killed.append(pid)
        return jsonify({
            'success': True,
            'output': f'Killed {scraper_name} (PIDs: {", ".join(killed)})',
            'fix_name': f'Kill {scraper_name}'
        })

    # --- View logs: logs:NAME ---
    if fix_type.startswith('logs:'):
        scraper_name = fix_type.split(':', 1)[1].upper()
        today = date.today().strftime('%Y%m%d')
        log_candidates = [
            f'/opt/ACTIVE/INFRA/LOGS/restart_{today}/{scraper_name}.log',
            f'/opt/ACTIVE/INFRA/LOGS/restart_{today}/{scraper_name}_full.log',
        ]
        # Add any matching restart logs (newest first)
        log_candidates += sorted(globmod.glob(f'/opt/ACTIVE/INFRA/LOGS/restart_*/{scraper_name}*.log'), reverse=True)[:3]
        # Name-based logs
        log_candidates += sorted(globmod.glob(f'/opt/ACTIVE/INFRA/LOGS/{scraper_name.lower()}*.log'), reverse=True)[:2]
        # Shared fix log
        log_candidates.append('/opt/ACTIVE/INFRA/LOGS/fix_restart.log')

        for log_path in log_candidates:
            if os.path.exists(log_path):
                try:
                    result = subprocess.run(['tail', '-50', log_path], capture_output=True, text=True, timeout=5)
                    return jsonify({
                        'success': True,
                        'output': f'=== {log_path} ===\n{result.stdout}',
                        'fix_name': f'Logs: {scraper_name}'
                    })
                except Exception:
                    continue
        return jsonify({
            'success': False,
            'output': f'No logs found for {scraper_name}',
            'fix_name': f'Logs: {scraper_name}'
        })

    # --- Restart all stale scrapers ---
    if fix_type == 'restart_all_stale':
        try:
            from static_dashboard_pure import get_scrapers
            scrapers = get_scrapers()
        except Exception as e:
            return jsonify({'success': False, 'output': f'Could not load scrapers: {e}', 'fix_name': 'Restart All Stale'})

        stale = [s for s in scrapers if s['age_h'] > 48 and s['name'] in SCRAPER_SCRIPTS]
        if not stale:
            return jsonify({'success': True, 'output': 'No stale scrapers with restart scripts found.', 'fix_name': 'Restart All Stale'})

        results = []
        started = 0
        for s in stale:
            name = s['name']
            search_term = _get_script_search_term(name)
            running = _find_running(search_term)
            if running:
                results.append(f'{name}: SKIPPED (already running)')
            else:
                subprocess.Popen(SCRAPER_SCRIPTS[name], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                results.append(f'{name}: STARTED (was {s["age_h"]}h stale)')
                started += 1
        return jsonify({
            'success': True,
            'output': '\n'.join(results),
            'fix_name': f'Restart All Stale ({started} started)'
        })

    # --- System load ---
    if fix_type == 'system_load':
        parts = []
        try:
            r = subprocess.run(['uptime'], capture_output=True, text=True, timeout=5)
            parts.append(f'UPTIME: {r.stdout.strip()}')
        except Exception:
            pass
        try:
            r = subprocess.run(['free', '-h'], capture_output=True, text=True, timeout=5)
            parts.append(f'\nMEMORY:\n{r.stdout}')
        except Exception:
            pass
        try:
            r = subprocess.run(['ps', 'aux', '--sort=-%cpu'], capture_output=True, text=True, timeout=5)
            lines = r.stdout.strip().split('\n')
            parts.append('\nTOP CPU PROCESSES:\n' + '\n'.join(lines[:11]))
        except Exception:
            pass
        try:
            r = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
            parts.append(f'\nDISK:\n{r.stdout}')
        except Exception:
            pass
        try:
            temp = open('/sys/class/thermal/thermal_zone0/temp').read().strip()
            parts.append(f'\nCPU TEMP: {int(temp)/1000:.1f}C')
        except Exception:
            pass
        return jsonify({
            'success': True,
            'output': '\n'.join(parts),
            'fix_name': 'System Load'
        })

    # --- Resolve aliases ---
    if fix_type in FIX_ALIASES:
        fix_type = FIX_ALIASES[fix_type]

    # --- Clear lock (special) ---
    if fix_type == 'clear_lock':
        lock = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK')
        if lock.exists():
            lock.unlink()
            return jsonify({'success': True, 'output': 'Send lock cleared.', 'fix_name': 'Clear Lock'})
        else:
            return jsonify({'success': True, 'output': 'No lock file found (already clear).', 'fix_name': 'Clear Lock'})

    # --- Async campaign feed (avoid 120s timeout) ---
    if fix_type == 'campaign_low':
        cmd = '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/scraper_to_campaigns.py >> /opt/ACTIVE/INFRA/LOGS/campaigns/auto_feed.log 2>&1'
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({
            'success': True,
            'output': 'Campaign feed started in background.\nCheck /opt/ACTIVE/INFRA/LOGS/campaigns/auto_feed.log for progress.\nTakes 2-3 min (MX validation on every email).',
            'fix_name': 'Feed Campaigns (async)'
        })

    # --- Standard FIX_COMMANDS ---
    if fix_type not in FIX_COMMANDS:
        return jsonify({'success': False, 'output': f'Unknown fix: {fix_type}', 'fix_name': fix_type})

    result = run_fix(fix_type)
    return jsonify({
        'success': result['success'],
        'output': result['output'][:2000],
        'fix_name': result.get('fix_name', FIX_COMMANDS[fix_type]['name'])
    })



# --- Campaign stats ---
@app.route('/campaigns')
def campaign_stats():
    """Detailed campaign statistics."""
    campaigns_dir = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
    today_str = date.today().strftime('%Y%m%d')
    today_iso = date.today().strftime('%Y-%m-%d')
    result = []

    if campaigns_dir.exists():
        for d in sorted(campaigns_dir.iterdir()):
            if not d.is_dir() or not (d / 'state.json').exists():
                continue
            try:
                state = json.loads((d / 'state.json').read_text())
                total_sent = len(state.get('sent', []))

                # Contact count
                contacts = 0
                contacts_dir = d / 'contacts'
                if contacts_dir.exists():
                    for csv_f in contacts_dir.glob('*.csv'):
                        try:
                            contacts += sum(1 for _ in open(csv_f)) - 1
                        except Exception:
                            pass

                # Today's sends from log
                today_count = 0
                log_file = d / 'logs' / f'sent_{today_str}.log'
                if log_file.exists():
                    try:
                        today_count = sum(1 for l in open(log_file) if l.strip())
                    except Exception:
                        pass

                # Yesterday's sends
                from datetime import timedelta
                yest_str = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
                yest_count = 0
                yest_log = d / 'logs' / f'sent_{yest_str}.log'
                if yest_log.exists():
                    try:
                        yest_count = sum(1 for l in open(yest_log) if l.strip())
                    except Exception:
                        pass

                queue = max(0, contacts - total_sent)
                paused = (d / 'PAUSED').exists()

                # Last send time from log
                last_send = ''
                if log_file.exists():
                    try:
                        lines = open(log_file).readlines()
                        if lines:
                            last_send = lines[-1].split('|')[0].strip()
                    except Exception:
                        pass

                result.append({
                    'name': d.name,
                    'contacts': contacts,
                    'total_sent': total_sent,
                    'today': today_count,
                    'yesterday': yest_count,
                    'queue': queue,
                    'paused': paused,
                    'last_send': last_send,
                    'completion_pct': round(total_sent / contacts * 100, 1) if contacts > 0 else 0,
                })
            except Exception:
                pass

    return jsonify({
        'success': True,
        'output': json.dumps(result, indent=2),
        'fix_name': f'Campaign Stats ({len(result)} campaigns)',
        'data': result,
    })


# --- Unified log viewer ---
@app.route('/logs_view')
@app.route('/logs_view/<category>')
def logs_view(category='all'):
    """List and view recent log files."""
    import glob as _glob
    log_dirs = {
        'scrapers': '/opt/ACTIVE/INFRA/LOGS/scrapers',
        'campaigns': '/opt/ACTIVE/INFRA/LOGS/campaigns',
        'brevo': '/opt/ACTIVE/INFRA/LOGS',
        'system': '/opt/ACTIVE/INFRA/LOGS',
        'capacity': '/opt/ACTIVE/INFRA/LOGS/capacity_maximizer',
    }

    files = []
    today_str = date.today().strftime('%Y%m%d')
    yest_str = (date.today() - __import__('datetime').timedelta(days=1)).strftime('%Y%m%d')

    if category in ('all', 'scrapers'):
        for f in sorted(_glob.glob('/opt/ACTIVE/INFRA/LOGS/scrapers/*.log'), reverse=True)[:20]:
            files.append(('scrapers', os.path.basename(f), f, os.path.getmtime(f)))
        # Also check restart dirs
        for f in sorted(_glob.glob(f'/opt/ACTIVE/INFRA/LOGS/scrapers/restart_{today_str}/*.log'), reverse=True):
            files.append(('scrapers', os.path.basename(f), f, os.path.getmtime(f)))

    if category in ('all', 'campaigns'):
        for f in sorted(_glob.glob('/opt/ACTIVE/INFRA/LOGS/campaigns/*.log'), reverse=True)[:20]:
            files.append(('campaigns', os.path.basename(f), f, os.path.getmtime(f)))

    if category in ('all', 'brevo'):
        for f in sorted(_glob.glob(f'/opt/ACTIVE/INFRA/LOGS/brevo_*_{today_str}.log') +
                        _glob.glob(f'/opt/ACTIVE/INFRA/LOGS/brevo_*_{yest_str}.log'), reverse=True):
            files.append(('brevo', os.path.basename(f), f, os.path.getmtime(f)))

    if category in ('all', 'system'):
        for name in ['fix_api.log', 'gmail_clean.log', 'followup_digest.log',
                      'followup_propose.log', 'necalificati_scrape.log', 'necalificati_watchdog.log']:
            fp = f'/opt/ACTIVE/INFRA/LOGS/{name}'
            if os.path.exists(fp):
                files.append(('system', name, fp, os.path.getmtime(fp)))

    if category in ('all', 'capacity'):
        for f in sorted(_glob.glob('/opt/ACTIVE/INFRA/LOGS/capacity_maximizer/*.log'), reverse=True)[:5]:
            files.append(('capacity', os.path.basename(f), f, os.path.getmtime(f)))

    # Sort by mtime desc
    files.sort(key=lambda x: x[3], reverse=True)

    # Format output
    lines = [f'=== LOG FILES ({category}) ===', '']
    for cat, name, path, mtime in files[:40]:
        ts = datetime.fromtimestamp(mtime).strftime('%m-%d %H:%M')
        size_kb = os.path.getsize(path) / 1024
        lines.append(f'[{cat:10s}] {ts}  {size_kb:>7.0f}KB  {name}')

    return jsonify({
        'success': True,
        'output': '\n'.join(lines),
        'fix_name': f'Log Files ({len(files)} found)',
    })


@app.route('/log/<path:log_path>')
def view_log(log_path):
    """View last 100 lines of a specific log file."""
    # Security: only allow files under /opt/ACTIVE/INFRA/LOGS
    full_path = os.path.realpath(f'/opt/ACTIVE/INFRA/LOGS/{log_path}')
    if not full_path.startswith('/opt/ACTIVE/INFRA/LOGS/'):
        return jsonify({'success': False, 'output': 'Access denied', 'fix_name': 'View Log'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'output': f'File not found: {log_path}', 'fix_name': 'View Log'})
    try:
        result = subprocess.run(['tail', '-100', full_path], capture_output=True, text=True, timeout=5)
        return jsonify({
            'success': True,
            'output': f'=== {log_path} (last 100 lines) ===\n{result.stdout}',
            'fix_name': f'Log: {os.path.basename(log_path)}',
        })
    except Exception as e:
        return jsonify({'success': False, 'output': str(e), 'fix_name': 'View Log'})


@app.route('/fixes')
def list_fixes():
    """List available fixes."""
    fixes = {fix_id: fix['name'] for fix_id, fix in FIX_COMMANDS.items()}
    fixes['restart_all_stale'] = 'Restart all stale scrapers'
    fixes['system_load'] = 'System load info'
    for name in SCRAPER_SCRIPTS:
        fixes[f'restart_scraper:{name}'] = f'Restart {name}'
        fixes[f'kill_scraper:{name}'] = f'Kill {name}'
        fixes[f'logs:{name}'] = f'View {name} logs'
    return jsonify(fixes)


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=8089)
    args = parser.parse_args()

    if args.serve:
        print(f"Fix API v2 running on port {args.port}")
        app.run(host='0.0.0.0', port=args.port, debug=False)
    else:
        parser.print_help()
