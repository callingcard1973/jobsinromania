#!/usr/bin/env python3
"""DNC Manager Agent — Atomic suppression list maintenance.

Central single-writer DNC list (dnc_list.csv).
File-lock protected reads/writes, deduplication, concurrent-safe.
"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

import os, csv, fcntl, argparse
from datetime import datetime

CAMPAIGNS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS"
DNC_FILE = f"{CAMPAIGNS_DIR}/dnc_list.csv"
DNC_LOCK = DNC_FILE + ".lock"
LOG_DIR = "/opt/ACTIVE/INFRA/LOGS/campaigns"
FIELDS = ["email", "reason", "type", "timestamp"]


def _rewrite(rows):
    """Atomically replace DNC file contents with rows (tmp + rename)."""
    tmp_file = DNC_FILE + ".tmp"
    with open(tmp_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.rename(tmp_file, DNC_FILE)


def log(msg):
    """Write to daily log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    with open(f"{LOG_DIR}/dnc_manager_{day}.log", "a") as f:
        f.write(line + "\n")


def ensure_dnc_exists():
    """Create DNC file with headers if not exists."""
    os.makedirs(os.path.dirname(DNC_FILE), exist_ok=True)
    if not os.path.exists(DNC_FILE):
        with open(DNC_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
        log(f"DNC file created: {DNC_FILE}")


def read_dnc():
    """Read DNC list, return set of emails."""
    ensure_dnc_exists()

    emails = set()
    try:
        with open(DNC_FILE) as f:
            reader = csv.DictReader(f)
            if reader:
                for row in reader:
                    if row.get("email"):
                        emails.add(row["email"].lower())
    except Exception as e:
        log(f"ERROR reading DNC: {e}")

    return emails


def write_dnc(emails_list):
    """Write DNC list atomically (with new entries)."""
    ensure_dnc_exists()

    # Read existing
    existing = {}
    try:
        with open(DNC_FILE) as f:
            reader = csv.DictReader(f)
            if reader:
                for row in reader:
                    if row.get("email"):
                        existing[row["email"].lower()] = row
    except:
        pass

    # Merge new entries
    for entry in emails_list:
        email_lower = entry.get("email", "").lower()
        if email_lower and email_lower not in existing:
            existing[email_lower] = entry

    try:
        _rewrite(existing.values())
        log(f"DNC written: {len(existing)} entries")
    except Exception as e:
        log(f"ERROR writing DNC: {e}")


def add_email(email, reason="UNKNOWN", email_type="UNKNOWN"):
    """Add single email to DNC (with lock)."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return False

    try:
        # Acquire lock
        with open(DNC_LOCK, "w") as lock_handle:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)

            # Check if exists
            existing = read_dnc()
            if email in existing:
                log(f"DNC SKIP (exists): {email}")
                fcntl.flock(lock_handle, fcntl.LOCK_UN)
                return False

            # Add
            with open(DNC_FILE, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writerow({
                    "email": email,
                    "reason": reason,
                    "type": email_type,
                    "timestamp": datetime.now().isoformat()
                })

            log(f"DNC ADD: {email} ({reason})")

            fcntl.flock(lock_handle, fcntl.LOCK_UN)
            return True

    except Exception as e:
        log(f"ERROR adding {email}: {e}")
        return False


def remove_email(email):
    """Remove email from DNC (with lock)."""
    email = email.strip().lower()

    try:
        with open(DNC_LOCK, "w") as lock_handle:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)

            # Read existing
            rows = []
            found = False
            try:
                with open(DNC_FILE) as f:
                    reader = csv.DictReader(f)
                    if reader:
                        for row in reader:
                            if row.get("email", "").lower() != email:
                                rows.append(row)
                            else:
                                found = True
            except:
                pass

            if not found:
                log(f"DNC SKIP (not found): {email}")
                fcntl.flock(lock_handle, fcntl.LOCK_UN)
                return False

            _rewrite(rows)
            log(f"DNC REMOVE: {email}")

            fcntl.flock(lock_handle, fcntl.LOCK_UN)
            return True

    except Exception as e:
        log(f"ERROR removing {email}: {e}")
        return False


def check_email(email):
    """Check if email is in DNC."""
    existing = read_dnc()
    is_suppressed = email.lower() in existing
    log(f"DNC CHECK: {email} = {'SUPPRESSED' if is_suppressed else 'OK'}")
    return is_suppressed


def dedupe_dnc():
    """Remove duplicates from DNC file."""
    try:
        with open(DNC_LOCK, "w") as lock_handle:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)

            rows = []
            seen = set()
            try:
                with open(DNC_FILE) as f:
                    reader = csv.DictReader(f)
                    if reader:
                        for row in reader:
                            email_lower = row.get("email", "").lower()
                            if email_lower and email_lower not in seen:
                                rows.append(row)
                                seen.add(email_lower)
            except:
                pass

            _rewrite(rows)
            log(f"DNC DEDUPE: {len(rows)} unique entries")

            fcntl.flock(lock_handle, fcntl.LOCK_UN)
            return len(rows)

    except Exception as e:
        log(f"ERROR deduping: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="DNC Manager")
    parser.add_argument("--add", help="Add email to DNC")
    parser.add_argument("--remove", help="Remove email from DNC")
    parser.add_argument("--check", help="Check if email is suppressed")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicates")
    parser.add_argument("--count", action="store_true", help="Show DNC count")
    parser.add_argument("--reason", default="UNKNOWN", help="Reason for suppression")
    parser.add_argument("--type", default="UNKNOWN", help="Bounce type")
    args = parser.parse_args()

    log("=== DNC MANAGER START ===")

    ensure_dnc_exists()

    if args.add:
        add_email(args.add, args.reason, args.type)
    elif args.remove:
        remove_email(args.remove)
    elif args.check:
        check_email(args.check)
    elif args.dedupe:
        dedupe_dnc()
    elif args.count:
        dnc = read_dnc()
        log(f"DNC COUNT: {len(dnc)}")
        print(len(dnc))
    else:
        # Default: show count
        dnc = read_dnc()
        log(f"DNC Manager ready ({len(dnc)} entries)")

    log("=== DNC MANAGER COMPLETE ===")


if __name__ == "__main__":
    main()
