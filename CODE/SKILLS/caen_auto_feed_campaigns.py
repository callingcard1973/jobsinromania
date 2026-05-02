#!/usr/bin/env python3
"""
Auto-Feed CAEN Leads to Campaigns

Automatically feeds high-score leads from CAEN exports to matching campaigns.
Score threshold: 40+ (configurable)

Usage:
    python3 caen_auto_feed_campaigns.py                    # Feed all sectors
    python3 caen_auto_feed_campaigns.py --sector horeca    # Feed specific sector
    python3 caen_auto_feed_campaigns.py --min-score 50     # Higher threshold
    python3 caen_auto_feed_campaigns.py --dry-run          # Preview only
    python3 caen_auto_feed_campaigns.py --status           # Show feed status
    python3 caen_auto_feed_campaigns.py --reset            # Clear feed history

Cron (daily 7 AM):
    0 7 * * * /usr/bin/python3 /opt/ACTIVE/INFRA/SKILLS/caen_auto_feed_campaigns.py >> /opt/ACTIVE/INFRA/LOGS/caen_auto_feed.log 2>&1
"""

import os
import sys
import csv
import json
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Paths
CAEN_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.caen_feed_state.json")
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")

# Sector to Campaign mapping
SECTOR_CAMPAIGN_MAP = {
    "horeca": "LUCIAN_HORECA_2026",
    "construction": "CONSTRUCT2026",
    "manufacturing": "FACTORYJOBS",
    "transport": "TRANSPORT_EU",
    "agriculture": "AGRI",
    "retail": "FACTORY_EU",
    "wholesale": "FACTORY_EU",
    "call_centers": "FACTORY_EU",
    "bpo_services_europe": "FACTORY_EU",
    "it_services": "FACTORY_EU",
    "recruitment": "AGENCIES_EUROPE",
}

# Default score threshold
MIN_SCORE = 40


def log(msg):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    """Load feed state (tracks what's been fed)."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "fed_emails": {},  # email -> {campaign, fed_at, score}
        "sector_stats": {},  # sector -> {total_fed, last_fed}
        "last_run": None
    }


def save_state(state):
    """Save feed state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_email_hash(email):
    """Generate hash for email tracking."""
    return hashlib.md5(email.lower().strip().encode()).hexdigest()[:12]


def load_campaign_contacts(campaign_name):
    """Load existing campaign contacts to avoid duplicates."""
    contacts_file = CAMPAIGNS_DIR / campaign_name / "contacts" / "contacts.csv"
    if not contacts_file.exists():
        return set()

    emails = set()
    try:
        with open(contacts_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if email:
                    emails.add(email)
    except Exception as e:
        log(f"  Warning: Could not read {contacts_file}: {e}")

    return emails


def append_to_campaign(campaign_name, leads):
    """Append leads to campaign contacts.csv."""
    contacts_dir = CAMPAIGNS_DIR / campaign_name / "contacts"
    contacts_file = contacts_dir / "contacts.csv"

    # Ensure directory exists
    contacts_dir.mkdir(parents=True, exist_ok=True)

    # Check if file exists to determine if we need headers
    file_exists = contacts_file.exists()

    # Standard columns for campaign contacts
    fieldnames = [
        'email', 'company', 'phone', 'city', 'county', 'country',
        'website', 'caen', 'caen_description', 'score', 'tags',
        'source', 'fed_at'
    ]

    with open(contacts_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for lead in leads:
            writer.writerow({
                'email': lead.get('email', ''),
                'company': lead.get('company', ''),
                'phone': lead.get('phone', ''),
                'city': lead.get('city', ''),
                'county': lead.get('county', ''),
                'country': lead.get('country', 'RO'),
                'website': lead.get('website', ''),
                'caen': lead.get('caen', ''),
                'caen_description': lead.get('caen_description', ''),
                'score': lead.get('score', ''),
                'tags': lead.get('tags', ''),
                'source': f"caen_auto_feed_{lead.get('sector', 'unknown')}",
                'fed_at': datetime.now().isoformat()
            })

    return len(leads)


def feed_sector(sector, min_score=MIN_SCORE, dry_run=False, state=None):
    """Feed high-score leads from a sector to its mapped campaign."""
    if state is None:
        state = load_state()

    # Find sector file
    sector_file = CAEN_EXPORT_DIR / f"{sector}_with_email.csv"
    if not sector_file.exists():
        log(f"  Sector file not found: {sector_file}")
        return 0, 0

    # Get target campaign
    campaign = SECTOR_CAMPAIGN_MAP.get(sector)
    if not campaign:
        log(f"  No campaign mapped for sector: {sector}")
        return 0, 0

    # Check campaign exists
    campaign_dir = CAMPAIGNS_DIR / campaign
    if not campaign_dir.exists():
        log(f"  Campaign directory not found: {campaign_dir}")
        return 0, 0

    # Load existing campaign contacts
    existing_emails = load_campaign_contacts(campaign)

    # Read sector leads
    leads_to_feed = []
    skipped_score = 0
    skipped_exists = 0
    skipped_fed = 0

    with open(sector_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('email', '').strip().lower()
            if not email:
                continue

            # Check score
            try:
                score = int(row.get('score', 0) or 0)
            except ValueError:
                score = 0

            if score < min_score:
                skipped_score += 1
                continue

            # Check if already in campaign
            if email in existing_emails:
                skipped_exists += 1
                continue

            # Check if already fed (ever)
            email_hash = get_email_hash(email)
            if email_hash in state.get('fed_emails', {}):
                skipped_fed += 1
                continue

            # Add to feed list
            row['sector'] = sector
            leads_to_feed.append(row)

    log(f"  {sector} -> {campaign}:")
    log(f"    Qualified (score>={min_score}): {len(leads_to_feed)}")
    log(f"    Skipped (low score): {skipped_score}")
    log(f"    Skipped (already in campaign): {skipped_exists}")
    log(f"    Skipped (previously fed): {skipped_fed}")

    if not leads_to_feed:
        return 0, 0

    if dry_run:
        log(f"    [DRY RUN] Would feed {len(leads_to_feed)} leads")
        return len(leads_to_feed), 0

    # Feed to campaign
    fed_count = append_to_campaign(campaign, leads_to_feed)

    # Update state
    for lead in leads_to_feed:
        email_hash = get_email_hash(lead['email'])
        state['fed_emails'][email_hash] = {
            'campaign': campaign,
            'sector': sector,
            'score': lead.get('score', 0),
            'fed_at': datetime.now().isoformat()
        }

    # Update sector stats
    if sector not in state['sector_stats']:
        state['sector_stats'][sector] = {'total_fed': 0, 'last_fed': None}
    state['sector_stats'][sector]['total_fed'] += fed_count
    state['sector_stats'][sector]['last_fed'] = datetime.now().isoformat()

    log(f"    Fed {fed_count} leads to {campaign}")

    return len(leads_to_feed), fed_count


def show_status():
    """Show auto-feed status."""
    state = load_state()

    print("\n=== CAEN Auto-Feed Status ===\n")
    print(f"Last run: {state.get('last_run', 'Never')}")
    print(f"Total emails tracked: {len(state.get('fed_emails', {}))}")

    print("\nSector Stats:")
    for sector, stats in sorted(state.get('sector_stats', {}).items()):
        campaign = SECTOR_CAMPAIGN_MAP.get(sector, 'unmapped')
        print(f"  {sector} -> {campaign}")
        print(f"    Total fed: {stats.get('total_fed', 0)}")
        print(f"    Last fed: {stats.get('last_fed', 'Never')}")

    print("\nAvailable Sectors:")
    for sector_file in sorted(CAEN_EXPORT_DIR.glob("*_with_email.csv")):
        sector = sector_file.stem.replace('_with_email', '')
        campaign = SECTOR_CAMPAIGN_MAP.get(sector, '(unmapped)')
        with open(sector_file) as f:
            rows = sum(1 for _ in f) - 1
        high_score = 0
        with open(sector_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if int(row.get('score', 0) or 0) >= MIN_SCORE:
                        high_score += 1
                except:
                    pass
        print(f"  {sector}: {rows} total, {high_score} score>={MIN_SCORE} -> {campaign}")

    print("\nCampaign Mapping:")
    for sector, campaign in sorted(SECTOR_CAMPAIGN_MAP.items()):
        exists = "OK" if (CAMPAIGNS_DIR / campaign).exists() else "MISSING"
        print(f"  {sector} -> {campaign} [{exists}]")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Auto-feed CAEN leads to campaigns")
    parser.add_argument("--sector", help="Feed specific sector only")
    parser.add_argument("--min-score", type=int, default=MIN_SCORE, help=f"Minimum score (default: {MIN_SCORE})")
    parser.add_argument("--dry-run", action="store_true", help="Preview without feeding")
    parser.add_argument("--status", action="store_true", help="Show feed status")
    parser.add_argument("--reset", action="store_true", help="Clear feed history")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("Feed history cleared.")
        return

    state = load_state()

    log("========================================")
    log("CAEN Auto-Feed Starting")
    log(f"Min score: {args.min_score}")
    log(f"Dry run: {args.dry_run}")
    log("========================================")

    total_qualified = 0
    total_fed = 0

    if args.sector:
        sectors = [args.sector]
    else:
        # All mapped sectors
        sectors = list(SECTOR_CAMPAIGN_MAP.keys())

    for sector in sectors:
        qualified, fed = feed_sector(sector, args.min_score, args.dry_run, state)
        total_qualified += qualified
        total_fed += fed

    state['last_run'] = datetime.now().isoformat()

    if not args.dry_run:
        save_state(state)

    log("========================================")
    log(f"Total qualified: {total_qualified}")
    log(f"Total fed: {total_fed}")
    log("CAEN Auto-Feed Complete")
    log("========================================")


if __name__ == "__main__":
    main()
