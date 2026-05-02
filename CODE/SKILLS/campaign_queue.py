#!/usr/bin/env python3
"""
Campaign Queue System - Redis-backed persistent queue for email campaigns.
Ensures no emails are lost if sender crashes mid-batch.

Usage:
    # Load contacts into queue
    python3 campaign_queue.py load FACTORY_EU /path/to/contacts.csv

    # Process queue (used by senders)
    python3 campaign_queue.py pop FACTORY_EU

    # Mark as sent
    python3 campaign_queue.py done FACTORY_EU email@example.com

    # Check status
    python3 campaign_queue.py status [CAMPAIGN]

    # Requeue failed
    python3 campaign_queue.py requeue FACTORY_EU
"""
import sys
import json
import csv
import redis
from pathlib import Path
from datetime import datetime

# Redis connection
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 1  # Use DB 1 for campaigns

# Key prefixes
QUEUE_PREFIX = 'campaign:queue:'      # List of pending emails
PROCESSING_PREFIX = 'campaign:proc:'  # Hash of emails being processed
SENT_PREFIX = 'campaign:sent:'        # Set of sent emails
FAILED_PREFIX = 'campaign:failed:'    # Set of failed emails
META_PREFIX = 'campaign:meta:'        # Hash of campaign metadata

class CampaignQueue:
    def __init__(self):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    def load_contacts(self, campaign: str, csv_path: str, email_col: str = 'email'):
        """Load contacts from CSV into queue."""
        queue_key = f"{QUEUE_PREFIX}{campaign}"
        sent_key = f"{SENT_PREFIX}{campaign}"
        meta_key = f"{META_PREFIX}{campaign}"

        # Get already sent emails to avoid duplicates
        sent = self.r.smembers(sent_key)

        loaded = 0
        skipped = 0

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get(email_col, '').strip().lower()
                if not email or '@' not in email:
                    continue

                if email in sent:
                    skipped += 1
                    continue

                # Store full contact data as JSON
                self.r.rpush(queue_key, json.dumps(row))
                loaded += 1

        # Update metadata
        self.r.hset(meta_key, mapping={
            'last_load': datetime.now().isoformat(),
            'source_file': csv_path,
            'loaded_count': loaded
        })

        print(f"Loaded {loaded} contacts, skipped {skipped} already sent")
        return loaded

    def pop(self, campaign: str) -> dict:
        """Get next contact from queue (moves to processing)."""
        queue_key = f"{QUEUE_PREFIX}{campaign}"
        proc_key = f"{PROCESSING_PREFIX}{campaign}"

        # Atomic pop from queue
        data = self.r.lpop(queue_key)
        if not data:
            return None

        contact = json.loads(data)
        email = contact.get('email', '').strip().lower()

        # Mark as processing with timestamp
        self.r.hset(proc_key, email, json.dumps({
            'contact': contact,
            'started': datetime.now().isoformat()
        }))

        return contact

    def done(self, campaign: str, email: str, success: bool = True):
        """Mark email as sent or failed."""
        email = email.strip().lower()
        proc_key = f"{PROCESSING_PREFIX}{campaign}"
        sent_key = f"{SENT_PREFIX}{campaign}"
        failed_key = f"{FAILED_PREFIX}{campaign}"

        # Remove from processing
        self.r.hdel(proc_key, email)

        # Add to sent or failed
        if success:
            self.r.sadd(sent_key, email)
        else:
            self.r.sadd(failed_key, email)

    def requeue_processing(self, campaign: str):
        """Requeue any stuck processing items (crashed mid-send)."""
        proc_key = f"{PROCESSING_PREFIX}{campaign}"
        queue_key = f"{QUEUE_PREFIX}{campaign}"

        processing = self.r.hgetall(proc_key)
        requeued = 0

        for email, data in processing.items():
            try:
                info = json.loads(data)
                contact = info.get('contact', {})
                # Put back at front of queue
                self.r.lpush(queue_key, json.dumps(contact))
                self.r.hdel(proc_key, email)
                requeued += 1
            except:
                pass

        print(f"Requeued {requeued} stuck contacts")
        return requeued

    def requeue_failed(self, campaign: str):
        """Move failed emails back to queue for retry."""
        failed_key = f"{FAILED_PREFIX}{campaign}"
        queue_key = f"{QUEUE_PREFIX}{campaign}"

        failed = self.r.smembers(failed_key)
        for email in failed:
            self.r.rpush(queue_key, json.dumps({'email': email}))

        count = len(failed)
        self.r.delete(failed_key)
        print(f"Requeued {count} failed emails")
        return count

    def status(self, campaign: str = None):
        """Get queue status for one or all campaigns."""
        if campaign:
            campaigns = [campaign]
        else:
            # Find all campaigns
            campaigns = set()
            for key in self.r.scan_iter(f"{QUEUE_PREFIX}*"):
                campaigns.add(key.replace(QUEUE_PREFIX, ''))
            for key in self.r.scan_iter(f"{SENT_PREFIX}*"):
                campaigns.add(key.replace(SENT_PREFIX, ''))

        print(f"\n=== CAMPAIGN QUEUES ({datetime.now():%H:%M}) ===\n")
        print(f"{'Campaign':<20} {'Pending':>10} {'Processing':>12} {'Sent':>10} {'Failed':>10}")
        print("-" * 65)

        for c in sorted(campaigns):
            pending = self.r.llen(f"{QUEUE_PREFIX}{c}")
            processing = self.r.hlen(f"{PROCESSING_PREFIX}{c}")
            sent = self.r.scard(f"{SENT_PREFIX}{c}")
            failed = self.r.scard(f"{FAILED_PREFIX}{c}")

            print(f"{c:<20} {pending:>10} {processing:>12} {sent:>10} {failed:>10}")

        print()

    def clear(self, campaign: str):
        """Clear all queue data for a campaign."""
        keys = [
            f"{QUEUE_PREFIX}{campaign}",
            f"{PROCESSING_PREFIX}{campaign}",
            f"{SENT_PREFIX}{campaign}",
            f"{FAILED_PREFIX}{campaign}",
            f"{META_PREFIX}{campaign}",
        ]
        for key in keys:
            self.r.delete(key)
        print(f"Cleared all data for {campaign}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    q = CampaignQueue()
    cmd = sys.argv[1].lower()

    if cmd == 'load':
        if len(sys.argv) < 4:
            print("Usage: campaign_queue.py load CAMPAIGN /path/to/contacts.csv [email_col]")
            sys.exit(1)
        campaign = sys.argv[2]
        csv_path = sys.argv[3]
        email_col = sys.argv[4] if len(sys.argv) > 4 else 'email'
        q.load_contacts(campaign, csv_path, email_col)

    elif cmd == 'pop':
        if len(sys.argv) < 3:
            print("Usage: campaign_queue.py pop CAMPAIGN")
            sys.exit(1)
        contact = q.pop(sys.argv[2])
        if contact:
            print(json.dumps(contact))
        else:
            print("Queue empty")

    elif cmd == 'done':
        if len(sys.argv) < 4:
            print("Usage: campaign_queue.py done CAMPAIGN email [success|fail]")
            sys.exit(1)
        success = sys.argv[4].lower() != 'fail' if len(sys.argv) > 4 else True
        q.done(sys.argv[2], sys.argv[3], success)
        print(f"Marked {sys.argv[3]} as {'sent' if success else 'failed'}")

    elif cmd == 'requeue':
        if len(sys.argv) < 3:
            print("Usage: campaign_queue.py requeue CAMPAIGN")
            sys.exit(1)
        q.requeue_processing(sys.argv[2])
        q.requeue_failed(sys.argv[2])

    elif cmd == 'status':
        campaign = sys.argv[2] if len(sys.argv) > 2 else None
        q.status(campaign)

    elif cmd == 'clear':
        if len(sys.argv) < 3:
            print("Usage: campaign_queue.py clear CAMPAIGN")
            sys.exit(1)
        q.clear(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
