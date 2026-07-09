#!/usr/bin/env python3
"""Raw email collector: IMAP -> JSONL training data. Read-only, no email modification."""

import imaplib
import email
import email.header
import email.utils
import json
import os
import sys
import time
import hashlib
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Load EMAIL/.env for Gmail/Yahoo app passwords
_env_file = Path("/opt/ACTIVE/EMAIL/.env")
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            if _k.strip() and not _k.strip().startswith(" "):
                os.environ.setdefault(_k.strip(), _v.split("#")[0].strip() if " #" in _v else _v.strip())

# =============================================================================
# CONFIG
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "training_data"
JSONL_FILE = DATA_DIR / "raw_emails.jsonl"
SEEN_FILE = DATA_DIR / "seen_message_ids.json"
LOG_FILE = DATA_DIR / "collector.log"
STATS_FILE = DATA_DIR / "collector_stats.json"

A2_IMAP = "nl1-cl8-ats1.a2hosting.com"
GMAIL_IMAP = "imap.gmail.com"
YAHOO_IMAP = "imap.mail.yahoo.com"

# Load credentials from a2_smtp_credentials.json + hardcoded Gmail/Yahoo
CREDS_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json"

# A2 accounts that need password from creds file
A2_ACCOUNTS = [
    "office@buildjobs.eu", "office@interjob.ro", "office@mivromania.info",
    "office@mivromania.online", "office@careworkers.eu", "office@cifn.info",
    "office@nepalezi.com", "office@expatsinromania.org",
    "office@horecaworkers.eu", "office@meatworkers.eu",
    "office@electricjobs.eu", "office@mechanicjobs.eu",
    "office@farmworkers.eu", "office@factoryjobs.eu",
    "office@warehouseworkers.eu", "office@horecaworkers2026.eu",
    "office@horecaworkers2026.com", "office@horecaworkers2026.online",
    "office@internaltransfers.eu", "office@aluminumrecyclehub.com",
    "office@agroevolution.com", "office@cumparlegume.com",
    "office@seicarescu.com",
    "tudor@seicarescu.com",
    "agencies@bppltd.co.uk",
    "apply@bppltd.co.uk",
    "articole@haritina.com",
    "clients@bppltd.co.uk",
    "elena@interjob.ro",
    "factoryjobs@interjob.ro",
    "factoryjobs@nepalezi.com",
    "horeca2026@interjob.ro",
    "info@baneasa39.com",
    "lucian@bppltd.co.uk",
    "norway@interjob.ro",
    "offers@aluminumrecyclehub.com",
    "office@ajwang.org",
    "office@baneasa39.com",
    "office@bppltd.co.uk",
    "office@haritina.com",
    "office@mivromania.com",
    "office@weddnesday.org",
    "partners@agroevolution.com",
    "partners@aluminumrecyclehub.com",
    "slovakia@interjob.ro",
    "support@interjob.ro",
    "tudor.seicarescu@agroevolution.com",
    "tudor@agroevolution.com",
    "tudor@aluminumrecyclehub.com",
    "tudor@cumparlegume.com",
    "tudor@interjob.ro",
]

# Gmail/Yahoo passwords loaded from .env (no hardcoded credentials)
GMAIL_ACCOUNTS = [
    {"email": "manpower.dristor@gmail.com",       "password": os.getenv("GMAIL_MANPOWER_APP_PASSWORD", "")},
    {"email": "manpowerdristor@gmail.com",        "password": os.getenv("GMAIL_MANPOWERDRISTOR_APP_PASSWORD", "")},
    {"email": "elena.manpower.dristor@gmail.com", "password": os.getenv("GMAIL_ELENA_PASSWORD", "")},
    {"email": "expatsinromania@gmail.com",        "password": os.getenv("GMAIL_EXPATS_PASSWORD", "")},
    {"email": "cumparlegume@gmail.com",           "password": os.getenv("GMAIL_CUMPARLEGUME_PASSWORD", "")},
    {"email": "casafaurbucuresti@gmail.com",      "password": os.getenv("GMAIL_CASAFAUR_PASSWORD", "")},
    {"email": "vegetablesbucharest@gmail.com",    "password": os.getenv("GMAIL_VEGETABLESBUCHAREST_PASSWORD", "")},
    {"email": "fructexportromania@gmail.com",     "password": os.getenv("GMAIL_FRUCTEXPORT_PASSWORD", "")},
    {"email": "lucian.bpandp@gmail.com",          "password": os.getenv("GMAIL_LUCIAN_APP_PASSWORD", "")},
]

YAHOO_ACCOUNTS = [
    {"email": "secretariatagentieasia@yahoo.com", "password": os.getenv("YAHOO_APP_PASSWORD", "")},
    {"email": "apaminerala@yahoo.com",            "password": os.getenv("YAHOO_APAMINERALA_APP_PASSWORD", "")},
]

CHECK_INTERVAL = 900  # 15 minutes

# =============================================================================
# LOGGING
# =============================================================================

def setup_logging():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("email_collector")

log = setup_logging()

# =============================================================================
# HELPERS
# =============================================================================

def load_a2_passwords():
    """Load A2 passwords from credentials JSON."""
    if not os.path.exists(CREDS_FILE):
        log.error(f"Credentials file not found: {CREDS_FILE}")
        return {}
    with open(CREDS_FILE) as f:
        creds = json.load(f)
    # Map email -> password
    pw_map = {}
    for domain, info in creds.items():
        pw_map[info["email"]] = info["password"]
    return pw_map


def load_seen_ids():
    """Load set of already-collected message IDs."""
    if SEEN_FILE.exists():
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen):
    """Persist seen message IDs."""
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f)


def decode_header_value(raw):
    """Decode a MIME-encoded header into a string."""
    if raw is None:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def get_text_body(msg):
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback: try text/html
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/html" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def get_attachment_names(msg):
    """List attachment filenames."""
    names = []
    if msg.is_multipart():
        for part in msg.walk():
            fn = part.get_filename()
            if fn:
                names.append(decode_header_value(fn))
    return names


def message_hash(msg_id, from_addr, date_str, subject):
    """Fallback dedup key when Message-ID is missing. MD5(subject+from) matches auto_organize."""
    text = f"{(subject or "").lower().strip()}|{(from_addr or "").lower().strip()}"
    return hashlib.md5(text.encode()).hexdigest()


# =============================================================================
# IMAP COLLECTION
# =============================================================================

def collect_from_account(addr, password, imap_server, days, seen_ids):
    """Connect to one IMAP account and collect emails as dicts."""
    collected = []
    try:
        mail = imaplib.IMAP4_SSL(imap_server, 993, timeout=30)
        mail.login(addr, password)
    except Exception as e:
        log.warning(f"  IMAP login failed for {addr}: {e}")
        return collected

    try:
        mail.select("INBOX", readonly=True)  # readonly=True — do NOT modify
        since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        status, data = mail.search(None, f'(SINCE {since})')
        if status != "OK" or not data[0]:
            mail.logout()
            return collected

        ids = data[0].split()
        log.info(f"  {addr}: {len(ids)} emails since {since}")

        for uid in ids:
            try:
                status, msg_data = mail.fetch(uid, "(BODY.PEEK[])")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                msg_id = msg.get("Message-ID", "")
                from_addr = decode_header_value(msg.get("From", ""))
                to_addr = decode_header_value(msg.get("To", ""))
                subject = decode_header_value(msg.get("Subject", ""))
                date_str = msg.get("Date", "")

                # Dedup key
                key = msg_id if msg_id else message_hash(msg_id, from_addr, date_str, subject)
                if key in seen_ids:
                    continue

                body = get_text_body(msg)
                attachments = get_attachment_names(msg)

                record = {
                    "message_id": msg_id,
                    "dedup_key": key,
                    "account": addr,
                    "imap_server": imap_server,
                    "from": from_addr,
                    "to": to_addr,
                    "subject": subject,
                    "date": date_str,
                    "body": body[:10000],  # cap at 10K chars
                    "body_length": len(body),
                    "attachments": attachments,
                    "has_attachments": len(attachments) > 0,
                    "collected_at": datetime.now().isoformat(),
                }

                collected.append(record)
                seen_ids.add(key)

            except Exception as e:
                log.warning(f"  Error fetching email {uid} from {addr}: {e}")
                continue

        mail.logout()
    except Exception as e:
        log.warning(f"  Error processing {addr}: {e}")
        try:
            mail.logout()
        except:
            pass

    return collected


def collect_all(days=3):
    """Collect from all accounts, append to JSONL, return count."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    seen_ids = load_seen_ids()
    total_new = 0

    # Load A2 passwords
    a2_pw = load_a2_passwords()

    # --- A2 accounts ---
    log.info(f"Scanning {len(A2_ACCOUNTS)} A2 accounts...")
    for addr in A2_ACCOUNTS:
        pw = a2_pw.get(addr)
        if not pw:
            log.warning(f"  No password for {addr}, skipping")
            continue
        emails = collect_from_account(addr, pw, A2_IMAP, days, seen_ids)
        if emails:
            append_jsonl(emails)
            total_new += len(emails)
            log.info(f"  +{len(emails)} new from {addr}")

    # --- Gmail accounts ---
    log.info(f"Scanning {len(GMAIL_ACCOUNTS)} Gmail accounts...")
    for acct in GMAIL_ACCOUNTS:
        emails = collect_from_account(acct["email"], acct["password"], GMAIL_IMAP, days, seen_ids)
        if emails:
            append_jsonl(emails)
            total_new += len(emails)
            log.info(f"  +{len(emails)} new from {acct['email']}")

    # --- Yahoo accounts ---
    log.info(f"Scanning {len(YAHOO_ACCOUNTS)} Yahoo accounts...")
    for acct in YAHOO_ACCOUNTS:
        emails = collect_from_account(acct["email"], acct["password"], YAHOO_IMAP, days, seen_ids)
        if emails:
            append_jsonl(emails)
            total_new += len(emails)
            log.info(f"  +{len(emails)} new from {acct['email']}")

    save_seen_ids(seen_ids)

    # Update stats
    stats = load_stats()
    stats["last_run"] = datetime.now().isoformat()
    stats["total_collected"] = len(seen_ids)
    stats["last_new"] = total_new
    stats["runs"] = stats.get("runs", 0) + 1
    save_stats(stats)

    log.info(f"Collection complete: {total_new} new emails. Total in dataset: {len(seen_ids)}")
    return total_new


def append_jsonl(records):
    """Append records to the JSONL file."""
    with open(JSONL_FILE, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# =============================================================================
# STATS
# =============================================================================

def load_stats():
    if STATS_FILE.exists():
        with open(STATS_FILE) as f:
            return json.load(f)
    return {}


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def show_stats():
    stats = load_stats()
    if not stats:
        print("No collection stats yet. Run the collector first.")
        return
    print(f"Last run:        {stats.get('last_run', 'never')}")
    print(f"Total collected: {stats.get('total_collected', 0)}")
    print(f"Last new:        {stats.get('last_new', 0)}")
    print(f"Total runs:      {stats.get('runs', 0)}")

    if JSONL_FILE.exists():
        size_mb = JSONL_FILE.stat().st_size / (1024 * 1024)
        print(f"JSONL file size: {size_mb:.1f} MB")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Raw Email Collector for Training")
    parser.add_argument("--days", type=int, default=3, help="Collect emails from last N days (default: 3)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously every 15 min")
    parser.add_argument("--stats", action="store_true", help="Show collection stats")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.daemon:
        log.info(f"Starting daemon mode (check every {CHECK_INTERVAL}s, looking back {args.days} days)")
        while True:
            try:
                collect_all(days=args.days)
            except Exception as e:
                log.error(f"Collection error: {e}")
            time.sleep(CHECK_INTERVAL)
    else:
        collect_all(days=args.days)


if __name__ == "__main__":
    main()
