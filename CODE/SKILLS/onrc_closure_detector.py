#!/usr/bin/env python3
"""
ONRC Company Closure Detector

Compares ONRC company registry exports to detect:
- New closures (status changed to RADIATA/DIZOLVATA)
- New insolvencies (status INSOLVENTA)
- Status changes that indicate layoffs

Usage:
    python onrc_closure_detector.py --download       # Download latest ONRC
    python onrc_closure_detector.py --detect         # Detect closures vs previous
    python onrc_closure_detector.py --stats          # Show closure statistics
    python onrc_closure_detector.py --export FILE    # Export closures to CSV
"""

import argparse
import csv
import gzip
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from alerting import send_telegram
    from skills_common import to_ascii
except ImportError:
    def send_telegram(msg, chat_id=None): print(f"[TG] {msg}"); return True
    def to_ascii(text): return text

DATA_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC")
CLOSURES_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CLOSURES")
CLOSURES_DIR.mkdir(parents=True, exist_ok=True)

# ONRC status codes that indicate closure/distress
CLOSURE_STATUSES = {
    'RADIATA': 'Deregistered (closed)',
    'DIZOLVATA': 'Dissolved',
    'IN LICHIDARE': 'In liquidation',
    'IN INSOLVENTA': 'In insolvency',
    'INSOLVENTA': 'Insolvency',
    'FALIMENT': 'Bankruptcy',
    'SUSPENDATA': 'Suspended',
}

# Sectors of interest (for worker sourcing)
WORKER_SECTORS = [
    '10', '11', '13', '14', '15', '16',  # Food, textiles, leather
    '22', '23', '24', '25', '26', '27', '28', '29',  # Manufacturing
    '41', '42', '43',  # Construction
    '45', '46', '47',  # Trade
    '49', '50', '51', '52', '53',  # Transport
    '55', '56',  # Hospitality
]


def get_latest_onrc_file() -> Path:
    """Find the most recent ONRC file."""
    files = sorted(DATA_DIR.glob("od_firme_*.csv"))
    if files:
        return files[-1]
    return None


def get_previous_onrc_file() -> Path:
    """Find the second-most recent ONRC file."""
    files = sorted(DATA_DIR.glob("od_firme_*.csv"))
    if len(files) >= 2:
        return files[-2]
    return None


def load_onrc_companies(filepath: Path) -> dict:
    """Load ONRC companies into dict keyed by CUI."""
    companies = {}

    if not filepath or not filepath.exists():
        print(f"File not found: {filepath}")
        return companies

    print(f"Loading {filepath.name}...")

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cui = row.get('cui', row.get('CUI', '')).strip()
            if cui:
                companies[cui] = {
                    'cui': cui,
                    'nume': row.get('denumire', row.get('DENUMIRE', '')),
                    'status': row.get('stare_firma', row.get('STARE_FIRMA', '')),
                    'caen': row.get('cod_caen', row.get('COD_CAEN', ''))[:2] if row.get('cod_caen', row.get('COD_CAEN', '')) else '',
                    'judet': row.get('judet', row.get('JUDET', '')),
                    'localitate': row.get('localitate', row.get('LOCALITATE', '')),
                }

    print(f"  Loaded {len(companies):,} companies")
    return companies


def detect_closures(old_companies: dict, new_companies: dict) -> list:
    """Detect companies that changed to closure status."""
    closures = []

    for cui, new_data in new_companies.items():
        new_status = new_data.get('status', '').upper()

        # Check if status indicates closure
        is_closure_status = any(s in new_status for s in CLOSURE_STATUSES.keys())

        if not is_closure_status:
            continue

        # Check if this is a NEW closure (wasn't closed before)
        old_data = old_companies.get(cui, {})
        old_status = old_data.get('status', '').upper()

        was_already_closed = any(s in old_status for s in CLOSURE_STATUSES.keys())

        if is_closure_status and not was_already_closed:
            closures.append({
                'cui': cui,
                'nume': new_data.get('nume', ''),
                'old_status': old_data.get('status', 'N/A'),
                'new_status': new_data.get('status', ''),
                'caen': new_data.get('caen', ''),
                'judet': new_data.get('judet', ''),
                'localitate': new_data.get('localitate', ''),
                'is_worker_sector': new_data.get('caen', '')[:2] in WORKER_SECTORS,
            })

    return closures


def summarize_closures(closures: list):
    """Print summary of closures."""
    print(f"\n{'='*60}")
    print(f"CLOSURES DETECTED: {len(closures)}")
    print(f"{'='*60}")

    if not closures:
        print("No new closures detected.")
        return

    # By status
    status_counts = Counter(c['new_status'] for c in closures)
    print("\nBy Status:")
    for status, count in status_counts.most_common(10):
        print(f"  {status}: {count}")

    # By county
    judet_counts = Counter(c['judet'] for c in closures)
    print("\nBy County (Top 10):")
    for judet, count in judet_counts.most_common(10):
        print(f"  {judet}: {count}")

    # Worker sectors
    worker_sector_closures = [c for c in closures if c['is_worker_sector']]
    print(f"\nWorker Sectors (manufacturing, construction, etc.): {len(worker_sector_closures)}")

    # Sample companies
    print("\nSample Closures (first 10):")
    for c in closures[:10]:
        sector_flag = "🏭" if c['is_worker_sector'] else ""
        print(f"  {sector_flag} {c['nume'][:40]:40} | {c['judet']:15} | {c['new_status']}")


def export_closures(closures: list, output_file: Path):
    """Export closures to CSV."""
    if not closures:
        print("No closures to export.")
        return

    fieldnames = ['cui', 'nume', 'old_status', 'new_status', 'caen', 'judet', 'localitate', 'is_worker_sector']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(closures)

    print(f"Exported {len(closures)} closures to {output_file}")


def send_closure_alert(closures: list):
    """Send Telegram alert about closures."""
    if not closures:
        return

    worker_count = sum(1 for c in closures if c['is_worker_sector'])

    message = f"""📉 *ROMANIA CLOSURE ALERT*

New closures detected: {len(closures)}
Worker sectors (mfg, construction): {worker_count}

Top counties:
"""
    judet_counts = Counter(c['judet'] for c in closures)
    for judet, count in judet_counts.most_common(5):
        message += f"  • {judet}: {count}\n"

    if worker_count > 0:
        message += f"\n🏭 {worker_count} companies in worker-heavy sectors may have laid-off employees."

    send_telegram(message)


def main():
    parser = argparse.ArgumentParser(description='ONRC Closure Detector')
    parser.add_argument('--detect', action='store_true', help='Detect closures vs previous export')
    parser.add_argument('--stats', action='store_true', help='Show closure statistics')
    parser.add_argument('--export', type=str, help='Export closures to CSV file')
    parser.add_argument('--alert', action='store_true', help='Send Telegram alert')
    parser.add_argument('--download', action='store_true', help='Download latest ONRC data')
    args = parser.parse_args()

    if args.download:
        print("Downloading latest ONRC data...")
        subprocess.run([
            '/opt/ACTIVE/INFRA/venv/bin/python3',
            '/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/DATA_GOV_RO/scrape_onrc.py'
        ])
        return

    if args.detect or args.stats or args.export:
        # Load files
        latest = get_latest_onrc_file()
        previous = get_previous_onrc_file()

        if not latest:
            print("No ONRC files found. Run --download first.")
            return

        print(f"Latest:   {latest.name}")
        print(f"Previous: {previous.name if previous else 'None'}")

        new_companies = load_onrc_companies(latest)
        old_companies = load_onrc_companies(previous) if previous else {}

        # Detect closures
        closures = detect_closures(old_companies, new_companies)

        if args.stats or args.detect:
            summarize_closures(closures)

        if args.export:
            export_closures(closures, Path(args.export))

        if args.alert and closures:
            send_closure_alert(closures)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
