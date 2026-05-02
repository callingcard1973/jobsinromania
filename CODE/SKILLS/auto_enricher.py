#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Auto Enricher - Runs automatically via cron/Node-RED
No Claude tokens needed - pure Python web scraping

Usage:
    python3 auto_enricher.py                    # Enrich all countries
    python3 auto_enricher.py --country DE       # Germany only
    python3 auto_enricher.py --status           # Show progress
    python3 auto_enricher.py --campaigns        # Find campaigns needing enrichment
"""

import sys
import os
import csv
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

# EURES master file (all countries combined)
EURES_MASTER = '/mnt/hdd/SCRAPER_DATA/csv/EURES/master_contacts_50.csv'

ENRICHERS = {
    'DE': {
        'name': 'Germany',
        'script': '/opt/ACTIVE/INFRA/SKILLS/germany_impressum_enricher_v2.py',
        'args': ['--batch-size', '50'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Germany/Germany_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/Germany_ENRICHED_MASTER.csv',
    },
    'NO': {
        'name': 'Norway',
        'script': '/opt/ACTIVE/INFRA/SKILLS/nordic_enricher.py',
        'args': ['--country', 'NO'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Norway/Norway_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/NO_ENRICHED.csv',
    },
    'DK': {
        'name': 'Denmark',
        'script': '/opt/ACTIVE/INFRA/SKILLS/nordic_enricher.py',
        'args': ['--country', 'DK'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Denmark/Denmark_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/DK_ENRICHED.csv',
    },
    'FI': {
        'name': 'Finland',
        'script': '/opt/ACTIVE/INFRA/SKILLS/multi_country_enricher.py',
        'args': ['--country', 'FI'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Finland/Finland_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/FI_ENRICHED.csv',
    },
    'PL': {
        'name': 'Poland',
        'script': '/opt/ACTIVE/INFRA/SKILLS/poland_enricher.py',
        'args': ['--limit', '500'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Poland/Poland_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/PL_ENRICHED.csv',
    },
    'SE': {
        'name': 'Sweden',
        'script': '/opt/ACTIVE/INFRA/SKILLS/nordic_enricher.py',
        'args': ['--country', 'SE'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Sweden/Sweden_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/SE_ENRICHED.csv',
    },
    'AT': {
        'name': 'Austria',
        'script': '/opt/ACTIVE/INFRA/SKILLS/multi_country_enricher.py',
        'args': ['--country', 'AT'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Austria/Austria_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/AT_ENRICHED.csv',
    },
    'CH': {
        'name': 'Switzerland',
        'script': '/opt/ACTIVE/INFRA/SKILLS/multi_country_enricher.py',
        'args': ['--country', 'CH'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Switzerland/Switzerland_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/CH_ENRICHED.csv',
    },
    'NL': {
        'name': 'Netherlands',
        'script': '/opt/ACTIVE/INFRA/SKILLS/multi_country_enricher.py',
        'args': ['--country', 'NL'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Netherlands/Netherlands_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/NL_ENRICHED.csv',
    },
    'BE': {
        'name': 'Belgium',
        'script': '/opt/ACTIVE/INFRA/SKILLS/multi_country_enricher.py',
        'args': ['--country', 'BE'],
        'source': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Belgium/Belgium_contacts_50.csv',
        'output': '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/BE_ENRICHED.csv',
    },
}

LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/enricher')

def get_email_coverage(csv_path):
    """Get email coverage percentage for a CSV"""
    if not os.path.exists(csv_path):
        return 0, 0, 0
    
    total = 0
    with_email = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                # Check common email column names
                for col in ['email', 'email1', 'contact_email', 'company_email']:
                    if row.get(col, '').strip() and '@' in row.get(col, ''):
                        with_email += 1
                        break
    except:
        pass
    
    pct = (with_email * 100 // total) if total > 0 else 0
    return total, with_email, pct

def show_status():
    """Show enrichment status for all countries"""
    print("=" * 60)
    print("AUTO ENRICHER STATUS")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    for code, cfg in ENRICHERS.items():
        src_total, src_email, src_pct = get_email_coverage(cfg['source'])
        out_total, out_email, out_pct = get_email_coverage(cfg['output'])
        
        print(f"\n{cfg['name']} ({code}):")
        print(f"  Source: {src_email}/{src_total} emails ({src_pct}%)")
        print(f"  Enriched: {out_total} companies")
        print(f"  Need enrichment: {src_total - out_total - src_email}")

def find_campaigns_needing_enrichment():
    """Find campaigns with low email coverage"""
    print("\n=== CAMPAIGNS NEEDING ENRICHMENT ===")
    
    campaign_dirs = [
        '/opt/ACTIVE/EMAIL/CAMPAIGNS',
        '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE',
    ]
    
    for base_dir in campaign_dirs:
        for csv_path in Path(base_dir).rglob('*.csv'):
            if 'MASTER' in csv_path.name or 'contacts' in csv_path.name:
                total, with_email, pct = get_email_coverage(str(csv_path))
                if total > 100 and pct < 50:
                    print(f"  {pct}% ({with_email}/{total}) - {csv_path}")

def run_enricher(country_code):
    """Run enricher for a specific country"""
    if country_code not in ENRICHERS:
        print(f"Unknown country: {country_code}")
        return False
    
    cfg = ENRICHERS[country_code]
    print(f"\n=== Enriching {cfg['name']} ===")
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{country_code.lower()}_{datetime.now():%Y%m%d}.log"
    
    cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', cfg['script']] + cfg['args']
    
    try:
        with open(log_file, 'a') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=3600)
        
        if result.returncode == 0:
            print(f"  {cfg['name']} enrichment complete")
            return True
        else:
            print(f"  {cfg['name']} enrichment failed (exit {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"  {cfg['name']} enrichment timed out")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def run_all():
    """Run all enrichers sequentially"""
    print("=" * 60)
    print("AUTO ENRICHER - FULL RUN")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    
    results = {}
    for code in ENRICHERS:
        results[code] = run_enricher(code)
    
    # Summary
    success = sum(1 for v in results.values() if v)
    print(f"\n=== COMPLETE: {success}/{len(results)} enrichers succeeded ===")
    
    # Send Telegram
    send_telegram(f"Auto Enricher: {success}/{len(results)} completed")

def enrich_eures_master():
    """Enrich the EURES master file with emails from web scraping."""
    print("\n=== ENRICHING EURES MASTER ===")

    if not os.path.exists(EURES_MASTER):
        print(f"  EURES master not found: {EURES_MASTER}")
        return

    total, with_email, pct = get_email_coverage(EURES_MASTER)
    print(f"  Current: {with_email}/{total} ({pct}%) have emails")

    # Group by country and run country-specific enrichers
    countries_needing_enrichment = []
    for code, cfg in ENRICHERS.items():
        if os.path.exists(cfg['source']):
            src_total, src_email, src_pct = get_email_coverage(cfg['source'])
            if src_total > 0 and src_pct < 80:
                countries_needing_enrichment.append((code, src_pct, src_total - src_email))

    # Sort by most contacts needing enrichment
    countries_needing_enrichment.sort(key=lambda x: x[2], reverse=True)

    print(f"\n  Countries needing enrichment:")
    for code, pct, missing in countries_needing_enrichment[:5]:
        print(f"    {code}: {pct}% coverage, {missing} missing emails")

    # Run top 3 enrichers
    for code, _, _ in countries_needing_enrichment[:3]:
        run_enricher(code)


def post_scrape_enrich(scraper_name: str):
    """Hook called after a scraper completes to enrich new data."""
    print(f"\n=== POST-SCRAPE ENRICHMENT: {scraper_name} ===")

    # Map scraper names to enricher codes
    scraper_to_enricher = {
        'EURES': None,  # Uses all country enrichers
        'FINLAND': 'FI',
        'NORWAY': 'NO',
        'DENMARK': 'DK',
        'SWEDEN': 'SE',
        'POLAND': 'PL',
        'ICELAND': None,  # No enricher yet
    }

    code = scraper_to_enricher.get(scraper_name.upper())

    if code:
        run_enricher(code)
    elif scraper_name.upper() == 'EURES':
        # EURES scraper finished - enrich all countries
        enrich_eures_master()
    else:
        print(f"  No enricher configured for {scraper_name}")


def main():
    parser = argparse.ArgumentParser(description='Auto Enricher')
    parser.add_argument('--country', help='Enrich specific country (DE, NO, DK, etc.)')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--campaigns', action='store_true', help='Find campaigns needing enrichment')
    parser.add_argument('--all', action='store_true', help='Run all enrichers')
    parser.add_argument('--eures', action='store_true', help='Enrich EURES master file')
    parser.add_argument('--post-scrape', help='Post-scrape hook (scraper name)')
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.campaigns:
        find_campaigns_needing_enrichment()
    elif args.country:
        run_enricher(args.country.upper())
    elif args.eures:
        enrich_eures_master()
    elif args.post_scrape:
        post_scrape_enrich(args.post_scrape)
    elif args.all:
        run_all()
    else:
        show_status()
        print("\nUse --all to run enrichment or --country XX for specific country")

if __name__ == '__main__':
    main()
