#!/usr/bin/env python3
"""
EU Beneficiari Scraper Skill
Scrapes beneficiar.fonduri-ue.ro for EU fund beneficiary data.

Usage:
    python3 eu_beneficiari_scraper.py --status
    python3 eu_beneficiari_scraper.py --scrape [--anunturi|--proiecte|--both]
    python3 eu_beneficiari_scraper.py --export
    python3 eu_beneficiari_scraper.py --parallel-start
    python3 eu_beneficiari_scraper.py --parallel-status
"""

import subprocess
import sys
import argparse
from pathlib import Path

SCRAPER_DIR = Path("/opt/ACTIVE/EU_FUNDING/SCRAPER_beneficiar.fonduri-ue")
CODE_DIR = SCRAPER_DIR / "CODE"
DATA_DIR = SCRAPER_DIR / "DATA"
ASYNC_SCRAPER = CODE_DIR / "async_scraper.py"

DB_NAME = "fonduri_europene"


def run_cmd(cmd, capture=True):
    """Run a shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    return result.stdout.strip() if capture else None


def get_db_stats():
    """Get database statistics."""
    cmd = f'sudo -u postgres psql -d {DB_NAME} -t -c "SELECT COUNT(*) FROM beneficiari_privati"'
    anunturi = run_cmd(cmd).strip()
    cmd = f'sudo -u postgres psql -d {DB_NAME} -t -c "SELECT COUNT(*) FROM proiecte"'
    proiecte = run_cmd(cmd).strip()
    cmd = f'sudo -u postgres psql -d {DB_NAME} -t -c "SELECT COUNT(*) FROM beneficiari_privati WHERE email <> \'\'"'
    with_email = run_cmd(cmd).strip()
    return {'anunturi': anunturi, 'proiecte': proiecte, 'with_email': with_email}


def status():
    """Show scraper and database status."""
    print("=== EU BENEFICIARI SCRAPER STATUS ===\n")

    # Database stats
    stats = get_db_stats()
    print(f"Database: {DB_NAME}")
    print(f"  Anunturi (beneficiari_privati): {stats['anunturi']} rows")
    print(f"  Proiecte: {stats['proiecte']} rows")
    print(f"  With email: {stats['with_email']} rows")

    # Check running scrapers
    print("\nRunning scrapers:")
    result = run_cmd("pgrep -af async_scraper.py | grep -v grep || echo 'None'")
    print(f"  Local: {result}")
    result = run_cmd("ssh raspi 'pgrep -af async_scraper.py' 2>/dev/null || echo 'None'")
    print(f"  Raspi: {result}")

    # CSV files
    print(f"\nData files in {DATA_DIR}:")
    for f in DATA_DIR.glob("*.csv"):
        size = f.stat().st_size / 1024
        print(f"  {f.name}: {size:.1f} KB")


def scrape(mode='both', rate=2, start=0):
    """Run the scraper."""
    args = f"--{mode} --rate {rate}"
    if start > 0:
        args += f" --start {start}"
    cmd = f"python3 {ASYNC_SCRAPER} {args}"
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True)


def export():
    """Export data to CSV."""
    print("Exporting data to CSV...")
    run_cmd(f'sudo -u postgres psql -d {DB_NAME} -c "\\COPY beneficiari_privati TO \'/tmp/beneficiari_privati.csv\' CSV HEADER"')
    run_cmd(f'sudo -u postgres psql -d {DB_NAME} -c "\\COPY proiecte TO \'/tmp/proiecte.csv\' CSV HEADER"')
    run_cmd(f"cp /tmp/beneficiari_privati.csv {DATA_DIR}/")
    run_cmd(f"cp /tmp/proiecte.csv {DATA_DIR}/")
    print(f"Exported to {DATA_DIR}/")
    for f in ['beneficiari_privati.csv', 'proiecte.csv']:
        p = DATA_DIR / f
        if p.exists():
            print(f"  {f}: {p.stat().st_size / 1024:.1f} KB")


def parallel_start():
    """Start parallel scraping on both machines."""
    print("Starting parallel scraping...")

    # Kill existing
    run_cmd("pkill -f async_scraper.py", capture=False)
    run_cmd("ssh raspi 'pkill -f async_scraper.py' 2>/dev/null", capture=False)

    # Start on raspibig
    run_cmd(f"nohup python3 {ASYNC_SCRAPER} --anunturi --start 0 --rate 2 > {SCRAPER_DIR}/LOGS/anunturi_raspibig.log 2>&1 &")
    run_cmd(f"nohup python3 {ASYNC_SCRAPER} --proiecte --start 0 --rate 2 > {SCRAPER_DIR}/LOGS/proiecte_raspibig.log 2>&1 &")
    print("  Started anunturi + proiecte on raspibig")

    # Start on raspi
    raspi_cmd = "export DB_HOST=192.168.100.21 PGPASSWORD=tudor_eu_funds_2026 && python3 /opt/ACTIVE/EU_FUNDING/SCRAPER_beneficiar.fonduri-ue/CODE/async_scraper.py"
    run_cmd(f"ssh raspi \"nohup bash -c '{raspi_cmd} --anunturi --start 2398 --rate 2' > /opt/ACTIVE/EU_FUNDING/SCRAPER_beneficiar.fonduri-ue/LOGS/anunturi_raspi.log 2>&1 &\"")
    run_cmd(f"ssh raspi \"nohup bash -c '{raspi_cmd} --proiecte --start 796 --rate 2' > /opt/ACTIVE/EU_FUNDING/SCRAPER_beneficiar.fonduri-ue/LOGS/proiecte_raspi.log 2>&1 &\"")
    print("  Started anunturi + proiecte on raspi")

    print("\nParallel scraping started. Use --status to monitor.")


def parallel_status():
    """Check parallel scraping status."""
    print("=== PARALLEL SCRAPING STATUS ===\n")

    # Check logs
    print("Raspibig logs:")
    for log in ['anunturi_raspibig.log', 'proiecte_raspibig.log']:
        p = SCRAPER_DIR / "LOGS" / log
        if p.exists():
            last = run_cmd(f"tail -1 {p}")
            print(f"  {log}: {last}")

    print("\nRaspi logs:")
    for log in ['anunturi_raspi.log', 'proiecte_raspi.log']:
        result = run_cmd(f"ssh raspi 'tail -1 /opt/ACTIVE/EU_FUNDING/SCRAPER_beneficiar.fonduri-ue/LOGS/{log}' 2>/dev/null")
        print(f"  {log}: {result}")

    # DB stats
    stats = get_db_stats()
    print(f"\nDatabase totals:")
    print(f"  Anunturi: {stats['anunturi']}")
    print(f"  Proiecte: {stats['proiecte']}")


def main():
    parser = argparse.ArgumentParser(description='EU Beneficiari Scraper Skill')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--scrape', action='store_true', help='Run scraper')
    parser.add_argument('--anunturi', action='store_true', help='Scrape anunturi only')
    parser.add_argument('--proiecte', action='store_true', help='Scrape proiecte only')
    parser.add_argument('--both', action='store_true', help='Scrape both')
    parser.add_argument('--export', action='store_true', help='Export to CSV')
    parser.add_argument('--parallel-start', action='store_true', help='Start parallel scraping')
    parser.add_argument('--parallel-status', action='store_true', help='Check parallel status')
    parser.add_argument('--rate', type=int, default=2, help='Requests per second')
    parser.add_argument('--start', type=int, default=0, help='Start page')

    args = parser.parse_args()

    if args.status:
        status()
    elif args.scrape:
        mode = 'anunturi' if args.anunturi else 'proiecte' if args.proiecte else 'both'
        scrape(mode, args.rate, args.start)
    elif args.export:
        export()
    elif args.parallel_start:
        parallel_start()
    elif args.parallel_status:
        parallel_status()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
