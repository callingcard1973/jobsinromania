#!/usr/bin/env python3
"""
Romania Faliment Skill - Automated insolvency database management.

Provides CLI interface for the LLM to run the full faliment pipeline,
enrich data, load into database, and check status.

Deploy to: /opt/SKILLS/faliment_skill.py on raspibig

Usage:
    python3 faliment_skill.py status          # Show all data status
    python3 faliment_skill.py refresh          # Download fresh ONRC + process
    python3 faliment_skill.py enrich           # Enrich with phones (local + ANAF API)
    python3 faliment_skill.py build            # Merge all sources into master
    python3 faliment_skill.py db-load          # Load into PostgreSQL
    python3 faliment_skill.py pipeline         # Run everything (refresh + enrich + build + db-load)
    python3 faliment_skill.py farms            # Extract farm subset
    python3 faliment_skill.py schedule         # Show cron setup
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# === CONFIG ===
PYTHON = '/opt/ACTIVE/INFRA/venv/bin/python3'
SCRIPT_DIR = Path('/opt/ACTIVE/OPENDATA/ROMANIA')
DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA')
LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/scrapers')
TODAY = datetime.now().strftime('%Y%m%d')

SCRIPTS = {
    'onrc': SCRIPT_DIR / 'scrape_onrc_faliment.py',
    'bpi': SCRIPT_DIR / 'scrape_bpi.py',
    'ejust': SCRIPT_DIR / 'scrape_ejust.py',
    'unpir': SCRIPT_DIR / 'scrape_unpir.py',
    'enrich': SCRIPT_DIR / 'enrich_faliment.py',
    'build': SCRIPT_DIR / 'build_faliment_master.py',
    'db': SCRIPT_DIR / 'load_faliment_db.py',
}


def run_script(name, args_list, background=False):
    """Run a script with logging."""
    script = SCRIPTS.get(name)
    if not script or not script.exists():
        print(f"ERROR: Script not found: {name} at {script}")
        return False

    cmd = [PYTHON, '-u', str(script)] + args_list
    log_file = LOG_DIR / f'faliment_{name}_{TODAY}.log'

    print(f"\n>>> Running: {' '.join(cmd)}")
    print(f"    Log: {log_file}")

    if background:
        with open(log_file, 'w') as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=lf)
            print(f"    PID: {proc.pid} (running in background)")
            return True
    else:
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode == 0


def cmd_status():
    """Show comprehensive status."""
    print("=" * 70)
    print("ROMANIA FALIMENT PIPELINE STATUS")
    print("=" * 70)

    # ONRC downloads
    print("\n--- ONRC Downloads ---")
    for name in ['od_firme.csv', 'od_stare_firma.csv', 'od_caen_autorizat.csv']:
        fp = DATA_DIR / 'ONRC' / name
        if fp.exists():
            size = fp.stat().st_size / (1024 * 1024)
            age = (datetime.now() - datetime.fromtimestamp(fp.stat().st_mtime)).days
            print(f"  {name}: {size:.0f} MB ({age} days old)")
        else:
            # Check for dated versions
            found = False
            for f in sorted((DATA_DIR / 'ONRC').glob(name.replace('.csv', '_*.csv')), reverse=True)[:1]:
                size = f.stat().st_size / (1024 * 1024)
                age = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days
                print(f"  {f.name}: {size:.0f} MB ({age} days old)")
                found = True
            if not found:
                print(f"  {name}: NOT DOWNLOADED")

    # Output files
    print("\n--- Output Files ---")
    patterns = [
        'faliment_onrc_all_*.csv', 'faliment_onrc_sectors_*.csv',
        'faliment_onrc_sectors_enriched_*.csv',
        'faliment_master_*.csv', 'faliment_ferme_master_*.csv',
    ]
    for pattern in patterns:
        for f in sorted(DATA_DIR.glob(pattern), reverse=True)[:1]:
            lines = sum(1 for _ in open(f, 'r', encoding='utf-8', errors='ignore')) - 1
            size = f.stat().st_size / (1024 * 1024)
            print(f"  {f.name}: {lines:,} rows ({size:.1f} MB)")

    # Stats file
    for f in sorted(DATA_DIR.glob('faliment_*stats*.json'), reverse=True)[:1]:
        with open(f) as fh:
            stats = json.load(fh)
        print(f"\n--- Latest Stats ({f.name}) ---")
        print(f"  Total insolvencies: {stats.get('total', stats.get('total_insolvencies', '?'))}")
        for k in ['by_status', 'by_sector', 'contact']:
            if k in stats:
                print(f"  {k}: {stats[k]}")

    # Database
    print("\n--- Database ---")
    try:
        import psycopg2
        conn = psycopg2.connect(host='localhost', dbname='opendata', user='tudor', password='scraper123')
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = 'faliment')")
        if cur.fetchone()[0]:
            cur.execute("SELECT COUNT(*) FROM faliment")
            print(f"  faliment table: {cur.fetchone()[0]:,} records")
            cur.execute("SELECT COUNT(*) FROM faliment WHERE phone IS NOT NULL AND phone != ''")
            print(f"  with phone: {cur.fetchone()[0]:,}")
            cur.execute("SELECT COUNT(*) FROM faliment WHERE is_farm = true")
            print(f"  farms: {cur.fetchone()[0]:,}")
        else:
            print("  faliment table: NOT CREATED")
        conn.close()
    except Exception as e:
        print(f"  DB: {e}")

    # Scraper progress
    print("\n--- Scraper Progress ---")
    for name in ['BPI/bpi_progress.json', 'EJUST/ejust_progress.json', 'UNPIR/unpir_progress.json']:
        fp = DATA_DIR / name
        if fp.exists():
            with open(fp) as f:
                p = json.load(f)
            print(f"  {name}: {p.get('total_results', 0)} results, last: {p.get('last_update', '?')}")


def cmd_refresh():
    """Download fresh ONRC data and extract insolvencies."""
    run_script('onrc', ['--all'])


def cmd_enrich():
    """Enrich latest sectors file with phones."""
    # Find latest sectors file
    sectors = sorted(DATA_DIR.glob('faliment_onrc_sectors_*.csv'), reverse=True)
    # Filter out enriched files
    sectors = [f for f in sectors if 'enriched' not in f.name]
    if not sectors:
        print("No sectors file found. Run 'refresh' first.")
        return
    input_file = sectors[0]
    output_file = DATA_DIR / f'faliment_onrc_sectors_enriched_{TODAY}.csv'
    run_script('enrich', [str(input_file), '-o', str(output_file)])


def cmd_build():
    """Merge all sources into master."""
    run_script('build', ['--merge'])


def cmd_db_load():
    """Load into PostgreSQL."""
    run_script('db', ['--all-csvs'])


def cmd_pipeline():
    """Run full pipeline."""
    print("=" * 70)
    print("FULL FALIMENT PIPELINE")
    print("=" * 70)

    # Step 1: Refresh ONRC
    print("\n>>> Step 1/4: Refresh ONRC data")
    cmd_refresh()

    # Step 2: Enrich with phones
    print("\n>>> Step 2/4: Enrich with phones")
    cmd_enrich()

    # Step 3: Build master
    print("\n>>> Step 3/4: Build master")
    cmd_build()

    # Step 4: Load into DB
    print("\n>>> Step 4/4: Load into database")
    cmd_db_load()

    # Final status
    print("\n>>> Pipeline complete!")
    cmd_status()


def cmd_farms():
    """Extract farm subset."""
    run_script('build', ['--farms'])


def cmd_schedule():
    """Show recommended cron schedule."""
    print("Recommended cron schedule for raspibig:")
    print()
    print("# Romania Faliment Pipeline - monthly refresh")
    print(f"0 1 1 * * {PYTHON} {SCRIPTS['onrc']} --all >> {LOG_DIR}/faliment_onrc_cron.log 2>&1")
    print(f"0 3 1 * * {PYTHON} /opt/SKILLS/faliment_skill.py enrich >> {LOG_DIR}/faliment_enrich_cron.log 2>&1")
    print(f"0 5 1 * * {PYTHON} /opt/SKILLS/faliment_skill.py build >> {LOG_DIR}/faliment_build_cron.log 2>&1")
    print(f"0 6 1 * * {PYTHON} /opt/SKILLS/faliment_skill.py db-load >> {LOG_DIR}/faliment_db_cron.log 2>&1")
    print()
    print("# BPI/eJust/UNPIR scraping - weekly")
    print(f"0 2 * * 0 {PYTHON} {SCRIPTS['bpi']} --recent 7 >> {LOG_DIR}/faliment_bpi_cron.log 2>&1")
    print(f"0 3 * * 0 {PYTHON} {SCRIPTS['ejust']} --insolventa >> {LOG_DIR}/faliment_ejust_cron.log 2>&1")
    print()
    print("To install: crontab -e")


def main():
    parser = argparse.ArgumentParser(description='Romania Faliment Skill')
    parser.add_argument('command', nargs='?', default='status',
                        choices=['status', 'refresh', 'enrich', 'build', 'db-load', 'pipeline', 'farms', 'schedule'],
                        help='Command to run')
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    commands = {
        'status': cmd_status,
        'refresh': cmd_refresh,
        'enrich': cmd_enrich,
        'build': cmd_build,
        'db-load': cmd_db_load,
        'pipeline': cmd_pipeline,
        'farms': cmd_farms,
        'schedule': cmd_schedule,
    }

    cmd_func = commands.get(args.command, cmd_status)
    cmd_func()


if __name__ == '__main__':
    main()
