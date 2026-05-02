#!/opt/ACTIVE/INFRA/venv/bin/python3
"""Campaign Health Check -- audit all unified campaigns for issues.

Usage:
    python3 campaign_health_check.py          # Full audit
    python3 campaign_health_check.py --quick  # Just status + errors

Checks:
    1. Config JSON files parse correctly
    2. Brevo API keys exist in .env
    3. Gmail passwords authenticate
    4. Enabled sectors have pending contacts
    5. DB columns match config mappings
    6. Orchestrator script paths exist
    7. Blacklist/bounces overlap with pending contacts
"""
import json
import os
import sys
import smtplib
import ssl
import sqlite3
import subprocess
import re
import psycopg2
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

CONFIGS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs')
ENV_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')
BLACKLIST_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt')
BOUNCES_DB = Path('/opt/ACTIVE/OPENDATA/DATA/bounces.db')
ORCH_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/campaign_orchestrator_24_7.py')
SENDER = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py')
PYTHON = '/opt/ACTIVE/INFRA/venv/bin/python3'

load_dotenv(ENV_FILE)


def check_configs():
    issues = []
    configs = {}
    for f in sorted(CONFIGS_DIR.glob('*.json')):
        try:
            cfg = json.loads(f.read_text())
            configs[f.stem] = cfg
            if 'sectors' not in cfg:
                issues.append('[CRITICAL] ' + f.name + ': missing sectors key')
            if 'db' not in cfg:
                issues.append('[CRITICAL] ' + f.name + ': missing db key')
        except Exception as e:
            issues.append('[CRITICAL] ' + f.name + ': parse error: ' + str(e))
    return configs, issues


def check_brevo_keys(configs):
    issues = []
    for name, cfg in configs.items():
        for sector, scfg in cfg.get('sectors', {}).items():
            key = scfg.get('sender_key', '')
            if key and not os.environ.get(key):
                issues.append('[CRITICAL] ' + name + '/' + sector + ': env var ' + key + ' missing')
    return issues


def check_gmail(configs):
    issues = []
    tested = set()
    for name, cfg in configs.items():
        for s in cfg.get('gmail_senders', []):
            email = s['email']
            if email in tested:
                continue
            tested.add(email)
            pw_key = s.get('env_pass', '')
            pw = os.environ.get(pw_key, '')
            if not pw:
                issues.append('[CRITICAL] ' + name + ': Gmail ' + email + ' env var ' + pw_key + ' missing')
                continue
            pw_clean = pw.strip().strip('"').replace(' ', '')
            try:
                ctx = ssl.create_default_context()
                srv = smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx, timeout=10)
                srv.login(email, pw_clean)
                srv.quit()
                print('  Gmail OK: ' + email)
            except smtplib.SMTPAuthenticationError as e:
                code = e.smtp_code
                if code == 534:
                    issues.append('[CRITICAL] ' + name + ': Gmail ' + email + ' LOCKED (needs browser login)')
                else:
                    issues.append('[CRITICAL] ' + name + ': Gmail ' + email + ' wrong password')
            except Exception as e:
                issues.append('[WARN] ' + name + ': Gmail ' + email + ' error: ' + str(e)[:50])
    return issues


def check_db_columns(configs):
    issues = []
    for name, cfg in configs.items():
        db = cfg.get('db', {})
        tables = cfg.get('tables', {})
        contacts_tbl = tables.get('contacts', 'contacts')
        try:
            conn = psycopg2.connect(**db)
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (contacts_tbl,)
            )
            actual_cols = {r[0] for r in cur.fetchall()}
            conn.close()
            for key, mapped in tables.items():
                if key.startswith('col_') and mapped not in actual_cols:
                    issues.append('[HIGH] ' + name + ': column ' + mapped + ' (from ' + key + ') missing in ' + contacts_tbl)
        except Exception as e:
            issues.append('[WARN] ' + name + ': DB connect error: ' + str(e)[:50])
    return issues


def check_orchestrator():
    issues = []
    if not ORCH_FILE.exists():
        issues.append('[CRITICAL] Orchestrator missing: ' + str(ORCH_FILE))
        return issues
    content = ORCH_FILE.read_text()
    for m in re.finditer(r'"enabled":\s*True', content):
        chunk = content[max(0, m.start()-200):m.start()]
        name_match = re.search(r'"(\w+)":\s*\{[^}]*$', chunk)
        if not name_match:
            continue
        cname = name_match.group(1)
        after = content[m.end():m.end()+500]
        script_match = re.search(r'"script":\s*"([^"]+)"', after)
        if script_match:
            spath = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS') / script_match.group(1)
            if not spath.exists():
                issues.append('[CRITICAL] Orchestrator ' + cname + ': script missing: ' + str(spath))
        else:
            dir_match = re.search(r'"campaign_dir":\s*"([^"]+)"', after)
            sender_match = re.search(r'"sender_script":\s*"([^"]+)"', after)
            if dir_match and sender_match:
                spath = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS') / dir_match.group(1) / sender_match.group(1)
                if not spath.exists():
                    issues.append('[CRITICAL] Orchestrator ' + cname + ': script missing: ' + str(spath))
    return issues


def check_pending(configs):
    issues = []
    for name, cfg in configs.items():
        for sector, scfg in cfg.get('sectors', {}).items():
            if not scfg.get('enabled', True):
                continue
            try:
                r = subprocess.run(
                    [PYTHON, str(SENDER), '--config', str(CONFIGS_DIR / (name + '.json')),
                     '--sector', sector, '--status'],
                    capture_output=True, text=True, timeout=30
                )
                line = r.stdout.strip()
                if '|      0 pend' in line or '|       0 pend' in line:
                    issues.append('[WARN] ' + name + '/' + sector + ': 0 pending contacts')
                print('  ' + line)
            except Exception:
                issues.append('[WARN] ' + name + '/' + sector + ': status check failed')
    return issues


def check_blacklist_overlap(configs):
    issues = []
    bl = set()
    if BLACKLIST_FILE.exists():
        with open(BLACKLIST_FILE) as f:
            for line in f:
                e = line.strip().lower()
                if '@' in e:
                    bl.add(e)
    if BOUNCES_DB.exists():
        try:
            conn = sqlite3.connect(str(BOUNCES_DB))
            for r in conn.execute('SELECT email FROM bounces'):
                bl.add(r[0].lower())
            conn.close()
        except Exception:
            pass
    if not bl:
        return issues
    for name, cfg in configs.items():
        db = cfg.get('db', {})
        tables = cfg.get('tables', {})
        email_col = tables.get('col_email', 'email')
        contacts_tbl = tables.get('contacts', 'contacts')
        try:
            conn = psycopg2.connect(**db)
            cur = conn.cursor()
            cur.execute('SELECT LOWER(' + email_col + ') FROM ' + contacts_tbl + ' WHERE ' + email_col + ' IS NOT NULL')
            emails = {r[0] for r in cur.fetchall()}
            conn.close()
            overlap = len(emails & bl)
            if overlap > 0:
                pct = overlap / len(emails) * 100
                sev = '[HIGH]' if pct > 20 else '[INFO]'
                issues.append(sev + ' ' + name + ': ' + str(overlap) + '/' + str(len(emails)) + ' (' + str(round(pct)) + '%) in blacklist/bounces')
        except Exception:
            pass
    return issues


def main():
    quick = '--quick' in sys.argv
    print('=' * 60)
    print('CAMPAIGN HEALTH CHECK  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('=' * 60)

    configs, issues = check_configs()
    print('\nConfigs: ' + str(len(configs)) + ' loaded')

    if not quick:
        print('\n-- Brevo API Keys --')
        issues += check_brevo_keys(configs)
        print('  Checked')

        print('\n-- Gmail Auth --')
        issues += check_gmail(configs)

        print('\n-- DB Columns --')
        issues += check_db_columns(configs)
        print('  Checked')

        print('\n-- Orchestrator Scripts --')
        issues += check_orchestrator()
        print('  Checked')

        print('\n-- Blacklist Overlap --')
        issues += check_blacklist_overlap(configs)

    print('\n-- Sector Status --')
    issues += check_pending(configs)

    critical = [i for i in issues if '[CRITICAL]' in i]
    high = [i for i in issues if '[HIGH]' in i]
    warn = [i for i in issues if '[WARN]' in i]
    info = [i for i in issues if '[INFO]' in i]

    print('\n' + '=' * 60)
    if critical:
        print('CRITICAL (' + str(len(critical)) + '):')
        for i in critical:
            print('  ' + i)
    if high:
        print('HIGH (' + str(len(high)) + '):')
        for i in high:
            print('  ' + i)
    if warn:
        print('WARNINGS (' + str(len(warn)) + '):')
        for i in warn:
            print('  ' + i)
    if info:
        print('INFO (' + str(len(info)) + '):')
        for i in info:
            print('  ' + i)

    if not issues:
        print('All checks passed.')

    print('\nTotal issues: ' + str(len(issues)))
    return 1 if critical else 0


if __name__ == '__main__':
    sys.exit(main())
