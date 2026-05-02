#!/usr/bin/env python3
"""
Reply Classifier Service - Continuous LLM-powered email classification

Runs every 5 minutes to classify new email replies using local LLM.
Zero Claude tokens - all processing on raspibig.

Features:
- Classifies replies: interested, not_interested, question, auto_reply, bounce
- Sends Telegram alerts for interested leads
- Adds unsubscribes to DNC automatically
- Tracks classification statistics

Part of InterJob Token Optimization - saves 100% tokens on classification.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add paths
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS')

from smart_router import SmartRouter, classify, route_query
from alerting import send_telegram

# Config
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")
STATE_FILE = Path("/opt/ACTIVE/INFRA/GOVERNOR/reply_classifier_state.json")
STATS_FILE = Path("/opt/ACTIVE/INFRA/GOVERNOR/reply_classifier_stats.json")

# Interval
CHECK_INTERVAL = 300  # 5 minutes


class ReplyClassifierService:
    """Continuous reply classification using local LLM"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.router = SmartRouter()
        self.stats = self._load_stats()
        self.running = True

    def _setup_logging(self) -> logging.Logger:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("reply_classifier")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            fh = logging.FileHandler(LOG_DIR / "reply_classifier.log")
            fh.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(fh)

            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter('[REPLY_CLASSIFIER] %(message)s'))
            ch.setLevel(logging.INFO)
            logger.addHandler(ch)

        return logger

    def _load_stats(self) -> dict:
        """Load classification statistics"""
        if STATS_FILE.exists():
            try:
                return json.loads(STATS_FILE.read_text())
            except:
                pass
        return {
            "total_classified": 0,
            "interested": 0,
            "not_interested": 0,
            "question": 0,
            "auto_reply": 0,
            "bounce": 0,
            "other": 0,
            "llm_calls": 0,
            "rule_matches": 0,
            "last_run": None
        }

    def _save_stats(self):
        """Save classification statistics"""
        self.stats["last_run"] = datetime.now().isoformat()
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(self.stats, indent=2))

    def classify_email(self, subject: str, body: str) -> dict:
        """Classify a single email using local LLM"""
        text = f"{subject}\n{body}"

        # Use smart_router (tries rules first, then local LLM)
        result = classify(text)

        intent = result.get('intent', 'other')
        confidence = result.get('confidence', 0)

        # Track stats
        self.stats["total_classified"] += 1
        if intent in self.stats:
            self.stats[intent] += 1
        else:
            self.stats["other"] += 1

        # Check if LLM was used or rules
        if 'raw' not in result and confidence > 0:
            self.stats["llm_calls"] += 1
        else:
            self.stats["rule_matches"] += 1

        return {
            "intent": intent,
            "confidence": confidence,
            "action": self._get_action(intent)
        }

    def _get_action(self, intent: str) -> str:
        """Get recommended action for intent"""
        actions = {
            "interested": "FOLLOW_UP",
            "not_interested": "ADD_DNC",
            "unsubscribe": "ADD_DNC",
            "question": "RESPOND",
            "auto_reply": "IGNORE",
            "bounce": "CHECK_EMAIL",
            "other": "REVIEW"
        }
        return actions.get(intent, "REVIEW")

    def process_new_replies(self):
        """Process new replies from all mailboxes"""
        try:
            # Import reply_detector functions
            from reply_detector import scan_all_mailboxes

            self.logger.info("Starting reply scan...")
            stats = scan_all_mailboxes(days=1, delete_negative=False, delete_bounces=False)

            # Log results
            positive = stats.get('positive', 0)
            negative = stats.get('negative', 0)
            bounces = stats.get('bounces', 0)

            self.logger.info(f"Processed: +{positive} -{negative} bounces:{bounces}")

            # Alert on positive leads
            if positive > 0:
                send_telegram(f"📧 {positive} interested replies detected!\nCheck mailboxes for follow-up.")

            self._save_stats()
            return stats

        except Exception as e:
            self.logger.error(f"Error processing replies: {e}")
            return {}

    def run_once(self):
        """Run a single classification cycle"""
        self.logger.info("=" * 50)
        self.logger.info("REPLY CLASSIFIER - Single Run")
        self.logger.info("=" * 50)

        # Check if LLM is available
        available = self.router.discover_available()
        if 'local' not in available:
            self.logger.warning("Local LLM not available, using keywords only")

        stats = self.process_new_replies()

        self.logger.info(f"Classification stats: {self.stats['total_classified']} total")
        self.logger.info(f"  LLM calls: {self.stats['llm_calls']}")
        self.logger.info(f"  Rule matches: {self.stats['rule_matches']}")

        return stats

    def run_daemon(self, interval: int = CHECK_INTERVAL):
        """Run as daemon, processing replies every interval"""
        self.logger.info("=" * 50)
        self.logger.info("REPLY CLASSIFIER SERVICE STARTING")
        self.logger.info(f"Interval: {interval}s")
        self.logger.info("=" * 50)

        while self.running:
            try:
                self.process_new_replies()

                # Log stats every hour
                if datetime.now().minute == 0:
                    self.logger.info(f"Hourly stats: {self.stats}")

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")

            time.sleep(interval)

        self.logger.info("Reply classifier shutdown")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Reply Classifier Service')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--interval', type=int, default=300, help='Check interval (seconds)')
    parser.add_argument('--stats', action='store_true', help='Show classification stats')
    parser.add_argument('--test', metavar='TEXT', help='Test classification on text')
    args = parser.parse_args()

    service = ReplyClassifierService()

    if args.stats:
        print(json.dumps(service.stats, indent=2))
        return 0

    if args.test:
        result = service.classify_email("Test Subject", args.test)
        print(json.dumps(result, indent=2))
        return 0

    if args.once:
        service.run_once()
        return 0

    if args.daemon:
        service.run_daemon(args.interval)
        return 0

    # Default: show status
    print("Reply Classifier Service")
    print("=" * 40)
    print(f"LLM endpoints: {service.router.discover_available()}")
    print(f"Total classified: {service.stats['total_classified']}")
    print(f"LLM calls: {service.stats['llm_calls']}")
    print(f"Rule matches: {service.stats['rule_matches']}")
    print(f"Last run: {service.stats['last_run']}")


if __name__ == '__main__':
    sys.exit(main() or 0)
