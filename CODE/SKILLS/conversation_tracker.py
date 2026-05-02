#!/usr/bin/env python3
"""
Conversation Tracker - Link reply chains to campaigns and leads

Tracks email conversations:
- Links replies to original campaign sends
- Tracks conversation threads
- Identifies follow-up opportunities
- Records engagement history per lead

Usage:
    python3 conversation_tracker.py                    # Process new replies
    python3 conversation_tracker.py --email user@x.com # Track specific email
    python3 conversation_tracker.py --campaign HORECA  # Campaign conversations
    python3 conversation_tracker.py --export           # Export conversation log
    python3 conversation_tracker.py --status           # Show tracking stats
"""

import os
import sys
import csv
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        import unicodedata
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

# Paths
DATA_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CONVERSATIONS")
STATE_FILE = DATA_DIR / ".tracker_state.json"
CONVERSATIONS_DB = DATA_DIR / "conversations.json"
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
REPLIES_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/REPLIES")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_conversations():
    """Load conversation database."""
    if CONVERSATIONS_DB.exists():
        with open(CONVERSATIONS_DB) as f:
            return json.load(f)
    return {}


def save_conversations(convos):
    """Save conversation database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONVERSATIONS_DB, 'w') as f:
        json.dump(convos, f, indent=2)


def get_email_hash(email):
    """Generate consistent hash for email."""
    return hashlib.md5(email.lower().strip().encode()).hexdigest()[:12]


def find_campaign_for_email(email):
    """Find which campaign sent to this email."""
    email_lower = email.lower().strip()

    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue

        # Check contacts
        contacts_file = campaign_dir / "contacts" / "contacts.csv"
        if contacts_file.exists():
            try:
                with open(contacts_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('email', '').lower().strip() == email_lower:
                            return campaign_dir.name
            except:
                pass

        # Check sent logs
        logs_dir = campaign_dir / "logs"
        if logs_dir.exists():
            for log_file in logs_dir.glob("sent*.log"):
                try:
                    with open(log_file, 'r') as f:
                        if email_lower in f.read().lower():
                            return campaign_dir.name
                except:
                    pass

    return None


def find_lead_info(email):
    """Find lead info from CAEN exports."""
    email_lower = email.lower().strip()
    caen_dir = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")

    for filepath in caen_dir.glob("*_with_email.csv"):
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('email', '').lower().strip() == email_lower:
                        return {
                            'company': row.get('company', ''),
                            'sector': filepath.stem.replace('_with_email', ''),
                            'city': row.get('city', ''),
                            'phone': row.get('phone', ''),
                            'score': row.get('score', 0)
                        }
        except:
            pass

    return None


def process_replies():
    """Process classified replies and link to conversations."""
    classified_file = REPLIES_DIR / "classified_replies.csv"
    if not classified_file.exists():
        log("No classified replies found")
        return 0

    convos = load_conversations()
    processed = 0

    try:
        with open(classified_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('sender_email', '').lower().strip()
                if not email:
                    continue

                email_hash = get_email_hash(email)

                # Initialize conversation if new
                if email_hash not in convos:
                    campaign = find_campaign_for_email(email)
                    lead_info = find_lead_info(email)

                    convos[email_hash] = {
                        'email': email,
                        'campaign': campaign,
                        'lead_info': lead_info,
                        'messages': [],
                        'status': 'new',
                        'first_contact': datetime.now().isoformat(),
                        'last_activity': datetime.now().isoformat()
                    }

                # Add message to thread
                msg_id = hashlib.md5(f"{row.get('date', '')}{row.get('subject', '')}".encode()).hexdigest()[:8]

                # Check if already tracked
                existing_ids = [m.get('id') for m in convos[email_hash]['messages']]
                if msg_id not in existing_ids:
                    convos[email_hash]['messages'].append({
                        'id': msg_id,
                        'date': row.get('date', ''),
                        'subject': row.get('subject', ''),
                        'category': row.get('category', ''),
                        'direction': 'inbound'
                    })
                    convos[email_hash]['last_activity'] = datetime.now().isoformat()

                    # Update status based on category
                    category = row.get('category', '')
                    if category == 'INTERESTED':
                        convos[email_hash]['status'] = 'hot'
                    elif category == 'QUESTION':
                        convos[email_hash]['status'] = 'engaged'
                    elif category == 'UNSUBSCRIBE':
                        convos[email_hash]['status'] = 'unsubscribed'
                    elif category == 'NOT_INTERESTED':
                        convos[email_hash]['status'] = 'closed'

                    processed += 1

    except Exception as e:
        log(f"Error processing replies: {e}")

    save_conversations(convos)
    return processed


def get_conversation(email):
    """Get conversation history for email."""
    convos = load_conversations()
    email_hash = get_email_hash(email)

    if email_hash in convos:
        return convos[email_hash]

    return None


def get_campaign_conversations(campaign_name):
    """Get all conversations for a campaign."""
    convos = load_conversations()

    campaign_convos = []
    for email_hash, convo in convos.items():
        if convo.get('campaign') == campaign_name:
            campaign_convos.append(convo)

    return sorted(campaign_convos, key=lambda x: x.get('last_activity', ''), reverse=True)


def export_conversations():
    """Export conversations to CSV."""
    convos = load_conversations()

    output_file = DATA_DIR / "conversations_export.csv"
    fieldnames = ['email', 'campaign', 'company', 'sector', 'status', 'message_count', 'last_activity', 'first_contact']

    rows = []
    for email_hash, convo in convos.items():
        lead = convo.get('lead_info') or {}
        rows.append({
            'email': convo.get('email', ''),
            'campaign': convo.get('campaign', ''),
            'company': lead.get('company', ''),
            'sector': lead.get('sector', ''),
            'status': convo.get('status', ''),
            'message_count': len(convo.get('messages', [])),
            'last_activity': convo.get('last_activity', ''),
            'first_contact': convo.get('first_contact', '')
        })

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log(f"Exported {len(rows)} conversations to {output_file}")


def show_status():
    """Show tracker status."""
    convos = load_conversations()

    print("\n=== Conversation Tracker Status ===\n")
    print(f"Total conversations: {len(convos)}")

    # Status breakdown
    statuses = {}
    campaigns = {}
    for convo in convos.values():
        status = convo.get('status', 'unknown')
        statuses[status] = statuses.get(status, 0) + 1

        campaign = convo.get('campaign', 'unknown')
        campaigns[campaign] = campaigns.get(campaign, 0) + 1

    print("\nBy status:")
    for status, count in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count}")

    print("\nBy campaign:")
    for campaign, count in sorted(campaigns.items(), key=lambda x: -x[1])[:10]:
        print(f"  {campaign}: {count}")

    # Hot leads
    hot = [c for c in convos.values() if c.get('status') == 'hot']
    if hot:
        print(f"\n🔥 Hot leads ({len(hot)}):")
        for convo in hot[:5]:
            print(f"  {convo.get('email')}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Conversation Tracker")
    parser.add_argument("--email", help="Track specific email")
    parser.add_argument("--campaign", help="Show campaign conversations")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--process", action="store_true", help="Process new replies")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.export:
        export_conversations()
        return

    if args.email:
        convo = get_conversation(args.email)
        if convo:
            print(json.dumps(convo, indent=2))
        else:
            print(f"No conversation found for {args.email}")
        return

    if args.campaign:
        convos = get_campaign_conversations(args.campaign)
        print(f"\n=== {args.campaign} Conversations ({len(convos)}) ===\n")
        for c in convos[:10]:
            print(f"{c.get('email')} [{c.get('status')}] - {len(c.get('messages', []))} messages")
        return

    # Default: process new replies
    log("Processing new replies...")
    processed = process_replies()
    log(f"Processed {processed} new messages")


if __name__ == "__main__":
    main()
