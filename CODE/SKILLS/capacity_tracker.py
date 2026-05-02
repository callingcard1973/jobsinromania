#!/usr/bin/env python3
"""
Capacity Tracker - Track sends per sender across all campaigns.

Monitors email sending capacity utilization across:
- A2 SMTP domains (10 domains, 500/day each)
- Brevo accounts (9 accounts, 290/day each)
- Gmail accounts (5 accounts, 100/day each)

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_tracker.py --status
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_tracker.py --sender brevo_interjob
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_tracker.py --json
"""
import os
import sys
import glob
import json
import argparse
from datetime import datetime, date
from collections import defaultdict
from pathlib import Path

# Add shared modules
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Import campaign config
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS')
try:
    from config import AVAILABLE_SENDERS, CAMPAIGNS
except ImportError:
    AVAILABLE_SENDERS = {}
    CAMPAIGNS = {}

# ============================================================
# SENDER DEFINITIONS
# ============================================================

# Full sender limits (post-warmup)
SENDER_LIMITS = {
    # A2 SMTP (7 original domains)
    "a2_horecaworkers": 500,
    "a2_meatworkers": 500,
    "a2_electricjobs": 500,
    "a2_mechanicjobs": 500,
    "a2_farmworkers": 500,
    "a2_factoryjobs": 500,
    "a2_warehouseworkers": 500,
    # A2 SMTP (HORECA 2026 domains)
    "a2_horeca2026_eu": 500,
    "a2_horeca2026_com": 500,
    "a2_horeca2026_online": 500,
    # Brevo accounts
    "brevo_interjob": 290,
    "brevo_mivromania": 250,
    "brevo_mivromania_online": 290,
    "brevo_buildjobs": 250,
    "brevo_factoryjobs": 290,
    "brevo_careworkers": 290,
    "brevo_warehouse": 290,
    "brevo_cifn": 290,
    "brevo_nepalezi": 290,
    "brevo_expatsinromania": 290,
    # Gmail accounts (only elena and manpower used for sending)
    "gmail_manpowerdristor": 100,
    "gmail_elenamanpowerdristor": 100,
    # Note: Other gmail accounts not used for campaigns
    # "gmail_expatsinromania": 100,  # Not used
    # "gmail_cumparlegume": 100,     # Not used
    # "gmail_casafaurbucuresti": 50, # Not used
    # Yahoo - not used for campaigns
    # "yahoo_secretariatagentieasia": 50,
}

# Sector mapping for sender assignment
SECTOR_MAPPING = {
    "HORECA": ["a2_horecaworkers", "a2_horeca2026_eu", "a2_horeca2026_com", "a2_horeca2026_online", "brevo_mivromania"],
    "FACTORY": ["a2_factoryjobs", "brevo_factoryjobs", "brevo_buildjobs"],
    "WAREHOUSE": ["a2_warehouseworkers", "brevo_warehouse", "brevo_careworkers"],
    "AGRICULTURE": ["a2_farmworkers", "brevo_cifn"],
    "FOOD": ["a2_meatworkers", "brevo_cifn"],
    "CONSTRUCTION": ["brevo_buildjobs", "a2_factoryjobs"],
    "BUILDJOBS": ["brevo_buildjobs"],  # Force brevo_buildjobs only
    "TECHNICAL": ["a2_electricjobs", "a2_mechanicjobs"],
    "CARE": ["brevo_careworkers"],
    "ELECTRICAL": ["a2_electricjobs", "a2_mechanicjobs"],
    "GENERAL": ["brevo_interjob", "brevo_mivromania_online", "brevo_expatsinromania"],
    "RECRUITMENT": ["brevo_interjob", "brevo_mivromania"],
    "NORDIC": ["brevo_expatsinromania", "brevo_nepalezi"],
    "ROMANIA": ["brevo_mivromania", "brevo_mivromania_online", "brevo_buildjobs"],
}

# Log directories to scan
LOG_DIRS = [
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/*/logs",
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/DATA/*/logs",
]

# ============================================================
# CAPACITY TRACKING
# ============================================================

def parse_log_line(line: str) -> dict:
    """Parse a log line and extract sender and status."""
    # Format: 2026-02-05 09:00:00 [sender] | STATUS | email | message
    try:
        if " | " not in line:
            return None

        parts = line.split(" | ")
        if len(parts) < 3:
            return None

        # Extract date, sender from first part
        first_part = parts[0]
        if "[" not in first_part or "]" not in first_part:
            return None

        # Get date
        date_str = first_part.split()[0]

        # Get sender
        sender_start = first_part.index("[") + 1
        sender_end = first_part.index("]")
        sender = first_part[sender_start:sender_end]

        # Get status
        status = parts[1].strip()

        return {
            "date": date_str,
            "sender": sender,
            "status": status,
            "email": parts[2].strip() if len(parts) > 2 else None,
        }
    except Exception:
        return None


def get_today_sends() -> dict:
    """Get sends per sender for today from all campaign logs."""
    today = date.today().strftime("%Y-%m-%d")
    today_file = date.today().strftime("%Y%m%d")

    sends = defaultdict(int)

    # Find all log files for today
    for log_pattern in LOG_DIRS:
        for log_dir in glob.glob(log_pattern):
            # Check for sent_YYYYMMDD.log format
            sent_log = os.path.join(log_dir, f"sent_{today_file}.log")
            if os.path.exists(sent_log):
                try:
                    with open(sent_log, "r") as f:
                        for line in f:
                            parsed = parse_log_line(line)
                            if parsed and parsed["status"] == "OK":
                                sends[parsed["sender"]] += 1
                except Exception as e:
                    pass

            # Also check campaign_YYYYMMDD.log
            campaign_log = os.path.join(log_dir, f"campaign_{today_file}.log")
            if os.path.exists(campaign_log):
                try:
                    with open(campaign_log, "r") as f:
                        for line in f:
                            parsed = parse_log_line(line)
                            if parsed and parsed["status"] == "OK":
                                sends[parsed["sender"]] += 1
                except Exception as e:
                    pass

    return dict(sends)


def get_sender_capacity() -> dict:
    """Get remaining capacity per sender for today."""
    sends = get_today_sends()
    capacity = {}

    for sender, limit in SENDER_LIMITS.items():
        used = sends.get(sender, 0)
        remaining = max(0, limit - used)
        capacity[sender] = {
            "limit": limit,
            "used": used,
            "remaining": remaining,
            "utilization": round(used / limit * 100, 1) if limit > 0 else 0,
        }

    return capacity


def get_total_capacity() -> dict:
    """Get total capacity summary by sender type."""
    capacity = get_sender_capacity()

    totals = {
        "a2": {"limit": 0, "used": 0, "remaining": 0},
        "brevo": {"limit": 0, "used": 0, "remaining": 0},
        "gmail": {"limit": 0, "used": 0, "remaining": 0},
        "yahoo": {"limit": 0, "used": 0, "remaining": 0},
    }

    for sender, stats in capacity.items():
        if sender.startswith("a2_"):
            cat = "a2"
        elif sender.startswith("brevo_"):
            cat = "brevo"
        elif sender.startswith("gmail_"):
            cat = "gmail"
        elif sender.startswith("yahoo_"):
            cat = "yahoo"
        else:
            continue

        totals[cat]["limit"] += stats["limit"]
        totals[cat]["used"] += stats["used"]
        totals[cat]["remaining"] += stats["remaining"]

    # Calculate utilization
    for cat in totals:
        if totals[cat]["limit"] > 0:
            totals[cat]["utilization"] = round(
                totals[cat]["used"] / totals[cat]["limit"] * 100, 1
            )
        else:
            totals[cat]["utilization"] = 0

    # Grand total
    totals["total"] = {
        "limit": sum(t["limit"] for t in totals.values() if "limit" in t),
        "used": sum(t["used"] for t in totals.values() if "used" in t),
        "remaining": sum(t["remaining"] for t in totals.values() if "remaining" in t),
    }
    totals["total"]["utilization"] = round(
        totals["total"]["used"] / totals["total"]["limit"] * 100, 1
    ) if totals["total"]["limit"] > 0 else 0

    return totals


def get_available_senders(sector: str = None, min_capacity: int = 1) -> list:
    """Get senders with available capacity, optionally filtered by sector."""
    capacity = get_sender_capacity()
    available = []

    # Get sector-specific senders if specified
    if sector and sector.upper() in SECTOR_MAPPING:
        preferred = SECTOR_MAPPING[sector.upper()]
    else:
        preferred = list(SENDER_LIMITS.keys())

    for sender in preferred:
        if sender in capacity and capacity[sender]["remaining"] >= min_capacity:
            available.append({
                "sender": sender,
                "remaining": capacity[sender]["remaining"],
                "type": sender.split("_")[0],
            })

    # Sort by remaining capacity (highest first)
    available.sort(key=lambda x: x["remaining"], reverse=True)

    return available


# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def print_status():
    """Print capacity status table."""
    capacity = get_sender_capacity()
    totals = get_total_capacity()

    print(f"\n=== SENDER CAPACITY STATUS ({date.today()}) ===\n")

    # Group by type
    groups = {
        "A2 SMTP": [s for s in capacity if s.startswith("a2_")],
        "Brevo": [s for s in capacity if s.startswith("brevo_")],
        "Gmail": [s for s in capacity if s.startswith("gmail_")],
        "Yahoo": [s for s in capacity if s.startswith("yahoo_")],
    }

    for group_name, senders in groups.items():
        if not senders:
            continue

        print(f"\n{group_name}:")
        print("-" * 60)
        print(f"{'Sender':<30} {'Used':>8} {'Limit':>8} {'Remain':>8} {'%':>6}")
        print("-" * 60)

        for sender in sorted(senders):
            stats = capacity[sender]
            bar = "█" * int(stats["utilization"] / 10) + "░" * (10 - int(stats["utilization"] / 10))
            print(f"{sender:<30} {stats['used']:>8} {stats['limit']:>8} {stats['remaining']:>8} {stats['utilization']:>5.1f}%")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("-" * 60)
    print(f"{'Type':<20} {'Used':>10} {'Limit':>10} {'Remain':>10} {'%':>8}")
    print("-" * 60)

    for cat, stats in totals.items():
        if cat == "total":
            print("-" * 60)
        print(f"{cat.upper():<20} {stats['used']:>10} {stats['limit']:>10} {stats['remaining']:>10} {stats['utilization']:>7.1f}%")

    print("=" * 60)


def print_json():
    """Print capacity as JSON."""
    data = {
        "date": date.today().isoformat(),
        "senders": get_sender_capacity(),
        "totals": get_total_capacity(),
        "available": get_available_senders(),
    }
    print(json.dumps(data, indent=2))


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Track email sender capacity")
    parser.add_argument("--status", action="store_true", help="Show capacity status")
    parser.add_argument("--sender", help="Show specific sender capacity")
    parser.add_argument("--sector", help="Show available senders for sector")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--available", action="store_true", help="List available senders")

    args = parser.parse_args()

    if args.json:
        print_json()
    elif args.sender:
        capacity = get_sender_capacity()
        if args.sender in capacity:
            stats = capacity[args.sender]
            print(f"{args.sender}: {stats['used']}/{stats['limit']} used, {stats['remaining']} remaining ({stats['utilization']}%)")
        else:
            print(f"Unknown sender: {args.sender}")
            sys.exit(1)
    elif args.sector:
        available = get_available_senders(args.sector)
        print(f"\nAvailable senders for {args.sector.upper()}:")
        for s in available:
            print(f"  {s['sender']}: {s['remaining']} remaining")
    elif args.available:
        available = get_available_senders()
        print("\nAll available senders:")
        for s in available:
            print(f"  {s['sender']} ({s['type']}): {s['remaining']} remaining")
    else:
        print_status()


if __name__ == "__main__":
    main()
