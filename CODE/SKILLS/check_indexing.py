#!/usr/bin/env python3
"""
Check if worker sites are indexed by search engines

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/check_indexing.py           # Check all domains
    python3 /opt/ACTIVE/INFRA/SKILLS/check_indexing.py --alert   # Send Telegram alert with results

Location: /opt/ACTIVE/INFRA/SKILLS/check_indexing.py
Schedule: Weekly via cron
"""

import urllib.request
import urllib.parse
import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path

# Load env for Telegram
env_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key, val)

sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")
try:
    from alerting import send_telegram
except:
    def send_telegram(msg):
        print("Telegram not available")
        return False

# Worker domains
DOMAINS = [
    "factoryjobs.eu", "buildjobs.eu", "careworkers.eu", "horecaworkers.eu",
    "meatworkers.eu", "electricjobs.eu", "mechanicjobs.eu", "farmworkers.eu"
]

# State file to track progress over time
STATE_FILE = Path("/opt/WORKERS/data/indexing_state.json")


def check_google(domain):
    """Check if domain appears in Google search results"""
    try:
        query = f"site:{domain}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

            # Check for "No results" or count results
            if "did not match any documents" in html or "No results found" in html:
                return 0

            # Try to find result count
            match = re.search(r'About ([\d,]+) results', html)
            if match:
                return int(match.group(1).replace(',', ''))

            # If we see the domain in results, count as indexed
            if domain in html:
                return 1  # At least 1 page indexed

            return 0
    except Exception as e:
        return -1  # Error


def check_bing(domain):
    """Check if domain appears in Bing search results"""
    try:
        query = f"site:{domain}"
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

            if "No results found" in html or "There are no results" in html:
                return 0

            # Check for result count
            match = re.search(r'([\d,]+) results', html)
            if match:
                return int(match.group(1).replace(',', ''))

            if domain in html:
                return 1

            return 0
    except Exception as e:
        return -1


def check_yandex(domain):
    """Check if domain appears in Yandex search results"""
    try:
        query = f"site:{domain}"
        url = f"https://yandex.com/search/?text={urllib.parse.quote(query)}"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

            if "Nothing found" in html or "no results" in html.lower():
                return 0

            # Check for result count
            match = re.search(r'found ([\d,]+)', html, re.I)
            if match:
                return int(match.group(1).replace(',', ''))

            if domain in html:
                return 1

            return 0
    except Exception as e:
        return -1


def load_state():
    """Load previous indexing state"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    """Save current indexing state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def format_count(count):
    """Format count for display"""
    if count < 0:
        return "error"
    elif count == 0:
        return "not indexed"
    else:
        return f"{count} pages"


def main():
    send_alert = "--alert" in sys.argv

    print("Search Engine Indexing Check")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print("=" * 60)

    # Load previous state
    prev_state = load_state()
    current_state = {"timestamp": datetime.now().isoformat(), "domains": {}}

    results = []
    newly_indexed = []

    for domain in DOMAINS:
        print(f"\n{domain}:")

        google = check_google(domain)
        bing = check_bing(domain)
        yandex = check_yandex(domain)

        print(f"  Google: {format_count(google)}")
        print(f"  Bing:   {format_count(bing)}")
        print(f"  Yandex: {format_count(yandex)}")

        # Store results
        current_state["domains"][domain] = {
            "google": google,
            "bing": bing,
            "yandex": yandex
        }

        results.append({
            "domain": domain,
            "google": google,
            "bing": bing,
            "yandex": yandex,
            "indexed": google > 0 or bing > 0 or yandex > 0
        })

        # Check if newly indexed
        prev = prev_state.get("domains", {}).get(domain, {})
        if (google > 0 and prev.get("google", 0) <= 0) or \
           (bing > 0 and prev.get("bing", 0) <= 0) or \
           (yandex > 0 and prev.get("yandex", 0) <= 0):
            newly_indexed.append(domain)

    # Save current state
    save_state(current_state)

    # Summary
    indexed_count = sum(1 for r in results if r["indexed"])

    print("\n" + "=" * 60)
    print(f"SUMMARY: {indexed_count}/{len(DOMAINS)} domains indexed")
    print("=" * 60)

    # Send Telegram alert
    if send_alert:
        msg = "\U0001F50D <b>Weekly Indexing Report</b>\n"
        msg += f"\U0001F4C5 {datetime.now().strftime('%B %d, %Y')}\n\n"

        msg += f"<b>Indexed: {indexed_count}/{len(DOMAINS)}</b>\n\n"

        for r in results:
            status = "\u2705" if r["indexed"] else "\u274C"
            engines = []
            if r["google"] > 0:
                engines.append(f"G:{r['google']}")
            if r["bing"] > 0:
                engines.append(f"B:{r['bing']}")
            if r["yandex"] > 0:
                engines.append(f"Y:{r['yandex']}")

            engine_str = " | ".join(engines) if engines else "not indexed"
            msg += f"{status} {r['domain']}: {engine_str}\n"

        if newly_indexed:
            msg += f"\n\U0001F389 <b>Newly indexed:</b> {', '.join(newly_indexed)}"

        print("\nSending Telegram alert...")
        if send_telegram(msg):
            print("Sent!")
        else:
            print("Failed to send")

    return 0 if indexed_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
