#!/usr/bin/env python3
"""
Dashboard Text Reports - Toggle hide_charts for campaigns

Usage:
    python3 dashboard_text_reports.py --apply-all    # Set hide_charts=true for all
    python3 dashboard_text_reports.py --campaign X   # Toggle for specific campaign
    python3 dashboard_text_reports.py --status       # Show current settings
    python3 dashboard_text_reports.py --enable X     # Enable hide_charts for campaign
    python3 dashboard_text_reports.py --disable X    # Disable hide_charts for campaign
"""

import json
import argparse
import sys
from pathlib import Path

PIPELINE_JSON = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/pipeline.json"


def load_pipeline():
    """Load pipeline.json"""
    with open(PIPELINE_JSON, "r") as f:
        return json.load(f)


def save_pipeline(data):
    """Save pipeline.json with pretty formatting"""
    with open(PIPELINE_JSON, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {PIPELINE_JSON}")


def get_status(data):
    """Get hide_charts status for all campaigns"""
    campaigns = data.get("campaigns", {})
    results = []

    for name, config in campaigns.items():
        hide_charts = config.get("hide_charts", False)
        status = "text" if hide_charts else "charts"
        results.append((name, status, hide_charts))

    return results


def show_status():
    """Show current hide_charts settings for all campaigns"""
    data = load_pipeline()
    results = get_status(data)

    text_count = sum(1 for _, _, hc in results if hc)
    chart_count = len(results) - text_count

    print("\n=== DASHBOARD REPORT FORMAT ===\n")
    print(f"{'Campaign':<30} {'Format':<10}")
    print("-" * 42)

    for name, status, _ in sorted(results):
        marker = "[T]" if status == "text" else "[C]"
        print(f"{name:<30} {marker} {status}")

    print("-" * 42)
    print(f"\nTotal: {len(results)} campaigns")
    print(f"  Text reports: {text_count}")
    print(f"  Chart reports: {chart_count}")

    return text_count, chart_count


def apply_all():
    """Set hide_charts=true for all campaigns"""
    data = load_pipeline()
    campaigns = data.get("campaigns", {})

    modified = 0
    for name, config in campaigns.items():
        if not config.get("hide_charts"):
            config["hide_charts"] = True
            modified += 1
            print(f"  + {name}: enabled hide_charts")

    if modified > 0:
        save_pipeline(data)
        print(f"\nModified {modified} campaigns")
    else:
        print("All campaigns already have hide_charts=true")

    return modified


def toggle_campaign(campaign_name):
    """Toggle hide_charts for a specific campaign"""
    data = load_pipeline()
    campaigns = data.get("campaigns", {})

    if campaign_name not in campaigns:
        print(f"Error: Campaign '{campaign_name}' not found")
        print(f"Available: {', '.join(sorted(campaigns.keys()))}")
        return False

    current = campaigns[campaign_name].get("hide_charts", False)
    campaigns[campaign_name]["hide_charts"] = not current

    new_status = "text" if not current else "charts"
    print(f"Campaign '{campaign_name}': toggled to {new_status}")

    save_pipeline(data)
    return True


def set_campaign(campaign_name, enable=True):
    """Set hide_charts for a specific campaign"""
    data = load_pipeline()
    campaigns = data.get("campaigns", {})

    if campaign_name not in campaigns:
        print(f"Error: Campaign '{campaign_name}' not found")
        print(f"Available: {', '.join(sorted(campaigns.keys()))}")
        return False

    campaigns[campaign_name]["hide_charts"] = enable
    status = "text" if enable else "charts"
    print(f"Campaign '{campaign_name}': set to {status}")

    save_pipeline(data)
    return True


def main():
    parser = argparse.ArgumentParser(description="Dashboard Text Reports Manager")
    parser.add_argument("--status", action="store_true", help="Show current settings")
    parser.add_argument("--apply-all", action="store_true", help="Enable hide_charts for all campaigns")
    parser.add_argument("--campaign", type=str, help="Toggle hide_charts for specific campaign")
    parser.add_argument("--enable", type=str, help="Enable hide_charts for specific campaign")
    parser.add_argument("--disable", type=str, help="Disable hide_charts for specific campaign")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.apply_all:
        print("Applying hide_charts=true to all campaigns...")
        apply_all()
        show_status()
    elif args.campaign:
        toggle_campaign(args.campaign)
    elif args.enable:
        set_campaign(args.enable, enable=True)
    elif args.disable:
        set_campaign(args.disable, enable=False)
    else:
        # Default: show status
        show_status()


if __name__ == "__main__":
    main()
