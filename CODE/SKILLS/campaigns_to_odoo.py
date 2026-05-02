#!/usr/bin/env python3
"""
Sync email campaigns to Odoo Mass Mailing.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/campaigns_to_odoo.py --sync      # Sync all campaigns
    python3 /opt/ACTIVE/INFRA/SKILLS/campaigns_to_odoo.py --stats     # Show stats
    python3 /opt/ACTIVE/INFRA/SKILLS/campaigns_to_odoo.py --list      # List campaigns

Author: Claude Code
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

import xmlrpc.client

# Odoo connection
ODOO_URL = os.getenv("ODOO_URL", "http://raspibig:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo_db")
ODOO_USER = os.getenv("ODOO_USER", "apaminerala@yahoo.com")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

# Campaigns directory
CAMPAIGNS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS"


class CampaignsToOdoo:
    """Sync email campaigns to Odoo."""

    def __init__(self):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USER
        self.password = ODOO_PASSWORD
        self.uid = None
        self.models = None

    def connect(self) -> bool:
        """Connect to Odoo."""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                print(f"ERROR: Auth failed")
                return False
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"Connected to Odoo: {self.url}")
            return True
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def _execute(self, model: str, method: str, *args, **kwargs):
        """Execute Odoo method."""
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, *args, **kwargs)

    def get_local_campaigns(self):
        """Get all local campaign stats."""
        campaigns = []

        # Find all state.json files
        state_files = glob.glob(f"{CAMPAIGNS_DIR}/*/state.json")

        for state_file in state_files:
            campaign_dir = os.path.dirname(state_file)
            campaign_name = os.path.basename(campaign_dir)

            # Skip templates and scripts
            if campaign_name in ['TEMPLATES', 'SCRIPTS', '__pycache__']:
                continue

            try:
                with open(state_file) as f:
                    state = json.load(f)

                # Count contacts
                contacts_file = os.path.join(campaign_dir, 'contacts', 'contacts.csv')
                contact_count = 0
                if os.path.exists(contacts_file):
                    with open(contacts_file) as f:
                        contact_count = sum(1 for _ in f) - 1  # minus header

                campaigns.append({
                    'name': campaign_name,
                    'path': campaign_dir,
                    'total_sent': state.get('total_sent', 0),
                    'sent_today': state.get('sent_today', 0),
                    'last_date': state.get('last_date', ''),
                    'contacts': contact_count,
                    'state': state
                })
            except Exception as e:
                print(f"Error reading {campaign_name}: {e}")

        return sorted(campaigns, key=lambda x: -x['total_sent'])

    def get_or_create_utm_campaign(self, name: str) -> int:
        """Get or create UTM campaign."""
        # Search existing
        ids = self._execute('utm.campaign', 'search', [[['name', '=', name]]])
        if ids:
            return ids[0]

        # Create new
        return self._execute('utm.campaign', 'create', [{'name': name}])

    def get_or_create_mailing_list(self, name: str) -> int:
        """Get or create mailing list."""
        ids = self._execute('mailing.list', 'search', [[['name', '=', name]]])
        if ids:
            return ids[0]
        return self._execute('mailing.list', 'create', [{'name': name}])

    def sync_campaign(self, campaign: dict) -> bool:
        """Sync single campaign to Odoo."""
        name = campaign['name']

        try:
            # Create UTM campaign
            utm_campaign_id = self.get_or_create_utm_campaign(f"Email: {name}")

            # Create mailing list
            list_id = self.get_or_create_mailing_list(f"Campaign: {name}")

            # Check if mailing exists
            mailing_ids = self._execute('mailing.mailing', 'search',
                [[['subject', '=', f"Campaign: {name}"]]])

            mailing_data = {
                'subject': f"Campaign: {name}",
                'campaign_id': utm_campaign_id,
                'mailing_type': 'mail',
                'state': 'done' if campaign['total_sent'] > 0 else 'draft',
                'body_html': f"""
                    <div style="padding: 20px; font-family: Arial, sans-serif;">
                        <h2>Campaign: {name}</h2>
                        <p><strong>Total Sent:</strong> {campaign['total_sent']}</p>
                        <p><strong>Sent Today:</strong> {campaign['sent_today']}</p>
                        <p><strong>Last Activity:</strong> {campaign['last_date']}</p>
                        <p><strong>Contacts:</strong> {campaign['contacts']}</p>
                        <p><strong>Path:</strong> {campaign['path']}</p>
                    </div>
                """,
            }

            if mailing_ids:
                # Update existing
                self._execute('mailing.mailing', 'write', [mailing_ids, mailing_data])
                print(f"  Updated: {name}")
            else:
                # Create new
                self._execute('mailing.mailing', 'create', [mailing_data])
                print(f"  Created: {name}")

            return True

        except Exception as e:
            print(f"  ERROR {name}: {e}")
            return False

    def sync_all(self):
        """Sync all campaigns to Odoo."""
        campaigns = self.get_local_campaigns()
        print(f"\nSyncing {len(campaigns)} campaigns to Odoo...\n")

        success = 0
        for c in campaigns:
            if self.sync_campaign(c):
                success += 1

        print(f"\nSynced: {success}/{len(campaigns)} campaigns")

    def show_stats(self):
        """Show campaign stats."""
        campaigns = self.get_local_campaigns()

        print("\n=== EMAIL CAMPAIGNS ===\n")
        print(f"{'Campaign':<25} {'Sent':>8} {'Today':>6} {'Contacts':>8} {'Last Date':<12}")
        print("-" * 70)

        total_sent = 0
        total_today = 0
        total_contacts = 0

        for c in campaigns:
            print(f"{c['name']:<25} {c['total_sent']:>8} {c['sent_today']:>6} {c['contacts']:>8} {c['last_date']:<12}")
            total_sent += c['total_sent']
            total_today += c['sent_today']
            total_contacts += c['contacts']

        print("-" * 70)
        print(f"{'TOTAL':<25} {total_sent:>8} {total_today:>6} {total_contacts:>8}")

        # Odoo stats
        print("\n=== ODOO MAILINGS ===\n")
        try:
            mailings = self._execute('mailing.mailing', 'search_count', [[]])
            utm_campaigns = self._execute('utm.campaign', 'search_count', [[]])
            lists = self._execute('mailing.list', 'search_count', [[]])
            print(f"Mailings: {mailings}")
            print(f"UTM Campaigns: {utm_campaigns}")
            print(f"Mailing Lists: {lists}")
        except Exception as e:
            print(f"Error: {e}")

    def list_campaigns(self):
        """List all campaigns."""
        campaigns = self.get_local_campaigns()

        print("\n=== CAMPAIGNS ===\n")
        for i, c in enumerate(campaigns, 1):
            status = "ACTIVE" if c['sent_today'] > 0 else "idle"
            print(f"{i:2}. {c['name']:<25} [{status}] sent={c['total_sent']}")


def main():
    parser = argparse.ArgumentParser(description='Sync campaigns to Odoo')
    parser.add_argument('--sync', action='store_true', help='Sync all campaigns')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--list', action='store_true', help='List campaigns')

    args = parser.parse_args()

    if not ODOO_PASSWORD:
        print("ERROR: ODOO_PASSWORD not set")
        sys.exit(1)

    syncer = CampaignsToOdoo()

    if not syncer.connect():
        sys.exit(1)

    if args.sync:
        syncer.sync_all()
    elif args.stats:
        syncer.show_stats()
    elif args.list:
        syncer.list_campaigns()
    else:
        syncer.show_stats()


if __name__ == "__main__":
    main()
