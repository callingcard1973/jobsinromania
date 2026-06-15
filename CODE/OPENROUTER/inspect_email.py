#!/usr/bin/env python3
"""Inspect email account and analyze what is filling it using OpenRouter."""

import imaplib
import os
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Load env
if Path(__file__).parent.joinpath(".env").exists():
    load_dotenv(Path(__file__).parent / ".env")

from llm import complete


async def analyze_email(email, password, imap_server):
    """Connect to email, analyze storage usage, use AI to explain."""

    print("\n[EMAIL] Inspecting %s..." % email)
    print("[SERVER] %s\n" % imap_server)

    try:
        # Connect
        imap = imaplib.IMAP4_SSL(imap_server)
        imap.login(email, password)

        # Get all folders
        status, folders = imap.list()
        folder_list = [f.decode() for f in folders]

        print("[OK] Connected. Found %d folders\n" % len(folder_list))

        # Analyze each folder
        analysis = []
        total_messages = 0

        for folder_info in folder_list:
            # Parse folder name
            parts = folder_info.split('"')
            if len(parts) >= 3:
                folder_name = parts[2]
            else:
                folder_name = folder_info.split()[-1]

            # Skip special folders
            if folder_name.startswith('['):
                continue

            try:
                status, count = imap.select(folder_name, readonly=True)
                if status == 'OK':
                    num_messages = int(count[0])
                    total_messages += num_messages

                    # Get folder details
                    status, response = imap.fetch(b'1:*', '(RFC822.SIZE)')

                    if status == 'OK':
                        total_size = 0

                        for i, msg_data in enumerate(response):
                            if isinstance(msg_data, tuple):
                                # Get size
                                msg_size = 0
                                if b'RFC822.SIZE' in msg_data[0]:
                                    try:
                                        size_str = msg_data[0].split(b'RFC822.SIZE ')[-1].split(b')')[0]
                                        msg_size = int(size_str)
                                    except:
                                        pass
                                total_size += msg_size

                        size_mb = total_size / (1024 * 1024)
                        analysis.append({
                            'folder': folder_name,
                            'messages': num_messages,
                            'size_mb': size_mb,
                            'avg_msg_kb': (total_size / 1024 / max(num_messages, 1))
                        })

                        avg_kb = total_size / 1024 / max(num_messages, 1)
                        print("[DIR] %s: %6d msgs | %8.1f MB | avg: %6.1f KB/msg" % (
                            folder_name, num_messages, size_mb, avg_kb))
            except Exception as e:
                print("[WARN] %s: %s" % (folder_name, str(e)))

        imap.close()
        imap.logout()

        # Sort by size
        analysis.sort(key=lambda x: x['size_mb'], reverse=True)

        total_size_mb = sum(a['size_mb'] for a in analysis)
        print("\n" + "="*70)
        print("TOTAL: %d messages | %.1f MB" % (total_messages, total_size_mb))
        print("="*70 + "\n")

        # Use AI to analyze
        report = "\n".join([
            "- %s: %d messages, %.1f MB (%.1f KB avg)" % (
                a['folder'], a['messages'], a['size_mb'], a['avg_msg_kb'])
            for a in analysis[:10]
        ])

        print("[AI] Analyzing with OpenRouter (free tier)...\n")

        analysis_prompt = """Email account: %s
IMAP Server: %s
Total: %d messages, %.1f MB

Top folders by size:
%s

Why is this email account full? Identify:
1. Root cause (e.g., backup dumps, newsletters, large attachments)
2. Which folders are problematic
3. Quick fixes (delete, archive, or rules)
4. Recommended cleanup priority

Be direct and specific.""" % (email, imap_server, total_messages, total_size_mb, report)

        result = await complete(
            analysis_prompt,
            system="You are an email administrator. Analyze mailbox bloat and recommend fixes."
        )

        print("[REPORT] AI Analysis:")
        print(result)

        return {
            'email': email,
            'total_messages': total_messages,
            'total_size_mb': total_size_mb,
            'analysis': analysis,
            'ai_report': result
        }

    except imaplib.IMAP4.error as e:
        print("[ERROR] IMAP Error: %s" % str(e))
        return None
    except Exception as e:
        print("[ERROR] %s" % str(e))
        return None


async def main():
    # office@interjob.ro on mail.interjob.ro
    email = "office@interjob.ro"
    password = "pADVouA01bYUkfpE"
    imap_server = "mail.interjob.ro"

    result = await analyze_email(email, password, imap_server)

    if result:
        print("\n[SUCCESS] Analysis complete")
    else:
        print("\n[FAILED] Analysis failed")


if __name__ == "__main__":
    asyncio.run(main())
