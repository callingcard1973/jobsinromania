#!/usr/bin/env python3
"""
Campaign Deduplication Skill

Ensures contacts don't exist in multiple campaigns.
Priority order determines which campaign keeps the contact.

Usage:
    python campaign_dedup.py                    # Dedupe all campaigns
    python campaign_dedup.py --dry-run          # Preview only
    python campaign_dedup.py --report           # Show overlap report
"""

import argparse
import sqlite3
from pathlib import Path
from datetime import datetime

# Campaign priority (higher priority keeps the contact)
# Contacts are removed from lower priority campaigns
CAMPAIGN_PRIORITY = [
    'BUILDJOBS_RO',      # 1st - construction (largest)
    'FACTORYJOBS_RO',    # 2nd - factory
    'WAREHOUSE_RO',      # 3rd - warehouse
]

CAMPAIGN_DBS = {
    'BUILDJOBS_RO': Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/BUILDJOBS_RO/campaign.db'),
    'FACTORYJOBS_RO': Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORYJOBS_RO/campaign.db'),
    'WAREHOUSE_RO': Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/WAREHOUSE_RO/campaign.db'),
}


def get_campaign_emails(campaign):
    """Get all emails from a campaign."""
    db_path = CAMPAIGN_DBS.get(campaign)
    if not db_path or not db_path.exists():
        return set()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT LOWER(email) FROM contacts")
    emails = set(row[0] for row in cur.fetchall())
    conn.close()
    return emails


def remove_emails_from_campaign(campaign, emails_to_remove, dry_run=False):
    """Remove emails from a campaign's contacts table."""
    db_path = CAMPAIGN_DBS.get(campaign)
    if not db_path or not db_path.exists():
        return 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Find matching contacts
    placeholders = ','.join(['?'] * len(emails_to_remove))
    cur.execute(f"SELECT id, email FROM contacts WHERE LOWER(email) IN ({placeholders})",
                list(emails_to_remove))
    matches = cur.fetchall()

    if not dry_run and matches:
        for contact_id, email in matches:
            cur.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            # Also remove from sends if not yet sent
            cur.execute("DELETE FROM sends WHERE contact_id = ? AND status != 'sent'", (contact_id,))
        conn.commit()

    conn.close()
    return len(matches)


def dedupe_campaigns(dry_run=False, verbose=True):
    """
    Dedupe all campaigns based on priority.
    Higher priority campaigns keep contacts, lower priority campaigns have them removed.
    """
    results = {
        'checked': 0,
        'removed': {},
        'overlaps': {}
    }

    # Collect emails from higher priority campaigns
    priority_emails = set()

    for i, campaign in enumerate(CAMPAIGN_PRIORITY):
        campaign_emails = get_campaign_emails(campaign)
        results['checked'] += len(campaign_emails)

        if i == 0:
            # First campaign keeps all
            priority_emails = campaign_emails
            if verbose:
                print(f"{campaign}: {len(campaign_emails)} contacts (priority 1 - keeps all)")
            continue

        # Find overlaps with higher priority campaigns
        overlaps = campaign_emails & priority_emails
        results['overlaps'][campaign] = len(overlaps)

        if overlaps:
            if verbose:
                print(f"{campaign}: {len(campaign_emails)} contacts, {len(overlaps)} overlap with higher priority")

            # Remove overlaps
            removed = remove_emails_from_campaign(campaign, overlaps, dry_run)
            results['removed'][campaign] = removed

            if verbose:
                action = "Would remove" if dry_run else "Removed"
                print(f"  {action} {removed} duplicates")
        else:
            if verbose:
                print(f"{campaign}: {len(campaign_emails)} contacts, no overlaps")

        # Add this campaign's emails to priority set for next iteration
        priority_emails.update(campaign_emails)

    return results


def generate_report():
    """Generate overlap report without making changes."""
    print("=" * 60)
    print("CAMPAIGN OVERLAP REPORT")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Get all emails
    all_emails = {}
    for campaign in CAMPAIGN_PRIORITY:
        all_emails[campaign] = get_campaign_emails(campaign)
        print(f"{campaign}: {len(all_emails[campaign])} contacts")

    print("\n--- Pairwise Overlaps ---")
    for i, c1 in enumerate(CAMPAIGN_PRIORITY):
        for c2 in CAMPAIGN_PRIORITY[i+1:]:
            overlap = all_emails[c1] & all_emails[c2]
            if overlap:
                print(f"{c1} ∩ {c2}: {len(overlap)}")

    # Check for contacts in all campaigns
    if len(CAMPAIGN_PRIORITY) >= 3:
        all_three = all_emails[CAMPAIGN_PRIORITY[0]]
        for c in CAMPAIGN_PRIORITY[1:]:
            all_three = all_three & all_emails[c]
        if all_three:
            print(f"\nIn ALL campaigns: {len(all_three)}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Campaign Deduplication')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--report', action='store_true', help='Show overlap report')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    args = parser.parse_args()

    if args.report:
        generate_report()
        return

    print("=" * 60)
    print("CAMPAIGN DEDUPLICATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)
    print(f"\nPriority order: {' > '.join(CAMPAIGN_PRIORITY)}")
    print()

    results = dedupe_campaigns(dry_run=args.dry_run, verbose=not args.quiet)

    print("\n--- Summary ---")
    total_removed = sum(results['removed'].values())
    if args.dry_run:
        print(f"Would remove {total_removed} duplicates")
    else:
        print(f"Removed {total_removed} duplicates")

    print("=" * 60)


if __name__ == '__main__':
    main()
