#!/usr/bin/env python3
"""
Brevo Contacts Sync
Upload contacts to Brevo and use Brevo automation for sending.

Usage:
    brevo_contacts_sync.py --campaign FACTORY_EU    # Sync campaign contacts to Brevo
    brevo_contacts_sync.py --list                   # List Brevo contact lists
    brevo_contacts_sync.py --status                 # Show sync status
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Brevo API
BREVO_API = "https://api.brevo.com/v3"

# Campaign to Brevo sender mapping
CAMPAIGN_BREVO = {
    "FACTORY_EU": {
        "api_key": os.getenv("BREVO_BUILDJOBS_API_KEY"),
        "sender_email": "office@buildjobs.eu",
        "sender_name": "BuildJobs EU",
        "list_name": "Factory EU Contacts"
    },
    "AGRI": {
        "api_key": os.getenv("BREVO_MIVROMANIA_API_KEY"),
        "sender_email": "office@mivromania.info",
        "sender_name": "MIV Romania",
        "list_name": "EU Agri Contacts"
    },
    "ANOFM": {
        "api_key": os.getenv("BREVO_INTERJOB_API_KEY"),
        "sender_email": "office@interjob.ro",
        "sender_name": "Interjob Romania",
        "list_name": "ANOFM Contacts"
    }
}

CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")


class BrevoSync:
    def __init__(self, campaign_name: str):
        if campaign_name not in CAMPAIGN_BREVO:
            raise ValueError(f"Unknown campaign: {campaign_name}")

        self.campaign = campaign_name
        self.config = CAMPAIGN_BREVO[campaign_name]
        self.api_key = self.config["api_key"]
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def get_lists(self):
        """Get all contact lists from Brevo."""
        resp = requests.get(f"{BREVO_API}/contacts/lists", headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("lists", [])
        return []

    def create_list(self, name: str, folder_id: int = 1):
        """Create a new contact list."""
        data = {"name": name, "folderId": folder_id}
        resp = requests.post(f"{BREVO_API}/contacts/lists", headers=self.headers, json=data)
        if resp.status_code == 201:
            return resp.json().get("id")
        print(f"Error creating list: {resp.text}")
        return None

    def get_or_create_list(self, name: str):
        """Get existing list or create new one."""
        lists = self.get_lists()
        for lst in lists:
            if lst["name"] == name:
                return lst["id"]
        return self.create_list(name)

    def import_contacts(self, contacts: list, list_id: int):
        """Import contacts to Brevo list."""
        # Brevo batch import
        data = {
            "listIds": [list_id],
            "updateExistingContacts": True,
            "emptyContactsAttributes": False,
            "jsonBody": contacts
        }

        resp = requests.post(f"{BREVO_API}/contacts/import", headers=self.headers, json=data)
        if resp.status_code == 202:
            return True, resp.json()
        return False, resp.text

    def load_campaign_contacts(self):
        """Load contacts from campaign CSV."""
        campaign_dir = CAMPAIGNS_DIR / self.campaign

        # Find contacts file
        contact_files = [
            campaign_dir / "contacts" / "contacts.csv",
            campaign_dir / "contacts" / "all_contacts.csv",
        ]

        contacts_file = None
        for f in contact_files:
            if f.exists():
                contacts_file = f
                break

        if not contacts_file:
            print(f"No contacts file found for {self.campaign}")
            return []

        contacts = []
        with open(contacts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if not email or '@' not in email:
                    continue

                contact = {
                    "email": email,
                    "attributes": {
                        "COMPANY": row.get('company', '')[:100],
                        "COUNTRY": row.get('country', ''),
                        "CITY": row.get('city', ''),
                        "PHONE": row.get('phone', ''),
                        "SOURCE": self.campaign
                    }
                }
                contacts.append(contact)

        return contacts

    def sync(self):
        """Sync campaign contacts to Brevo."""
        print(f"\n=== Syncing {self.campaign} to Brevo ===")
        print(f"Sender: {self.config['sender_email']}")

        # Load contacts
        contacts = self.load_campaign_contacts()
        print(f"Contacts loaded: {len(contacts)}")

        if not contacts:
            return False

        # Get or create list
        list_name = self.config["list_name"]
        list_id = self.get_or_create_list(list_name)
        print(f"Brevo list: {list_name} (ID: {list_id})")

        # Import in batches of 1000
        batch_size = 1000
        total_imported = 0

        for i in range(0, len(contacts), batch_size):
            batch = contacts[i:i+batch_size]
            success, result = self.import_contacts(batch, list_id)
            if success:
                total_imported += len(batch)
                print(f"  Batch {i//batch_size + 1}: {len(batch)} contacts imported")
            else:
                print(f"  Batch {i//batch_size + 1}: FAILED - {result}")

        print(f"\nTotal imported: {total_imported}")
        print(f"Brevo list '{list_name}' ready for automation")
        return True

    def show_status(self):
        """Show Brevo account status."""
        # Get account info
        resp = requests.get(f"{BREVO_API}/account", headers=self.headers)
        if resp.status_code == 200:
            account = resp.json()
            print(f"\nBrevo Account: {account.get('email')}")
            plan = account.get('plan', [{}])[0]
            print(f"Plan: {plan.get('type', 'Unknown')}")
            print(f"Credits: {plan.get('credits', 'N/A')}")

        # Get lists
        lists = self.get_lists()
        print(f"\nContact Lists ({len(lists)}):")
        for lst in lists:
            print(f"  - {lst['name']}: {lst.get('totalSubscribers', 0)} contacts (ID: {lst['id']})")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Sync contacts to Brevo')
    parser.add_argument('--campaign', '-c', help='Campaign to sync')
    parser.add_argument('--list', '-l', action='store_true', help='List Brevo lists')
    parser.add_argument('--status', '-s', action='store_true', help='Show status')
    parser.add_argument('--all', '-a', action='store_true', help='Sync all campaigns')
    args = parser.parse_args()

    if args.all:
        for campaign in CAMPAIGN_BREVO.keys():
            try:
                syncer = BrevoSync(campaign)
                syncer.sync()
            except Exception as e:
                print(f"Error syncing {campaign}: {e}")
        return

    if args.campaign:
        syncer = BrevoSync(args.campaign)
        if args.list:
            lists = syncer.get_lists()
            for lst in lists:
                print(f"{lst['id']}: {lst['name']} ({lst.get('totalSubscribers', 0)} contacts)")
        elif args.status:
            syncer.show_status()
        else:
            syncer.sync()
    else:
        # Default: show status for buildjobs
        syncer = BrevoSync("FACTORY_EU")
        syncer.show_status()


if __name__ == "__main__":
    main()
