#!/usr/bin/env python3
"""Sync bounced emails from Brevo to blacklist every 3 hours."""
import os
import csv
import requests
from pathlib import Path
from datetime import datetime

BLACKLIST_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt"
ENV_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env"

def get_api_keys():
    """Load all Brevo API keys from env file."""
    api_keys = {}
    with open(ENV_FILE) as f:
        for line in f:
            if "_API_KEY=" in line and line.startswith("BREVO_"):
                name = line.split("_API_KEY=")[0].replace("BREVO_", "")
                key = line.split("=", 1)[1].strip()
                if key and not key.startswith("#"):
                    api_keys[name] = key
    return api_keys

def get_bounced_emails():
    """Fetch all bounced emails from Brevo accounts."""
    api_keys = get_api_keys()
    bounced = set()

    for name, key in api_keys.items():
        try:
            # Hard bounces
            r = requests.get(
                "https://api.brevo.com/v3/smtp/statistics/events",
                headers={"api-key": key},
                params={"limit": 100, "event": "hardBounces"},
                timeout=10
            )
            if r.ok:
                for e in r.json().get("events", []):
                    email = e.get("email", "").lower().strip()
                    if email:
                        bounced.add(email)

            # Soft bounces (repeated = problematic)
            r = requests.get(
                "https://api.brevo.com/v3/smtp/statistics/events",
                headers={"api-key": key},
                params={"limit": 100, "event": "softBounces"},
                timeout=10
            )
            if r.ok:
                for e in r.json().get("events", []):
                    email = e.get("email", "").lower().strip()
                    if email:
                        bounced.add(email)
        except Exception as e:
            print(f"Error fetching from {name}: {e}")

    return bounced

def load_blacklist():
    """Load existing blacklist."""
    existing = set()
    if Path(BLACKLIST_FILE).exists():
        with open(BLACKLIST_FILE) as f:
            existing = set(line.strip().lower() for line in f if line.strip() and not line.startswith("#"))
    return existing

def save_blacklist(emails):
    """Save blacklist sorted."""
    with open(BLACKLIST_FILE, "w") as f:
        f.write("# Blacklist - auto-synced from Brevo\n")
        f.write(f"# Last updated: {datetime.now().isoformat()}\n")
        for email in sorted(emails):
            f.write(f"{email}\n")

def clean_campaigns(blacklist):
    """Remove blacklisted emails from campaign contacts."""
    campaigns_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    total_removed = 0

    for camp in campaigns_dir.iterdir():
        if not camp.is_dir():
            continue
        contacts_dir = camp / "contacts"
        if not contacts_dir.exists():
            continue

        for csv_file in contacts_dir.glob("*.csv"):
            try:
                rows = []
                removed = 0
                with open(csv_file, newline='', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    if not fieldnames:
                        continue
                    email_col = next((fn for fn in fieldnames if fn.lower() == 'email'), None)
                    if not email_col:
                        continue
                    for row in reader:
                        email = (row.get(email_col) or '').strip().lower()
                        if email and email not in blacklist:
                            rows.append(row)
                        else:
                            removed += 1

                if removed > 0:
                    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    total_removed += removed
            except:
                pass

    return total_removed

def main():
    print(f"[{datetime.now()}] Starting blacklist sync...")

    # Get bounced emails from Brevo
    bounced = get_bounced_emails()
    print(f"Found {len(bounced)} bounced emails from Brevo")

    # Load existing blacklist
    existing = load_blacklist()
    print(f"Existing blacklist: {len(existing)} emails")

    # Merge
    new_emails = bounced - existing
    all_emails = existing | bounced

    if new_emails:
        print(f"New bounces to add: {len(new_emails)}")
        save_blacklist(all_emails)
        print(f"Blacklist updated: {len(all_emails)} total")

        # Clean campaigns
        removed = clean_campaigns(all_emails)
        print(f"Cleaned {removed} emails from campaigns")

        # Sync to raspi
        import subprocess
        try:
            subprocess.run(["scp", BLACKLIST_FILE, "raspi:" + BLACKLIST_FILE],
                          capture_output=True, timeout=30)
            print("Synced blacklist to raspi")
        except:
            print("Warning: Could not sync to raspi")
    else:
        print("No new bounces found")

    print(f"[{datetime.now()}] Sync complete")

if __name__ == "__main__":
    main()
