#!/usr/bin/env -S python3 -u
"""
Bounce Manager Skill
Unified bounce management: search, sync, clean, report, validate

Usage:
    bounce_manager.py search [email]     - Search all sources for bounced emails
    bounce_manager.py sync               - Sync all bounce sources to unified DB
    bounce_manager.py clean              - Remove bounces from campaign segments
    bounce_manager.py report             - Generate bounce report with causes
    bounce_manager.py validate <file>    - Validate email list before campaign
    bounce_manager.py brevo-sync         - Pull blocked contacts from Brevo API
    bounce_manager.py gmail-sync         - Extract bounces from Gmail mailer-daemon messages
    bounce_manager.py gmail-clean        - Delete bounce messages from Gmail inboxes
    bounce_manager.py full-sync          - Full sync: Brevo + Gmail + Master CSV
    bounce_manager.py watch <campaign>   - Watch mode: sync every 7min while campaign active
    bounce_manager.py quick-clean        - Fast brevo-sync + clean (for mid-campaign use)
    bounce_manager.py fix-factory        - Fix active Factory campaign failures
"""

import os
import sys
import re
import csv
import json
import sqlite3
from glob import glob
from datetime import datetime
from collections import defaultdict

# Paths
DATA_DIR = "/opt/ACTIVE/OPENDATA/DATA"
BREVO_DIR = f"{DATA_DIR}/BREVO"
BOUNCES_DIR = f"{DATA_DIR}/BOUNCES"
BOUNCES_DB = f"{DATA_DIR}/bounces.db"
BOUNCES_CSV = f"{DATA_DIR}/bounces.csv"
MASTER_DNC = f"{DATA_DIR}/MASTER_DNC.csv"
BLACKLIST_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt"
CAMPAIGNS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS"

# Data sources
SOURCES = {
    "brevo_csv": f"{BREVO_DIR}/brevo_problems_*.csv",
    "bounces_db": BOUNCES_DB,
    "bounces_csv": BOUNCES_CSV,
    "problem_emails": f"{BREVO_DIR}/all_problem_emails.txt",
    "elena_bounces": f"{BOUNCES_DIR}/*.txt",
    "campaign_states": f"{CAMPAIGNS_DIR}/*/.*.json",
    "blacklist": BLACKLIST_FILE,
}

# Campaigns to clean
CAMPAIGNS = ["FACTORY", "WAREHOUSE", "CAREWORKERS"]

# Sender-side errors to IGNORE (not recipient bounces)
# These are our configuration issues, not invalid emails
SENDER_SIDE_ERRORS = [
    "UNKNOWN_SENDER",       # Brevo sender not verified
    "CONFIG_ERROR",         # Configuration issues
    "INVALID_API_KEY",      # API key issues
    "SENDER_NOT_FOUND",     # Sender not in config
    "RATE_LIMIT",           # Our rate limit, not recipient
    "QUOTA_EXCEEDED",       # Our quota, not recipient mailbox
    "AUTHENTICATION",       # Our auth failed
    "SPAM_DETECTED:bounce:Bounce rate",  # Campaign paused itself, not actual bounce
]


def is_sender_side_error(error_msg: str) -> bool:
    """Check if error is a sender-side issue (not a recipient bounce)."""
    if not error_msg:
        return False
    error_upper = error_msg.upper()
    for pattern in SENDER_SIDE_ERRORS:
        if pattern.upper() in error_upper:
            return True
    return False


def get_failure_reason_from_logs(email: str, campaign_dir: str) -> str:
    """Check campaign logs to find failure reason for an email."""
    logs_dir = os.path.join(campaign_dir, "logs")
    if not os.path.exists(logs_dir):
        return ""

    email_lower = email.lower()
    for log_file in sorted(glob(f"{logs_dir}/*.log"), reverse=True)[:5]:
        try:
            with open(log_file, "r") as f:
                for line in f:
                    if email_lower in line.lower() and "FAIL" in line:
                        # Extract the reason after the last |
                        parts = line.split("|")
                        if len(parts) >= 4:
                            return parts[-1].strip()
        except Exception:
            pass
    return ""


def init_db():
    """Initialize SQLite database."""
    os.makedirs(os.path.dirname(BOUNCES_DB), exist_ok=True)
    conn = sqlite3.connect(BOUNCES_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bounces (
            email TEXT PRIMARY KEY,
            bounce_type TEXT,
            reason TEXT,
            source TEXT,
            bounced_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def load_all_bounces():
    """Load bounces from all sources, return dict of email -> info."""
    bounces = {}

    # 1. Brevo CSV files
    for csv_file in glob(SOURCES["brevo_csv"]):
        try:
            with open(csv_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get("email", "").lower().strip()
                    if email and "@" in email:
                        bounces[email] = {
                            "type": row.get("type", "hard_bounce"),
                            "reason": row.get("reason", "")[:200],
                            "source": f"brevo_{os.path.basename(csv_file)}",
                            "date": row.get("date", ""),
                        }
        except Exception as e:
            print(f"  Warning: {csv_file}: {e}")

    # 2. Bounces CSV
    if os.path.exists(SOURCES["bounces_csv"]):
        try:
            with open(SOURCES["bounces_csv"], "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get("email", "").lower().strip()
                    if email and "@" in email and email not in bounces:
                        bounces[email] = {
                            "type": row.get("bounce_type", "hard"),
                            "reason": row.get("reason", ""),
                            "source": row.get("source", "bounces_csv"),
                            "date": row.get("bounced_at", ""),
                        }
        except Exception as e:
            print(f"  Warning: bounces.csv: {e}")

    # 3. Problem emails text file
    if os.path.exists(SOURCES["problem_emails"]):
        try:
            with open(SOURCES["problem_emails"], "r") as f:
                for line in f:
                    email = line.strip().lower()
                    if email and "@" in email and email not in bounces:
                        bounces[email] = {
                            "type": "hard_bounce",
                            "reason": "In Brevo problem list",
                            "source": "all_problem_emails.txt",
                            "date": "",
                        }
        except Exception as e:
            print(f"  Warning: all_problem_emails.txt: {e}")

    # 4. Elena bounces
    for txt_file in glob(SOURCES["elena_bounces"]):
        try:
            with open(txt_file, "r") as f:
                for line in f:
                    email = line.strip().lower()
                    if email and "@" in email and email not in bounces:
                        bounces[email] = {
                            "type": "hard_bounce",
                            "reason": "Gmail bounce notification",
                            "source": f"elena_{os.path.basename(txt_file)}",
                            "date": "",
                        }
        except Exception as e:
            print(f"  Warning: {txt_file}: {e}")

    # 5. Campaign state files (failed_emails)
    # NOTE: Check logs to exclude sender-side errors (UNKNOWN_SENDER, CONFIG_ERROR, etc.)
    for state_file in glob(SOURCES["campaign_states"]):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)

            # Get campaign directory for log lookup
            campaign_dir = os.path.dirname(state_file)

            # Failed emails dict
            for email in state.get("failed_emails", {}):
                email = email.lower().strip()
                if email and "@" in email and email not in bounces:
                    # Check logs for actual failure reason
                    reason = get_failure_reason_from_logs(email, campaign_dir)
                    if is_sender_side_error(reason):
                        continue  # Skip sender-side errors
                    bounces[email] = {
                        "type": "soft_bounce",
                        "reason": reason or "Campaign retry failure",
                        "source": os.path.basename(state_file),
                        "date": state.get("daily_sends", {}).get("date", ""),
                    }

            # Permanent failures list
            for email in state.get("permanent_failures", []):
                email = email.lower().strip()
                if email and "@" in email:
                    # Check logs for actual failure reason
                    reason = get_failure_reason_from_logs(email, campaign_dir)
                    if is_sender_side_error(reason):
                        continue  # Skip sender-side errors
                    bounces[email] = {
                        "type": "hard_bounce",
                        "reason": reason or "Permanent campaign failure",
                        "source": os.path.basename(state_file),
                        "date": "",
                    }
        except Exception as e:
            pass  # Skip invalid JSON files

    # 6. Blacklist file
    if os.path.exists(SOURCES["blacklist"]):
        try:
            with open(SOURCES["blacklist"], "r") as f:
                for line in f:
                    email = line.strip().lower()
                    if email and "@" in email and email not in bounces:
                        bounces[email] = {
                            "type": "blacklist",
                            "reason": "In DNC blacklist",
                            "source": "blacklist.txt",
                            "date": "",
                        }
        except Exception as e:
            print(f"  Warning: blacklist.txt: {e}")

    return bounces


def validate_email(email):
    """Validate email format and check against DNC."""
    email = email.lower().strip()

    # Check format
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid format"

    # Check for spaces
    if " " in email:
        return False, "Contains space"

    # Check for typo domains
    typo_domains = ["gamil.com", "gmial.com", "yahooo.com", "yaho.com", "hotmai.com"]
    domain = email.split("@")[1]
    if domain in typo_domains:
        return False, f"Typo domain: {domain}"

    # Check no-reply
    if "no-reply" in email or "noreply" in email or "do-not-reply" in email:
        return False, "No-reply address"

    # Check single-char local part
    local_part = email.split("@")[0]
    if len(local_part) <= 1:
        return False, "Invalid local part"

    return True, "OK"


def cmd_search(query=None):
    """Search all sources for bounced emails."""
    print("Loading bounces from all sources...")
    bounces = load_all_bounces()

    if query:
        query = query.lower()
        matches = {k: v for k, v in bounces.items() if query in k or query in v.get("reason", "").lower()}
        print(f"\nFound {len(matches)} matches for '{query}':")
        for email, info in sorted(matches.items())[:50]:
            print(f"  {email}")
            print(f"    Type: {info['type']}, Source: {info['source']}")
            if info['reason']:
                print(f"    Reason: {info['reason'][:80]}")
    else:
        print(f"\nTotal bounced emails: {len(bounces)}")

        # Group by type
        by_type = defaultdict(int)
        for info in bounces.values():
            by_type[info["type"]] += 1

        print("\nBy type:")
        for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c}")

        # Group by source
        by_source = defaultdict(int)
        for info in bounces.values():
            by_source[info["source"]] += 1

        print("\nBy source:")
        for s, c in sorted(by_source.items(), key=lambda x: -x[1])[:10]:
            print(f"  {s}: {c}")

    return bounces


def cmd_sync():
    """Sync all bounce sources to unified database and MASTER_DNC.csv."""
    print("Syncing all bounce sources...")
    bounces = load_all_bounces()

    # Initialize DB
    init_db()

    # Update SQLite
    conn = sqlite3.connect(BOUNCES_DB)
    now = datetime.now().isoformat()
    added = 0

    for email, info in bounces.items():
        try:
            conn.execute("""
                INSERT OR REPLACE INTO bounces (email, bounce_type, reason, source, bounced_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (email, info["type"], info["reason"], info["source"], info["date"], now))
            added += 1
        except Exception as e:
            print(f"  Error inserting {email}: {e}")

    conn.commit()
    conn.close()
    print(f"  SQLite: {added} records synced to {BOUNCES_DB}")

    # Write MASTER_DNC.csv
    os.makedirs(os.path.dirname(MASTER_DNC), exist_ok=True)
    with open(MASTER_DNC, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "type", "reason", "source", "date"])
        writer.writeheader()
        for email, info in sorted(bounces.items()):
            writer.writerow({
                "email": email,
                "type": info["type"],
                "reason": info["reason"][:200],
                "source": info["source"],
                "date": info["date"],
            })
    print(f"  CSV: {len(bounces)} records written to {MASTER_DNC}")

    # Update blacklist
    os.makedirs(os.path.dirname(BLACKLIST_FILE), exist_ok=True)
    hard_bounces = [e for e, info in bounces.items() if info["type"] in ("hard_bounce", "blacklist")]
    with open(BLACKLIST_FILE, "w") as f:
        for email in sorted(set(hard_bounces)):
            f.write(email + "\n")
    print(f"  Blacklist: {len(hard_bounces)} hard bounces written to {BLACKLIST_FILE}")

    return bounces


def cmd_clean():
    """Remove bounces from campaign segment files."""
    print("Loading bounce list...")
    bounces = load_all_bounces()
    dnc_set = set(bounces.keys())
    print(f"  {len(dnc_set)} emails in DNC list")

    total_removed = 0

    for campaign in CAMPAIGNS:
        campaign_dir = f"{CAMPAIGNS_DIR}/{campaign}"
        segments_dir = f"{campaign_dir}/segments"

        if not os.path.exists(segments_dir):
            print(f"\n{campaign}: No segments directory")
            continue

        print(f"\n{campaign}:")

        for csv_file in glob(f"{segments_dir}/*.csv"):
            try:
                # Read original
                with open(csv_file, "r") as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    rows = list(reader)

                original_count = len(rows)

                # Filter out bounces
                clean_rows = []
                removed = []
                for row in rows:
                    email = row.get("email", "").lower().strip()
                    if email in dnc_set:
                        removed.append(email)
                    else:
                        # Also validate format
                        valid, reason = validate_email(email)
                        if valid:
                            clean_rows.append(row)
                        else:
                            removed.append(f"{email} ({reason})")

                if removed:
                    # Backup original
                    backup_file = f"{csv_file}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(csv_file, backup_file)

                    # Write cleaned
                    with open(csv_file, "w", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(clean_rows)

                    print(f"  {os.path.basename(csv_file)}: {original_count} -> {len(clean_rows)} (-{len(removed)})")
                    total_removed += len(removed)
                else:
                    print(f"  {os.path.basename(csv_file)}: {original_count} (clean)")

            except Exception as e:
                print(f"  Error processing {csv_file}: {e}")

    print(f"\nTotal removed: {total_removed}")
    return total_removed


def cmd_report():
    """Generate bounce report with causes."""
    print("=" * 60)
    print("BOUNCE REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    bounces = load_all_bounces()

    # Summary
    print(f"\nTotal bounced emails: {len(bounces)}")

    # By type
    by_type = defaultdict(int)
    for info in bounces.values():
        by_type[info["type"]] += 1

    print("\n[BY TYPE]")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        pct = c / len(bounces) * 100
        print(f"  {t:20} {c:5} ({pct:.1f}%)")

    # By source
    by_source = defaultdict(int)
    for info in bounces.values():
        by_source[info["source"]] += 1

    print("\n[BY SOURCE]")
    for s, c in sorted(by_source.items(), key=lambda x: -x[1])[:10]:
        print(f"  {s:40} {c:5}")

    # By domain
    by_domain = defaultdict(int)
    for email in bounces.keys():
        domain = email.split("@")[1] if "@" in email else "unknown"
        by_domain[domain] += 1

    print("\n[TOP BOUNCING DOMAINS]")
    for d, c in sorted(by_domain.items(), key=lambda x: -x[1])[:15]:
        print(f"  {d:30} {c:5}")

    # Common reasons
    reasons = defaultdict(int)
    for info in bounces.values():
        reason = info.get("reason", "")[:50]
        if reason:
            reasons[reason] += 1

    print("\n[TOP BOUNCE REASONS]")
    for r, c in sorted(reasons.items(), key=lambda x: -x[1])[:10]:
        print(f"  {r:50} {c:5}")

    # Data quality issues
    print("\n[DATA QUALITY ISSUES]")
    typos = [e for e in bounces.keys() if any(t in e for t in ["gamil", "gmial", "yahooo", "hotmai"])]
    noreply = [e for e in bounces.keys() if "no-reply" in e or "noreply" in e]
    invalid = [e for e in bounces.keys() if not validate_email(e)[0]]

    print(f"  Typo domains: {len(typos)}")
    print(f"  No-reply addresses: {len(noreply)}")
    print(f"  Invalid format: {len(invalid)}")

    return bounces


def cmd_validate(filepath):
    """Validate email list before campaign."""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"Validating: {filepath}")

    # Load DNC
    bounces = load_all_bounces()
    dnc_set = set(bounces.keys())

    # Read file
    valid_emails = []
    invalid_emails = []
    dnc_emails = []

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("email", "").lower().strip()
            if not email:
                continue

            # Check DNC
            if email in dnc_set:
                dnc_emails.append((email, f"In DNC: {bounces[email]['reason'][:30]}"))
                continue

            # Validate format
            valid, reason = validate_email(email)
            if valid:
                valid_emails.append(email)
            else:
                invalid_emails.append((email, reason))

    # Report
    total = len(valid_emails) + len(invalid_emails) + len(dnc_emails)
    print(f"\nResults:")
    print(f"  Total: {total}")
    print(f"  Valid: {len(valid_emails)} ({len(valid_emails)/total*100:.1f}%)")
    print(f"  Invalid format: {len(invalid_emails)}")
    print(f"  In DNC list: {len(dnc_emails)}")

    if invalid_emails:
        print(f"\n[INVALID FORMAT - First 20]")
        for email, reason in invalid_emails[:20]:
            print(f"  {email}: {reason}")

    if dnc_emails:
        print(f"\n[IN DNC LIST - First 20]")
        for email, reason in dnc_emails[:20]:
            print(f"  {email}: {reason}")

    return valid_emails, invalid_emails, dnc_emails


def cmd_brevo_sync():
    """Sync blocked contacts from all Brevo accounts to blacklist."""
    import subprocess

    # Brevo API keys from /opt/ACTIVE/EMAIL/CAMPAIGNS/.env
    BREVO_APIS = [
        ("mivromania", "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"),
        ("buildjobs", "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"),
        ("interjob", "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"),
        ("expatsinromania", "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"),
    ]

    def get_all_blocked(name, key):
        """Fetch all blocked contacts with pagination (limit 100 per request)."""
        all_contacts = []
        offset = 0
        while True:
            cmd = f'curl -s "https://api.brevo.com/v3/smtp/blockedContacts?limit=100&offset={offset}" -H "api-key:{key}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            try:
                data = json.loads(result.stdout)
                contacts = data.get("contacts", [])
                if not contacts:
                    break
                all_contacts.extend(contacts)
                if len(contacts) < 100:
                    break
                offset += 100
            except:
                break
        return all_contacts

    print("Syncing Brevo blocked contacts...")
    all_blocked = {}
    reasons = {}

    for name, key in BREVO_APIS:
        contacts = get_all_blocked(name, key)
        print(f"  {name}: {len(contacts)} blocked")

        for c in contacts:
            email = c.get("email", "").lower().strip()
            code = c.get("reason", {}).get("code", "unknown")
            all_blocked[email] = {"account": name, "reason": code}
            reasons[code] = reasons.get(code, 0) + 1

    print(f"\nTotal unique from Brevo: {len(all_blocked)}")
    print("\nBy reason:")
    for code, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {code}: {cnt}")

    # Load existing blacklist
    try:
        with open(BLACKLIST_FILE, "r") as f:
            existing = set(line.strip().lower() for line in f if line.strip())
    except FileNotFoundError:
        existing = set()

    # Find new emails
    new = set(all_blocked.keys()) - existing
    print(f"\nExisting blacklist: {len(existing)}")
    print(f"New to add: {len(new)}")

    if new:
        os.makedirs(os.path.dirname(BLACKLIST_FILE), exist_ok=True)
        with open(BLACKLIST_FILE, "a") as f:
            for email in sorted(new):
                f.write(email + "\n")
        print(f"\nADDED {len(new)} emails to {BLACKLIST_FILE}")

        # Show sample
        print("\nSample new emails:")
        for email in list(new)[:10]:
            info = all_blocked[email]
            print(f"  {email[:40]:40} | {info['reason']}")

    return all_blocked


def cmd_gmail_sync():
    """Extract bounced emails from Gmail mailer-daemon messages."""
    import imaplib
    import email
    from email.header import decode_header
    from datetime import timedelta

    GMAIL_ACCOUNTS = [
        ("elena.manpower.dristor@gmail.com", "wmfnpikkcierkmrq"),
        ("manpowerdristor@gmail.com", "dmrsuqiudvqtrpzu"),
        ("expatsinromania@gmail.com", "hxdn mukn jloe shkk"),
        ("pamintstrabun@gmail.com", "irqw ozlp dzdu bidj"),
        ("casafaurbucuresti@gmail.com", "zlfb mbqf xiki mcbw"),
        ("fructexportromania@gmail.com", "wqkp hejw nooo ztpv"),
        ("manpowersearchromania@gmail.com", "ypyz guab vsaa rpld"),
    ]

    print("Extracting bounces from Gmail...")
    all_bounced = {}
    today = datetime.now().strftime("%Y-%m-%d")

    for email_addr, password in GMAIL_ACCOUNTS:
        print(f"\n  {email_addr}:")
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_addr, password)
            mail.select("INBOX")

            since_date = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
            _, msg_ids = mail.search(None, f'(FROM "mailer-daemon" SINCE {since_date})')

            bounces = msg_ids[0].split()
            print(f"    Found {len(bounces)} bounce messages")

            for msg_id in bounces:
                try:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])

                    # Get body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                except:
                                    pass
                                break
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                        except:
                            pass

                    # Extract failed email address
                    patterns = [
                        r"Your message to ([^\s<>]+@[^\s<>]+) has been blocked",
                        r"delivery to ([^\s<>]+@[^\s<>]+) failed",
                        r"couldn't be delivered to ([^\s<>]+@[^\s<>]+)",
                        r"The email account that you tried to reach \(([^\)]+)\)",
                        r"550[- ].*?<([^>]+@[^>]+)>",
                        r"Final-Recipient:.*?([^\s<>;]+@[^\s<>;]+)",
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, body, re.IGNORECASE)
                        for match in matches:
                            clean_email = match.strip().lower()
                            if "@" in clean_email and "mailer-daemon" not in clean_email:
                                # Determine reason
                                if "Message blocked" in body or "spam" in body.lower():
                                    reason = "spam_blocked"
                                elif "does not exist" in body or "user unknown" in body.lower():
                                    reason = "user_not_found"
                                elif "mailbox full" in body.lower():
                                    reason = "mailbox_full"
                                else:
                                    reason = "rejected"

                                all_bounced[clean_email] = {
                                    "type": "hard_bounce" if reason != "mailbox_full" else "soft_bounce",
                                    "reason": reason,
                                    "source": f"gmail_{email_addr.split('@')[0]}",
                                    "date": today,
                                }
                except:
                    pass

            mail.logout()
        except Exception as e:
            print(f"    Error: {e}")

    print(f"\n  Total unique bounced: {len(all_bounced)}")

    # Add to blacklist
    if all_bounced:
        try:
            with open(BLACKLIST_FILE, "r") as f:
                existing = set(line.strip().lower() for line in f if line.strip())
        except:
            existing = set()

        new_emails = set(all_bounced.keys()) - existing
        if new_emails:
            with open(BLACKLIST_FILE, "a") as f:
                for email_item in sorted(new_emails):
                    f.write(email_item + "\n")
            print(f"  Added {len(new_emails)} new emails to blacklist")

    return all_bounced


def cmd_gmail_clean():
    """Delete bounce messages from Gmail inboxes."""
    import imaplib
    from datetime import timedelta

    GMAIL_ACCOUNTS = [
        ("elena.manpower.dristor@gmail.com", "wmfnpikkcierkmrq"),
        ("manpowerdristor@gmail.com", "dmrsuqiudvqtrpzu"),
        ("expatsinromania@gmail.com", "hxdn mukn jloe shkk"),
        ("pamintstrabun@gmail.com", "irqw ozlp dzdu bidj"),
        ("casafaurbucuresti@gmail.com", "zlfb mbqf xiki mcbw"),
        ("fructexportromania@gmail.com", "wqkp hejw nooo ztpv"),
        ("manpowersearchromania@gmail.com", "ypyz guab vsaa rpld"),
    ]

    print("Cleaning bounce messages from Gmail...")
    total_deleted = 0

    for email_addr, password in GMAIL_ACCOUNTS:
        print(f"\n  {email_addr}:")
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_addr, password)
            mail.select("INBOX")

            since_date = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
            _, msg_ids = mail.search(None, f'(FROM "mailer-daemon" SINCE {since_date})')

            bounces = msg_ids[0].split()
            print(f"    Found {len(bounces)} bounce messages")

            if bounces:
                for msg_id in bounces:
                    mail.store(msg_id, '+FLAGS', '\\Deleted')
                mail.expunge()
                print(f"    Deleted {len(bounces)} messages")
                total_deleted += len(bounces)

            mail.logout()
        except Exception as e:
            print(f"    Error: {e}")

    print(f"\n  Total deleted: {total_deleted}")
    return total_deleted


def cmd_full_sync():
    """Full sync: Brevo + Gmail + Master CSV."""
    print("=" * 60)
    print("FULL BOUNCE SYNC")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Brevo sync
    print("\n[1/4] Syncing from Brevo API...")
    cmd_brevo_sync()

    # 2. Gmail sync
    print("\n[2/4] Extracting from Gmail bounces...")
    cmd_gmail_sync()

    # 3. Unified sync (updates MASTER_DNC.csv)
    print("\n[3/4] Syncing to unified database...")
    cmd_sync()

    # 4. Gmail cleanup
    print("\n[4/4] Cleaning Gmail bounce messages...")
    cmd_gmail_clean()

    print("\n" + "=" * 60)
    print("FULL SYNC COMPLETE")
    print("=" * 60)

    # Final stats
    bounces = load_all_bounces()
    print(f"\nTotal bounced emails: {len(bounces)}")
    print(f"Blacklist: {BLACKLIST_FILE}")
    print(f"Master DNC: {MASTER_DNC}")


def cmd_quick_clean():
    """Fast bounce sync + clean for mid-campaign use."""
    print("=== QUICK CLEAN (brevo-sync + clean) ===")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")

    # 1. Sync from Brevo
    blocked = cmd_brevo_sync()

    # 2. Clean segments
    if blocked:
        print("\n--- Cleaning segments ---")
        cmd_clean()

    print(f"\nDone at {datetime.now().strftime('%H:%M:%S')}")


def cmd_watch(campaign_name, interval=420):
    """
    Watch mode: run brevo-sync + clean every 7 minutes while campaign is active.

    Args:
        campaign_name: Name of campaign (FACTORY, WAREHOUSE, etc.)
        interval: Seconds between checks (default 420 = 7 minutes)
    """
    import time
    import signal

    # Watch file to control loop
    watch_file = f"/tmp/bounce_watch_{campaign_name.lower()}.pid"
    state_file = f"{CAMPAIGNS_DIR}/{campaign_name}/.{campaign_name.lower()}_sender_state.json"

    # Check campaign exists
    if not os.path.exists(state_file):
        # Try alternate naming patterns
        alt_patterns = [
            f"{CAMPAIGNS_DIR}/{campaign_name}/.{campaign_name.lower()}_state.json",
            f"{CAMPAIGNS_DIR}/{campaign_name}/.*state*.json",
        ]
        found = False
        for pattern in alt_patterns:
            from glob import glob as g
            matches = g(pattern)
            if matches:
                state_file = matches[0]
                found = True
                break
        if not found:
            print(f"Warning: No state file found for {campaign_name}")
            print(f"Will run anyway - stop with Ctrl+C or: rm {watch_file}")

    # Write PID file
    with open(watch_file, "w") as f:
        f.write(str(os.getpid()))

    def cleanup(sig=None, frame=None):
        if os.path.exists(watch_file):
            os.remove(watch_file)
        print(f"\nWatch stopped for {campaign_name}")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print(f"=== BOUNCE WATCH MODE ===")
    print(f"Campaign: {campaign_name}")
    print(f"Interval: {interval}s ({interval//60}min)")
    print(f"PID file: {watch_file}")
    print(f"Stop with: rm {watch_file} or Ctrl+C")
    print("=" * 40)

    iteration = 0
    while os.path.exists(watch_file):
        iteration += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iteration {iteration}")

        # Run quick-clean
        cmd_quick_clean()

        # Check if campaign still has pending emails
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
                sent = state.get("total_sent", 0)
                pending = state.get("pending", state.get("remaining", "?"))
                print(f"Campaign status: sent={sent}, pending={pending}")
            except:
                pass

        print(f"Sleeping {interval}s until next check...")

        # Sleep in small chunks to allow quick exit
        for _ in range(interval // 10):
            if not os.path.exists(watch_file):
                break
            time.sleep(10)

    cleanup()


def cmd_fix_factory():
    """Fix active Factory campaign failures."""
    state_file = f"{CAMPAIGNS_DIR}/FACTORY/.factory_sender_state.json"

    if not os.path.exists(state_file):
        print(f"State file not found: {state_file}")
        return

    with open(state_file, "r") as f:
        state = json.load(f)

    failed = state.get("failed_emails", {})
    print(f"Current failed emails: {len(failed)}")

    for email, retries in failed.items():
        valid, reason = validate_email(email)
        print(f"  {email}: {retries} retries - {reason}")

    if failed:
        # Clear failed emails
        state["failed_emails"] = {}

        # Backup and save
        backup_file = f"{state_file}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(state_file, backup_file)

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        print(f"\nCleared {len(failed)} failed emails from state")
        print(f"Backup: {backup_file}")

    return failed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_search(query)

    elif cmd == "sync":
        cmd_sync()

    elif cmd == "clean":
        cmd_clean()

    elif cmd == "report":
        cmd_report()

    elif cmd == "validate":
        if len(sys.argv) < 3:
            print("Usage: bounce_manager.py validate <file>")
            sys.exit(1)
        cmd_validate(sys.argv[2])

    elif cmd == "brevo-sync":
        cmd_brevo_sync()

    elif cmd == "gmail-sync":
        cmd_gmail_sync()

    elif cmd == "gmail-clean":
        cmd_gmail_clean()

    elif cmd == "full-sync":
        cmd_full_sync()

    elif cmd == "quick-clean":
        cmd_quick_clean()

    elif cmd == "watch":
        if len(sys.argv) < 3:
            print("Usage: bounce_manager.py watch <campaign> [interval_seconds]")
            print("Example: bounce_manager.py watch FACTORY 420")
            sys.exit(1)
        campaign = sys.argv[2].upper()
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 420
        cmd_watch(campaign, interval)

    elif cmd == "fix-factory":
        cmd_fix_factory()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()


# === AUTOMATIC SEGMENT CLEANING ===
# Proposal 5: Daily job to remove bounced emails from all segments

def clean_all_segments():
    """
    Clean bounced emails from ALL campaign segments.
    Run daily via cron.
    """
    import csv
    import shutil
    from datetime import datetime
    
    # Load all bounced emails
    bounced = set()
    
    # From SQLite
    if os.path.exists(BOUNCES_DB):
        conn = sqlite3.connect(BOUNCES_DB)
        cur = conn.execute("SELECT email FROM bounces")
        for row in cur:
            bounced.add(row[0].lower().strip())
        conn.close()
    
    # From blacklist
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    bounced.add(line.strip().lower())
    
    print(f"Loaded {len(bounced)} bounced emails")
    
    # Find all segment CSVs
    campaigns_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    total_removed = 0
    
    for campaign_dir in campaigns_dir.iterdir():
        if not campaign_dir.is_dir():
            continue
        
        # Check segments directory
        seg_dir = campaign_dir / "segments"
        if not seg_dir.exists():
            # Also check for direct CSV files
            csv_files = list(campaign_dir.glob("*.csv"))
        else:
            csv_files = list(seg_dir.glob("*.csv"))
        
        for csv_file in csv_files:
            # Skip backup files
            if '.bak' in str(csv_file):
                continue
            
            try:
                # Read CSV
                with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames
                    rows = list(reader)
                
                if not headers:
                    continue
                
                # Find email column
                email_col = None
                for col in headers:
                    if 'email' in col.lower():
                        email_col = col
                        break
                
                if not email_col:
                    continue
                
                # Filter out bounced
                original_count = len(rows)
                valid_rows = []
                for row in rows:
                    email = row.get(email_col, '').lower().strip()
                    if email and email not in bounced:
                        valid_rows.append(row)
                
                removed = original_count - len(valid_rows)
                
                if removed > 0:
                    # Backup
                    backup = str(csv_file) + '.bak.' + datetime.now().strftime('%Y%m%d')
                    if not os.path.exists(backup):
                        shutil.copy(csv_file, backup)
                    
                    # Write cleaned
                    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(valid_rows)
                    
                    print(f"  {csv_file.name}: removed {removed}")
                    total_removed += removed
            
            except Exception as e:
                print(f"  Error processing {csv_file}: {e}")
    
    print(f"\nTotal removed: {total_removed}")
    return total_removed


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "clean-all":
            clean_all_segments()
