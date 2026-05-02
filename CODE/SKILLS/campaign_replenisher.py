#!/usr/bin/env python3
"""
Campaign Replenisher - Auto-feed campaigns when contacts < threshold

Runs 3x daily via cron. If a campaign has < MIN_CONTACTS, pulls from data sources.

Usage:
    python3 campaign_replenisher.py           # Check and replenish all
    python3 campaign_replenisher.py --status  # Show contact counts
    python3 campaign_replenisher.py --feed POLAND  # Feed specific campaign
"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

import csv
import os
import glob
import shutil
from datetime import datetime
from pathlib import Path

try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

MIN_CONTACTS = 100
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")

# Campaign -> Data sources mapping
CAMPAIGN_SOURCES = {
    "POLAND": {
        "sources": ["/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/POLAND/OUTPUT/kraz_agencies_*.csv"],
        "contacts_file": "data/kraz_agencies_latest.csv",
        "email_field": "email",
        "company_field": "name"
    },
    "FACTORY_EU": {
        "sources": [
            "/mnt/hdd/SCRAPER_DATA/csv/SWEDEN/*.csv",
            "/opt/ACTIVE/OPENDATA/DATA/ENRICHED/*_ENRICHED.csv"
        ],
        "contacts_file": "contacts/all_contacts.csv",
        "email_field": "email",
        "company_field": "company"
    },
    "CAREWORKERS_BREVO": {
        "sources": ["/mnt/hdd/SCRAPER_DATA/csv/ANOFM/*.csv"],
        "contacts_file": "contacts/contacts.csv",
        "email_field": "email_1",
        "company_field": "company_name",
        "filter_field": "sector",
        "filter_values": ["healthcare", "care", "medical"]
    },
    "NORWAY_BREVO": {
        "sources": ["/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/OUTPUT/Norway_*.csv"],
        "contacts_file": "contacts/contacts.csv",
        "email_field": "email_1",
        "company_field": "company_name"
    }
}


def count_contacts(campaign):
    """Count total contacts in campaign."""
    config = CAMPAIGN_SOURCES.get(campaign)
    if not config:
        return -1, "Unknown campaign"
    
    contacts_file = CAMPAIGNS_DIR / campaign / config["contacts_file"]
    if not contacts_file.exists():
        return 0, "No contacts file"
    
    try:
        count = sum(1 for _ in open(contacts_file, errors="ignore")) - 1
        return max(0, count), str(contacts_file)
    except Exception as e:
        return -1, str(e)


def get_sent_emails(campaign):
    """Get set of already sent emails from logs."""
    sent = set()
    log_dir = CAMPAIGNS_DIR / campaign / "logs"
    
    if log_dir.exists():
        for log in log_dir.glob("sent_*.log"):
            try:
                for line in log.read_text(errors="ignore").splitlines():
                    if "|" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            email = parts[1].strip().lower()
                            if "@" in email:
                                sent.add(email)
            except Exception:
                pass
    
    # Also check state.json
    state_file = CAMPAIGNS_DIR / campaign / "state.json"
    if state_file.exists():
        try:
            import json
            state = json.loads(state_file.read_text())
            for email in state.get("sent", []):
                sent.add(email.lower())
        except Exception:
            pass
    
    return sent


def load_existing_contacts(campaign):
    """Load existing contacts to avoid duplicates."""
    config = CAMPAIGN_SOURCES.get(campaign)
    if not config:
        return set()
    
    existing = set()
    contacts_file = CAMPAIGNS_DIR / campaign / config["contacts_file"]
    
    if contacts_file.exists():
        try:
            with open(contacts_file, "r", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = (row.get("email") or "").lower().strip()
                    if email:
                        existing.add(email)
        except Exception:
            pass
    
    return existing


def find_new_contacts(campaign, limit=500):
    """Find new contacts from source files."""
    config = CAMPAIGN_SOURCES.get(campaign)
    if not config:
        return []
    
    sent = get_sent_emails(campaign)
    existing = load_existing_contacts(campaign)
    excluded = sent | existing
    
    email_field = config["email_field"]
    company_field = config["company_field"]
    filter_field = config.get("filter_field")
    filter_values = [v.lower() for v in config.get("filter_values", [])]
    
    new_contacts = []
    seen_emails = set()
    
    # Process each source
    for source_pattern in config["sources"]:
        files = glob.glob(source_pattern)
        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)
        
        for source_file in files[:5]:  # Limit to 5 newest files
            try:
                with open(source_file, "r", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email = (row.get(email_field) or "").lower().strip()
                        
                        if not email or "@" not in email:
                            continue
                        if email in excluded or email in seen_emails:
                            continue
                        
                        # Apply filter if configured
                        if filter_field and filter_values:
                            field_val = (row.get(filter_field) or "").lower()
                            if not any(v in field_val for v in filter_values):
                                continue
                        
                        company = row.get(company_field) or ""
                        
                        new_contacts.append({
                            "email": email,
                            "company": company,
                            "source": Path(source_file).name
                        })
                        seen_emails.add(email)
                        
                        if len(new_contacts) >= limit:
                            return new_contacts
            except Exception as e:
                print(f"  Error reading {source_file}: {e}")
    
    return new_contacts


def replenish_campaign(campaign, dry_run=False):
    """Add new contacts to campaign."""
    config = CAMPAIGN_SOURCES.get(campaign)
    if not config:
        return {"error": "Unknown campaign"}
    
    count, _ = count_contacts(campaign)
    
    new_contacts = find_new_contacts(campaign)
    
    if not new_contacts:
        return {"status": "no_new", "current": count, "added": 0}
    
    if dry_run:
        return {
            "status": "dry_run",
            "current": count,
            "would_add": len(new_contacts),
            "sample": [c["email"] for c in new_contacts[:5]]
        }
    
    # Append to contacts file
    contacts_file = CAMPAIGNS_DIR / campaign / config["contacts_file"]
    contacts_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Backup existing
    if contacts_file.exists():
        backup = contacts_file.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d')}")
        if not backup.exists():
            shutil.copy(contacts_file, backup)
    
    # Append new contacts
    file_exists = contacts_file.exists()
    with open(contacts_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "company", "source"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_contacts)
    
    return {
        "status": "ok",
        "previous": count,
        "added": len(new_contacts),
        "new_total": count + len(new_contacts)
    }


def check_and_replenish(dry_run=False):
    """Check all campaigns and replenish if needed."""
    results = []
    alerts = []
    
    for campaign in CAMPAIGN_SOURCES.keys():
        count, path = count_contacts(campaign)
        
        if count < 0:
            results.append(f"{campaign}: ERROR - {path}")
            continue
        
        if count < MIN_CONTACTS:
            result = replenish_campaign(campaign, dry_run)
            
            if result.get("status") == "ok":
                msg = f"{campaign}: {result[previous]} -> {result[new_total]} (+{result[added]})"
                alerts.append(msg)
            elif result.get("status") == "dry_run":
                msg = f"{campaign}: Would add {result[would_add]} contacts"
            elif result.get("status") == "no_new":
                msg = f"{campaign}: {count} contacts, no new sources found"
            else:
                msg = f"{campaign}: {count} contacts - {result}"
            
            results.append(msg)
        else:
            results.append(f"{campaign}: OK ({count} contacts)")
    
    print("Campaign Replenisher Status")
    print("-" * 50)
    for r in results:
        print(f"  {r}")
    
    if alerts and not dry_run:
        send_telegram("CAMPAIGN REPLENISHER\n\n" + "\n".join(alerts))
    
    return results


def get_status_json():
    """Get status as JSON for dashboard API."""
    campaigns = []
    
    for campaign in CAMPAIGN_SOURCES.keys():
        count, path = count_contacts(campaign)
        
        campaigns.append({
            "name": campaign,
            "contacts": count,
            "path": str(path) if count >= 0 else None,
            "low": count < MIN_CONTACTS and count >= 0,
            "can_replenish": count < MIN_CONTACTS and count >= 0
        })
    
    return {"campaigns": campaigns, "threshold": MIN_CONTACTS}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Campaign Replenisher")
    parser.add_argument("--status", action="store_true", help="Show status only")
    parser.add_argument("--feed", type=str, help="Feed specific campaign")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    if args.json:
        import json
        print(json.dumps(get_status_json(), indent=2))
    elif args.feed:
        result = replenish_campaign(args.feed.upper(), args.dry_run)
        import json
        print(json.dumps(result, indent=2))
    elif args.status:
        for campaign in CAMPAIGN_SOURCES.keys():
            count, path = count_contacts(campaign)
            status = "LOW" if 0 <= count < MIN_CONTACTS else "OK" if count >= 0 else "ERR"
            print(f"{campaign:20} {status:4} {count:5} contacts")
    else:
        check_and_replenish(args.dry_run)
