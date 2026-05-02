#!/usr/bin/env python3
"""
Brevo Stats API
Get sending statistics from Brevo for dashboards.

Usage:
    brevo_stats.py                  # Show all stats
    brevo_stats.py --json           # Output JSON for dashboard
    brevo_stats.py --account NAME   # Specific account
"""
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

BREVO_API = "https://api.brevo.com/v3"

# All Brevo accounts
ACCOUNTS = {
    "buildjobs": {
        "api_key": os.getenv("BREVO_BUILDJOBS_API_KEY"),
        "email": "office@buildjobs.eu"
    },
    "factoryjobs": {
        "api_key": os.getenv("BREVO_FACTORYJOBS_API_KEY"),
        "email": "office@factoryjobs.eu"
    },
    "mivromania": {
        "api_key": os.getenv("BREVO_API_KEY"),
        "email": "office@mivromania.info"
    },
    "interjob": {
        "api_key": os.getenv("BREVO_INTERJOB_API_KEY"),
        "email": "office@interjob.ro"
    },
    "expatsinromania": {
        "api_key": os.getenv("BREVO_EXPATSINROMANIA_API_KEY"),
        "email": "office@expatsinromania.org"
    },
    "warehouseworkers": {
        "api_key": os.getenv("BREVO_WAREHOUSEWORKERS_API_KEY"),
        "email": "office@warehouseworkers.eu"
    }
}


def get_stats(api_key: str, days: int = 7):
    """Get sending statistics from Brevo."""
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    # Get aggregated report
    params = {"days": days}
    resp = requests.get(f"{BREVO_API}/smtp/statistics/aggregatedReport", headers=headers, params=params)

    if resp.status_code != 200:
        return None

    return resp.json()


def get_events(api_key: str, days: int = 1):
    """Get recent email events."""
    headers = {"api-key": api_key}

    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")

    params = {"startDate": start, "endDate": end, "limit": 100}
    resp = requests.get(f"{BREVO_API}/smtp/statistics/events", headers=headers, params=params)

    if resp.status_code != 200:
        return []

    return resp.json().get("events", [])


def get_all_stats(days: int = 7):
    """Get stats for all accounts."""
    results = {}

    for name, config in ACCOUNTS.items():
        if not config["api_key"]:
            continue

        stats = get_stats(config["api_key"], days)
        if stats:
            results[name] = {
                "email": config["email"],
                "requests": stats.get("requests", 0),
                "delivered": stats.get("delivered", 0),
                "opens": stats.get("opens", 0),
                "clicks": stats.get("clicks", 0),
                "bounces": stats.get("hardBounces", 0) + stats.get("softBounces", 0),
                "blocked": stats.get("blocked", 0),
                "unsubscribed": stats.get("unsubscribed", 0),
                "open_rate": round(stats.get("opens", 0) / max(stats.get("delivered", 1), 1) * 100, 1),
                "bounce_rate": round((stats.get("hardBounces", 0) + stats.get("softBounces", 0)) / max(stats.get("requests", 1), 1) * 100, 1)
            }

    return results


def output_json():
    """Output JSON for dashboard."""
    stats = get_all_stats(7)

    # Calculate totals
    totals = {
        "requests": sum(s["requests"] for s in stats.values()),
        "delivered": sum(s["delivered"] for s in stats.values()),
        "opens": sum(s["opens"] for s in stats.values()),
        "bounces": sum(s["bounces"] for s in stats.values())
    }

    output = {
        "timestamp": datetime.now().isoformat(),
        "period": "7 days",
        "accounts": stats,
        "totals": totals
    }

    print(json.dumps(output, indent=2))


def show_stats():
    """Display stats in terminal."""
    stats = get_all_stats(7)

    print(f"\n=== BREVO STATS (Last 7 Days) ===\n")

    total_sent = 0
    total_opens = 0

    for name, data in stats.items():
        print(f"{name} ({data['email']}):")
        print(f"  Sent: {data['requests']} | Delivered: {data['delivered']}")
        print(f"  Opens: {data['opens']} ({data['open_rate']}%)")
        print(f"  Bounces: {data['bounces']} ({data['bounce_rate']}%)")
        print()
        total_sent += data['requests']
        total_opens += data['opens']

    print(f"TOTAL: {total_sent} sent, {total_opens} opens")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON')
    parser.add_argument('--account', '-a', help='Specific account')
    parser.add_argument('--days', '-d', type=int, default=7, help='Days to report')
    args = parser.parse_args()

    if args.json:
        output_json()
    else:
        show_stats()


if __name__ == "__main__":
    main()
