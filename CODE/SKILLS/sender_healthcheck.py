#!/usr/bin/env python3
"""
Sender Health Check — verify all active email senders are consistent and operational.

Checks:
  - Syntax (py_compile)
  - Required features (sender_utils imports, fix_email, load_blacklist, bounce check, lock file, dedup)
  - State file integrity
  - Gmail app password validity (IMAP login test)
  - Blacklist coverage (all sources loaded)
  - Stale state detection
  - Template unsubscribe link

Usage:
    python3 sender_healthcheck.py           # Full check
    python3 sender_healthcheck.py --quick   # Skip IMAP tests
    python3 sender_healthcheck.py --fix     # Auto-fix where possible
"""

import os
import sys
import json
import csv
import py_compile
import imaplib
from pathlib import Path
from datetime import datetime, date, timedelta

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS/lib')

# === Config ===

ACTIVE_SENDERS = {
    'NECALIFICATI': {
        'script': '/opt/ACTIVE/EMAIL/CAMPAIGNS/NECALIFICATI_FEB_2026/send_necalificati.py',
        'state': '/opt/ACTIVE/EMAIL/CAMPAIGNS/NECALIFICATI_FEB_2026/.state.json',
        'templates': '/opt/ACTIVE/EMAIL/CAMPAIGNS/NECALIFICATI_FEB_2026/templates/',
        'campaign_name': 'NECALIFICATI_FEB_2026',
    },
    'ANOFM': {
        'script': '/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/anofm_sender.py',
        'state': '/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/gmail_yahoo_state.json',
        'templates': '/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/',
        'campaign_name': 'ANOFM_YAHOO',
    },
}

REQUIRED_FEATURES = [
    'sender_utils',       # Shared library import
    'fix_email',          # Email validation
    'load_blacklist',     # Unified blacklist loading
    'check_gmail_bounce', # IMAP bounce detection
    'acquire_lock',       # Lock file
    'release_lock',       # Lock release
    'was_recently_sent',  # Cross-campaign dedup
    'log_send',           # Global send logging
    'unsubscribe_url',    # Unsubscribe link
    'add_to_blacklist',   # Bounce write-back
]

BLACKLIST_SOURCES = [
    Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt'),
    Path('/opt/ACTIVE/OPENDATA/DATA/MASTER_DNC.csv'),
    Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/master_blacklist.csv'),
]

from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

GMAIL_ACCOUNTS = [
    {'email': 'elena.manpower.dristor@gmail.com', 'password_env': 'GMAIL_ELENA_PASSWORD'},
    {'email': 'manpowerdristor@gmail.com', 'password_env': 'GMAIL_APP_PASSWORD'},
    {'email': 'expatsinromania@gmail.com', 'password_env': 'GMAIL_EXPATS_PASSWORD'},
    {'email': 'pamintstrabun@gmail.com', 'password_env': 'GMAIL_PAMINTSTRABUN_PASSWORD'},
    {'email': 'casafaurbucuresti@gmail.com', 'password_env': 'GMAIL_CASAFAUR_PASSWORD'},
    {'email': 'fructexportromania@gmail.com', 'password_env': 'GMAIL_FRUCTEXPORT_PASSWORD'},
    {'email': 'manpowersearchromania@gmail.com', 'password_env': 'GMAIL_MANPOWERSEARCH_PASSWORD'},
]


# === Checks ===

def check_syntax(name, cfg):
    """Check if sender script compiles."""
    script = cfg['script']
    if not os.path.exists(script):
        return False, f'Script not found: {script}'
    try:
        py_compile.compile(script, doraise=True)
        return True, 'OK'
    except py_compile.PyCompileError as e:
        return False, f'Syntax error: {e}'


def check_features(name, cfg):
    """Check if all required features are present."""
    script = cfg['script']
    with open(script) as f:
        code = f.read()

    missing = []
    for feature in REQUIRED_FEATURES:
        if feature not in code:
            missing.append(feature)

    if missing:
        return False, f'Missing: {", ".join(missing)}'
    return True, f'All {len(REQUIRED_FEATURES)} features present'


def check_state(name, cfg):
    """Check state file integrity and format."""
    state_path = cfg['state']
    if not os.path.exists(state_path):
        return False, 'State file not found'

    try:
        with open(state_path) as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        return False, f'Invalid JSON: {e}'

    issues = []

    # Check sent format is dict
    sent = state.get('sent', {})
    if isinstance(sent, list):
        issues.append(f'sent is list ({len(sent)} items) - should be dict')
    elif isinstance(sent, dict):
        pass  # OK
    else:
        issues.append(f'sent is {type(sent).__name__} - should be dict')

    # Check failed format
    failed = state.get('failed', {})
    if isinstance(failed, list):
        issues.append(f'failed is list ({len(failed)} items) - should be dict')

    # Check for stale state (no sends in last 7 days)
    daily = state.get('daily', {})
    if daily:
        last_date = max(daily.keys())
        days_ago = (date.today() - date.fromisoformat(last_date)).days
        if days_ago > 7:
            issues.append(f'Last send was {days_ago} days ago ({last_date})')

    # Check lock file isn't stuck
    lock_file = Path(cfg['script']).parent / '.send.lock'
    if lock_file.exists():
        try:
            pid = int(lock_file.read_text().strip())
            os.kill(pid, 0)
            issues.append(f'Lock file active (PID {pid})')
        except (ProcessLookupError, ValueError):
            issues.append(f'Stale lock file (PID gone)')
        except PermissionError:
            pass

    if issues:
        return False, '; '.join(issues)

    sent_count = len(sent) if isinstance(sent, dict) else len(sent)
    return True, f'OK (sent={sent_count}, daily entries={len(daily)})'


def check_templates(name, cfg):
    """Check templates have unsubscribe placeholder."""
    tpl_dir = cfg['templates']
    issues = []

    if os.path.isdir(tpl_dir):
        for f in os.listdir(tpl_dir):
            if f.endswith('.txt'):
                content = open(os.path.join(tpl_dir, f)).read()
                if '{unsubscribe_url}' not in content and 'unsubscribe' not in content.lower():
                    issues.append(f'{f}: no unsubscribe')
    else:
        # Single template file
        tpl_file = Path(tpl_dir) / 'email_template.txt'
        if tpl_file.exists():
            content = tpl_file.read_text()
            if '{unsubscribe_url}' not in content:
                issues.append('email_template.txt: no unsubscribe')

    if issues:
        return False, '; '.join(issues)
    return True, 'OK'


def check_blacklists():
    """Check all blacklist sources are present and loaded."""
    issues = []
    total = 0

    for src in BLACKLIST_SOURCES:
        if not src.exists():
            issues.append(f'Missing: {src.name}')
        else:
            try:
                count = sum(1 for _ in open(src)) - (1 if src.suffix == '.csv' else 0)
                total += count
            except Exception:
                issues.append(f'Unreadable: {src.name}')

    if issues:
        return False, f'{"; ".join(issues)} (total readable: {total})'
    return True, f'All {len(BLACKLIST_SOURCES)} sources OK ({total} total entries)'


def check_global_tracker():
    """Check global send tracker is operational."""
    log_path = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/global_send_log.csv')
    if not log_path.exists():
        return False, 'global_send_log.csv not found'

    lines = sum(1 for _ in open(log_path))
    if lines < 10:
        return False, f'Only {lines} entries (expected thousands)'

    # Check if recent entries exist
    last_line = ''
    with open(log_path) as f:
        for line in f:
            last_line = line
    if last_line:
        parts = last_line.strip().split(',')
        if parts[0] and parts[0] >= (date.today() - timedelta(days=7)).isoformat():
            return True, f'OK ({lines} entries, last: {parts[0]})'

    return True, f'OK ({lines} entries, but recent activity unclear)'


def check_gmail_passwords(quick=False):
    """Test Gmail IMAP login for all accounts."""
    if quick:
        # Just check env vars exist
        results = []
        for acct in GMAIL_ACCOUNTS:
            pwd = os.getenv(acct['password_env'], '')
            short = acct['email'].split('@')[0][:20]
            if pwd:
                results.append(f'{short}: env OK')
            else:
                results.append(f'{short}: MISSING')
        missing = sum(1 for r in results if 'MISSING' in r)
        if missing:
            return False, f'{missing} missing passwords'
        return True, f'All {len(GMAIL_ACCOUNTS)} env vars set'

    # Full IMAP test
    results = []
    for acct in GMAIL_ACCOUNTS:
        short = acct['email'].split('@')[0][:20]
        pwd = os.getenv(acct['password_env'], '')
        if not pwd:
            results.append((False, f'{short}: no password'))
            continue
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com', 993, timeout=10)
            mail.login(acct['email'], pwd)
            mail.logout()
            results.append((True, f'{short}: OK'))
        except Exception as e:
            results.append((False, f'{short}: {str(e)[:40]}'))

    failures = [r[1] for r in results if not r[0]]
    if failures:
        return False, f'{len(failures)} failed: {"; ".join(failures)}'
    return True, f'All {len(results)} accounts OK'


def check_crontab():
    """Check cron entries exist for active senders."""
    import subprocess
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
        cron = result.stdout
    except Exception:
        return False, 'Cannot read crontab'

    checks = {
        'NECALIFICATI watchdog': 'necalificati' in cron.lower() and 'watchdog' in cron.lower(),
        'ANOFM sender': 'anofm_sender' in cron,
        'Reply detector': 'reply_detector' in cron,
        'Blacklist consolidation': 'consolidate_blacklist' in cron,
        'Unsubscribe sync': 'sync_unsubscribe' in cron,
        'Bounce manager': 'bounce' in cron.lower(),
    }

    missing = [k for k, v in checks.items() if not v]
    if missing:
        return False, f'Missing cron: {", ".join(missing)}'
    return True, f'All {len(checks)} cron entries found'


def fix_stale_lock(name, cfg):
    """Remove stale lock files."""
    lock_file = Path(cfg['script']).parent / '.send.lock'
    if lock_file.exists():
        try:
            pid = int(lock_file.read_text().strip())
            os.kill(pid, 0)
            return False, f'Lock is active (PID {pid}), cannot remove'
        except (ProcessLookupError, ValueError):
            lock_file.unlink()
            return True, 'Removed stale lock'
        except PermissionError:
            return False, 'Permission denied'
    return True, 'No lock to remove'


# === Main ===

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Email Sender Health Check')
    parser.add_argument('--quick', action='store_true', help='Skip IMAP login tests')
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues where possible')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    args = parser.parse_args()

    results = {}
    all_ok = True

    print('=' * 60)
    print('  EMAIL SENDER HEALTH CHECK')
    print(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    # Per-sender checks
    for name, cfg in ACTIVE_SENDERS.items():
        print(f'\n--- {name} ---')
        sender_results = {}

        for check_name, check_fn in [
            ('Syntax', check_syntax),
            ('Features', check_features),
            ('State', check_state),
            ('Templates', check_templates),
        ]:
            ok, msg = check_fn(name, cfg)
            status = 'PASS' if ok else 'FAIL'
            print(f'  {check_name:20s} [{status}] {msg}')
            sender_results[check_name.lower()] = {'ok': ok, 'message': msg}
            if not ok:
                all_ok = False

        results[name] = sender_results

        # Auto-fix stale locks if --fix
        if args.fix:
            ok, msg = fix_stale_lock(name, cfg)
            if 'Removed' in msg:
                print(f'  {"Fix: Lock":20s} [FIXED] {msg}')

    # Global checks
    print(f'\n--- GLOBAL ---')
    for check_name, check_fn in [
        ('Blacklists', lambda: check_blacklists()),
        ('Global Tracker', lambda: check_global_tracker()),
        ('Gmail Passwords', lambda: check_gmail_passwords(args.quick)),
        ('Crontab', lambda: check_crontab()),
    ]:
        ok, msg = check_fn()
        status = 'PASS' if ok else 'FAIL'
        print(f'  {check_name:20s} [{status}] {msg}')
        results[check_name.lower()] = {'ok': ok, 'message': msg}
        if not ok:
            all_ok = False

    # Summary
    print('\n' + '=' * 60)
    if all_ok:
        print('  ALL CHECKS PASSED')
    else:
        fails = sum(1 for v in results.values()
                    if isinstance(v, dict) and (
                        not v.get('ok', True) if 'ok' in v
                        else any(not sv.get('ok', True) for sv in v.values() if isinstance(sv, dict))
                    ))
        print(f'  {fails} CHECK(S) NEED ATTENTION')
    print('=' * 60)

    if args.json:
        print(json.dumps(results, indent=2))

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
