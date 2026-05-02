#!/usr/bin/env python3
"""
Shared sender utilities for all email campaigns.
Provides: fix_email, load_blacklist, check_gmail_bounce, acquire_lock, release_lock.

Import: sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS/lib')
        from sender_utils import fix_email, load_blacklist, check_gmail_bounce, acquire_lock, release_lock
"""

import os
import csv
import imaplib
from pathlib import Path

# === Email validation ===

DOMAIN_FIXES = {
    'gmailcom': 'gmail.com', 'gmai': 'gmail.com', 'gmial.com': 'gmail.com',
    'gmal.com': 'gmail.com', 'gmail.co': 'gmail.com', 'gmail.om': 'gmail.com',
    'yahoocom': 'yahoo.com', 'yahoo.co': 'yahoo.com', 'yahooo.com': 'yahoo.com',
    'yahoo.om': 'yahoo.com', 'yahoo.cm': 'yahoo.com', 'yaho.com': 'yahoo.com',
    'yahho.com': 'yahoo.com', 'yahoo.ro.': 'yahoo.ro',
    'hotmailcom': 'hotmail.com', 'hotmal.com': 'hotmail.com',
    'outllook.com': 'outlook.com', 'outlookcom': 'outlook.com',
}


def fix_email(email):
    """Validate and auto-fix common email typos. Returns (fixed_email, is_valid)."""
    if not email:
        return email, False
    email = email.strip().lower()
    if '@' not in email:
        return email, False

    # Take only first email if multiple in one field
    if ' ' in email:
        email = email.split()[0]

    # Re-check after split — the first part may not have @
    if '@' not in email:
        return email, False

    local, domain = email.rsplit('@', 1)
    if not local:
        return email, False

    # Strip trailing dots
    domain = domain.rstrip('.')

    # Apply known domain fixes
    if domain in DOMAIN_FIXES:
        domain = DOMAIN_FIXES[domain]

    # Must have at least one dot in domain
    if '.' not in domain:
        return email, False

    # Double dots
    if '..' in domain or '..' in local:
        return email, False

    fixed = local + '@' + domain
    return fixed, True


# === Blacklist loading ===

BLACKLIST_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")
MASTER_DNC_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/MASTER_DNC.csv")
MASTER_BLACKLIST_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/master_blacklist.csv")


def load_blacklist():
    """Load unified blacklist from blacklist.txt + MASTER_DNC.csv + master_blacklist.csv."""
    emails = set()

    # Primary blacklist
    if BLACKLIST_FILE.exists():
        with open(BLACKLIST_FILE) as f:
            for line in f:
                email = line.strip().lower()
                if email and '@' in email:
                    emails.add(email)

    # Master Do Not Contact
    if MASTER_DNC_FILE.exists():
        try:
            with open(MASTER_DNC_FILE) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = (row.get('email') or '').strip().lower()
                    if email and '@' in email:
                        emails.add(email)
        except Exception:
            pass

    # Consolidated master blacklist
    if MASTER_BLACKLIST_FILE.exists():
        try:
            with open(MASTER_BLACKLIST_FILE) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = (row.get('email') or '').strip().lower()
                    if email and '@' in email:
                        emails.add(email)
        except Exception:
            pass

    return emails


def add_to_blacklist(email):
    """Append a bounced/invalid email to blacklist.txt for cross-campaign protection."""
    email = email.strip().lower()
    if not email or '@' not in email:
        return
    try:
        with open(BLACKLIST_FILE, 'a') as f:
            f.write(email + '\n')
    except Exception:
        pass


# === Gmail IMAP bounce check ===

def check_gmail_bounce(sender_email, password, sent_to_email):
    """Check Gmail IMAP for bounce-back after sending.
    Returns (bounced: bool, message: str)."""
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993, timeout=15)
        mail.login(sender_email, password)
        mail.select('INBOX')
        status, data = mail.search(None, '(FROM "mailer-daemon" UNSEEN)')
        if status != 'OK' or not data[0]:
            mail.logout()
            return False, 'no bounces'
        msg_ids = data[0].split()[-5:]
        for mid in msg_ids:
            status, msg_data = mail.fetch(mid, '(BODY[TEXT])')
            if msg_data[0] and msg_data[0][1]:
                body = msg_data[0][1].decode('utf-8', errors='replace').lower()
                if sent_to_email.lower() in body:
                    mail.logout()
                    return True, 'bounce detected for ' + sent_to_email
        mail.logout()
        return False, 'no bounce for this recipient'
    except Exception as e:
        return False, 'check error: ' + str(e)[:50]


# === Lock file ===

def acquire_lock(lock_file):
    """Acquire a PID-based lock file. Auto-cleans stale locks from dead processes."""
    lock_path = Path(lock_file)
    if lock_path.exists():
        try:
            old_pid = int(lock_path.read_text().strip())
            os.kill(old_pid, 0)
            # Process is alive - check if it's been running too long (>6 hours = probably stuck)
            import time
            lock_age = time.time() - lock_path.stat().st_mtime
            if lock_age > 6 * 3600:
                lock_path.unlink(missing_ok=True)
                # Log the cleanup
                try:
                    with open('/opt/ACTIVE/INFRA/LOGS/sender_lock_cleanup.log', 'a') as f:
                        from datetime import datetime
                        f.write(f'{datetime.now().isoformat()} Removed stuck lock {lock_file} (PID {old_pid}, age {lock_age/3600:.1f}h)\n')
                except Exception:
                    pass
            else:
                return False  # Process is alive and not stuck
        except (ProcessLookupError, ValueError):
            # PID is dead - clean up stale lock
            lock_path.unlink(missing_ok=True)
        except PermissionError:
            return False
    lock_path.write_text(str(os.getpid()))
    return True


def release_lock(lock_file):
    """Release a PID-based lock file."""
    lock_path = Path(lock_file)
    try:
        if lock_path.exists():
            pid = int(lock_path.read_text().strip())
            if pid == os.getpid():
                lock_path.unlink(missing_ok=True)
    except (ValueError, OSError):
        lock_path.unlink(missing_ok=True)


# === Warmup schedule ===

GMAIL_WARMUP_SCHEDULE = {
    3: 20,    # Days 1-3: 20/day
    7: 50,    # Days 4-7: 50/day
    14: 100,  # Days 8-14: 100/day
    999: 200, # Day 15+: 200/day
}


def get_warmup_limit(start_date, schedule=None):
    """Get current per-sender daily limit based on warmup day number.
    start_date: date object when warmup started.
    Returns (limit, day_number)."""
    from datetime import date as _date
    if schedule is None:
        schedule = GMAIL_WARMUP_SCHEDULE
    day_num = (_date.today() - start_date).days + 1
    for max_day, limit in sorted(schedule.items()):
        if day_num <= max_day:
            return limit, day_num
    return 200, day_num


# === Dynamic send delay based on sender score ===

SENDER_SCORES_FILE = '/opt/ACTIVE/EMAIL/CAMPAIGNS/sender_scores.json'


def get_dynamic_delay(sender_name, default=300):
    """Get recommended delay for a sender based on bounce rate.
    0% bounces -> 240s, 1-2% -> 300s, >2% -> 360s."""
    import json as _json
    scores_path = Path(SENDER_SCORES_FILE)
    if not scores_path.exists():
        return default
    try:
        scores = _json.loads(scores_path.read_text())
        data = scores.get(sender_name, {})
        bounce_rate = data.get('bounce_rate', 1.0)
        if bounce_rate == 0:
            return 240
        elif bounce_rate <= 2:
            return 300
        else:
            return 360
    except Exception:
        return default
