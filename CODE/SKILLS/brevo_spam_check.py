#!/usr/bin/env python3
"""
Brevo Spam Check - Check spam/bounce status across all Brevo accounts.

Usage:
    brevo_spam_check.py                    # Check all accounts
    brevo_spam_check.py --account buildjobs  # Check specific account
    brevo_spam_check.py --last-hour          # Recent complaints only
    brevo_spam_check.py --detailed           # Show event details
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

BREVO_API = "https://api.brevo.com/v3"

# All Brevo accounts with their API keys
BREVO_ACCOUNTS = {
    "buildjobs": {
        "api_key": os.getenv("BREVO_BUILDJOBS_API_KEY"),
        "email": "office@buildjobs.eu"
    },
    "factoryjobs": {
        "api_key": os.getenv("BREVO_FACTORYJOBS_API_KEY"),
        "email": "office@factoryjobs.eu"
    },
    "warehouseworkers": {
        "api_key": os.getenv("BREVO_WAREHOUSEWORKERS_API_KEY"),
        "email": "office@warehouseworkers.eu"
    },
    "mivromania": {
        "api_key": os.getenv("BREVO_MIVROMANIA_API_KEY"),
        "email": "office@mivromania.info"
    },
    "mivromania_online": {
        "api_key": os.getenv("BREVO_MIVROMANIA_ONLINE_API_KEY"),
        "email": "office@mivromania.online"
    },
    "careworkers": {
        "api_key": os.getenv("BREVO_CAREWORKERS_API_KEY"),
        "email": "office@careworkers.eu"
    },
    "cifn": {
        "api_key": os.getenv("BREVO_CIFN_API_KEY"),
        "email": "office@cifn.info"
    },
    "interjob": {
        "api_key": os.getenv("BREVO_INTERJOB_API_KEY"),
        "email": "office@interjob.ro"
    },
    "nepalezi": {
        "api_key": os.getenv("BREVO_NEPALEZI_API_KEY"),
        "email": "office@nepalezi.com"
    },
    "expatsinromania": {
        "api_key": os.getenv("BREVO_EXPATSINROMANIA_API_KEY"),
        "email": "office@expatsinromania.org"
    },
    "cumparlegume": {
        "api_key": os.getenv("BREVO_CUMPARLEGUME_API_KEY"),
        "email": "office@cumparlegume.com"
    }
}


def check_spam_events(api_key: str, last_hour_only: bool = False) -> dict:
    """Check spam complaints for an account."""
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    # Date range
    if last_hour_only:
        start_date = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d")
    else:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    end_date = datetime.now().strftime("%Y-%m-%d")

    try:
        resp = requests.get(
            f"{BREVO_API}/smtp/statistics/events",
            headers=headers,
            params={
                "event": "complaint",
                "limit": 100,
                "startDate": start_date,
                "endDate": end_date
            },
            timeout=30
        )

        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "events": []}

        events = resp.json().get("events", [])

        # Filter to last hour if requested
        if last_hour_only:
            hour_ago = datetime.now() - timedelta(hours=1)
            filtered = []
            for event in events:
                try:
                    event_time = datetime.fromisoformat(event.get("date", "").replace("Z", "+00:00"))
                    if event_time.replace(tzinfo=None) > hour_ago:
                        filtered.append(event)
                except (ValueError, TypeError):
                    pass
            events = filtered

        return {"events": events, "count": len(events)}

    except requests.RequestException as e:
        return {"error": str(e), "events": []}


def check_bounce_stats(api_key: str) -> dict:
    """Check bounce/block statistics for an account."""
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    try:
        resp = requests.get(
            f"{BREVO_API}/smtp/statistics/aggregatedReport",
            headers=headers,
            params={"days": 1},
            timeout=30
        )

        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}"}

        data = resp.json()

        total = data.get("requests", 0)
        delivered = data.get("delivered", 0)
        hard_bounces = data.get("hardBounces", 0)
        soft_bounces = data.get("softBounces", 0)
        blocked = data.get("blocked", 0)
        opens = data.get("opens", 0)
        clicks = data.get("clicks", 0)

        bounce_rate = ((hard_bounces + soft_bounces) / total * 100) if total > 0 else 0
        blocked_rate = (blocked / total * 100) if total > 0 else 0
        open_rate = (opens / delivered * 100) if delivered > 0 else 0

        return {
            "requests": total,
            "delivered": delivered,
            "hard_bounces": hard_bounces,
            "soft_bounces": soft_bounces,
            "blocked": blocked,
            "opens": opens,
            "clicks": clicks,
            "bounce_rate": bounce_rate,
            "blocked_rate": blocked_rate,
            "open_rate": open_rate
        }

    except requests.RequestException as e:
        return {"error": str(e)}


def check_account(name: str, config: dict, last_hour: bool = False, detailed: bool = False) -> dict:
    """Check a single Brevo account."""
    api_key = config.get("api_key")
    email = config.get("email")

    if not api_key:
        return {"name": name, "email": email, "error": "No API key configured"}

    # Check spam
    spam_result = check_spam_events(api_key, last_hour_only=last_hour)

    # Check bounces
    bounce_result = check_bounce_stats(api_key)

    result = {
        "name": name,
        "email": email,
        "spam_complaints": spam_result.get("count", 0),
        "spam_events": spam_result.get("events", []) if detailed else None,
        "spam_error": spam_result.get("error"),
        **bounce_result
    }

    # Status determination
    if spam_result.get("count", 0) > 0:
        result["status"] = "SPAM DETECTED"
    elif bounce_result.get("bounce_rate", 0) > 5.0:
        result["status"] = "HIGH BOUNCES"
    elif bounce_result.get("blocked_rate", 0) > 3.0:
        result["status"] = "HIGH BLOCKED"
    elif bounce_result.get("error"):
        result["status"] = "ERROR"
    else:
        result["status"] = "OK"

    return result


def print_account_status(result: dict):
    """Print status for one account."""
    status = result.get("status", "UNKNOWN")
    name = result.get("name", "Unknown")
    email = result.get("email", "")

    # Status indicator
    if status == "OK":
        indicator = "[OK]"
    elif status == "SPAM DETECTED":
        indicator = "[SPAM!]"
    elif status == "HIGH BOUNCES":
        indicator = "[BOUNCES!]"
    elif status == "HIGH BLOCKED":
        indicator = "[BLOCKED]"
    else:
        indicator = "[ERROR]"

    print(f"\n{indicator} {name} ({email})")

    if result.get("error"):
        print(f"  Error: {result['error']}")
        return

    # Stats
    requests = result.get("requests", 0)
    delivered = result.get("delivered", 0)
    bounce_rate = result.get("bounce_rate", 0)
    blocked_rate = result.get("blocked_rate", 0)
    open_rate = result.get("open_rate", 0)
    spam = result.get("spam_complaints", 0)

    print(f"  Last 24h: {requests} sent, {delivered} delivered")
    print(f"  Bounces: {bounce_rate:.1f}%, Blocked: {blocked_rate:.1f}%, Opens: {open_rate:.1f}%")
    print(f"  Spam complaints: {spam}")

    # Show spam events if any
    spam_events = result.get("spam_events", [])
    if spam_events:
        print(f"  Recent complaints:")
        for event in spam_events[:5]:
            recipient = event.get("email", "unknown")
            event_date = event.get("date", "")[:19]
            print(f"    - {recipient} ({event_date})")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check Brevo spam/bounce status")
    parser.add_argument("--account", "-a", help="Check specific account (e.g., buildjobs)")
    parser.add_argument("--last-hour", action="store_true", help="Only show last hour complaints")
    parser.add_argument("--detailed", "-d", action="store_true", help="Show detailed spam events")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    print(f"=== BREVO SPAM CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    if args.account:
        # Check specific account
        if args.account not in BREVO_ACCOUNTS:
            print(f"Unknown account: {args.account}")
            print(f"Available: {', '.join(BREVO_ACCOUNTS.keys())}")
            sys.exit(1)

        result = check_account(
            args.account,
            BREVO_ACCOUNTS[args.account],
            last_hour=args.last_hour,
            detailed=args.detailed
        )

        if args.json:
            import json
            print(json.dumps(result, indent=2, default=str))
        else:
            print_account_status(result)

    else:
        # Check all accounts
        results = []
        ok_count = 0
        problem_count = 0

        for name, config in BREVO_ACCOUNTS.items():
            if not config.get("api_key"):
                continue

            result = check_account(name, config, last_hour=args.last_hour, detailed=args.detailed)
            results.append(result)

            if result.get("status") == "OK":
                ok_count += 1
            elif result.get("status") not in ("ERROR",):
                problem_count += 1

        if args.json:
            import json
            print(json.dumps(results, indent=2, default=str))
        else:
            for result in results:
                print_account_status(result)

            print(f"\n=== SUMMARY ===")
            print(f"  OK: {ok_count}")
            print(f"  Problems: {problem_count}")

            if problem_count > 0:
                print("\n  ACTION: Stop campaigns for accounts with problems!")


if __name__ == "__main__":
    main()
