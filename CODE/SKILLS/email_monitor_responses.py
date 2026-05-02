#!/usr/bin/env python3
"""
Email Monitoring & Response System
Real-time spam/bounce detection with automatic responses
"""

import sqlite3
import json
import smtplib
import time
import dns.resolver
import requests
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText

class EmailMonitoringSystem:
    def __init__(self):
        self.monitor_db = '/opt/EMAIL/CAMPAIGNS/email_monitoring.db'
        self.response_strategies = {
            'SPAM': 'pause_and_switch',
            'BOUNCE': 'mark_invalid_and_continue',
            'DOMAIN_NOT_FOUND': 'mark_invalid_and_continue',
            'REJECTED': 'pause_and_switch',
            'RATE_LIMITED': 'pause_and_retry',
            'SUCCESS': 'continue'
        }

        # Brevo API for checking delivery status
        self.brevo_api_key = self.load_brevo_key()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.init_monitor_db()

    def load_brevo_key(self):
        """Load Brevo API key from environment"""
        try:
            with open('/opt/EMAIL/CAMPAIGNS/.env', 'r') as f:
                for line in f:
                    if line.startswith('BREVO_API_KEY='):
                        return line.split('=', 1)[1].strip()
        except:
            pass
        return None

    def init_monitor_db(self):
        """Initialize monitoring database"""
        conn = sqlite3.connect(self.monitor_db)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                company TEXT,
                campaign TEXT,
                sent_at TIMESTAMP,
                status TEXT,  -- SUCCESS, SPAM, BOUNCE, REJECTED, etc.
                response_details TEXT,
                action_taken TEXT,
                verified_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS domain_status (
                domain TEXT PRIMARY KEY,
                status TEXT,  -- VALID, INVALID, SUSPICIOUS
                last_checked TIMESTAMP,
                mx_records TEXT,
                notes TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaign_health (
                campaign TEXT,
                date DATE,
                sent_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                spam_count INTEGER DEFAULT 0,
                bounce_count INTEGER DEFAULT 0,
                health_score REAL,  -- 0-100
                status TEXT,  -- HEALTHY, WARNING, PAUSED
                PRIMARY KEY (campaign, date)
            )
        """)

        conn.commit()
        conn.close()

    def verify_domain(self, email):
        """Verify if email domain exists and has MX records"""
        domain = email.split('@')[1].lower()

        # Check cache first
        conn = sqlite3.connect(self.monitor_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status, mx_records FROM domain_status WHERE domain = ?", (domain,))
        cached = cursor.fetchone()
        conn.close()

        if cached:
            return cached[0] == 'VALID', cached[1]

        try:
            # Check MX records
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_list = [str(mx) for mx in mx_records]

            # Cache result
            conn = sqlite3.connect(self.monitor_db)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO domain_status
                (domain, status, last_checked, mx_records)
                VALUES (?, 'VALID', ?, ?)
            """, (domain, datetime.now(), json.dumps(mx_list)))
            conn.commit()
            conn.close()

            return True, mx_list

        except Exception as e:
            # Cache as invalid
            conn = sqlite3.connect(self.monitor_db)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO domain_status
                (domain, status, last_checked, notes)
                VALUES (?, 'INVALID', ?, ?)
            """, (domain, datetime.now(), str(e)))
            conn.commit()
            conn.close()

            return False, str(e)

    def check_brevo_delivery(self, email, sent_time):
        """Check email delivery status via Brevo API"""
        if not self.brevo_api_key:
            return 'UNKNOWN'

        try:
            # Wait a bit for delivery
            time.sleep(30)

            headers = {
                'api-key': self.brevo_api_key,
                'Content-Type': 'application/json'
            }

            # Get email events from Brevo
            url = 'https://api.brevo.com/v3/smtp/statistics/events'
            params = {
                'email': email,
                'startDate': sent_time.strftime('%Y-%m-%d'),
                'endDate': sent_time.strftime('%Y-%m-%d')
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])

                for event in events:
                    event_type = event.get('event')
                    if event_type == 'spam':
                        return 'SPAM'
                    elif event_type == 'bounce':
                        return 'BOUNCE'
                    elif event_type == 'delivered':
                        return 'SUCCESS'
                    elif event_type == 'blocked':
                        return 'REJECTED'

                # If no negative events, assume success
                return 'SUCCESS'

        except Exception as e:
            self.logger.warning(f"Brevo API check failed: {e}")

        return 'UNKNOWN'

    def log_email_status(self, email, company, campaign, status, details=""):
        """Log email delivery status"""
        conn = sqlite3.connect(self.monitor_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO email_status
            (email, company, campaign, sent_at, status, response_details, verified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (email, company, campaign, datetime.now(), status, details, datetime.now()))

        conn.commit()
        conn.close()

    def update_campaign_health(self, campaign, status):
        """Update campaign health metrics"""
        today = datetime.now().date()

        conn = sqlite3.connect(self.monitor_db)
        cursor = conn.cursor()

        # Get or create today's record
        cursor.execute("""
            INSERT OR IGNORE INTO campaign_health (campaign, date, sent_count, success_count, spam_count, bounce_count)
            VALUES (?, ?, 0, 0, 0, 0)
        """, (campaign, today))

        # Update counters
        if status == 'SUCCESS':
            cursor.execute("UPDATE campaign_health SET sent_count = sent_count + 1, success_count = success_count + 1 WHERE campaign = ? AND date = ?", (campaign, today))
        elif status == 'SPAM':
            cursor.execute("UPDATE campaign_health SET sent_count = sent_count + 1, spam_count = spam_count + 1 WHERE campaign = ? AND date = ?", (campaign, today))
        elif status in ['BOUNCE', 'REJECTED']:
            cursor.execute("UPDATE campaign_health SET sent_count = sent_count + 1, bounce_count = bounce_count + 1 WHERE campaign = ? AND date = ?", (campaign, today))
        else:
            cursor.execute("UPDATE campaign_health SET sent_count = sent_count + 1 WHERE campaign = ? AND date = ?", (campaign, today))

        # Calculate health score
        cursor.execute("SELECT sent_count, success_count, spam_count, bounce_count FROM campaign_health WHERE campaign = ? AND date = ?", (campaign, today))
        counts = cursor.fetchone()

        if counts and counts[0] > 0:
            sent, success, spam, bounce = counts
            health_score = (success / sent) * 100 - (spam * 10) - (bounce * 5)
            health_score = max(0, min(100, health_score))

            # Determine status
            if health_score >= 80:
                health_status = 'HEALTHY'
            elif health_score >= 60:
                health_status = 'WARNING'
            else:
                health_status = 'PAUSED'

            cursor.execute("UPDATE campaign_health SET health_score = ?, status = ? WHERE campaign = ? AND date = ?", (health_score, health_status, campaign, today))

        conn.commit()
        conn.close()

    def get_response_action(self, status, campaign):
        """Get response action for email status"""
        strategy = self.response_strategies.get(status, 'continue')

        if strategy == 'pause_and_switch':
            return {
                'action': 'PAUSE_CAMPAIGN',
                'duration_minutes': 60,
                'switch_sender': True,
                'reason': f'High {status.lower()} rate detected'
            }
        elif strategy == 'mark_invalid_and_continue':
            return {
                'action': 'MARK_INVALID',
                'continue_sending': True,
                'reason': f'{status} - invalid email/domain'
            }
        elif strategy == 'pause_and_retry':
            return {
                'action': 'PAUSE_CAMPAIGN',
                'duration_minutes': 30,
                'retry_later': True,
                'reason': 'Rate limiting detected'
            }
        else:
            return {
                'action': 'CONTINUE',
                'reason': 'Normal operation'
            }

    def execute_response_action(self, action_data, campaign, email):
        """Execute the response action"""
        action = action_data['action']

        if action == 'PAUSE_CAMPAIGN':
            # Create pause file
            pause_file = f'/opt/EMAIL/CAMPAIGNS/{campaign}/.paused'
            with open(pause_file, 'w') as f:
                json.dump({
                    'paused_at': datetime.now().isoformat(),
                    'duration_minutes': action_data.get('duration_minutes', 60),
                    'reason': action_data['reason'],
                    'triggered_by': email
                }, f, indent=2)

            self.logger.warning(f"{campaign} PAUSED: {action_data['reason']}")

            # Send Telegram alert
            self.send_telegram_alert(f"🚨 {campaign} PAUSED\nReason: {action_data['reason']}\nEmail: {email}\nDuration: {action_data.get('duration_minutes', 60)} minutes")

        elif action == 'MARK_INVALID':
            # Mark email as invalid in campaign database
            campaign_db = f'/opt/EMAIL/CAMPAIGNS/{campaign}/{campaign.lower()}.db'
            conn = sqlite3.connect(campaign_db)
            cursor = conn.cursor()
            cursor.execute("UPDATE contacts SET status = 'invalid' WHERE email = ?", (email,))
            conn.commit()
            conn.close()

            self.logger.info(f"Marked {email} as invalid in {campaign}")

    def send_telegram_alert(self, message):
        """Send Telegram alert for critical issues"""
        try:
            # Use existing Telegram notification system
            import subprocess
            subprocess.run(['/opt/EMAIL/CAMPAIGNS/send_telegram_alert.sh', message], timeout=10)
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")

    def monitor_email_after_send(self, email, company, campaign):
        """Complete monitoring workflow after sending email"""
        self.logger.info(f"Monitoring {email} for {campaign}...")

        # Step 1: Verify domain
        domain_valid, mx_info = self.verify_domain(email)
        if not domain_valid:
            self.log_email_status(email, company, campaign, 'DOMAIN_NOT_FOUND', mx_info)
            action = self.get_response_action('DOMAIN_NOT_FOUND', campaign)
            self.execute_response_action(action, campaign, email)
            self.update_campaign_health(campaign, 'DOMAIN_NOT_FOUND')
            return 'DOMAIN_NOT_FOUND'

        # Step 2: Check delivery status via Brevo
        delivery_status = self.check_brevo_delivery(email, datetime.now())

        # Step 3: Log status
        self.log_email_status(email, company, campaign, delivery_status)

        # Step 4: Update campaign health
        self.update_campaign_health(campaign, delivery_status)

        # Step 5: Execute response action
        action = self.get_response_action(delivery_status, campaign)
        self.execute_response_action(action, campaign, email)

        # Step 6: Log action taken
        conn = sqlite3.connect(self.monitor_db)
        cursor = conn.cursor()
        cursor.execute("UPDATE email_status SET action_taken = ? WHERE email = ? AND campaign = ?",
                      (json.dumps(action), email, campaign))
        conn.commit()
        conn.close()

        self.logger.info(f"{email} monitoring complete: {delivery_status} -> {action['action']}")

        return delivery_status

def main():
    import sys

    if len(sys.argv) < 4:
        print("Usage: python3 email_monitor_responses.py <email> <company> <campaign>")
        sys.exit(1)

    monitor = EmailMonitoringSystem()

    email = sys.argv[1]
    company = sys.argv[2]
    campaign = sys.argv[3]

    status = monitor.monitor_email_after_send(email, company, campaign)
    print(f"Final status: {status}")

if __name__ == "__main__":
    main()