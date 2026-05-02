#!/usr/bin/env python3
"""
Capacity Dashboard - Real-time view of email sending capacity.

Shows:
- Sender utilization (today)
- Campaign contact levels
- Projected exhaustion time
- Alerts for dry campaigns

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_dashboard.py             # Full dashboard
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_dashboard.py --alerts    # Only alerts
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_dashboard.py --json      # JSON output
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_dashboard.py --telegram  # Send to Telegram
"""
import os
import sys
import json
import argparse
from datetime import datetime, date, timedelta
from typing import List, Dict

# Add shared modules
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
from skills_common import to_ascii
from alerting import send_telegram
from capacity_tracker import (
    get_sender_capacity,
    get_total_capacity,
    get_available_senders,
    SENDER_LIMITS,
)
from capacity_maximizer import (
    get_all_campaign_status,
    get_optimal_assignments,
    load_state,
)

# ============================================================
# ALERT THRESHOLDS
# ============================================================

ALERT_THRESHOLDS = {
    "campaign_contacts_low": 100,      # Alert if < 100 contacts remaining
    "campaign_contacts_critical": 20,  # Critical if < 20 contacts
    "sender_utilization_low": 20,      # Warning if sender < 20% utilized
    "sender_utilization_high": 95,     # Warning if sender > 95% utilized
    "total_utilization_target": 80,    # Target utilization
}

# ============================================================
# DASHBOARD DATA
# ============================================================

def get_dashboard_data() -> dict:
    """Gather all dashboard data."""
    now = datetime.now()

    # Sender capacity
    sender_capacity = get_sender_capacity()
    total_capacity = get_total_capacity()

    # Campaign status
    campaigns = get_all_campaign_status()

    # Assignments
    assignments = get_optimal_assignments()

    # State
    state = load_state()

    # Alerts
    alerts = generate_alerts(sender_capacity, campaigns)

    return {
        "timestamp": now.isoformat(),
        "date": date.today().isoformat(),
        "senders": sender_capacity,
        "totals": total_capacity,
        "campaigns": campaigns,
        "assignments": assignments,
        "state": state,
        "alerts": alerts,
    }


def generate_alerts(sender_capacity: dict, campaigns: list) -> List[dict]:
    """Generate alerts based on current status."""
    alerts = []

    # Check for dry campaigns
    for c in campaigns:
        if not c["enabled"]:
            continue

        if c["total_contacts"] < ALERT_THRESHOLDS["campaign_contacts_critical"]:
            alerts.append({
                "type": "critical",
                "category": "campaign",
                "message": f"CRITICAL: {c['name']} has only {c['total_contacts']} contacts remaining",
                "campaign": c["name"],
            })
        elif c["total_contacts"] < ALERT_THRESHOLDS["campaign_contacts_low"]:
            alerts.append({
                "type": "warning",
                "category": "campaign",
                "message": f"WARNING: {c['name']} has only {c['total_contacts']} contacts remaining",
                "campaign": c["name"],
            })

    # Check for underutilized senders
    for sender, stats in sender_capacity.items():
        if stats["utilization"] < ALERT_THRESHOLDS["sender_utilization_low"] and stats["limit"] > 100:
            alerts.append({
                "type": "info",
                "category": "sender",
                "message": f"Underutilized: {sender} at {stats['utilization']:.1f}% ({stats['remaining']} remaining)",
                "sender": sender,
            })

    # Check total utilization
    totals = get_total_capacity()
    if totals["total"]["utilization"] < 50:
        alerts.append({
            "type": "warning",
            "category": "utilization",
            "message": f"Low utilization: {totals['total']['utilization']:.1f}% of total capacity used",
        })

    return alerts


# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def print_dashboard():
    """Print full dashboard to terminal."""
    data = get_dashboard_data()

    print("\n" + "=" * 80)
    print(f"  CAPACITY DASHBOARD - {data['timestamp']}")
    print("=" * 80)

    # Overall summary
    totals = data["totals"]
    print(f"\n  TOTAL CAPACITY: {totals['total']['used']}/{totals['total']['limit']} ({totals['total']['utilization']:.1f}%)")

    bar_len = 50
    filled = int(totals["total"]["utilization"] / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"  [{bar}]")

    # By type
    print(f"\n  By Type:")
    for cat in ["a2", "brevo", "gmail"]:
        if cat in totals:
            t = totals[cat]
            print(f"    {cat.upper():<8} {t['used']:>6}/{t['limit']:<6} ({t['utilization']:.1f}%)")

    # Sender details
    print(f"\n  SENDER DETAILS:")
    print("  " + "-" * 76)
    print(f"  {'Sender':<30} {'Used':>8} {'Limit':>8} {'Remain':>8} {'%':>8}")
    print("  " + "-" * 76)

    senders = data["senders"]
    for sender in sorted(senders.keys()):
        s = senders[sender]
        if s["limit"] > 0:
            util_bar = "█" * int(s["utilization"] / 10) + "░" * (10 - int(s["utilization"] / 10))
            print(f"  {sender:<30} {s['used']:>8} {s['limit']:>8} {s['remaining']:>8} {s['utilization']:>6.1f}%")

    # Campaign status
    print(f"\n  CAMPAIGN STATUS:")
    print("  " + "-" * 76)
    print(f"  {'Campaign':<25} {'Contacts':>10} {'Sent':>8} {'Limit':>8} {'Status':<15}")
    print("  " + "-" * 76)

    for c in data["campaigns"]:
        if not c["enabled"]:
            continue
        status = "READY" if c["can_send"] else "BLOCKED"
        if c["total_contacts"] < ALERT_THRESHOLDS["campaign_contacts_low"]:
            status = "LOW CONTACTS"
        print(f"  {c['name']:<25} {c['total_contacts']:>10} {c['sent_today']:>8} {c['daily_limit']:>8} {status:<15}")

    # Alerts
    if data["alerts"]:
        print(f"\n  ALERTS ({len(data['alerts'])}):")
        print("  " + "-" * 76)
        for alert in data["alerts"]:
            icon = "🔴" if alert["type"] == "critical" else "🟡" if alert["type"] == "warning" else "🔵"
            print(f"  {icon} {alert['message']}")

    # Next actions
    if data["assignments"]:
        print(f"\n  NEXT ASSIGNMENTS:")
        print("  " + "-" * 76)
        for a in data["assignments"][:5]:
            print(f"  -> {a['campaign']:<25} via {a['sender']:<25} (batch {a['batch_size']})")

    print("\n" + "=" * 80)


def print_alerts_only():
    """Print only alerts."""
    data = get_dashboard_data()

    if not data["alerts"]:
        print("No alerts")
        return

    print(f"\n=== ALERTS ({datetime.now()}) ===\n")
    for alert in data["alerts"]:
        icon = "[CRITICAL]" if alert["type"] == "critical" else "[WARNING]" if alert["type"] == "warning" else "[INFO]"
        print(f"{icon} {alert['message']}")


def send_telegram_summary():
    """Send summary to Telegram."""
    data = get_dashboard_data()
    totals = data["totals"]

    # Build message
    lines = [
        f"📊 Capacity Dashboard ({date.today()})",
        "",
        f"Total: {totals['total']['used']}/{totals['total']['limit']} ({totals['total']['utilization']:.1f}%)",
        f"A2: {totals['a2']['used']}/{totals['a2']['limit']}",
        f"Brevo: {totals['brevo']['used']}/{totals['brevo']['limit']}",
    ]

    # Add alerts
    critical_alerts = [a for a in data["alerts"] if a["type"] == "critical"]
    if critical_alerts:
        lines.append("")
        lines.append("⚠️ Critical:")
        for a in critical_alerts[:3]:
            lines.append(f"  - {a['message']}")

    # Add next assignments
    if data["assignments"]:
        lines.append("")
        lines.append("Next:")
        for a in data["assignments"][:3]:
            lines.append(f"  {a['campaign']} -> {a['sender']}")

    message = "\n".join(lines)
    send_telegram(message)
    print("Sent to Telegram")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Capacity Dashboard")
    parser.add_argument("--alerts", action="store_true", help="Show only alerts")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--telegram", action="store_true", help="Send to Telegram")
    parser.add_argument("--summary", action="store_true", help="Brief summary")

    args = parser.parse_args()

    if args.json:
        data = get_dashboard_data()
        print(json.dumps(data, indent=2, default=str))
    elif args.telegram:
        send_telegram_summary()
    elif args.alerts:
        print_alerts_only()
    elif args.summary:
        totals = get_total_capacity()
        print(f"Capacity: {totals['total']['used']}/{totals['total']['limit']} ({totals['total']['utilization']:.1f}%)")
    else:
        print_dashboard()


if __name__ == "__main__":
    main()
