#!/usr/bin/env python3
"""
Typo Email Watchdog

Automatically scans and fixes typo domains in campaign contacts.
Sends Telegram alerts when typos are found and fixed.

Usage:
    python3 typo_email_watchdog.py              # Scan and fix all campaigns
    python3 typo_email_watchdog.py --scan-only  # Scan only, don't fix
    python3 typo_email_watchdog.py --status     # Show last run status
    python3 typo_email_watchdog.py --test       # Test mode (no alerts)

Schedule: Runs daily at 5:30 AM via cron (before campaigns start)
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path

from alerting import send_telegram
from skills_common import to_ascii

# Configuration
CAMPAIGNS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS"
LOG_FILE = "/opt/ACTIVE/INFRA/LOGS/typo_watchdog.log"
STATE_FILE = "/opt/ACTIVE/INFRA/LOGS/typo_watchdog_state.json"

# Known typo domains and their corrections
TYPO_DOMAINS = {
    # Gmail typos
    "gamil.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gnail.com": "gmail.com",
    "gmail.co": "gmail.com",
    "gmail.ro": "gmail.com",
    "gmailcom": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.om": "gmail.com",
    "gamil.co": "gmail.com",
    "gmaill.com": "gmail.com",
    "gmil.com": "gmail.com",
    # Yahoo typos
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "yhoo.com": "yahoo.com",
    "yahoo.co": "yahoo.com",
    "yahoo.ro": "yahoo.com",
    "yahoocom": "yahoo.com",
    "yahoo.con": "yahoo.com",
    "yhaoo.com": "yahoo.com",
    "yaoo.com": "yahoo.com",
    # Hotmail typos
    "hotmal.com": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "hotmail.co": "hotmail.com",
    "hotmail.con": "hotmail.com",
    "hotmailcom": "hotmail.com",
    # Outlook typos
    "outlok.com": "outlook.com",
    "outloo.com": "outlook.com",
    "outlook.co": "outlook.com",
    "outlook.con": "outlook.com",
    # Other common typos
    "icloud.co": "icloud.com",
    "protonmail.co": "protonmail.com",
    "live.co": "live.com",
}


def log(message: str):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {message}"
    print(log_line)

    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(log_line + "\n")


def fix_email(email: str) -> tuple:
    """Fix typo domain in email. Returns (fixed_email, was_fixed)."""
    if not email or "@" not in email:
        return email, False

    email = email.strip().lower()
    local, domain = email.rsplit("@", 1)

    if domain in TYPO_DOMAINS:
        fixed = f"{local}@{TYPO_DOMAINS[domain]}"
        return fixed, True

    return email, False


def scan_csv(filepath: str) -> list:
    """Scan CSV for typo emails. Returns list of (row_num, column, old, new)."""
    typos = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return typos

            email_cols = [c for c in reader.fieldnames if "email" in c.lower()]
            if not email_cols:
                return typos

            for row_num, row in enumerate(reader, start=2):
                for col in email_cols:
                    old_email = row.get(col, "").strip()
                    if old_email:
                        new_email, was_fixed = fix_email(old_email)
                        if was_fixed:
                            typos.append((row_num, col, old_email, new_email))
    except Exception as e:
        log(f"Error scanning {filepath}: {e}")

    return typos


def fix_csv(filepath: str, typos: list) -> bool:
    """Fix typos in CSV file. Returns True if successful."""
    if not typos:
        return True

    try:
        # Read all rows
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # Create lookup for fixes
        fixes = {}
        for row_num, col, old, new in typos:
            fixes[(row_num - 2, col)] = (old, new)  # -2 because enumerate starts at 2

        # Apply fixes
        for idx, row in enumerate(rows):
            for col in row:
                if (idx, col) in fixes:
                    old, new = fixes[(idx, col)]
                    if row[col].strip().lower() == old.lower():
                        row[col] = new

        # Write back
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return True
    except Exception as e:
        log(f"Error fixing {filepath}: {e}")
        return False


def scan_campaigns(fix: bool = True, test: bool = False) -> dict:
    """Scan all campaign contacts for typos. Returns summary."""
    results = {
        "scanned": 0,
        "files_with_typos": 0,
        "total_typos": 0,
        "fixed": 0,
        "details": []
    }

    campaigns_path = Path(CAMPAIGNS_DIR)
    csv_files = list(campaigns_path.rglob("contacts/*.csv"))

    log(f"Scanning {len(csv_files)} contact files...")

    for csv_file in csv_files:
        results["scanned"] += 1
        typos = scan_csv(str(csv_file))

        if typos:
            results["files_with_typos"] += 1
            results["total_typos"] += len(typos)

            relative_path = str(csv_file).replace(CAMPAIGNS_DIR + "/", "")
            detail = {
                "file": relative_path,
                "typos": [(old, new) for _, _, old, new in typos]
            }
            results["details"].append(detail)

            log(f"  {relative_path}: {len(typos)} typos")
            for _, col, old, new in typos:
                log(f"    {old} -> {new}")

            if fix and not test:
                if fix_csv(str(csv_file), typos):
                    results["fixed"] += len(typos)
                    log(f"    [FIXED]")

    return results


def save_state(results: dict):
    """Save run state to JSON."""
    state = {
        "last_run": datetime.now().isoformat(),
        "scanned": results["scanned"],
        "files_with_typos": results["files_with_typos"],
        "total_typos": results["total_typos"],
        "fixed": results["fixed"]
    }

    state_path = Path(STATE_FILE)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def load_state() -> dict:
    """Load last run state."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return None


def send_alert(results: dict, test: bool = False):
    """Send Telegram alert if typos were found."""
    if results["total_typos"] == 0:
        return

    msg = f"Typo Email Watchdog\n\n"
    msg += f"Files scanned: {results['scanned']}\n"
    msg += f"Files with typos: {results['files_with_typos']}\n"
    msg += f"Total typos: {results['total_typos']}\n"
    msg += f"Fixed: {results['fixed']}\n\n"

    for detail in results["details"][:5]:  # Max 5 files in alert
        msg += f"{detail['file']}:\n"
        for old, new in detail["typos"][:3]:  # Max 3 typos per file
            msg += f"  {old} -> {new}\n"
        if len(detail["typos"]) > 3:
            msg += f"  ... and {len(detail['typos']) - 3} more\n"

    if not test:
        try:
            send_telegram(msg)
            log("Telegram alert sent")
        except Exception as e:
            log(f"Failed to send Telegram: {e}")
    else:
        log(f"[TEST] Would send alert:\n{msg}")


def show_status():
    """Show last run status."""
    state = load_state()
    if not state:
        print("No previous runs found")
        return

    print("=" * 50)
    print("TYPO EMAIL WATCHDOG STATUS")
    print("=" * 50)
    print(f"Last run: {state['last_run']}")
    print(f"Files scanned: {state['scanned']}")
    print(f"Files with typos: {state['files_with_typos']}")
    print(f"Total typos found: {state['total_typos']}")
    print(f"Typos fixed: {state['fixed']}")


def main():
    parser = argparse.ArgumentParser(description="Typo Email Watchdog")
    parser.add_argument("--scan-only", action="store_true", help="Scan only, don't fix")
    parser.add_argument("--status", action="store_true", help="Show last run status")
    parser.add_argument("--test", action="store_true", help="Test mode (no alerts)")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    log("=" * 50)
    log("TYPO EMAIL WATCHDOG")
    log("=" * 50)

    fix = not args.scan_only
    results = scan_campaigns(fix=fix, test=args.test)

    log("-" * 50)
    log(f"Summary: {results['scanned']} files, {results['total_typos']} typos, {results['fixed']} fixed")

    save_state(results)

    if results["total_typos"] > 0:
        send_alert(results, test=args.test)
    else:
        log("No typos found")


if __name__ == "__main__":
    main()
