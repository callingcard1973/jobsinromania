#!/usr/bin/env python3
"""
ANOFM Fresh Jobs Scraper
Scrapes ANOFM, compares with previous run, outputs ONLY new jobs.
Filters: 1-5 positions, corporate emails only.

Usage:
    anofm_fresh_scraper.py              # Scrape and output fresh jobs
    anofm_fresh_scraper.py --status     # Show state
    anofm_fresh_scraper.py --reset      # Reset seen job_ids
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from skills_common import to_ascii

# Paths
ANOFM_SCRAPER = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/anofm_scraper.py"
ANOFM_OUTPUT = Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM/")
FRESH_OUTPUT = Path("/opt/ACTIVE/OPENDATA/DATA/ANOFM_FRESH/")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/brevo_state/MIV_IMM_state.json")

# Free email domains to exclude
FREE_DOMAINS = {'gmail.com', 'yahoo.com', 'yahoo.ro', 'hotmail.com', 'outlook.com',
                'live.com', 'icloud.com', 'aol.com', 'mail.com', 'protonmail.com',
                'ymail.com', 'googlemail.com', 'msn.com', 'live.ro', 'yahoo.fr'}

FRESH_OUTPUT.mkdir(exist_ok=True)
STATE_FILE.parent.mkdir(exist_ok=True)


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "sent": [],
        "seen_job_ids": [],
        "last_scrape": None,
        "sent_today": 0,
        "last_send": None
    }


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def is_corporate_email(email):
    """Check if email is corporate (not free provider)."""
    if not email or '@' not in email:
        return False
    domain = email.split('@')[1].lower()
    return domain not in FREE_DOMAINS


def run_anofm_scraper():
    """Run the ANOFM scraper and return output file path."""
    print(f"Running ANOFM scraper...")
    result = subprocess.run(
        ["/opt/ACTIVE/INFRA/venv/bin/python3", ANOFM_SCRAPER],
        capture_output=True,
        text=True,
        cwd=Path(ANOFM_SCRAPER).parent
    )

    if result.returncode != 0:
        print(f"Scraper error: {result.stderr}")
        return None

    # Find latest output file
    files = sorted(ANOFM_OUTPUT.glob("anofm_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
    if files:
        print(f"Latest scrape: {files[0].name}")
        return files[0]
    return None


def extract_fresh_jobs(csv_file, state):
    """Extract new jobs that match criteria."""
    seen_ids = set(state.get("seen_job_ids", []))
    fresh_jobs = []
    new_ids = []

    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_id = row.get('job_id', '').strip()
            if not job_id:
                continue

            # Skip already seen
            if job_id in seen_ids:
                continue

            # Filter: 1-5 positions
            try:
                positions = int(row.get('positions_available', '0').strip() or '0')
            except ValueError:
                positions = 0

            if positions < 1 or positions > 5:
                continue

            # Filter: corporate email only
            email = row.get('email_1', '').strip().lower()
            if not is_corporate_email(email):
                continue

            # Passed all filters
            new_ids.append(job_id)

            # Extract contact person name
            contact_name = to_ascii(row.get('contact_person_1', ''))[:50]
            if not contact_name:
                contact_name = to_ascii(row.get('contact_person_2', ''))[:50]

            fresh_jobs.append({
                'job_id': job_id,
                'email': email,
                'company': to_ascii(row.get('company_name', ''))[:100],
                'job_title': to_ascii(row.get('job_title', ''))[:100],
                'occupation': to_ascii(row.get('occupation', ''))[:100],  # COR code
                'contact_name': contact_name,
                'contact_title': to_ascii(row.get('contact_title', ''))[:50],
                'city': to_ascii(row.get('company_city', row.get('city', ''))),
                'positions': positions,
                'phone': row.get('phone_1', ''),
                'job_url': f"https://mediere.anofm.ro/app/module/mediere/job/{job_id}",
                'scrape_time': datetime.now().isoformat()
            })

    return fresh_jobs, new_ids


def save_fresh_jobs(jobs):
    """Save fresh jobs to timestamped CSV."""
    if not jobs:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = FRESH_OUTPUT / f"fresh_{timestamp}.csv"

    fieldnames = ['job_id', 'email', 'company', 'job_title', 'occupation', 'contact_name',
                  'contact_title', 'city', 'positions', 'phone', 'job_url', 'scrape_time']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)

    return output_file


def scrape_fresh():
    """Main function: scrape, compare, output fresh."""
    print(f"\n=== ANOFM FRESH SCRAPER - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    state = load_state()

    # Run scraper
    csv_file = run_anofm_scraper()
    if not csv_file:
        print("ERROR: No scrape output")
        return

    # Extract fresh jobs
    fresh_jobs, new_ids = extract_fresh_jobs(csv_file, state)

    print(f"New jobs found: {len(fresh_jobs)}")
    print(f"  (1-5 positions, corporate email)")

    if fresh_jobs:
        # Save to CSV
        output = save_fresh_jobs(fresh_jobs)
        print(f"Output: {output}")

        # Update state with new job_ids
        state["seen_job_ids"].extend(new_ids)
        state["seen_job_ids"] = list(set(state["seen_job_ids"]))  # Dedupe
        state["last_scrape"] = datetime.now().isoformat()
        save_state(state)

        # Show sample
        print(f"\nSample fresh jobs:")
        for job in fresh_jobs[:5]:
            print(f"  {job['company'][:30]} - {job['job_title'][:30]} ({job['positions']} pos)")
    else:
        print("No new jobs matching criteria")

    return fresh_jobs


def show_status():
    """Show current state."""
    state = load_state()

    # Count fresh files
    fresh_files = list(FRESH_OUTPUT.glob("fresh_*.csv"))

    print(f"\n=== MIV_IMM FRESH SCRAPER STATUS ===")
    print(f"Seen job_ids: {len(state.get('seen_job_ids', []))}")
    print(f"Last scrape: {state.get('last_scrape', 'Never')}")
    print(f"Fresh files: {len(fresh_files)}")
    if fresh_files:
        latest = max(fresh_files, key=lambda x: x.stat().st_mtime)
        print(f"Latest: {latest.name}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', '-s', action='store_true')
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    if args.reset:
        save_state({
            "sent": [],
            "seen_job_ids": [],
            "last_scrape": None,
            "sent_today": 0,
            "last_send": None
        })
        print("State reset")
    elif args.status:
        show_status()
    else:
        scrape_fresh()


if __name__ == "__main__":
    main()
