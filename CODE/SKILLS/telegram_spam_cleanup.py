#!/usr/bin/env python3
"""
Telegram Spam Cleanup - Scan and clean drug/spam from admin groups.
Detects: spam messages, emoji dealers, drug menus.
"""

import asyncio
import argparse
import re
import json
import sys
from pathlib import Path

# LLM spam scoring (optional)
try:
    sys.path.insert(0, "/opt/ACTIVE/LLM/MEMORY/llm_tasks")
    from telegram.llm_spam_bridge import is_spam_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

API_ID = 29861462
API_HASH = "2a0615c09a7bd6b274c4310a16f2708f"
SESSION_PATH = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM/raspi_spam_cleanup")
GROUPS_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM/groups.json")
LEARNED_WORDS_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM/learned_spam_words.json")

# Regex patterns for drug spam in messages
DRUG_PATTERNS = [
    r'\bketa\b', r'\bcoke\b', r'\bmeth\b', r'\bweed\b', r'\bmdma\b',
    r'\bpills?\b', r'\bdealer\b', r'\bpercs?\b', r'\bxans?\b', r'\bmolly\b',
    r'\bcocaine\b', r'\bheroin\b', r'\becstasy\b', r'\bketamine\b',
    r'\bhashish\b', r'\bamphetamine\b', r'\btramadol\b', r'\bxanax\b',
    r'24/7.*order', r'need.*keta', r'top.*dealer',
]

# Drug emojis in usernames (2+ = dealer)
DRUG_EMOJIS = ['🍄', '❄️', '🍀', '💊', '🍫', '🌈', '🍁', '🍑', '🎯', '📦']

# Dealer keywords in names
DEALER_KEYWORDS = ['dealer', 'plug', 'vendor', 'menu', 'delivery', 'disponible']


def load_learned_words():
    if LEARNED_WORDS_FILE.exists():
        with open(LEARNED_WORDS_FILE) as f:
            return set(json.load(f))
    return set()


def save_learned_words(words):
    with open(LEARNED_WORDS_FILE, 'w') as f:
        json.dump(sorted(list(words)), f, indent=2)


def load_groups():
    if GROUPS_FILE.exists():
        with open(GROUPS_FILE) as f:
            return json.load(f)
    return {}


def is_spam(text, learned_words):
    if not text:
        return False
    text_lower = text.lower()

    # Check regex patterns
    for pattern in DRUG_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    # Check learned words
    for word in learned_words:
        if word.lower() in text_lower:
            return True

    return False


def is_spam_enhanced(text, learned_words, sender_name="Unknown", group_name="Unknown"):
    """Check spam with regex first, then LLM as fallback."""
    # Fast regex check first
    if is_spam(text, learned_words):
        return True, "regex"

    # LLM check for messages that passed regex
    if HAS_LLM and text and len(text) >= 20:
        try:
            result = is_spam_llm(text, sender_name, group_name)
            if result and result["is_spam"]:
                return True, f"llm:{result['score']}"
        except Exception:
            pass

    return False, None


def is_emoji_dealer(name):
    """Check if username has drug emoji pattern (2+ emojis or 1 emoji + keyword)"""
    if not name:
        return False, []

    emoji_count = sum(1 for e in DRUG_EMOJIS if e in name)
    has_keyword = any(kw in name.lower() for kw in DEALER_KEYWORDS)

    is_dealer = emoji_count >= 2 or (emoji_count >= 1 and has_keyword)
    emojis_found = [e for e in DRUG_EMOJIS if e in name]

    return is_dealer, emojis_found


async def scan_groups(group_filter=None):
    from telethon import TelegramClient

    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"Logged in: {me.first_name}")
    print("=" * 60)

    groups = load_groups()
    learned_words = load_learned_words()

    results = []

    for group_id, group_name in groups.items():
        if group_filter and group_filter.lower() not in group_name.lower():
            continue

        print(f"\n--- {group_name} ---")

        try:
            group = await client.get_entity(int(group_id))
            perms = await client.get_permissions(group, me)
            if not perms.is_admin:
                print("  Skip: not admin")
                continue
        except Exception as e:
            print(f"  Skip: {e}")
            continue

        spam_found = []
        async for msg in client.iter_messages(group, limit=200):
            if not msg.text or not msg.sender_id:
                continue

            spam_hit, method = is_spam_enhanced(msg.text, learned_words, group_name=group_name)
            if spam_hit:
                name = "Unknown"
                if msg.sender:
                    name = f"{msg.sender.first_name or ''} {msg.sender.last_name or ''}".strip()
                spam_found.append({
                    'msg_id': msg.id,
                    'user_id': msg.sender_id,
                    'user': name,
                    'text': msg.text[:80],
                    'date': str(msg.date)[:10]
                })

        if spam_found:
            print(f"  Found {len(spam_found)} spam messages:")
            for s in spam_found[:5]:
                print(f"    [{s['date']}] {s['user']}: {s['text'][:50]}...")
            if len(spam_found) > 5:
                print(f"    ... and {len(spam_found) - 5} more")
            results.append({'group': group_name, 'spam': spam_found})
        else:
            print("  Clean")

    await client.disconnect()
    return results


async def clean_groups(group_filter=None):
    from telethon import TelegramClient
    from telethon.tl.functions.channels import EditBannedRequest
    from telethon.tl.types import ChatBannedRights

    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"Logged in: {me.first_name}")
    print("=" * 60)

    groups = load_groups()
    learned_words = load_learned_words()

    total_msgs = 0
    total_banned = 0

    ban_rights = ChatBannedRights(
        until_date=None,
        view_messages=True, send_messages=True, send_media=True,
        send_stickers=True, send_gifs=True, send_games=True,
        send_inline=True, embed_links=True
    )

    for group_id, group_name in groups.items():
        if group_filter and group_filter.lower() not in group_name.lower():
            continue

        print(f"\n--- {group_name} ---")

        try:
            group = await client.get_entity(int(group_id))
            perms = await client.get_permissions(group, me)
            if not (perms.is_admin and perms.ban_users):
                print("  Skip: not admin with ban rights")
                continue
        except Exception as e:
            print(f"  Skip: {e}")
            continue

        spammers = {}
        msg_ids = []

        async for msg in client.iter_messages(group, limit=300):
            if not msg.text or not msg.sender_id:
                continue

            spam_hit, method = is_spam_enhanced(msg.text, learned_words, group_name=group_name)
            if spam_hit:
                if msg.sender_id not in spammers:
                    name = "Unknown"
                    if msg.sender:
                        name = f"{msg.sender.first_name or ''} {msg.sender.last_name or ''}".strip()
                    spammers[msg.sender_id] = name
                msg_ids.append(msg.id)

        if not msg_ids:
            print("  Clean")
            continue

        # Delete
        try:
            await client.delete_messages(group, msg_ids)
            print(f"  Deleted {len(msg_ids)} messages")
            total_msgs += len(msg_ids)
        except Exception as e:
            print(f"  Delete error: {e}")

        # Ban
        for user_id, name in spammers.items():
            try:
                await client(EditBannedRequest(group, user_id, ban_rights))
                print(f"  BANNED: {name} ({user_id})")
                total_banned += 1
            except Exception as e:
                if 'USER_NOT_PARTICIPANT' not in str(e):
                    print(f"  Ban error {name}: {e}")

    print("\n" + "=" * 60)
    print(f"TOTAL: Deleted {total_msgs} msgs, Banned {total_banned} users")

    await client.disconnect()
    return {'deleted': total_msgs, 'banned': total_banned}


def add_word(word):
    words = load_learned_words()
    word = word.lower().strip()
    if word in words:
        print(f"'{word}' already in list")
        return
    words.add(word)
    save_learned_words(words)
    print(f"Added '{word}' to spam words ({len(words)} total)")


def remove_word(word):
    words = load_learned_words()
    word = word.lower().strip()
    if word not in words:
        print(f"'{word}' not in list")
        return
    words.discard(word)
    save_learned_words(words)
    print(f"Removed '{word}' from spam words ({len(words)} total)")


def list_words():
    words = sorted(load_learned_words())
    print(f"Spam words ({len(words)}):")
    print(", ".join(words))


async def scan_dealers(group_filter=None):
    """Scan for users with drug emoji patterns in their names"""
    from telethon import TelegramClient

    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"Logged in: {me.first_name}")
    print("Scanning for emoji dealers...")
    print("=" * 60)

    groups = load_groups()
    dealers = []

    for group_id, group_name in groups.items():
        if group_filter and group_filter.lower() not in group_name.lower():
            continue

        print(f"\n--- {group_name} ---")

        try:
            group = await client.get_entity(int(group_id))
            perms = await client.get_permissions(group, me)
            if not perms.is_admin:
                print("  Skip: not admin")
                continue
        except Exception as e:
            print(f"  Skip: {e}")
            continue

        async for user in client.iter_participants(group):
            if not user:
                continue

            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            is_dealer, emojis = is_emoji_dealer(full_name)

            if is_dealer:
                print(f"  DEALER: {full_name}")
                print(f"    ID: {user.id} | Emojis: {' '.join(emojis)}")
                dealers.append({
                    'user_id': user.id,
                    'name': full_name,
                    'emojis': emojis,
                    'group': group_name,
                    'group_id': int(group_id)
                })

        if not any(d['group'] == group_name for d in dealers):
            print("  Clean")

    print("\n" + "=" * 60)
    print(f"TOTAL DEALERS: {len(dealers)}")

    await client.disconnect()
    return dealers


async def clean_dealers(group_filter=None):
    """Ban emoji dealers and delete their messages"""
    from telethon import TelegramClient
    from telethon.tl.functions.channels import EditBannedRequest
    from telethon.tl.types import ChatBannedRights

    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"Logged in: {me.first_name}")
    print("Cleaning emoji dealers...")
    print("=" * 60)

    groups = load_groups()
    total_banned = 0
    total_msgs = 0

    ban_rights = ChatBannedRights(
        until_date=None,
        view_messages=True, send_messages=True, send_media=True,
        send_stickers=True, send_gifs=True, send_games=True,
        send_inline=True, embed_links=True
    )

    for group_id, group_name in groups.items():
        if group_filter and group_filter.lower() not in group_name.lower():
            continue

        print(f"\n--- {group_name} ---")

        try:
            group = await client.get_entity(int(group_id))
            perms = await client.get_permissions(group, me)
            if not (perms.is_admin and perms.ban_users):
                print("  Skip: not admin with ban rights")
                continue
        except Exception as e:
            print(f"  Skip: {e}")
            continue

        dealers_here = []
        async for user in client.iter_participants(group):
            if not user:
                continue

            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            is_dealer, emojis = is_emoji_dealer(full_name)

            if is_dealer:
                dealers_here.append({
                    'user_id': user.id,
                    'name': full_name,
                    'emojis': emojis
                })

        if not dealers_here:
            print("  Clean")
            continue

        for d in dealers_here:
            # Delete their messages
            msg_ids = []
            async for msg in client.iter_messages(group, from_user=d['user_id'], limit=50):
                msg_ids.append(msg.id)

            if msg_ids:
                try:
                    await client.delete_messages(group, msg_ids)
                    print(f"  Deleted {len(msg_ids)} msgs from {d['name']}")
                    total_msgs += len(msg_ids)
                except Exception as e:
                    print(f"  Delete error: {e}")

            # Ban
            try:
                await client(EditBannedRequest(group, d['user_id'], ban_rights))
                print(f"  BANNED: {d['name']} ({' '.join(d['emojis'])})")
                total_banned += 1
            except Exception as e:
                if 'USER_NOT_PARTICIPANT' not in str(e):
                    print(f"  Ban error: {e}")

    print("\n" + "=" * 60)
    print(f"TOTAL: Deleted {total_msgs} msgs, Banned {total_banned} dealers")

    await client.disconnect()
    return {'deleted': total_msgs, 'banned': total_banned}


async def full_cleanup(group_filter=None):
    """Run both message spam cleanup AND dealer cleanup"""
    print("FULL CLEANUP: Messages + Dealers")
    print("=" * 60)

    # Clean spam messages first
    result1 = await clean_groups(group_filter)

    # Then clean emoji dealers
    result2 = await clean_dealers(group_filter)

    print("\n" + "=" * 60)
    print("COMBINED RESULTS:")
    print(f"  Messages deleted: {result1['deleted'] + result2['deleted']}")
    print(f"  Users banned: {result1['banned'] + result2['banned']}")

    return {
        'deleted': result1['deleted'] + result2['deleted'],
        'banned': result1['banned'] + result2['banned']
    }


def main():
    parser = argparse.ArgumentParser(description='Telegram spam cleanup')
    parser.add_argument('--scan', action='store_true', help='Scan for spam messages')
    parser.add_argument('--clean', action='store_true', help='Clean spam messages + ban')
    parser.add_argument('--dealers', action='store_true', help='Scan/clean emoji dealers')
    parser.add_argument('--full', action='store_true', help='Full cleanup (msgs + dealers)')
    parser.add_argument('--group', type=str, help='Filter by group name')
    parser.add_argument('--add-word', type=str, help='Add word to spam list')
    parser.add_argument('--remove-word', type=str, help='Remove word from spam list')
    parser.add_argument('--list-words', action='store_true', help='List spam words')

    args = parser.parse_args()

    if args.add_word:
        add_word(args.add_word)
    elif args.remove_word:
        remove_word(args.remove_word)
    elif args.list_words:
        list_words()
    elif args.full:
        asyncio.run(full_cleanup(args.group))
    elif args.dealers and args.scan:
        asyncio.run(scan_dealers(args.group))
    elif args.dealers:
        asyncio.run(clean_dealers(args.group))
    elif args.scan:
        asyncio.run(scan_groups(args.group))
    elif args.clean:
        asyncio.run(clean_groups(args.group))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
