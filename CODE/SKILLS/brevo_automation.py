#!/usr/bin/env python3
"""
Brevo Automation - Full campaign setup via API
Creates lists, imports contacts, creates email campaigns with daily limits.

Usage:
    brevo_automation.py --setup CONSTRUCT2026     # Full setup
    brevo_automation.py --send CONSTRUCT2026      # Send batch (290/day)
    brevo_automation.py --status                  # Show all campaigns
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from skills_common import to_ascii

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

BREVO_API = "https://api.brevo.com/v3"
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
STATE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/brevo_state")
STATE_DIR.mkdir(exist_ok=True)

# Campaign configs
CAMPAIGNS = {
    "BUILDJOBS": {
        "api_key": os.getenv("BREVO_BUILDJOBS_API_KEY"),
        "sender_email": "office@buildjobs.eu",
        "sender_name": "BuildJobs EU",
        "subject": "Construction teams available for 2026",
        "master_csv": "/opt/ACTIVE/OPENDATA/DATA/CONSTRUCTION_ALL_COMBINED.csv",
        "template_file": "/opt/ACTIVE/EMAIL/CAMPAIGNS/CONSTRUCT2026/templates/01_english.txt",
        "template_file_ro": "/opt/ACTIVE/EMAIL/CAMPAIGNS/CONSTRUCT2026/templates/brevo_buildjobs.txt",
        "subject_ro": "Echipe de constructori disponibile pentru 2026",
        "daily_limit": 290
    }
}


class BrevoAutomation:
    def __init__(self, campaign_name: str):
        if campaign_name not in CAMPAIGNS:
            raise ValueError(f"Unknown campaign: {campaign_name}")

        self.campaign = campaign_name
        self.config = CAMPAIGNS[campaign_name]
        self.api_key = self.config["api_key"]
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        self.state_file = STATE_DIR / f"{campaign_name}_state.json"
        self.state = self.load_state()

    def load_state(self):
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"sent": [], "list_id": None, "last_send": None}

    def save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def api_call(self, method, endpoint, data=None):
        url = f"{BREVO_API}/{endpoint}"
        if method == "GET":
            resp = requests.get(url, headers=self.headers)
        elif method == "POST":
            resp = requests.post(url, headers=self.headers, json=data)
        elif method == "PUT":
            resp = requests.put(url, headers=self.headers, json=data)
        return resp

    def get_or_create_list(self, name):
        # Check existing
        resp = self.api_call("GET", "contacts/lists?limit=50")
        if resp.status_code == 200:
            for lst in resp.json().get("lists", []):
                if lst["name"] == name:
                    return lst["id"]

        # Create new
        resp = self.api_call("POST", "contacts/lists", {"name": name, "folderId": 1})
        if resp.status_code == 201:
            return resp.json().get("id")
        return None

    def load_contacts(self):
        campaign_dir = CAMPAIGNS_DIR / self.config.get("campaign_dir", self.campaign) / "contacts"
        contacts_file = campaign_dir / self.config["contacts_file"]

        if not contacts_file.exists():
            print(f"File not found: {contacts_file}")
            return []

        contacts = []
        with open(contacts_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if not email or '@' not in email:
                    continue
                if email in self.state["sent"]:
                    continue

                contacts.append({
                    "email": email,
                    "company": to_ascii(row.get('company', ''))[:100],
                    "country": row.get('country', ''),
                    "city": to_ascii(row.get('city', '')),
                    "phone": row.get('phone', '')
                })
        return contacts

    def import_contacts_to_brevo(self, contacts, list_id):
        batch_size = 1000
        imported = 0

        for i in range(0, len(contacts), batch_size):
            batch = contacts[i:i+batch_size]
            brevo_contacts = [{
                "email": c["email"],
                "attributes": {
                    "COMPANY": c["company"],
                    "COUNTRY": c["country"],
                    "CITY": c["city"],
                    "PHONE": c["phone"]
                }
            } for c in batch]

            data = {
                "listIds": [list_id],
                "updateExistingContacts": True,
                "jsonBody": brevo_contacts
            }

            resp = self.api_call("POST", "contacts/import", data)
            if resp.status_code == 202:
                imported += len(batch)
                print(f"  Imported batch: {len(batch)}")

        return imported

    def load_template(self):
        campaign_dir = self.config.get("campaign_dir", self.campaign)
        template_dir = CAMPAIGNS_DIR / campaign_dir / "templates"

        # Use specific template if configured
        if self.config.get("template_file"):
            template_file = template_dir / self.config["template_file"]
        else:
            templates = list(template_dir.glob("*.txt"))
            template_file = templates[0] if templates else None

        if not template_file or not template_file.exists():
            return None, None

        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse subject from first line
        lines = content.strip().split('\n')
        subject = self.config["subject"]
        body = content

        if lines[0].startswith("Subject:"):
            subject = lines[0].replace("Subject:", "").strip()
            body = '\n'.join(lines[2:])  # Skip subject and blank line

        return subject, body

    def create_campaign(self, contacts_batch, subject, body):
        """Create and send a Brevo email campaign."""

        # Create campaign
        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">
<pre style="font-family: Arial, sans-serif; white-space: pre-wrap;">
{to_ascii(body)}
</pre>
</body>
</html>
"""

        campaign_data = {
            "name": f"{self.campaign}_{datetime.now().strftime('%Y%m%d_%H%M')}",
            "subject": to_ascii(subject),
            "sender": {
                "name": self.config["sender_name"],
                "email": self.config["sender_email"]
            },
            "type": "classic",
            "htmlContent": html_body,
            "recipients": {"listIds": [self.state["list_id"]]},
        }

        # Create campaign
        resp = self.api_call("POST", "emailCampaigns", campaign_data)
        if resp.status_code != 201:
            print(f"Failed to create campaign: {resp.text}")
            return False

        campaign_id = resp.json().get("id")
        print(f"Campaign created: {campaign_id}")

        # Send campaign immediately
        resp = self.api_call("POST", f"emailCampaigns/{campaign_id}/sendNow")
        if resp.status_code == 204:
            print(f"Campaign sent!")
            return True
        else:
            print(f"Failed to send: {resp.text}")
            return False

    def send_batch(self):
        """Send daily batch of emails."""
        print(f"\n=== {self.campaign} - Sending Batch ===")

        # Check daily limit
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("last_send") == today:
            sent_today = self.state.get("sent_today", 0)
            remaining = self.config["daily_limit"] - sent_today
            if remaining <= 0:
                print(f"Daily limit reached ({self.config['daily_limit']})")
                return
        else:
            self.state["sent_today"] = 0
            remaining = self.config["daily_limit"]

        # Load unsent contacts
        contacts = self.load_contacts()
        print(f"Unsent contacts: {len(contacts)}")

        if not contacts:
            print("No contacts to send")
            return

        # Get batch
        batch = contacts[:remaining]
        print(f"Batch size: {len(batch)}")

        # Ensure list exists
        list_name = f"{self.campaign}_Sending"
        if not self.state.get("list_id"):
            self.state["list_id"] = self.get_or_create_list(list_name)
            self.save_state()

        # Import batch to Brevo
        self.import_contacts_to_brevo(batch, self.state["list_id"])

        # Load template and create campaign
        subject, body = self.load_template()
        if not subject:
            print("No template found")
            return

        # Send via transactional API (more control)
        sent_count = 0
        for contact in batch:
            email_data = {
                "sender": {
                    "name": self.config["sender_name"],
                    "email": self.config["sender_email"]
                },
                "to": [{"email": contact["email"]}],
                "subject": to_ascii(subject),
                "htmlContent": f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px;">
<pre style="font-family: Arial, sans-serif; white-space: pre-wrap;">{to_ascii(body)}</pre>
</body>
</html>
"""
            }

            resp = self.api_call("POST", "smtp/email", email_data)
            if resp.status_code == 201:
                sent_count += 1
                self.state["sent"].append(contact["email"])
            else:
                print(f"  Failed: {contact['email']} - {resp.status_code}")

            if sent_count % 50 == 0:
                print(f"  Sent: {sent_count}/{len(batch)}")
                self.save_state()

        # Update state
        self.state["sent_today"] = self.state.get("sent_today", 0) + sent_count
        self.state["last_send"] = today
        self.save_state()

        print(f"\nSent: {sent_count}")
        print(f"Total sent: {len(self.state['sent'])}")
        print(f"Remaining: {len(contacts) - sent_count}")

    def setup(self):
        """Full setup - import all contacts to Brevo."""
        print(f"\n=== Setting up {self.campaign} ===")

        # Load all contacts
        contacts = self.load_contacts()
        print(f"Total contacts: {len(contacts)}")

        # Create list
        list_name = f"{self.campaign}_Contacts"
        list_id = self.get_or_create_list(list_name)
        print(f"Brevo list: {list_name} (ID: {list_id})")

        self.state["list_id"] = list_id
        self.save_state()

        # Import all
        imported = self.import_contacts_to_brevo(contacts, list_id)
        print(f"\nImported: {imported}")
        print(f"List ready in Brevo for automation")

    def status(self):
        """Show campaign status."""
        print(f"\n=== {self.campaign} Status ===")
        print(f"Sent: {len(self.state.get('sent', []))}")
        print(f"Last send: {self.state.get('last_send', 'Never')}")
        print(f"Today: {self.state.get('sent_today', 0)}/{self.config['daily_limit']}")

        contacts = self.load_contacts()
        print(f"Remaining: {len(contacts)}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', help='Setup campaign')
    parser.add_argument('--send', help='Send batch')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--campaign', '-c', help='Campaign name')
    args = parser.parse_args()

    if args.setup:
        auto = BrevoAutomation(args.setup)
        auto.setup()
    elif args.send:
        auto = BrevoAutomation(args.send)
        auto.send_batch()
    elif args.status:
        for name in CAMPAIGNS:
            try:
                auto = BrevoAutomation(name)
                auto.status()
            except:
                pass
    elif args.campaign:
        auto = BrevoAutomation(args.campaign)
        auto.status()


if __name__ == "__main__":
    main()
