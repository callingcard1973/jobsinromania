#!/usr/bin/env python3
"""
Weekly Auto-Enrich Cron

Runs every Sunday to:
1. Rescan company websites for new contacts
2. Update lead scores
3. Refresh CAEN sector exports
4. Sync to Odoo

Usage:
    python3 weekly_enrich_cron.py              # Run full enrichment
    python3 weekly_enrich_cron.py --websites   # Rescan websites only
    python3 weekly_enrich_cron.py --scores     # Update scores only
    python3 weekly_enrich_cron.py --export     # Re-export sectors only
    python3 weekly_enrich_cron.py --status     # Show last run status

Cron entry (Sunday 3 AM):
0 3 * * 0 /usr/bin/python3 /opt/ACTIVE/INFRA/SKILLS/weekly_enrich_cron.py >> /opt/ACTIVE/INFRA/LOGS/weekly_enrich.log 2>&1
"""

import os
import sys
import csv
import json
import re
import time
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Paths
CAEN_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")
BPO_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/BPO_EUROPE")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.weekly_enrich_state.json")
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")

# Skills
CAEN_EXPORT_SCRIPT = "/opt/ACTIVE/INFRA/SKILLS/caen_export_sectors.py"
BPO_SCRAPER = "/opt/ACTIVE/INFRA/SKILLS/bpo_scraper_europe.py"
ODOO_SYNC = "/opt/ACTIVE/INFRA/SKILLS/sync_caen_leads_odoo.py"


def log(msg):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    """Load cron state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "last_run": None,
        "websites_scanned": 0,
        "scores_updated": 0,
        "exports_refreshed": 0,
        "errors": []
    }


def save_state(state):
    """Save cron state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def extract_contact_from_website(url):
    """Try to extract email/phone from website."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return None, None

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; ContactBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return None, None

        text = resp.text

        # Extract email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        email = None
        for e in emails:
            e = e.lower()
            if not any(x in e for x in ['example.com', 'test.com', 'noreply', 'wix.', 'google.', 'facebook.']):
                email = e
                break

        # Extract phone
        phone_pattern = r'\+?\d[\d\s\-().]{8,}\d'
        phones = re.findall(phone_pattern, text)
        phone = None
        for p in phones:
            clean = re.sub(r'[^\d+]', '', p)
            if len(clean) >= 9:
                phone = clean
                break

        return email, phone

    except Exception:
        return None, None


def rescan_websites(limit=100):
    """Rescan company websites for missing contacts."""
    log("=== Rescanning Websites ===")

    scanned = 0
    found_emails = 0
    found_phones = 0

    # Process each sector export
    for csv_file in CAEN_EXPORT_DIR.glob("*_with_email.csv"):
        if scanned >= limit:
            break

        log(f"Processing: {csv_file.name}")

        rows = []
        updated = 0

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        for row in rows:
            if scanned >= limit:
                break

            website = row.get("website", "")
            if not website:
                continue

            # Skip if already has email and phone
            if row.get("email") and row.get("phone"):
                continue

            # Add protocol if missing
            if not website.startswith("http"):
                website = "https://" + website

            scanned += 1
            email, phone = extract_contact_from_website(website)

            if email and not row.get("email"):
                row["email"] = email
                row["web_email"] = email
                found_emails += 1
                updated += 1

            if phone and not row.get("phone"):
                row["phone"] = phone
                row["web_phone"] = phone
                found_phones += 1
                updated += 1

            # Rate limit
            time.sleep(0.5)

        # Save if updated
        if updated > 0:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            log(f"  Updated {updated} rows in {csv_file.name}")

    log(f"Scanned: {scanned} websites")
    log(f"Found emails: {found_emails}")
    log(f"Found phones: {found_phones}")

    return scanned, found_emails, found_phones


def update_scores():
    """Recalculate lead scores for all exports."""
    log("=== Updating Lead Scores ===")

    total_updated = 0

    for csv_file in CAEN_EXPORT_DIR.glob("*_with_email.csv"):
        rows = []
        fieldnames = None

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            if 'score' not in fieldnames:
                fieldnames.append('score')
            if 'tags' not in fieldnames:
                fieldnames.append('tags')
            rows = list(reader)

        for row in rows:
            score = 0
            tags = []

            # Has email
            email = row.get('email', '')
            if email:
                score += 10
                domain = email.split('@')[1] if '@' in email else ''
                if domain and domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    score += 15
                    tags.append('corporate_email')

            # Has phone
            if row.get('phone'):
                score += 10
                tags.append('phone')

            # Has website
            if row.get('website'):
                score += 10
                tags.append('website')

            # Has CUI
            if row.get('cui'):
                score += 10
                tags.append('cui')

            # Major city
            city = (row.get('city') or '').lower()
            major = ['bucuresti', 'bucharest', 'cluj', 'timisoara', 'iasi', 'brasov', 'constanta']
            if any(c in city for c in major):
                score += 5
                tags.append('major_city')

            row['score'] = str(score)
            row['tags'] = ','.join(tags)
            total_updated += 1

        # Sort by score and save
        rows.sort(key=lambda x: int(x.get('score', 0)), reverse=True)

        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        log(f"  Updated scores in {csv_file.name}")

    log(f"Total rows scored: {total_updated}")
    return total_updated


def refresh_exports():
    """Re-run CAEN sector exports."""
    log("=== Refreshing CAEN Exports ===")

    try:
        result = subprocess.run(
            ["/usr/bin/python3", CAEN_EXPORT_SCRIPT, "--all", "--score"],
            capture_output=True,
            text=True,
            timeout=600
        )
        log(result.stdout[-500:] if result.stdout else "No output")
        return True
    except Exception as e:
        log(f"Error: {e}")
        return False


def refresh_bpo():
    """Re-run BPO scraper."""
    log("=== Refreshing BPO Data ===")

    try:
        result = subprocess.run(
            ["/usr/bin/python3", BPO_SCRAPER, "--all"],
            capture_output=True,
            text=True,
            timeout=300
        )
        log(result.stdout[-500:] if result.stdout else "No output")
        return True
    except Exception as e:
        log(f"Error: {e}")
        return False


def sync_odoo():
    """Sync to Odoo."""
    log("=== Syncing to Odoo ===")

    try:
        result = subprocess.run(
            ["/usr/bin/python3", ODOO_SYNC, "--all"],
            capture_output=True,
            text=True,
            timeout=600
        )
        log(result.stdout[-500:] if result.stdout else "No output")
        return True
    except Exception as e:
        log(f"Error: {e}")
        return False


def show_status():
    """Show last run status."""
    state = load_state()
    print("\n=== Weekly Enrich Status ===\n")
    print(f"Last run: {state.get('last_run', 'Never')}")
    print(f"Websites scanned: {state.get('websites_scanned', 0)}")
    print(f"Scores updated: {state.get('scores_updated', 0)}")
    print(f"Exports refreshed: {state.get('exports_refreshed', 0)}")

    if state.get('errors'):
        print("\nErrors:")
        for err in state['errors'][-5:]:
            print(f"  - {err}")

    # Show export stats
    print("\nCurrent exports:")
    total = 0
    for csv_file in sorted(CAEN_EXPORT_DIR.glob("*_with_email.csv")):
        with open(csv_file) as f:
            rows = sum(1 for _ in f) - 1
        print(f"  {csv_file.stem}: {rows}")
        total += rows
    print(f"  Total: {total}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Weekly Auto-Enrich")
    parser.add_argument("--websites", action="store_true", help="Rescan websites only")
    parser.add_argument("--scores", action="store_true", help="Update scores only")
    parser.add_argument("--export", action="store_true", help="Re-export sectors only")
    parser.add_argument("--bpo", action="store_true", help="Refresh BPO only")
    parser.add_argument("--odoo", action="store_true", help="Sync to Odoo only")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--limit", type=int, default=100, help="Website scan limit")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    state = load_state()
    state["errors"] = []

    log("========================================")
    log("Weekly Auto-Enrich Starting")
    log("========================================")

    # Run selected or all tasks
    run_all = not any([args.websites, args.scores, args.export, args.bpo, args.odoo])

    if args.websites or run_all:
        try:
            scanned, emails, phones = rescan_websites(args.limit)
            state["websites_scanned"] = scanned
        except Exception as e:
            state["errors"].append(f"websites: {e}")
            log(f"Website error: {e}")

    if args.scores or run_all:
        try:
            updated = update_scores()
            state["scores_updated"] = updated
        except Exception as e:
            state["errors"].append(f"scores: {e}")
            log(f"Score error: {e}")

    if args.export or run_all:
        try:
            if refresh_exports():
                state["exports_refreshed"] = len(list(CAEN_EXPORT_DIR.glob("*_with_email.csv")))
        except Exception as e:
            state["errors"].append(f"export: {e}")
            log(f"Export error: {e}")

    if args.bpo or run_all:
        try:
            refresh_bpo()
        except Exception as e:
            state["errors"].append(f"bpo: {e}")
            log(f"BPO error: {e}")

    if args.odoo or run_all:
        try:
            sync_odoo()
        except Exception as e:
            state["errors"].append(f"odoo: {e}")
            log(f"Odoo error: {e}")

    state["last_run"] = datetime.now().isoformat()
    save_state(state)

    log("========================================")
    log("Weekly Auto-Enrich Complete")
    log("========================================")


if __name__ == "__main__":
    main()
