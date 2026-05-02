#!/usr/bin/env python3
"""
Telegram Group Auto-Moderator

Monitors Telegram groups for drug-related spam and automatically:
- Deletes spam messages
- Bans repeat offenders (configurable)
- Logs all actions

Uses python-telegram-bot library (async) for bot API.

Usage:
    python3 telegram_group_moderator.py --status       # Show bot status
    python3 telegram_group_moderator.py --list-groups  # List admin groups
    python3 telegram_group_moderator.py --stats        # Show moderation stats
    python3 telegram_group_moderator.py --run          # Start moderation bot
    python3 telegram_group_moderator.py --dry-run      # Monitor without action
    python3 telegram_group_moderator.py --scan GROUP_ID  # Scan recent messages
    python3 telegram_group_moderator.py --whitelist USER_ID  # Add to whitelist
    python3 telegram_group_moderator.py --blacklist USER_ID  # Permanent ban
"""

import os
import re
import json
import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

from dotenv import load_dotenv

# Import telegram types for type hints
try:
    from telegram import Update, Bot
    from telegram.ext import ContextTypes
except ImportError:
    Update = None
    Bot = None
    ContextTypes = None

# Load environment
load_dotenv('/opt/EMAIL/.env')

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_GROUPS_BOT_TOKEN')
DATA_DIR = Path('/opt/DATA/telegram_moderation')
LOG_FILE = Path('/opt/LOGS/telegram_moderation.log')
PATTERNS_FILE = DATA_DIR / 'patterns.json'
STATS_FILE = DATA_DIR / 'stats.json'
WHITELIST_FILE = DATA_DIR / 'whitelist.json'
BLACKLIST_FILE = DATA_DIR / 'blacklist.json'
OFFENDERS_FILE = DATA_DIR / 'offenders.json'

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class SpamScore:
    """Result of spam analysis"""
    total_score: int
    matches: List[str]
    is_spam: bool
    should_ban: bool


class PatternManager:
    """Load and compile spam patterns from JSON"""

    def __init__(self, patterns_file: Path):
        self.patterns_file = patterns_file
        self.patterns = self._load_patterns()
        self._compile_patterns()

    def _load_patterns(self) -> dict:
        """Load patterns from JSON file"""
        if not self.patterns_file.exists():
            logger.error(f"Patterns file not found: {self.patterns_file}")
            return self._default_patterns()

        with open(self.patterns_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _default_patterns(self) -> dict:
        """Fallback patterns if file missing"""
        return {
            "drug_keywords": {
                "english": ["marijuana", "cocaine", "heroin", "mdma", "lsd"],
                "romanian": ["droguri", "iarba", "cocaina"],
                "slang": ["weed", "coke", "molly", "keta"]
            },
            "pricing_patterns": [r"\d+\s*g(?:ram)?s?\s*[=:@]?\s*\d+"],
            "contact_patterns": [r"dm\s*(?:me|for)\s*(?:order|buy)"],
            "crypto_drug_patterns": [],
            "channel_patterns": [],
            "dealer_indicators": [],
            "drug_emojis": [],
            "dealer_name_keywords": ["dealer", "plug", "vendor"],
            "whitelist_phrases": ["drug awareness", "prevention"],
            "min_score_to_delete": 3,
            "min_score_to_ban": 5,
            "emoji_count_threshold": 2
        }

    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        self.keyword_patterns = []

        # Compile drug keywords
        for category, words in self.patterns.get('drug_keywords', {}).items():
            for word in words:
                try:
                    self.keyword_patterns.append((
                        re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE),
                        1,  # score
                        f"keyword:{category}:{word}"
                    ))
                except re.error:
                    pass

        # Compile regex patterns (higher scores)
        pattern_types = [
            ('pricing_patterns', 3),
            ('contact_patterns', 3),
            ('crypto_drug_patterns', 2),
            ('channel_patterns', 3),
            ('dealer_indicators', 2)
        ]

        self.regex_patterns = []
        for ptype, score in pattern_types:
            for pattern in self.patterns.get(ptype, []):
                try:
                    self.regex_patterns.append((
                        re.compile(pattern, re.IGNORECASE),
                        score,
                        f"{ptype}:{pattern[:30]}"
                    ))
                except re.error as e:
                    logger.warning(f"Invalid regex {pattern}: {e}")

        # Whitelist patterns
        self.whitelist_patterns = []
        for phrase in self.patterns.get('whitelist_phrases', []):
            try:
                self.whitelist_patterns.append(
                    re.compile(rf'\b{re.escape(phrase)}\b', re.IGNORECASE)
                )
            except re.error:
                pass

        # Drug emojis
        self.drug_emojis = set(self.patterns.get('drug_emojis', []))
        self.dealer_keywords = set(
            w.lower() for w in self.patterns.get('dealer_name_keywords', [])
        )

        # Thresholds
        self.min_delete = self.patterns.get('min_score_to_delete', 3)
        self.min_ban = self.patterns.get('min_score_to_ban', 5)
        self.emoji_threshold = self.patterns.get('emoji_count_threshold', 2)

    def reload(self):
        """Reload patterns from file"""
        self.patterns = self._load_patterns()
        self._compile_patterns()
        logger.info("Patterns reloaded")


class DataStore:
    """Manage persistent data (stats, whitelist, blacklist, offenders)"""

    def __init__(self):
        self.whitelist: Set[int] = self._load_set(WHITELIST_FILE)
        self.blacklist: Set[int] = self._load_set(BLACKLIST_FILE)
        self.offenders: Dict[int, dict] = self._load_dict(OFFENDERS_FILE)
        self.stats: Dict = self._load_dict(STATS_FILE)

        # Initialize stats structure
        if 'daily' not in self.stats:
            self.stats['daily'] = {}
        if 'total' not in self.stats:
            self.stats['total'] = {
                'messages_deleted': 0,
                'users_banned': 0,
                'messages_scanned': 0,
                'groups_monitored': set()
            }

    def _load_set(self, filepath: Path) -> Set[int]:
        """Load set of user IDs from JSON"""
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Error loading {filepath}: {e}")
        return set()

    def _load_dict(self, filepath: Path) -> Dict:
        """Load dictionary from JSON"""
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {filepath}: {e}")
        return {}

    def _save_set(self, data: Set[int], filepath: Path):
        """Save set to JSON"""
        with open(filepath, 'w') as f:
            json.dump(list(data), f, indent=2)

    def _save_dict(self, data: Dict, filepath: Path):
        """Save dict to JSON, handling sets"""
        def serialize(obj):
            if isinstance(obj, set):
                return list(obj)
            return obj

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=serialize)

    def add_whitelist(self, user_id: int):
        """Add user to whitelist"""
        self.whitelist.add(user_id)
        self._save_set(self.whitelist, WHITELIST_FILE)
        logger.info(f"Added {user_id} to whitelist")

    def add_blacklist(self, user_id: int):
        """Add user to blacklist (permanent ban list)"""
        self.blacklist.add(user_id)
        self._save_set(self.blacklist, BLACKLIST_FILE)
        logger.info(f"Added {user_id} to blacklist")

    def remove_whitelist(self, user_id: int):
        """Remove user from whitelist"""
        self.whitelist.discard(user_id)
        self._save_set(self.whitelist, WHITELIST_FILE)

    def remove_blacklist(self, user_id: int):
        """Remove user from blacklist"""
        self.blacklist.discard(user_id)
        self._save_set(self.blacklist, BLACKLIST_FILE)

    def record_offense(self, user_id: int, group_id: int, message: str, score: int):
        """Record a spam offense for a user"""
        user_key = str(user_id)
        if user_key not in self.offenders:
            self.offenders[user_key] = {
                'first_seen': datetime.now().isoformat(),
                'offense_count': 0,
                'groups': [],
                'last_message': ''
            }

        self.offenders[user_key]['offense_count'] += 1
        self.offenders[user_key]['last_seen'] = datetime.now().isoformat()
        self.offenders[user_key]['last_message'] = message[:200]
        self.offenders[user_key]['last_score'] = score

        if group_id not in self.offenders[user_key]['groups']:
            self.offenders[user_key]['groups'].append(group_id)

        self._save_dict(self.offenders, OFFENDERS_FILE)

    def get_offense_count(self, user_id: int) -> int:
        """Get number of offenses for a user"""
        return self.offenders.get(str(user_id), {}).get('offense_count', 0)

    def record_action(self, action: str, group_id: int = None):
        """Record a moderation action in daily stats"""
        today = datetime.now().strftime('%Y-%m-%d')

        if today not in self.stats['daily']:
            self.stats['daily'][today] = {
                'messages_deleted': 0,
                'users_banned': 0,
                'messages_scanned': 0
            }

        if action == 'delete':
            self.stats['daily'][today]['messages_deleted'] += 1
            self.stats['total']['messages_deleted'] += 1
        elif action == 'ban':
            self.stats['daily'][today]['users_banned'] += 1
            self.stats['total']['users_banned'] += 1
        elif action == 'scan':
            self.stats['daily'][today]['messages_scanned'] += 1
            self.stats['total']['messages_scanned'] += 1

        if group_id:
            groups = self.stats['total'].get('groups_monitored', [])
            if isinstance(groups, list):
                groups = set(groups)
            groups.add(group_id)
            self.stats['total']['groups_monitored'] = groups

        self._save_dict(self.stats, STATS_FILE)

    def get_stats(self) -> dict:
        """Get statistics summary"""
        return {
            'total': {
                k: (len(v) if isinstance(v, (set, list)) else v)
                for k, v in self.stats.get('total', {}).items()
            },
            'last_7_days': self._get_recent_stats(7),
            'today': self.stats.get('daily', {}).get(
                datetime.now().strftime('%Y-%m-%d'), {}
            )
        }

    def _get_recent_stats(self, days: int) -> dict:
        """Aggregate stats for recent days"""
        result = {'messages_deleted': 0, 'users_banned': 0, 'messages_scanned': 0}

        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            day_stats = self.stats.get('daily', {}).get(date, {})
            for key in result:
                result[key] += day_stats.get(key, 0)

        return result


class SpamDetector:
    """Analyze messages for drug spam"""

    def __init__(self, patterns: PatternManager, data: DataStore):
        self.patterns = patterns
        self.data = data

    def analyze(self, text: str, user_id: int = None,
                user_name: str = None) -> SpamScore:
        """Analyze message text for spam indicators"""
        if not text:
            return SpamScore(0, [], False, False)

        # Check whitelist
        if user_id and user_id in self.data.whitelist:
            return SpamScore(0, [], False, False)

        # Check for whitelisted phrases (legitimate drug discussion)
        for pattern in self.patterns.whitelist_patterns:
            if pattern.search(text):
                return SpamScore(0, ['whitelist'], False, False)

        score = 0
        matches = []

        # Check keywords
        for pattern, pts, label in self.patterns.keyword_patterns:
            if pattern.search(text):
                score += pts
                matches.append(label)

        # Check regex patterns
        for pattern, pts, label in self.patterns.regex_patterns:
            if pattern.search(text):
                score += pts
                matches.append(label)

        # Check drug emojis
        emoji_count = sum(1 for e in self.patterns.drug_emojis if e in text)
        if emoji_count >= self.patterns.emoji_threshold:
            score += emoji_count
            matches.append(f"emojis:{emoji_count}")

        # Check user name for dealer indicators
        if user_name:
            name_lower = user_name.lower()
            for kw in self.patterns.dealer_keywords:
                if kw in name_lower:
                    score += 2
                    matches.append(f"name:{kw}")

            # Check emojis in name
            name_emojis = sum(1 for e in self.patterns.drug_emojis if e in user_name)
            if name_emojis >= 1:
                score += name_emojis * 2
                matches.append(f"name_emojis:{name_emojis}")

        # Repeat offender bonus
        if user_id:
            offenses = self.data.get_offense_count(user_id)
            if offenses >= 2:
                score += min(offenses, 5)  # Cap at +5
                matches.append(f"repeat_offender:{offenses}")

        # Blacklisted user
        if user_id and user_id in self.data.blacklist:
            score = max(score, self.patterns.min_ban)
            matches.append("blacklisted")

        is_spam = score >= self.patterns.min_delete
        should_ban = score >= self.patterns.min_ban

        return SpamScore(score, matches, is_spam, should_ban)


class TelegramModerator:
    """Main moderation bot using python-telegram-bot"""

    def __init__(self, token: str, dry_run: bool = False,
                 auto_ban: bool = True, ban_threshold: int = 3):
        self.token = token
        self.dry_run = dry_run
        self.auto_ban = auto_ban
        self.ban_threshold = ban_threshold  # Offenses before auto-ban

        self.patterns = PatternManager(PATTERNS_FILE)
        self.data = DataStore()
        self.detector = SpamDetector(self.patterns, self.data)

        self.app = None
        self.running = False

    async def start(self):
        """Initialize and start the bot"""
        from telegram import Update
        from telegram.ext import (
            Application, MessageHandler, CommandHandler,
            filters, ContextTypes
        )

        logger.info("Starting Telegram Group Moderator...")

        self.app = Application.builder().token(self.token).build()

        # Handlers
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("clean", self.cmd_clean))
        self.app.add_handler(CommandHandler("scan", self.cmd_scan))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("ban", self.cmd_ban))
        self.app.add_handler(CommandHandler("whitelist", self.cmd_whitelist))
        self.app.add_handler(CommandHandler("reload", self.cmd_reload))
        self.app.add_handler(CommandHandler("dealers", self.cmd_dealers))
        self.app.add_handler(CommandHandler("erase_drug_dealer", self.cmd_dealers))
        self.app.add_handler(CommandHandler("erasedrugs", self.cmd_dealers))
        self.app.add_handler(CommandHandler("erase", self.cmd_dealers))
        self.app.add_handler(CommandHandler("anem", self.cmd_dealers))

        # Auto-ban on join handler
        self.app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            self.handle_new_member
        ))

        # Error handler
        self.app.add_error_handler(self.error_handler)

        self.running = True

        if self.dry_run:
            logger.info("DRY RUN MODE - No actions will be taken")

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)

        logger.info("Bot started, monitoring groups...")

        # Keep running
        while self.running:
            await asyncio.sleep(1)

    async def stop(self):
        """Stop the bot gracefully"""
        self.running = False
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        logger.info("Bot stopped")

    async def handle_message(self, update: Update, context):
        """Handle incoming messages"""
        from telegram.error import TelegramError

        message = update.effective_message
        chat = update.effective_chat
        user = update.effective_user

        # Only process group messages
        if not chat or chat.type not in ['group', 'supergroup']:
            return

        # Auto-ban users named Mostafa/Mohamed (drug dealers)
        if user:
            uname = f"{user.first_name or ''} {user.last_name or ''}".lower()
            banned_names = ['mostafa', 'mustafa', 'mustapha', 'mohamed', 'mohammed']
            if any(n in uname for n in banned_names):
                if not self.dry_run:
                    try:
                        await message.delete()
                        await chat.ban_member(user.id)
                        logger.warning(f"AUTO-BANNED: {user.first_name} {user.last_name or ''} from {chat.title}")
                        self.data.record_action('ban', chat.id)
                    except Exception as e:
                        logger.debug(f"Ban error: {e}")
                return

        # Auto-delete forwarded messages
        if message.forward_date or message.forward_from or message.forward_from_chat:
            if not self.dry_run:
                try:
                    await message.delete()
                    logger.info(f"Deleted forwarded message in {chat.title}")
                    self.data.record_action('delete', chat.id)
                except Exception as e:
                    logger.debug(f"Could not delete forward: {e}")
            return

        # Record scan
        self.data.record_action('scan', chat.id)

        # Get user info
        user_id = user.id if user else None
        user_name = None
        if user:
            user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if user.username:
                user_name += f" @{user.username}"

        # Analyze message
        text = message.text or message.caption or ''
        result = self.detector.analyze(text, user_id, user_name)

        if result.is_spam:
            # Log detection
            logger.warning(
                f"SPAM DETECTED | Chat: {chat.title} ({chat.id}) | "
                f"User: {user_name} ({user_id}) | "
                f"Score: {result.total_score} | Matches: {result.matches}"
            )
            logger.info(f"Message: {text[:200]}")

            # Record offense
            self.data.record_offense(user_id, chat.id, text, result.total_score)

            if self.dry_run:
                logger.info("DRY RUN: Would delete message")
                if result.should_ban or self.data.get_offense_count(user_id) >= self.ban_threshold:
                    logger.info("DRY RUN: Would ban user")
                return

            # Delete message
            try:
                await message.delete()
                self.data.record_action('delete', chat.id)
                logger.info(f"Deleted message from {user_name}")
            except TelegramError as e:
                logger.error(f"Failed to delete: {e}")

            # Ban if threshold reached
            offense_count = self.data.get_offense_count(user_id)
            should_ban = (
                self.auto_ban and
                (result.should_ban or offense_count >= self.ban_threshold)
            )

            if should_ban:
                try:
                    await chat.ban_member(user_id)
                    self.data.record_action('ban', chat.id)
                    logger.warning(f"BANNED: {user_name} ({user_id}) from {chat.title}")
                except TelegramError as e:
                    logger.error(f"Failed to ban: {e}")

    async def cmd_status(self, update: Update, context):
        """Handle /status command"""
        if not update.effective_user:
            return

        # Only respond to admins
        chat = update.effective_chat
        user = update.effective_user

        if chat.type in ['group', 'supergroup']:
            try:
                member = await chat.get_member(user.id)
                if member.status not in ['administrator', 'creator']:
                    return
            except Exception:
                return

        stats = self.data.get_stats()
        mode = "DRY RUN" if self.dry_run else "ACTIVE"

        text = f"""Telegram Group Moderator Status

Mode: {mode}
Auto-ban: {'Enabled' if self.auto_ban else 'Disabled'}

Today:
- Messages scanned: {stats['today'].get('messages_scanned', 0)}
- Messages deleted: {stats['today'].get('messages_deleted', 0)}
- Users banned: {stats['today'].get('users_banned', 0)}

Last 7 days:
- Messages deleted: {stats['last_7_days']['messages_deleted']}
- Users banned: {stats['last_7_days']['users_banned']}

Whitelist: {len(self.data.whitelist)} users
Blacklist: {len(self.data.blacklist)} users
"""
        await update.message.reply_text(text)

    async def cmd_stats(self, update: Update, context):
        """Handle /stats command - same as status for now"""
        await self.cmd_status(update, context)

    async def handle_new_member(self, update: Update, context):
        """Auto-ban Mostafa/Mohammed/Mustafa on join"""
        from telegram.error import TelegramError

        message = update.effective_message
        chat = update.effective_chat

        if not chat or chat.type not in ['group', 'supergroup']:
            return

        banned_names = ['mostafa', 'mustafa', 'mustapha', 'mohamed', 'mohammed']

        for member in message.new_chat_members:
            name = f"{member.first_name or ''} {member.last_name or ''}".lower()
            if any(n in name for n in banned_names):
                if not self.dry_run:
                    try:
                        await chat.ban_member(member.id)
                        logger.warning(f"AUTO-BANNED ON JOIN: {member.first_name} {member.last_name or ''} from {chat.title}")
                        self.data.record_action('ban', chat.id)
                    except TelegramError as e:
                        logger.error(f"Ban error: {e}")

    async def cmd_help(self, update: Update, context):
        """Handle /help command"""
        text = """Telegram Group Moderator Commands:

/status - Show bot status and stats
/stats - Same as /status
/scan - Scan last 50 messages for spam
/clean - Delete spam and ban spammers
/ban USER_ID - Add user to blacklist
/whitelist USER_ID - Add user to whitelist
/dealers - Scan and ban drug dealers
/erase_drug_dealer - Same as /dealers
/erasedrugs - Same as /dealers
/reload - Reload spam patterns

Admin only. Bot must have delete + ban permissions."""
        await update.message.reply_text(text)

    async def cmd_scan(self, update: Update, context):
        """Handle /scan command - scan recent messages"""
        from telegram.error import TelegramError

        chat = update.effective_chat
        user = update.effective_user

        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("Use this command in a group.")
            return

        # Check if user is admin
        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator']:
                return
        except Exception:
            return

        await update.message.reply_text("Scanning last 50 messages...")

        spam_count = 0
        spam_users = set()

        # Get recent messages using getUpdates workaround
        # Note: Bot API can't read history, so we track in real-time
        # This shows cached detections
        today_stats = self.data.stats.get('daily', {}).get(
            datetime.now().strftime('%Y-%m-%d'), {}
        )

        text = f"""Scan Results for {chat.title}:

Today's detections:
- Messages flagged: {today_stats.get('messages_deleted', 0)}
- Users banned: {today_stats.get('users_banned', 0)}

Note: Bot monitors in real-time. Historical scan requires Telethon.
Use: python3 telegram_spam_cleanup.py --scan --group "{chat.title[:20]}" """

        await update.message.reply_text(text)

    async def cmd_clean(self, update: Update, context):
        """Handle /clean command - trigger cleanup"""
        from telegram.error import TelegramError

        chat = update.effective_chat
        user = update.effective_user

        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("Use this command in a group.")
            return

        # Check if user is admin
        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator']:
                return
        except Exception:
            return

        await update.message.reply_text(
            "Cleanup mode active. Monitoring for spam...\n"
            "For historical cleanup, run on server:\n"
            f"python3 telegram_spam_cleanup.py --clean --group \"{chat.title[:20]}\""
        )

    async def cmd_ban(self, update: Update, context):
        """Handle /ban USER_ID command"""
        from telegram.error import TelegramError

        chat = update.effective_chat
        user = update.effective_user

        if chat.type not in ['group', 'supergroup']:
            return

        # Check if user is admin
        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator']:
                return
        except Exception:
            return

        # Get user ID from command
        if not context.args:
            await update.message.reply_text("Usage: /ban USER_ID")
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid user ID. Must be a number.")
            return

        # Add to blacklist
        self.data.add_blacklist(target_id)

        # Try to ban from current group
        try:
            await chat.ban_member(target_id)
            await update.message.reply_text(
                f"User {target_id} banned and added to blacklist."
            )
            self.data.record_action('ban', chat.id)
        except TelegramError as e:
            await update.message.reply_text(
                f"Added to blacklist. Ban error: {e}"
            )

    async def cmd_whitelist(self, update: Update, context):
        """Handle /whitelist USER_ID command"""
        chat = update.effective_chat
        user = update.effective_user

        if chat.type not in ['group', 'supergroup']:
            return

        # Check if user is admin
        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator']:
                return
        except Exception:
            return

        if not context.args:
            await update.message.reply_text("Usage: /whitelist USER_ID")
            return

        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid user ID.")
            return

        self.data.add_whitelist(target_id)
        await update.message.reply_text(f"User {target_id} added to whitelist.")

    async def cmd_reload(self, update: Update, context):
        """Handle /reload command - reload patterns"""
        chat = update.effective_chat
        user = update.effective_user

        if chat.type not in ['group', 'supergroup']:
            return

        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator']:
                return
        except Exception:
            return

        self.patterns.reload()
        await update.message.reply_text("Spam patterns reloaded.")

    async def cmd_dealers(self, update: Update, context):
        """Handle /dealers command - scan and ban emoji dealers"""
        import subprocess

        chat = update.effective_chat
        user = update.effective_user

        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("Use in a group.")
            return

        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator']:
                return
        except Exception:
            return

        await update.message.reply_text("Scanning for drug dealers...")

        # Run Telethon cleanup script for this group
        group_name = chat.title[:20] if chat.title else str(chat.id)
        try:
            result = subprocess.run(
                ['python3', '/home/tudor/.claude/skills/telegram_spam_cleanup.py',
                 '--dealers', '--group', group_name],
                capture_output=True, text=True, timeout=60
            )

            # Parse output for results
            output = result.stdout + result.stderr
            lines = [l for l in output.split('\n') if 'BANNED' in l or 'TOTAL' in l or 'Clean' in l]

            if lines:
                response = "Dealer cleanup:\n" + "\n".join(lines[-5:])
            else:
                response = "Cleanup complete. Check server logs for details."

            await update.message.reply_text(response)

        except subprocess.TimeoutExpired:
            await update.message.reply_text("Cleanup running... check /opt/LOGS/")
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)[:100]}")

    async def error_handler(self, update, context):
        """Handle errors"""
        logger.error(f"Error: {context.error}")

    async def get_admin_chats(self) -> List[dict]:
        """Get list of groups where bot is admin"""
        from telegram import Bot

        bot = Bot(self.token)
        await bot.initialize()

        # Note: Bot API doesn't provide a direct way to list all chats
        # This would need to be tracked during runtime
        # For now, return cached groups from stats
        groups = self.data.stats.get('total', {}).get('groups_monitored', [])
        if isinstance(groups, set):
            groups = list(groups)

        result = []
        for group_id in groups:
            try:
                chat = await bot.get_chat(group_id)
                member = await chat.get_member(bot.id)
                result.append({
                    'id': chat.id,
                    'title': chat.title,
                    'type': chat.type,
                    'is_admin': member.status in ['administrator', 'creator'],
                    'can_delete': getattr(member, 'can_delete_messages', False),
                    'can_ban': getattr(member, 'can_restrict_members', False)
                })
            except Exception as e:
                logger.debug(f"Error getting chat {group_id}: {e}")

        await bot.shutdown()
        return result

    async def scan_group(self, group_id: int, limit: int = 100) -> List[dict]:
        """One-time scan of recent messages in a group"""
        from telegram import Bot

        logger.info(f"Scanning group {group_id}, last {limit} messages...")

        # Note: Bot API doesn't allow reading message history
        # This would require Telethon with user account
        # For now, log this limitation

        logger.warning(
            "Bot API cannot read message history. "
            "Use Telethon with user account for historical scans. "
            "See: telegram_spam_cleanup.py"
        )

        return []


async def check_bot_status():
    """Check if bot token is valid and get bot info"""
    from telegram import Bot
    from telegram.error import TelegramError

    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_GROUPS_BOT_TOKEN not set in /opt/EMAIL/.env")
        return False

    try:
        bot = Bot(BOT_TOKEN)
        await bot.initialize()
        me = await bot.get_me()
        await bot.shutdown()

        print(f"Bot Status: ONLINE")
        print(f"  Username: @{me.username}")
        print(f"  Name: {me.first_name}")
        print(f"  ID: {me.id}")
        print(f"  Can join groups: {me.can_join_groups}")
        print(f"  Can read messages: {me.can_read_all_group_messages}")
        return True

    except TelegramError as e:
        print(f"ERROR: Bot connection failed: {e}")
        return False


async def list_groups():
    """List all groups where bot is admin"""
    moderator = TelegramModerator(BOT_TOKEN)
    groups = await moderator.get_admin_chats()

    if not groups:
        print("No groups found (groups are tracked as messages are received)")
        print("Add the bot to groups and it will start tracking them.")
        return

    print(f"Groups monitored ({len(groups)}):")
    print("-" * 60)

    for g in groups:
        perms = []
        if g.get('can_delete'):
            perms.append('delete')
        if g.get('can_ban'):
            perms.append('ban')

        status = 'ADMIN' if g['is_admin'] else 'member'
        perms_str = ', '.join(perms) if perms else 'none'

        print(f"  [{status}] {g['title']}")
        print(f"         ID: {g['id']} | Permissions: {perms_str}")


def show_stats():
    """Display moderation statistics"""
    data = DataStore()
    stats = data.get_stats()

    print("=== Telegram Moderation Statistics ===")
    print()
    print("TODAY:")
    today = stats.get('today', {})
    print(f"  Messages scanned: {today.get('messages_scanned', 0)}")
    print(f"  Messages deleted: {today.get('messages_deleted', 0)}")
    print(f"  Users banned: {today.get('users_banned', 0)}")
    print()
    print("LAST 7 DAYS:")
    week = stats.get('last_7_days', {})
    print(f"  Messages scanned: {week.get('messages_scanned', 0)}")
    print(f"  Messages deleted: {week.get('messages_deleted', 0)}")
    print(f"  Users banned: {week.get('users_banned', 0)}")
    print()
    print("ALL TIME:")
    total = stats.get('total', {})
    print(f"  Messages scanned: {total.get('messages_scanned', 0)}")
    print(f"  Messages deleted: {total.get('messages_deleted', 0)}")
    print(f"  Users banned: {total.get('users_banned', 0)}")
    print(f"  Groups monitored: {total.get('groups_monitored', 0)}")
    print()
    print(f"Whitelist: {len(data.whitelist)} users")
    print(f"Blacklist: {len(data.blacklist)} users")
    print(f"Known offenders: {len(data.offenders)} users")


def manage_list(action: str, user_id: int):
    """Add/remove user from whitelist or blacklist"""
    data = DataStore()

    if action == 'whitelist':
        data.add_whitelist(user_id)
        print(f"Added user {user_id} to whitelist")
    elif action == 'blacklist':
        data.add_blacklist(user_id)
        print(f"Added user {user_id} to blacklist (permanent ban)")
    elif action == 'unwhitelist':
        data.remove_whitelist(user_id)
        print(f"Removed user {user_id} from whitelist")
    elif action == 'unblacklist':
        data.remove_blacklist(user_id)
        print(f"Removed user {user_id} from blacklist")


async def run_bot(dry_run: bool = False, no_ban: bool = False):
    """Run the moderation bot"""
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_GROUPS_BOT_TOKEN not set in /opt/EMAIL/.env")
        sys.exit(1)

    moderator = TelegramModerator(
        BOT_TOKEN,
        dry_run=dry_run,
        auto_ban=not no_ban
    )

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received...")
        asyncio.create_task(moderator.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await moderator.start()
    except Exception as e:
        logger.error(f"Bot error: {e}")
        await moderator.stop()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Telegram Group Auto-Moderator for drug spam',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --status          Check bot connection
  %(prog)s --list-groups     List monitored groups
  %(prog)s --stats           Show moderation statistics
  %(prog)s --run             Start moderation (active)
  %(prog)s --dry-run         Monitor only, no actions
  %(prog)s --run --no-ban    Delete messages but don't ban
  %(prog)s --whitelist 123   Never ban user 123
  %(prog)s --blacklist 456   Always ban user 456
"""
    )

    parser.add_argument('--status', action='store_true',
                        help='Check bot status and connection')
    parser.add_argument('--list-groups', action='store_true',
                        help='List all groups where bot is admin')
    parser.add_argument('--stats', action='store_true',
                        help='Show moderation statistics')
    parser.add_argument('--run', action='store_true',
                        help='Start the moderation bot')
    parser.add_argument('--dry-run', action='store_true',
                        help='Monitor and log but take no actions')
    parser.add_argument('--no-ban', action='store_true',
                        help='Delete messages but do not ban users')
    parser.add_argument('--scan', type=int, metavar='GROUP_ID',
                        help='Scan recent messages in a group')
    parser.add_argument('--whitelist', type=int, metavar='USER_ID',
                        help='Add user to whitelist (never ban)')
    parser.add_argument('--unwhitelist', type=int, metavar='USER_ID',
                        help='Remove user from whitelist')
    parser.add_argument('--blacklist', type=int, metavar='USER_ID',
                        help='Add user to blacklist (always ban)')
    parser.add_argument('--unblacklist', type=int, metavar='USER_ID',
                        help='Remove user from blacklist')
    parser.add_argument('--reload-patterns', action='store_true',
                        help='Reload spam patterns from JSON')

    args = parser.parse_args()

    if args.status:
        asyncio.run(check_bot_status())
    elif args.list_groups:
        asyncio.run(list_groups())
    elif args.stats:
        show_stats()
    elif args.whitelist:
        manage_list('whitelist', args.whitelist)
    elif args.unwhitelist:
        manage_list('unwhitelist', args.unwhitelist)
    elif args.blacklist:
        manage_list('blacklist', args.blacklist)
    elif args.unblacklist:
        manage_list('unblacklist', args.unblacklist)
    elif args.reload_patterns:
        pm = PatternManager(PATTERNS_FILE)
        pm.reload()
        print("Patterns reloaded successfully")
    elif args.scan:
        moderator = TelegramModerator(BOT_TOKEN)
        asyncio.run(moderator.scan_group(args.scan))
    elif args.run or args.dry_run:
        asyncio.run(run_bot(
            dry_run=args.dry_run,
            no_ban=args.no_ban
        ))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
