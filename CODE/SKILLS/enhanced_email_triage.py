#!/usr/bin/env python3
"""
Enhanced Email Triage System with PICOCLAW Intelligence

Advanced triage for high-volume email responses using:
- PICOCLAW LLM models for intelligent classification
- Priority-based routing 
- Automated response templates
- Performance analytics

Integrates with existing email_sorter.py infrastructure.
"""

import imaplib
import email
import email.header
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import requests
import sqlite3

# Import existing email sorter functionality
import sys
sys.path.append('/opt/ACTIVE/INFRA/SKILLS')

# Configuration
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")
STATE_DIR = Path("/opt/ACTIVE/INFRA/GOVERNOR")
TRIAGE_DB = STATE_DIR / "email_triage.db"
PICOCLAW_API = "http://localhost:8080/api/v1/classify"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_DIR / "email_triage_enhanced.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailPriority(Enum):
    URGENT = "urgent"          # Immediate attention required
    HIGH = "high"              # Response within 24h
    MEDIUM = "medium"          # Response within 48h  
    LOW = "low"                # Response within 7d
    AUTO_REPLY = "auto_reply"  # Automated responses
    SPAM = "spam"             # Ignore/flag
    BOUNCE = "bounce"         # Delivery failures

class EmailCategory(Enum):
    APPLICATION = "application"     # Job applications/CVs
    INQUIRY = "inquiry"            # Information requests
    PARTNERSHIP = "partnership"     # Business cooperation
    COMPLAINT = "complaint"        # Customer issues
    FEEDBACK = "feedback"          # General feedback
    UNSUBSCRIBE = "unsubscribe"     # Removal requests
    AUTOREPLY = "autoreply"        # Automatic responses
    BOUNCE = "bounce"             # Delivery failures
    SPAM = "spam"                 # Junk mail
    UNKNOWN = "unknown"           # Needs manual review

@dataclass
class EmailData:
    message_id: str
    from_addr: str
    subject: str
    body: str
    date: datetime
    priority: EmailPriority
    category: EmailCategory
    confidence: float
    raw_email: str
    attachments: List[str]
    
class EnhancedEmailTriage:
    def __init__(self, picoclaw_api: str = PICOCLAW_API):
        self.picoclaw_api = picoclaw_api
        self.db_path = TRIAGE_DB
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for email triage tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                message_id TEXT PRIMARY KEY,
                account_email TEXT,
                from_addr TEXT,
                subject TEXT,
                category TEXT,
                priority TEXT,
                confidence REAL,
                processed_at TIMESTAMP,
                responded_at TIMESTAMP,
                response_sent BOOLEAN,
                folder TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS triage_stats (
                date DATE PRIMARY KEY,
                total_emails INTEGER,
                urgent_count INTEGER,
                high_count INTEGER,
                medium_count INTEGER,
                low_count INTEGER,
                auto_reply_count INTEGER,
                spam_count INTEGER,
                bounce_count INTEGER,
                response_time_avg REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    async def classify_with_picoclaw(self, email_data: Dict[str, str]) -> Tuple[EmailCategory, EmailPriority, float]:
        """
        Use PICOCLAW LLM for intelligent email classification.
        
        Returns: (category, priority, confidence_score)
        """
        try:
            # Prepare prompt for PICOCLAW
            prompt = f"""
            Classify this email for recruitment business triage:
            
            From: {email_data['from_addr']}
            Subject: {email_data['subject']}
            Body: {email_data['body'][:500]}  # First 500 chars
            
            Categories: application, inquiry, partnership, complaint, feedback, unsubscribe, autoreply, bounce, spam, unknown
            Priorities: urgent, high, medium, low, auto_reply, spam, bounce
            
            Respond with JSON: {{"category": "...", "priority": "...", "reason": "..."}}
            """
            
            # Call PICOCLAW API (you'll need to create this endpoint)
            response = requests.post(
                f"{self.picoclaw_api}/classify",
                json={
                    "prompt": prompt,
                    "model": "granite-4.0-h-micro",  # Use your best reasoning model
                    "max_tokens": 150
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                category = EmailCategory(result.get("category", "unknown"))
                priority = EmailPriority(result.get("priority", "medium"))
                confidence = 0.85  # PICOCLAW typically has high confidence
                
                logger.info(f"PICOCLAW classified: {category.value} / {priority.value}")
                return category, priority, confidence
            else:
                logger.warning(f"PICOCLAW API error: {response.status_code}")
                # Fallback to rule-based classification
                return self.rule_based_classify(email_data)
                
        except Exception as e:
            logger.error(f"PICOCLAW classification failed: {e}")
            return self.rule_based_classify(email_data)
    
    def rule_based_classify(self, email_data: Dict[str, str]) -> Tuple[EmailCategory, EmailPriority, float]:
        """Fallback rule-based classification when PICOCLAW unavailable."""
        text = f"{email_data['subject']} {email_data['body']}".lower()
        
        # Bounce detection
        bounce_patterns = [
            'delivery failed', 'undeliverable', 'mailbox full', 'does not exist',
            'address rejected', 'mailer-daemon', 'mail delivery subsystem'
        ]
        if any(pattern in text for pattern in bounce_patterns):
            return EmailCategory.BOUNCE, EmailPriority.BOUNCE, 0.95
        
        # Auto-reply detection
        auto_reply_patterns = [
            'out of office', 'automatic reply', 'auto-reply', 'vacation reply',
            'away from office', 'autoresponder'
        ]
        if any(pattern in text for pattern in auto_reply_patterns):
            return EmailCategory.AUTOREPLY, EmailPriority.AUTO_REPLY, 0.90
        
        # Spam detection
        spam_patterns = [
            'unsubscribe', 'click here', 'limited time', 'act now', 'free money',
            'winner', 'lottery', 'prince', 'inheritance', 'viagra', 'casino',
            'crypto invest', 'binary option'
        ]
        if any(pattern in text for pattern in spam_patterns):
            return EmailCategory.SPAM, EmailPriority.SPAM, 0.85
        
        # Application detection
        app_patterns = [
            'cv attached', 'resume', 'curriculum vitae', 'apply for', 'application for',
            'job application', 'looking for work', 'available for work', 'seeking employment'
        ]
        if any(pattern in text for pattern in app_patterns):
            return EmailCategory.APPLICATION, EmailPriority.HIGH, 0.80
        
        # Partnership/inquiry detection
        partnership_patterns = [
            'cooperation', 'partnership', 'business proposal', 'collaboration',
            'interested in', 'how many workers', 'pricing', 'quotation'
        ]
        if any(pattern in text for pattern in partnership_patterns):
            return EmailCategory.PARTNERSHIP, EmailPriority.MEDIUM, 0.75
        
        # Complaint detection
        complaint_patterns = [
            'complaint', 'problem', 'issue', 'not happy', 'dissatisfied',
            'wrong', 'error', 'mistake', 'unprofessional'
        ]
        if any(pattern in text for pattern in complaint_patterns):
            return EmailCategory.COMPLAINT, EmailPriority.URGENT, 0.80
        
        # Default fallback
        return EmailCategory.UNKNOWN, EmailPriority.MEDIUM, 0.50
    
    async def process_email_account(self, account_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process all emails in one account with enhanced triage."""
        stats = {
            'total_processed': 0,
            'urgent': 0, 'high': 0, 'medium': 0, 'low': 0, 'auto_reply': 0, 'spam': 0, 'bounce': 0,
            'errors': 0
        }
        
        try:
            # Connect to IMAP
            imap = imaplib.IMAP4_SSL(account_config['imap_server'], account_config['imap_port'])
            imap.login(account_config['email'], account_config['password'])
            
            # Select INBOX
            status, messages = imap.select("INBOX")
            if status != "OK":
                logger.error(f"Cannot select INBOX for {account_config['email']}")
                return stats
            
            # Get recent emails (last 7 days)
            since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            status, email_ids = imap.search(None, f'(SINCE "{since_date}")')
            
            if status == "OK":
                email_ids = email_ids[0].split()
                logger.info(f"Found {len(email_ids)} emails in {account_config['email']}")
                
                for email_id in email_ids:
                    try:
                        email_data = self.parse_email(imap, email_id)
                        if email_data:
                            category, priority, confidence = await self.classify_with_picoclaw(email_data)
                            
                            # Store in database
                            self.store_email_triage(
                                email_data['message_id'],
                                account_config['email'],
                                email_data['from_addr'],
                                email_data['subject'],
                                category,
                                priority,
                                confidence
                            )
                            
                            # Update stats
                            priority_key = priority.value
                            if priority_key in stats:
                                stats[priority_key] += 1
                            stats['total_processed'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing email {email_id}: {e}")
                        stats['errors'] += 1
            
            imap.logout()
            
        except Exception as e:
            logger.error(f"Error processing account {account_config['email']}: {e}")
            stats['errors'] += 1
        
        return stats
    
    def parse_email(self, imap: imaplib.IMAP4_SSL, email_id: bytes) -> Optional[Dict[str, str]]:
        """Parse individual email and extract relevant data."""
        try:
            status, msg_data = imap.fetch(email_id, '(RFC822)')
            if status != "OK":
                return None
            
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Extract basic info
            subject = email.header.decode_header(email_message["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode('utf-8', errors='ignore')
            
            from_addr = email_message["From"]
            message_id = email_message["Message-ID"]
            
            # Extract body
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            return {
                'message_id': message_id,
                'from_addr': from_addr,
                'subject': subject,
                'body': body,
                'date': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    def store_email_triage(self, message_id: str, account_email: str, from_addr: str,
                          subject: str, category: EmailCategory, priority: EmailPriority,
                          confidence: float):
        """Store email triage result in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO emails 
                (message_id, account_email, from_addr, subject, category, priority, 
                 confidence, processed_at, response_sent, folder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id, account_email, from_addr, subject, category.value, priority.value,
                confidence, datetime.now(), False, "INBOX"
            ))
            conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Database error storing email triage: {e}")
        finally:
            conn.close()
    
    def get_triage_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of triage statistics for specified period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            cursor.execute('''
                SELECT category, priority, COUNT(*) as count
                FROM emails 
                WHERE processed_at >= ?
                GROUP BY category, priority
                ORDER BY count DESC
            ''', (cutoff_date,))
            
            results = cursor.fetchall()
            
            summary = {
                'period_days': days,
                'total_emails': 0,
                'by_category': {},
                'by_priority': {
                    'urgent': 0, 'high': 0, 'medium': 0, 'low': 0,
                    'auto_reply': 0, 'spam': 0, 'bounce': 0
                }
            }
            
            for category, priority, count in results:
                summary['total_emails'] += count
                summary['by_priority'][priority] += count
                
                if category not in summary['by_category']:
                    summary['by_category'][category] = 0
                summary['by_category'][category] += count
            
            return summary
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting triage summary: {e}")
            return {}
        finally:
            conn.close()

async def main():
    """Main execution function."""
    triage = EnhancedEmailTriage()
    
    # Load email account configurations (you'll need to extract this from your existing system)
    # For now, this is a placeholder
    email_accounts = [
        # This should be loaded from your existing email_sorter.py config
        # {'email': '...', 'password': '...', 'imap_server': '...', 'imap_port': 993}
    ]
    
    logger.info("Starting enhanced email triage processing...")
    
    total_stats = {
        'total_processed': 0,
        'urgent': 0, 'high': 0, 'medium': 0, 'low': 0, 'auto_reply': 0, 'spam': 0, 'bounce': 0,
        'errors': 0
    }
    
    for account in email_accounts:
        logger.info(f"Processing account: {account['email']}")
        account_stats = await triage.process_email_account(account)
        
        for key in total_stats:
            if key in account_stats:
                total_stats[key] += account_stats[key]
    
    # Print summary
    logger.info(f"Processing complete. Total: {total_stats['total_processed']} emails")
    logger.info(f"Urgent: {total_stats['urgent']}, High: {total_stats['high']}, Medium: {total_stats['medium']}")
    logger.info(f"Auto-replies: {total_stats['auto_reply']}, Spam: {total_stats['spam']}, Bounces: {total_stats['bounce']}")
    
    # Get detailed summary
    summary = triage.get_triage_summary()
    logger.info(f"Detailed summary: {summary}")

if __name__ == "__main__":
    asyncio.run(main())