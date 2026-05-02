#!/usr/bin/env python3
"""Fast Telegram cleanup - regex only, no LLM"""
import asyncio
import re
import json
from pathlib import Path

API_ID = 29861462
API_HASH = "2a0615c09a7bd6b274c4310a16f2708f"
SESSION_PATH = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM/raspi_spam_cleanup")
GROUPS_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM/groups.json")

DRUG_PATTERNS = [
    r'\bketa\b', r'\bcoke\b', r'\bmeth\b', r'\bweed\b', r'\bmdma\b',
    r'\bpills?\b', r'\bdealer\b', r'\bpercs?\b', r'\bxans?\b', r'\bmolly\b',
    r'\bcocaine\b', r'\bheroin\b', r'\becstasy\b', r'\bketamine\b',
    r'\bhashish\b', r'\bamphetamine\b', r'\btramadol\b', r'\bxanax\b',
    r'24/7.*order', r'need.*keta', r'top.*dealer', r'\bmarijuana\b',
    r'\bcannabis\b', r'\biarba\b', r'\bdroguri\b', r'\bpastile\b',
    r'dm.*for.*(?:order|buy)', r'available.*24', r'\bplug\b.*available',
]

DRUG_EMOJIS = ['🍄', '❄️', '🍀', '💊', '🍫', '🌈', '🍁', '🍑', '🎯', '📦', '🌿', '💨', '🔥', '⚡']
DEALER_KEYWORDS = ['dealer', 'plug', 'vendor', 'menu', 'delivery', 'disponible', 'available 24']

def is_spam(text):
    if not text:
        return False
    text_lower = text.lower()
    for pattern in DRUG_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False

def is_emoji_dealer(name):
    if not name:
        return False
    emoji_count = sum(1 for e in DRUG_EMOJIS if e in name)
    has_keyword = any(kw in name.lower() for kw in DEALER_KEYWORDS)
    return emoji_count >= 2 or (emoji_count >= 1 and has_keyword)

async def full_cleanup():
    from telethon import TelegramClient
    from telethon.tl.functions.channels import EditBannedRequest
    from telethon.tl.types import ChatBannedRights

    client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"Logged in: {me.first_name}")
    print("=" * 60)

    with open(GROUPS_FILE) as f:
        groups = json.load(f)

    total_msgs = 0
    total_banned = 0

    ban_rights = ChatBannedRights(
        until_date=None,
        view_messages=True, send_messages=True, send_media=True,
        send_stickers=True, send_gifs=True, send_games=True,
        send_inline=True, embed_links=True
    )

    for group_id, group_name in groups.items():
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

        # Find spam messages
        spammers = {}
        msg_ids = []

        async for msg in client.iter_messages(group, limit=300):
            if not msg.text or not msg.sender_id:
                continue
            if is_spam(msg.text):
                if msg.sender_id not in spammers:
                    name = "Unknown"
                    if msg.sender:
                        name = f"{msg.sender.first_name or ''} {msg.sender.last_name or ''}".strip()
                    spammers[msg.sender_id] = name
                msg_ids.append(msg.id)

        # Find emoji dealers
        dealers = []
        async for user in client.iter_participants(group):
            if not user:
                continue
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if is_emoji_dealer(full_name):
                dealers.append({'id': user.id, 'name': full_name})

        if not msg_ids and not dealers:
            print("  Clean")
            continue

        # Delete spam messages
        if msg_ids:
            try:
                await client.delete_messages(group, msg_ids)
                print(f"  Deleted {len(msg_ids)} spam messages")
                total_msgs += len(msg_ids)
            except Exception as e:
                print(f"  Delete error: {e}")

            # Ban spammers
            for user_id, name in spammers.items():
                try:
                    await client(EditBannedRequest(group, user_id, ban_rights))
                    print(f"  BANNED (spam): {name}")
                    total_banned += 1
                except Exception as e:
                    if 'USER_NOT_PARTICIPANT' not in str(e):
                        print(f"  Ban error: {e}")

        # Ban emoji dealers
        for d in dealers:
            # Delete their messages first
            dealer_msgs = []
            async for msg in client.iter_messages(group, from_user=d['id'], limit=50):
                dealer_msgs.append(msg.id)
            if dealer_msgs:
                try:
                    await client.delete_messages(group, dealer_msgs)
                    print(f"  Deleted {len(dealer_msgs)} msgs from dealer {d['name']}")
                    total_msgs += len(dealer_msgs)
                except:
                    pass

            try:
                await client(EditBannedRequest(group, d['id'], ban_rights))
                print(f"  BANNED (dealer): {d['name']}")
                total_banned += 1
            except Exception as e:
                if 'USER_NOT_PARTICIPANT' not in str(e):
                    print(f"  Ban error: {e}")

    print("\n" + "=" * 60)
    print(f"TOTAL: Deleted {total_msgs} messages, Banned {total_banned} users")
    await client.disconnect()

asyncio.run(full_cleanup())
