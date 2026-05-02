#!/usr/bin/env python3
"""
Auto-Feed Pipeline - Automatically feed campaigns from scraper output.

Runs every 4 hours via Node-RED/cron.
Checks each campaign queue, feeds from scraper output if low.

Usage:
    python3 auto_feed_pipeline.py              # Run full pipeline
    python3 auto_feed_pipeline.py --status     # Check status only
    python3 auto_feed_pipeline.py --campaign X # Feed specific campaign
    python3 auto_feed_pipeline.py --dry-run    # Preview only
"""
import sys
import csv
import json
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram
from skills_common import to_ascii

# Campaign to Scraper mapping
# email_col can be a list to check multiple columns (uses first found)
FEED_CONFIG = {
    'FACTORY_EU': {
        'sources': [
            '/opt/ACTIVE/OPENDATA/DATA/SCRAPERS/SWEDEN/Sweden_contacts.csv',
            '/opt/ACTIVE/OPENDATA/DATA/SCRAPERS/ANOFM/employers_1plus_parallel_20251219_110847.csv',
        ],
        'min_queue': 100,
        'email_col': ['email_1', 'email', 'email1'],  # Try multiple columns
        'target_dir': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/contacts/',
    },
    'POLAND_AGENCIES': {
        'sources': [
            '/opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT/poland_kraz_unsent.csv',
        ],
        'min_queue': 50,
        'email_col': 'email',
        'target_dir': '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND_AGENCIES/contacts/',
    },
    'TOURISM_RO': {
        'sources': [
            '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/PAGINI_AURII/pagini_aurii_contacts.csv',
        ],
        'min_queue': 100,
        'email_col': 'email',
        'target_dir': '/opt/ACTIVE/EMAIL/CAMPAIGNS/TOURISM_RO/contacts/',
    },
    'CAREWORKERS': {
        'sources': [
            '/opt/ACTIVE/OPENDATA/DATA/CQC_MASTER.csv',
        ],
        'min_queue': 100,
        'email_col': ['email1', 'email', 'email_1'],
        'target_dir': '/opt/ACTIVE/EMAIL/CAMPAIGNS/CAREWORKERS/segments/',
    },
    'HORECA2026': {
        'sources': [
            '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/PAGINI_AURII/pagini_aurii_contacts.csv',
        ],
        'min_queue': 100,
        'email_col': 'email',
        'target_dir': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026/contacts/',
    },
}

# Email validation
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
BLACKLIST_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt')

def load_blacklist():
    """Load email blacklist."""
    if BLACKLIST_FILE.exists():
        return set(line.strip().lower() for line in BLACKLIST_FILE.read_text().split('\n') if line.strip())
    return set()

def load_sent_emails(campaign_dir):
    """Load already sent emails from state files."""
    sent = set()
    campaign_path = Path(campaign_dir).parent

    # Check state files
    for state_file in campaign_path.glob('*.json'):
        try:
            data = json.loads(state_file.read_text())
            if 'sent_emails' in data:
                sent.update(e.lower() for e in data['sent_emails'])
            if 'sent' in data and isinstance(data['sent'], list):
                sent.update(e.lower() for e in data['sent'])
        except:
            pass

    # Check log files
    for log_file in (campaign_path / 'logs').glob('sent_*.log'):
        try:
            for line in log_file.read_text().split('\n'):
                if '| OK |' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        email = parts[2].strip().lower()
                        if '@' in email:
                            sent.add(email)
        except:
            pass

    return sent

def validate_email(email, blacklist):
    """Validate email address."""
    if not email:
        return False
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return False
    if email in blacklist:
        return False
    # Skip common bad patterns
    if any(x in email for x in ['noreply', 'no-reply', 'donotreply', 'test@', 'example.com']):
        return False
    return True

def count_queue(target_dir):
    """Count contacts in queue."""
    target_path = Path(target_dir)
    total = 0
    for csv_file in target_path.glob('*.csv'):
        if '.bak.' in csv_file.name:
            continue
        try:
            with open(csv_file, 'r') as f:
                total += sum(1 for _ in f) - 1  # Minus header
        except:
            pass
    return total

def feed_campaign(campaign, config, dry_run=False):
    """Feed a campaign from its sources."""
    target_dir = Path(config['target_dir'])
    target_dir.mkdir(parents=True, exist_ok=True)

    # Count current queue
    current_queue = count_queue(target_dir)
    if current_queue >= config['min_queue']:
        print(f"  {campaign}: {current_queue} contacts, OK")
        return 0

    print(f"  {campaign}: {current_queue} contacts, LOW (min: {config['min_queue']})")

    # Load exclusions
    blacklist = load_blacklist()
    sent_emails = load_sent_emails(target_dir)
    existing_emails = set()

    # Load existing contacts in queue
    for csv_file in target_dir.glob('*.csv'):
        if '.bak.' in csv_file.name:
            continue
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get(config['email_col'], '').strip().lower()
                    if email:
                        existing_emails.add(email)
        except:
            pass

    # Collect new contacts from sources
    new_contacts = []
    email_cols = config['email_col']
    if isinstance(email_cols, str):
        email_cols = [email_cols]

    for source in config['sources']:
        source_path = Path(source)
        if not source_path.exists():
            print(f"    Source not found: {source}")
            continue

        try:
            with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Try multiple email columns
                    email = ''
                    for col in email_cols:
                        email = row.get(col, '').strip().lower()
                        if email and '@' in email:
                            break
                    if not validate_email(email, blacklist):
                        continue
                    if email in sent_emails or email in existing_emails:
                        continue

                    # Clean row
                    clean_row = {k: to_ascii(str(v))[:200] for k, v in row.items() if v}
                    clean_row['email'] = email
                    new_contacts.append(clean_row)
                    existing_emails.add(email)

                    # Stop if we have enough
                    if len(new_contacts) >= config['min_queue'] * 2:
                        break
        except Exception as e:
            print(f"    Error reading {source}: {e}")

        if len(new_contacts) >= config['min_queue'] * 2:
            break

    if not new_contacts:
        print(f"    No new contacts found in sources")
        return 0

    # Write new contacts
    if dry_run:
        print(f"    [DRY RUN] Would add {len(new_contacts)} contacts")
        return len(new_contacts)

    output_file = target_dir / f'auto_feed_{datetime.now():%Y%m%d_%H%M}.csv'
    fieldnames = list(new_contacts[0].keys())

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(new_contacts)

    print(f"    Added {len(new_contacts)} contacts to {output_file.name}")
    return len(new_contacts)

def run_pipeline(campaigns=None, dry_run=False):
    """Run the full pipeline."""
    print(f"\n=== AUTO-FEED PIPELINE ({datetime.now():%Y-%m-%d %H:%M}) ===\n")

    if campaigns is None:
        campaigns = FEED_CONFIG.keys()

    total_added = 0
    alerts = []

    for campaign in campaigns:
        if campaign not in FEED_CONFIG:
            print(f"  {campaign}: Unknown campaign")
            continue

        config = FEED_CONFIG[campaign]
        added = feed_campaign(campaign, config, dry_run)
        total_added += added

        if added > 0:
            alerts.append(f"{campaign}: +{added}")
        elif count_queue(config['target_dir']) < config['min_queue']:
            alerts.append(f"{campaign}: LOW, no sources")

    print(f"\n=== DONE: {total_added} contacts added ===\n")

    # Alert if issues
    if alerts and not dry_run:
        msg = f"📥 AUTO-FEED PIPELINE\n\n" + "\n".join(alerts)
        send_telegram(msg)

    return total_added

def show_status():
    """Show pipeline status."""
    print(f"\n=== AUTO-FEED STATUS ({datetime.now():%H:%M}) ===\n")
    print(f"{'Campaign':<20} {'Queue':>8} {'Min':>6} {'Status':>10}")
    print("-" * 50)

    for campaign, config in FEED_CONFIG.items():
        queue = count_queue(config['target_dir'])
        min_q = config['min_queue']
        status = 'OK' if queue >= min_q else 'LOW'

        print(f"{campaign:<20} {queue:>8} {min_q:>6} {status:>10}")

    print()

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--status', action='store_true', help='Show status only')
    p.add_argument('--campaign', '-c', help='Feed specific campaign')
    p.add_argument('--dry-run', action='store_true', help='Preview only')
    args = p.parse_args()

    if args.status:
        show_status()
    elif args.campaign:
        run_pipeline([args.campaign], args.dry_run)
    else:
        run_pipeline(dry_run=args.dry_run)
