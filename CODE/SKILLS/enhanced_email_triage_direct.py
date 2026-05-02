#!/usr/bin/env python3
"""
Enhanced Email Triage - Direct Integration Version

This script directly processes emails using your existing infrastructure
without requiring the API server. It's the most robust solution for
handling high-volume email responses.

Usage:
    python3 enhanced_email_triage_direct.py --process-all
    python3 enhanced_email_triage_direct.py --single-email test@example.com "Subject" "Body content"
"""

import imaplib
import email
import email.header
import json
import logging
import sqlite3
import argparse
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Configuration
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")
STATE_DIR = Path("/opt/ACTIVE/INFRA/GOVERNOR")
TRIAGE_DB = STATE_DIR / "email_triage_direct.db"
LM_STUDIO_API = "http://localhost:1234/v1/chat/completions"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "email_triage_direct.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class EmailData:
    message_id: str
    account_email: str
    from_addr: str
    subject: str
    body: str
    date: datetime
    attachments: List[str]

class DirectEmailTriage:
    def __init__(self):
        self.db_path = TRIAGE_DB
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                message_id TEXT PRIMARY KEY,
                account_email TEXT,
                from_addr TEXT,
                subject TEXT,
                body_preview TEXT,
                category TEXT,
                priority TEXT,
                confidence REAL,
                processed_at TIMESTAMP,
                recommendations TEXT,
                folder TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_stats (
                date DATE PRIMARY KEY,
                total_processed INTEGER,
                urgent_count INTEGER,
                high_count INTEGER,
                medium_count INTEGER,
                low_count INTEGER,
                auto_reply_count INTEGER,
                spam_count INTEGER,
                bounce_count INTEGER,
                avg_response_time REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def classify_with_lm_studio(self, email_data: EmailData) -> Tuple[str, str, float, str]:
        """
        Direct classification using LM Studio API.
        
        Returns: (category, priority, confidence, reasoning)
        """
        # Create prompt for classification
        prompt = f"""
        Classify this recruitment business email:
        
        From: {email_data.from_addr}
        Subject: {email_data.subject}
        Body: {email_data.body[:500]}
        
        Categories: application, inquiry, partnership, complaint, feedback, unsubscribe, autoreply, bounce, spam, unknown
        Priorities: urgent, high, medium, low, auto_reply, spam, bounce
        
        Respond with JSON only: {{"category": "...", "priority": "...", "reasoning": "..."}}
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use shorter timeout for faster processing
                response = requests.post(
                    LM_STUDIO_API,
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": "lfm2.5-1.2b-instruct",  # Use faster model
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                        "temperature": 0.3
                    },
                    timeout=10  # 10 second timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Parse JSON response
                    try:
                        json_result = json.loads(content.strip())
                        category = json_result.get('category', 'unknown')
                        priority = json_result.get('priority', 'medium')
                        reasoning = json_result.get('reasoning', '')
                        confidence = 0.8  # Default confidence
                        
                        logger.info(f"LM Studio classified: {category}/{priority}")
                        return category, priority, confidence, reasoning
                        
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON: {content}")
                        if attempt == max_retries - 1:
                            return self.rule_based_fallback(email_data)
                        continue
                        
                else:
                    logger.warning(f"LM Studio error: {response.status_code}")
                    if attempt == max_retries - 1:
                        return self.rule_based_fallback(email_data)
                    time.sleep(1)  # Wait before retry
                    
            except requests.exceptions.Timeout:
                logger.warning(f"LM Studio timeout (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return self.rule_based_fallback(email_data)
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"LM Studio error: {e}")
                if attempt == max_retries - 1:
                    return self.rule_based_fallback(email_data)
                time.sleep(1)
        
        return self.rule_based_fallback(email_data)
    
    def rule_based_fallback(self, email_data: EmailData) -> Tuple[str, str, float, str]:
        """Fallback rule-based classification."""
        text = f"{email_data.subject} {email_data.body}".lower()
        
        # Bounce detection
        bounce_patterns = [
            'delivery failed', 'undeliverable', 'mailbox full', 'does not exist',
            'address rejected', 'mailer-daemon', 'mail delivery subsystem'
        ]
        if any(pattern in text for pattern in bounce_patterns):
            return 'bounce', 'bounce', 0.95, 'Rule-based: Bounce detected'
        
        # Auto-reply detection
        auto_reply_patterns = [
            'out of office', 'automatic reply', 'auto-reply', 'vacation reply',
            'away from office', 'autoresponder'
        ]
        if any(pattern in text for pattern in auto_reply_patterns):
            return 'autoreply', 'auto_reply', 0.90, 'Rule-based: Auto-reply detected'
        
        # Spam detection
        spam_patterns = [
            'unsubscribe', 'click here', 'limited time', 'act now', 'free money',
            'winner', 'lottery', 'prince', 'inheritance', 'viagra', 'casino'
        ]
        if any(pattern in text for pattern in spam_patterns):
            return 'spam', 'spam', 0.85, 'Rule-based: Spam detected'
        
        # Application detection
        app_patterns = [
            'cv attached', 'resume', 'curriculum vitae', 'apply for', 'application for',
            'job application', 'looking for work', 'available for work'
        ]
        if any(pattern in text for pattern in app_patterns):
            return 'application', 'high', 0.80, 'Rule-based: Application detected'
        
        # Partnership detection
        partnership_patterns = [
            'cooperation', 'partnership', 'business proposal', 'collaboration',
            'interested in', 'how many workers', 'pricing', 'quotation'
        ]
        if any(pattern in text for pattern in partnership_patterns):
            return 'partnership', 'medium', 0.75, 'Rule-based: Partnership detected'
        
        # Complaint detection
        complaint_patterns = [
            'complaint', 'problem', 'issue', 'not happy', 'dissatisfied'
        ]
        if any(pattern in text for pattern in complaint_patterns):
            return 'complaint', 'urgent', 0.80, 'Rule-based: Complaint detected'
        
        # Default fallback
        return 'unknown', 'medium', 0.50, 'Rule-based: Default classification'
    
    def generate_recommendations(self, category: str, priority: str, email_data: EmailData) -> Dict[str, Any]:
        """Generate response recommendations."""
        recommendations = {
            "should_respond": True,
            "response_timeframe": "24h",
            "template": None,
            "escalation_needed": False
        }
        
        if category in ['spam', 'bounce', 'autoreply']:
            recommendations['should_respond'] = False
            recommendations['response_timeframe'] = "never"
        
        elif priority == 'urgent':
            recommendations['response_timeframe'] = "2h"
            recommendations['escalation_needed'] = True
        
        elif priority == 'high':
            recommendations['response_timeframe'] = "4h"
        
        elif priority == 'medium':
            recommendations['response_timeframe'] = "24h"
        
        else:  # low or unknown
            recommendations['response_timeframe'] = "7d"
        
        # Set template based on category
        if category == 'application':
            recommendations['template'] = "job_application_acknowledgment"
        elif category == 'inquiry':
            recommendations['template'] = "information_request"
        elif category == 'partnership':
            recommendations['template'] = "partnership_interest"
        elif category == 'complaint':
            recommendations['template'] = "complaint_acknowledgment"
        
        return recommendations
    
    def store_result(self, email_data: EmailData, category: str, priority: str, 
                    confidence: float, reasoning: str, recommendations: Dict[str, Any]):
        """Store classification result in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO emails 
                (message_id, account_email, from_addr, subject, body_preview, 
                 category, priority, confidence, processed_at, recommendations, folder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                email_data.message_id,
                email_data.account_email,
                email_data.from_addr,
                email_data.subject,
                email_data.body[:200],  # Preview only
                category,
                priority,
                confidence,
                datetime.now(),
                json.dumps(recommendations),
                "INBOX"
            ))
            conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
        finally:
            conn.close()
    
    def process_single_email(self, email_data: EmailData) -> Dict[str, Any]:
        """Process a single email."""
        logger.info(f"Processing email from {email_data.from_addr}: {email_data.subject}")
        
        # Classify email
        category, priority, confidence, reasoning = self.classify_with_lm_studio(email_data)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(category, priority, email_data)
        
        # Store result
        self.store_result(email_data, category, priority, confidence, reasoning, recommendations)
        
        result = {
            "message_id": email_data.message_id,
            "from": email_data.from_addr,
            "subject": email_data.subject,
            "category": category,
            "priority": priority,
            "confidence": confidence,
            "reasoning": reasoning,
            "recommendations": recommendations,
            "processed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Classified: {category}/{priority} (confidence: {confidence:.2f})")
        return result
    
    def parse_email_from_imap(self, imap_conn, email_id: bytes, account_email: str) -> Optional[EmailData]:
        """Parse email from IMAP connection."""
        try:
            status, msg_data = imap_conn.fetch(email_id, '(RFC822)')
            if status != "OK":
                return None
            
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Extract basic info
            subject = email.header.decode_header(email_message["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode('utf-8', errors='ignore')
            
            from_addr = email_message["From"]
            message_id = email_message.get("Message-ID", f"unknown_{datetime.now().timestamp()}")
            
            # Extract body
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            return EmailData(
                message_id=message_id,
                account_email=account_email,
                from_addr=from_addr,
                subject=subject,
                body=body,
                date=datetime.now(),
                attachments=[]
            )
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    def process_account(self, account_config: Dict[str, Any], days: int = 7) -> Dict[str, int]:
        """Process all emails in one account."""
        stats = {
            "total": 0, "urgent": 0, "high": 0, "medium": 0, "low": 0,
            "auto_reply": 0, "spam": 0, "bounce": 0, "errors": 0
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
            
            # Get recent emails
            since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            status, email_ids = imap.search(None, f'(SINCE "{since_date}" UNSEEN)')
            
            if status == "OK":
                email_ids = email_ids[0].split()
                logger.info(f"Found {len(email_ids)} unread emails in {account_config['email']}")
                
                for email_id in email_ids:
                    try:
                        email_data = self.parse_email_from_imap(imap, email_id, account_config['email'])
                        if email_data:
                            result = self.process_single_email(email_data)
                            
                            # Update stats
                            priority = result['priority']
                            if priority in stats:
                                stats[priority] += 1
                            stats['total'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing email {email_id}: {e}")
                        stats['errors'] += 1
            
            imap.logout()
            
        except Exception as e:
            logger.error(f"Error processing account {account_config['email']}: {e}")
            stats['errors'] += 1
        
        return stats
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processed emails."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        cursor.execute('''
            SELECT category, priority, COUNT(*) as count
            FROM emails 
            WHERE processed_at >= ?
            GROUP BY category, priority
            ORDER BY count DESC
        ''', (seven_days_ago,))
        
        results = cursor.fetchall()
        conn.close()
        
        return {
            "period": "Last 7 days",
            "categories_priorities": [
                {"category": row[0], "priority": row[1], "count": row[2]}
                for row in results
            ]
        }

def main():
    parser = argparse.ArgumentParser(description="Direct Email Triage Processing")
    parser.add_argument("--process-all", action="store_true", help="Process all configured accounts")
    parser.add_argument("--summary", action="store_true", help="Show processing summary")
    parser.add_argument("--single-email", nargs=3, metavar=('FROM', 'SUBJECT', 'BODY'), 
                       help="Process a single email for testing")
    
    args = parser.parse_args()
    
    triage = DirectEmailTriage()
    
    if args.summary:
        summary = triage.get_processing_summary()
        print("Processing Summary:")
        print(json.dumps(summary, indent=2))
    
    elif args.single_email:
        email_data = EmailData(
            message_id="test",
            account_email="test@example.com",
            from_addr=args.single_email[0],
            subject=args.single_email[1],
            body=args.single_email[2],
            date=datetime.now(),
            attachments=[]
        )
        result = triage.process_single_email(email_data)
        print("Classification Result:")
        print(json.dumps(result, indent=2))
    
    elif args.process_all:
        # This would load your account configurations
        # For now, it's a placeholder
        print("Processing all accounts (placeholder - would load your 30 email accounts)")
        print("Run with --single-email to test with a sample email")
    
    else:
        print("Use --help for usage options")
        print("Examples:")
        print("  python3 enhanced_email_triage_direct.py --single-email test@example.com 'Job Application' 'I want to apply'")
        print("  python3 enhanced_email_triage_direct.py --summary")

if __name__ == "__main__":
    main()