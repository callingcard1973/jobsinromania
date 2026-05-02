#!/usr/bin/env python3
"""
Telegram Phone Checker - Verify which phone numbers have Telegram accounts.

Uses Telethon to check if phone numbers are registered on Telegram.
Requires Telegram API credentials (api_id, api_hash).

Usage:
    python3 telegram_checker.py check +40722789938
    python3 telegram_checker.py scan /path/to/contacts.csv --phone-col phone
    python3 telegram_checker.py scan /path/to/contacts.csv --limit 100
    
Setup:
    1. Get API credentials: https://my.telegram.org/apps
    2. Set in .env: TELEGRAM_API_ID, TELEGRAM_API_HASH
    3. First run will ask for phone verification
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import asyncio
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Telegram API credentials
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_FILE = '/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM/raspi_outreach'

# Output paths
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/TELEGRAM_VERIFIED')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_phone(phone):
    """Normalize phone number to international format."""
    if not phone:
        return None
    # Remove all non-digits except +
    cleaned = re.sub(r'[^\d+]', '', str(phone))
    if not cleaned:
        return None
    # Add + if missing and starts with country code
    if not cleaned.startswith('+'):
        if cleaned.startswith('40') and len(cleaned) >= 11:
            cleaned = '+' + cleaned
        elif cleaned.startswith('0') and len(cleaned) == 10:
            cleaned = '+4' + cleaned  # Romania
        else:
            cleaned = '+' + cleaned
    # Validate length
    if len(cleaned) < 10 or len(cleaned) > 15:
        return None
    return cleaned


async def check_phones_telegram(phones, batch_size=100):
    """Check if phone numbers are on Telegram using Telethon."""
    try:
        from telethon import TelegramClient
        from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
        from telethon.tl.types import InputPhoneContact
    except ImportError:
        print("ERROR: telethon not installed. Run: pip install telethon")
        return {}
    
    if not API_ID or not API_HASH:
        print("ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH not set in .env")
        return {}
    
    results = {}
    
    async with TelegramClient(SESSION_FILE, int(API_ID), API_HASH) as client:
        await client.start()
        
        # Process in batches
        for i in range(0, len(phones), batch_size):
            batch = phones[i:i+batch_size]
            
            # Create contact objects
            contacts = []
            for idx, phone in enumerate(batch):
                contacts.append(InputPhoneContact(
                    client_id=idx,
                    phone=phone,
                    first_name=f"Check{idx}",
                    last_name=""
                ))
            
            try:
                # Import contacts to check
                result = await client(ImportContactsRequest(contacts))
                
                # Get which ones were found
                for user in result.users:
                    if user.phone:
                        norm = normalize_phone(user.phone)
                        if norm:
                            results[norm] = {
                                'has_telegram': True,
                                'user_id': user.id,
                                'username': user.username,
                                'first_name': user.first_name,
                                'last_name': user.last_name
                            }
                
                # Mark not found
                for phone in batch:
                    if phone not in results:
                        results[phone] = {'has_telegram': False}
                
                # Delete imported contacts (cleanup)
                if result.users:
                    await client(DeleteContactsRequest([u.id for u in result.users]))
                
                print(f"Checked {min(i+batch_size, len(phones))}/{len(phones)}")
                
                # Rate limit
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Batch error: {e}")
                for phone in batch:
                    results[phone] = {'has_telegram': None, 'error': str(e)}
    
    return results


def scan_csv(csv_path, phone_col='phone', limit=None, output=None):
    """Scan CSV file for Telegram-enabled phones."""
    
    phones_to_check = []
    phone_to_row = {}
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        
        # Find phone column
        if phone_col not in reader.fieldnames:
            # Try to find it
            phone_cols = [c for c in reader.fieldnames if 'phone' in c.lower()]
            if phone_cols:
                phone_col = phone_cols[0]
            else:
                print(f"No phone column found. Available: {reader.fieldnames}")
                return
        
        for row in reader:
            phone = row.get(phone_col, '')
            norm = normalize_phone(phone)
            if norm and norm not in phone_to_row:
                phones_to_check.append(norm)
                phone_to_row[norm] = row
                if limit and len(phones_to_check) >= limit:
                    break
    
    print(f"Found {len(phones_to_check)} unique phones to check")
    
    if not phones_to_check:
        return
    
    # Run async check
    results = asyncio.run(check_phones_telegram(phones_to_check))
    
    # Count results
    has_tg = sum(1 for r in results.values() if r.get('has_telegram'))
    no_tg = sum(1 for r in results.values() if r.get('has_telegram') == False)
    errors = sum(1 for r in results.values() if r.get('has_telegram') is None)
    
    print(f"\n=== RESULTS ===")
    print(f"Has Telegram: {has_tg} ({has_tg/len(results)*100:.1f}%)")
    print(f"No Telegram:  {no_tg}")
    print(f"Errors:       {errors}")
    
    # Save results
    output_file = output or OUTPUT_DIR / f"telegram_verified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['phone', 'has_telegram', 'telegram_username', 'telegram_name'] + list(phone_to_row[phones_to_check[0]].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for phone, tg_data in results.items():
            if phone in phone_to_row:
                row = phone_to_row[phone].copy()
                row['phone'] = phone
                row['has_telegram'] = tg_data.get('has_telegram', '')
                row['telegram_username'] = tg_data.get('username', '')
                row['telegram_name'] = f"{tg_data.get('first_name', '')} {tg_data.get('last_name', '')}".strip()
                writer.writerow(row)
    
    print(f"\nSaved to: {output_file}")
    
    # Also save just Telegram-enabled contacts
    tg_only = OUTPUT_DIR / f"telegram_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(tg_only, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for phone, tg_data in results.items():
            if tg_data.get('has_telegram') and phone in phone_to_row:
                row = phone_to_row[phone].copy()
                row['phone'] = phone
                row['has_telegram'] = True
                row['telegram_username'] = tg_data.get('username', '')
                row['telegram_name'] = f"{tg_data.get('first_name', '')} {tg_data.get('last_name', '')}".strip()
                writer.writerow(row)
    
    print(f"Telegram-only: {tg_only}")
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Check phone numbers for Telegram')
    subparsers = parser.add_subparsers(dest='command')
    
    # Check single phone
    check_parser = subparsers.add_parser('check', help='Check single phone')
    check_parser.add_argument('phone', help='Phone number to check')
    
    # Scan CSV
    scan_parser = subparsers.add_parser('scan', help='Scan CSV file')
    scan_parser.add_argument('csv_file', help='CSV file path')
    scan_parser.add_argument('--phone-col', default='phone', help='Phone column name')
    scan_parser.add_argument('--limit', type=int, help='Limit phones to check')
    scan_parser.add_argument('--output', help='Output file path')
    
    # Setup
    setup_parser = subparsers.add_parser('setup', help='Setup API credentials')
    
    args = parser.parse_args()
    
    if args.command == 'check':
        norm = normalize_phone(args.phone)
        if not norm:
            print(f"Invalid phone: {args.phone}")
            return
        results = asyncio.run(check_phones_telegram([norm]))
        print(json.dumps(results, indent=2))
        
    elif args.command == 'scan':
        scan_csv(args.csv_file, args.phone_col, args.limit, args.output)
        
    elif args.command == 'setup':
        print("Setup Telegram API:")
        print("1. Go to https://my.telegram.org/apps")
        print("2. Create an app to get api_id and api_hash")
        print("3. Add to /opt/ACTIVE/EMAIL/CAMPAIGNS/.env:")
        print("   TELEGRAM_API_ID=your_id")
        print("   TELEGRAM_API_HASH=your_hash")
        print("4. Run: python3 telegram_checker.py check +40722789938")
        print("   (First run will ask for phone verification)")
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
