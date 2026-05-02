#!/usr/bin/env python3
"""
Enrichment Skill - standalone tool for LLM Studio or cron.
Wraps enrich_countries.py with simple commands.
No LLM tokens needed - pure rapidfuzz matching.

Install on raspibig: /opt/SKILLS/enrichment_skill.py
Companion: /opt/ACTIVE/OPENDATA/enrich_countries.py

Commands (from LLM or CLI):
    python3 enrichment_skill.py status
    python3 enrichment_skill.py enrich france
    python3 enrichment_skill.py enrich all
    python3 enrichment_skill.py enrich slovenia
    python3 enrichment_skill.py results
    python3 enrichment_skill.py schedule    # show cron setup
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PYTHON = '/opt/ACTIVE/INFRA/venv/bin/python3'
ENRICHER = '/opt/ACTIVE/OPENDATA/enrich_countries.py'
LOG_DIR = Path('/opt/ACTIVE/OPENDATA')
DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA')
ENRICHED_DIR = DATA_DIR / 'ENRICHED'

COUNTRIES = ['france', 'slovenia', 'bosnia']


def run_status():
    """Show data and enrichment status."""
    print('=== TARGET DATA ===')
    targets = {
        'france': DATA_DIR / 'FRANCE/COMPANIES',
        'slovenia': DATA_DIR / 'SLOVENIA/COMPANIES',
        'bosnia': DATA_DIR / 'BOSNIA/COMPANIES',
    }
    for country, d in targets.items():
        if d.exists():
            csvs = sorted(d.glob('*target*csv')) or sorted(d.glob('*companies*csv'))
            if csvs:
                f = csvs[-1]
                lines = sum(1 for _ in open(f, encoding='utf-8', errors='ignore')) - 1
                mb = f.stat().st_size / (1024*1024)
                print(f'  {country}: {lines:,} companies ({mb:.1f}MB) - {f.name}')
            else:
                print(f'  {country}: no CSV files')
        else:
            print(f'  {country}: directory not found')

    print('\n=== ENRICHED OUTPUT ===')
    if ENRICHED_DIR.exists():
        for f in sorted(ENRICHED_DIR.glob('*_enriched_*.csv')):
            mb = f.stat().st_size / (1024*1024)
            # Count matched rows
            matched = 0
            total = 0
            with open(f, encoding='ascii', errors='ignore') as fh:
                header = fh.readline()
                for line in fh:
                    total += 1
                    if ',TED,' in line or ',EURES,' in line or ',GM,' in line:
                        matched += 1
            rate = 100*matched/total if total else 0
            print(f'  {f.name}: {matched:,}/{total:,} matched ({rate:.1f}%) [{mb:.1f}MB]')
    else:
        print('  No enriched files yet')

    print('\n=== RUNNING PROCESSES ===')
    result = subprocess.run(['pgrep', '-af', 'enrich_countries'], capture_output=True, text=True)
    if result.stdout.strip():
        for line in result.stdout.strip().split('\n'):
            print(f'  {line}')
    else:
        print('  None running')


def run_enrich(country):
    """Run enrichment for a country or all."""
    if country == 'all':
        flag = '--all'
    elif country in COUNTRIES:
        flag = f'--{country}'
    else:
        print(f'Unknown country: {country}. Use: {", ".join(COUNTRIES)} or all')
        return

    log = LOG_DIR / f'enrich_{country}.log'
    cmd = f'nohup {PYTHON} -u {ENRICHER} {flag} > {log} 2>&1 &'
    print(f'Starting enrichment: {country}')
    print(f'Log: {log}')
    os.system(cmd)
    print(f'Running in background. Monitor with: tail -f {log}')


def run_results():
    """Show enrichment results summary as JSON (for LLM consumption)."""
    results = {}
    if ENRICHED_DIR.exists():
        for f in sorted(ENRICHED_DIR.glob('*_enriched_*.csv')):
            country = f.stem.split('_enriched_')[0]
            matched = 0
            total = 0
            emails = 0
            phones = 0
            with open(f, encoding='ascii', errors='ignore') as fh:
                header = fh.readline()
                for line in fh:
                    total += 1
                    parts = line.split(',')
                    if len(parts) > 12 and parts[-4]:  # match_source column
                        matched += 1
                    if len(parts) > 11 and '@' in parts[11]:
                        emails += 1
                    if len(parts) > 12 and parts[12].startswith('+'):
                        phones += 1
            results[country] = {
                'total': total,
                'matched': matched,
                'emails': emails,
                'phones': phones,
                'rate': f'{100*matched/total:.1f}%' if total else '0%',
                'file': str(f),
            }
    print(json.dumps(results, indent=2))


def show_schedule():
    """Show recommended cron setup."""
    print('=== RECOMMENDED CRON SCHEDULE ===')
    print('# Weekly enrichment (Sunday 3am) - add to crontab -e:')
    print(f'0 3 * * 0 {PYTHON} -u {ENRICHER} --all > {LOG_DIR}/enrich_weekly.log 2>&1')
    print()
    print('# Or run manually:')
    print(f'  {PYTHON} -u {ENRICHER} --france')
    print(f'  {PYTHON} -u {ENRICHER} --slovenia')
    print(f'  {PYTHON} -u {ENRICHER} --bosnia')
    print(f'  {PYTHON} -u {ENRICHER} --all')
    print(f'  {PYTHON} -u {ENRICHER} --status')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: enrichment_skill.py {status|enrich <country>|results|schedule}')
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'status':
        run_status()
    elif cmd == 'enrich':
        country = sys.argv[2] if len(sys.argv) > 2 else 'all'
        run_enrich(country)
    elif cmd == 'results':
        run_results()
    elif cmd == 'schedule':
        show_schedule()
    else:
        print(f'Unknown command: {cmd}')
        print('Usage: enrichment_skill.py {status|enrich <country>|results|schedule}')
