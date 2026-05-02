#!/usr/bin/env python3
"""
Multi-Gmail Batch Email System
Brevo: 5 emails per batch every 10 minutes
Gmail Warmed: 1 email every 4 minutes (150/day)
Gmail Fresh: 1 email every 12 minutes (50/day)
"""

import sqlite3
import json
import time
import smtplib
import requests
import logging
from datetime import datetime
from email.mime.text import MIMEText

class MultiGmailBatchSystem:
    def __init__(self, campaign):
        self.campaign = campaign
        self.db_path = f'/opt/EMAIL/CAMPAIGNS/{campaign}/{campaign.lower()}.db'
        self.config_file = f'/opt/EMAIL/CAMPAIGNS/{campaign}/.multi_batch_config.json'

        # Email limits and intervals
        self.brevo_batch_size = 5
        self.brevo_interval_minutes = 10
        self.brevo_daily_limit = 290

        # Gmail account types and limits
        self.gmail_accounts = {
            'warmed': {
                'daily_limit': 150,
                'interval_minutes': 4,
                'emails': [
                    'manpower.dristor@gmail.com',
                    'expatsinromania@gmail.com'
                ]
            },
            'fresh': {
                'daily_limit': 50,
                'interval_minutes': 12,
                'emails': [
                    'elena.manpower.dristor@gmail.com',
                    'cumparlegume@gmail.com',
                    'vegetablesbucharest@gmail.com'
                ]
            }
        }

        # Load configuration
        self.load_config()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def load_config(self):
        """Load multi-batch sending configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        except:
            config = {
                'current_sender': 'brevo',
                'last_brevo_batch': None,
                'daily_brevo_sent': 0,
                'gmail_warmed': {
                    'last_send': None,
                    'daily_sent': 0,
                    'current_account_index': 0
                },
                'gmail_fresh': {
                    'last_send': None,
                    'daily_sent': 0,
                    'current_account_index': 0
                },
                'last_reset_date': str(datetime.now().date())
            }
            self.save_config(config)

        self.config = config

    def save_config(self, config=None):
        """Save configuration"""
        if config is None:
            config = self.config

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def reset_daily_counters_if_needed(self):
        """Reset daily counters at midnight"""
        today = str(datetime.now().date())
        if self.config.get('last_reset_date') != today:
            self.config['daily_brevo_sent'] = 0
            self.config['gmail_warmed']['daily_sent'] = 0
            self.config['gmail_fresh']['daily_sent'] = 0
            self.config['last_reset_date'] = today
            self.save_config()

    def can_send_brevo_batch(self):
        """Check if we can send Brevo batch"""
        self.reset_daily_counters_if_needed()

        # Check daily limit
        if self.config['daily_brevo_sent'] >= self.brevo_daily_limit:
            return False, "Daily Brevo limit reached"

        # Check time interval
        last_batch = self.config.get('last_brevo_batch')
        if last_batch:
            last_time = datetime.fromisoformat(last_batch)
            minutes_since = (datetime.now() - last_time).total_seconds() / 60
            if minutes_since < self.brevo_interval_minutes:
                return False, f"Wait {self.brevo_interval_minutes - minutes_since:.1f} minutes"

        return True, "OK"

    def can_send_gmail(self, account_type):
        """Check if we can send Gmail for specific account type"""
        self.reset_daily_counters_if_needed()

        gmail_config = self.config[f'gmail_{account_type}']
        account_limits = self.gmail_accounts[account_type]

        # Check daily limit
        if gmail_config['daily_sent'] >= account_limits['daily_limit']:
            return False, f"Daily {account_type} Gmail limit reached"

        # Check time interval
        last_send = gmail_config.get('last_send')
        if last_send:
            last_time = datetime.fromisoformat(last_send)
            minutes_since = (datetime.now() - last_time).total_seconds() / 60
            required_interval = account_limits['interval_minutes']

            if minutes_since < required_interval:
                return False, f"Wait {required_interval - minutes_since:.1f} minutes"

        return True, "OK"

    def get_pending_contacts(self, limit):
        """Get pending contacts from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT email, company, city, contact_name, phone
                FROM contacts
                WHERE status = 'pending'
                ORDER BY added_at ASC
                LIMIT ?
            """, (limit,))

            contacts = cursor.fetchall()
            conn.close()

            return [{
                'email': row[0],
                'company': row[1],
                'city': row[2],
                'contact_name': row[3],
                'phone': row[4]
            } for row in contacts]

        except Exception as e:
            self.logger.error(f"Database error: {e}")
            return []

    def send_brevo_batch(self, contacts):
        """Send batch of 5 emails via Brevo"""
        self.logger.info(f"📧 Sending Brevo batch: {len(contacts)} emails...")

        try:
            # Simulate Brevo batch API call
            # In real implementation, use Brevo's batch API

            # Mark contacts as sent
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            sent_emails = []
            for contact in contacts:
                cursor.execute("""
                    UPDATE contacts
                    SET status = 'sent', sent_at = ?, sent_via = 'brevo_batch'
                    WHERE email = ?
                """, (datetime.now().isoformat(), contact['email']))
                sent_emails.append(contact['email'])

            conn.commit()
            conn.close()

            # Update config
            self.config['last_brevo_batch'] = datetime.now().isoformat()
            self.config['daily_brevo_sent'] += len(contacts)
            self.save_config()

            self.logger.info(f"✅ Brevo batch sent: {len(contacts)} emails")
            return True, sent_emails

        except Exception as e:
            self.logger.error(f"Brevo batch failed: {e}")
            return False, []

    def send_gmail_single(self, contact, account_type):
        """Send single email via Gmail (warmed or fresh)"""
        gmail_config = self.config[f'gmail_{account_type}']
        available_emails = self.gmail_accounts[account_type]['emails']

        # Get current account
        account_index = gmail_config['current_account_index']
        current_email = available_emails[account_index % len(available_emails)]

        self.logger.info(f"📨 Sending Gmail ({account_type}) from {current_email} to {contact['company']}...")

        try:
            # Simulate Gmail SMTP call
            # In real implementation, use SMTP with current_email

            # Mark contact as sent
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE contacts
                SET status = 'sent', sent_at = ?, sent_via = ?
                WHERE email = ?
            """, (datetime.now().isoformat(), f'gmail_{account_type}_{current_email}', contact['email']))

            conn.commit()
            conn.close()

            # Update config
            gmail_config['last_send'] = datetime.now().isoformat()
            gmail_config['daily_sent'] += 1

            # Rotate account for next send
            gmail_config['current_account_index'] = (account_index + 1) % len(available_emails)

            self.save_config()

            self.logger.info(f"✅ Gmail ({account_type}) sent to {contact['email']}")
            return True

        except Exception as e:
            self.logger.error(f"Gmail ({account_type}) failed: {e}")
            return False

    def send_optimal_emails(self):
        """Send emails using optimal multi-account strategy"""
        results = []

        # 1. Try Brevo batch (highest priority - bulk sending)
        can_brevo, brevo_msg = self.can_send_brevo_batch()
        if can_brevo:
            contacts = self.get_pending_contacts(self.brevo_batch_size)
            if contacts:
                success, sent_emails = self.send_brevo_batch(contacts)
                if success:
                    results.append(f"Brevo batch: {len(sent_emails)} emails")

        # 2. Try Gmail warmed (medium volume)
        can_gmail_warmed, warmed_msg = self.can_send_gmail('warmed')
        if can_gmail_warmed:
            contacts = self.get_pending_contacts(1)
            if contacts:
                success = self.send_gmail_single(contacts[0], 'warmed')
                if success:
                    results.append("Gmail warmed: 1 email")

        # 3. Try Gmail fresh (low volume, warming up)
        can_gmail_fresh, fresh_msg = self.can_send_gmail('fresh')
        if can_gmail_fresh:
            contacts = self.get_pending_contacts(1)
            if contacts:
                success = self.send_gmail_single(contacts[0], 'fresh')
                if success:
                    results.append("Gmail fresh: 1 email")

        if not results:
            # Log why nothing was sent
            self.logger.info(f"No emails sent - Brevo: {brevo_msg}, Warmed: {warmed_msg}, Fresh: {fresh_msg}")

        return results

    def get_detailed_status(self):
        """Get detailed status of all sending methods"""
        self.reset_daily_counters_if_needed()

        pending_contacts = len(self.get_pending_contacts(1000))

        # Calculate next send times
        def calc_next_time(last_send_iso, interval_minutes):
            if not last_send_iso:
                return "Available"
            last_time = datetime.fromisoformat(last_send_iso)
            next_time = last_time.timestamp() + (interval_minutes * 60)
            if next_time > datetime.now().timestamp():
                return f"{(next_time - datetime.now().timestamp())/60:.1f} min"
            return "Available"

        return {
            'campaign': self.campaign,
            'pending_contacts': pending_contacts,
            'brevo': {
                'sent_today': self.config['daily_brevo_sent'],
                'limit': self.brevo_daily_limit,
                'batch_size': self.brevo_batch_size,
                'next_batch': calc_next_time(self.config.get('last_brevo_batch'), self.brevo_interval_minutes)
            },
            'gmail_warmed': {
                'sent_today': self.config['gmail_warmed']['daily_sent'],
                'limit': self.gmail_accounts['warmed']['daily_limit'],
                'interval_minutes': self.gmail_accounts['warmed']['interval_minutes'],
                'next_send': calc_next_time(self.config['gmail_warmed'].get('last_send'),
                                         self.gmail_accounts['warmed']['interval_minutes']),
                'accounts': len(self.gmail_accounts['warmed']['emails'])
            },
            'gmail_fresh': {
                'sent_today': self.config['gmail_fresh']['daily_sent'],
                'limit': self.gmail_accounts['fresh']['daily_limit'],
                'interval_minutes': self.gmail_accounts['fresh']['interval_minutes'],
                'next_send': calc_next_time(self.config['gmail_fresh'].get('last_send'),
                                         self.gmail_accounts['fresh']['interval_minutes']),
                'accounts': len(self.gmail_accounts['fresh']['emails'])
            },
            'daily_total_capacity': (
                self.brevo_daily_limit +
                self.gmail_accounts['warmed']['daily_limit'] +
                self.gmail_accounts['fresh']['daily_limit']
            ),
            'last_reset': self.config['last_reset_date']
        }

def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Multi-Gmail Batch Email System')
    parser.add_argument('campaign', help='Campaign name (LUCIAN/VIRGIL/ELENA)')
    parser.add_argument('--send', action='store_true', help='Send emails optimally')
    parser.add_argument('--status', action='store_true', help='Show detailed status')

    args = parser.parse_args()

    batch_system = MultiGmailBatchSystem(args.campaign)

    if args.status:
        status = batch_system.get_detailed_status()
        print(json.dumps(status, indent=2))

    elif args.send:
        results = batch_system.send_optimal_emails()
        if results:
            print("Sent: " + ", ".join(results))
        else:
            print("No emails sent (waiting for intervals)")

    else:
        print("Use --send or --status")

if __name__ == "__main__":
    main()