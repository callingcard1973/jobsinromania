#!/usr/bin/env python3
"""
Brevo Email Monitoring Script
Checks delivery stats, spam complaints, and bounces across all accounts.
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import argparse

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# All Brevo API keys
ACCOUNTS = {
    'EXPATSINROMANIA': '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',
    'CIFN': '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',
    'MIVROMANIA': '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',
    'MIVROMANIA_ONL': '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',
    'FACTORYJOBS': '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',
    'CAREWORKERS': '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',
    'BUILDJOBS': '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',
    'WAREHOUSEWORKERS': os.getenv('BREVO_WAREHOUSEWORKERS_API_KEY', ''),
    'NEPALEZI': os.getenv('BREVO_NEPALEZI_API_KEY', ''),
}


def get_stats(key: str, days: int = 1) -> dict:
    """Get aggregated stats from Brevo."""
    if not key:
        return None
    try:
        r = requests.get(
            'https://api.brevo.com/v3/smtp/statistics/aggregatedReport',
            headers={'api-key': key},
            params={'days': days},
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


def check_spam_complaints(key: str) -> int:
    """Check for spam complaints."""
    if not key:
        return 0
    try:
        r = requests.get(
            'https://api.brevo.com/v3/smtp/statistics/events',
            headers={'api-key': key},
            params={'limit': 100, 'event': 'complaint'},
            timeout=10
        )
        if r.status_code == 200:
            return len(r.json().get('events', []))
    except:
        pass
    return 0


def main():
    parser = argparse.ArgumentParser(description='Monitor Brevo email stats')
    parser.add_argument('--days', type=int, default=1, help='Days to check (default: 1)')
    parser.add_argument('--alerts-only', action='store_true', help='Only show if there are issues')
    args = parser.parse_args()

    print(f"=== BREVO MONITOR ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===\n")
    print(f"{'Account':<16} {'Req':>6} {'Del':>6} {'Soft':>5} {'Hard':>5} {'Spam':>5} {'Rate':>7}")
    print("-" * 60)

    total_req = 0
    total_del = 0
    total_spam = 0
    alerts = []

    for name, key in ACCOUNTS.items():
        if not key:
            continue

        stats = get_stats(key, args.days)
        spam = check_spam_complaints(key)

        if stats:
            req = stats.get('requests', 0)
            deliv = stats.get('delivered', 0)
            soft = stats.get('softBounces', 0)
            hard = stats.get('hardBounces', 0)
            rate = f"{(deliv/req*100):.0f}%" if req > 0 else "-"

            total_req += req
            total_del += deliv
            total_spam += spam

            print(f"{name:<16} {req:>6} {deliv:>6} {soft:>5} {hard:>5} {spam:>5} {rate:>7}")

            # Check for issues
            if spam > 0:
                alerts.append(f"SPAM: {name} has {spam} complaints!")
            if hard > 10:
                alerts.append(f"BOUNCES: {name} has {hard} hard bounces")
            if req > 0 and deliv/req < 0.5:
                alerts.append(f"DELIVERY: {name} only {rate} delivered")

    print("-" * 60)
    rate = f"{(total_del/total_req*100):.0f}%" if total_req > 0 else "-"
    print(f"{'TOTAL':<16} {total_req:>6} {total_del:>6} {'':>5} {'':>5} {total_spam:>5} {rate:>7}")

    if alerts:
        print(f"\n=== ALERTS ===")
        for alert in alerts:
            print(f"  ! {alert}")
    elif not args.alerts_only:
        print(f"\nNo issues detected.")


if __name__ == '__main__':
    main()
