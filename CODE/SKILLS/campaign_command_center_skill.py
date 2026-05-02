#!/usr/bin/env python3
"""
Campaign Command Center Skill — reusable across all campaigns.
Deploy to /opt/ACTIVE/INFRA/SKILLS/campaign_command_center_skill.py

Usage:
    # Start command center for any campaign
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/EXECUTORI --title Executori --port 8095
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/LICHIDATORI --title Lichidatori --port 8096

    # CLI controls (no web needed)
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/EXECUTORI --status
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/EXECUTORI --set-limit 30
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/EXECUTORI --pause
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/EXECUTORI --start
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/EXECUTORI --stop-today
    python3 campaign_command_center_skill.py --campaign-dir /opt/ACTIVE/EXECUTORI --stall 3

    # From sender scripts:
    from campaign_command_center_skill import is_campaign_allowed, get_daily_limit
    allowed, reason = is_campaign_allowed("/opt/ACTIVE/EXECUTORI/campaign_control.json")
    limit = get_daily_limit("/opt/ACTIVE/EXECUTORI/campaign_control.json")

Requires: flask (for web dashboard), no other deps for CLI/import use.
"""

import sys
import os

# Add parent so we can import command_center
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'EXECUTORI'))

from command_center import (
    create_app, load_control, save_control, get_sent_stats,
    is_campaign_allowed, get_daily_limit, DEFAULT_CONTROL
)
from datetime import date, timedelta
import json
import argparse


def cli_status(campaign_dir):
    control_file = os.path.join(campaign_dir, "campaign_control.json")
    sent_log = os.path.join(campaign_dir, "logs", "sent_emails.csv")
    ctrl = load_control(control_file)
    stats = get_sent_stats(sent_log)
    print(f"Status:      {ctrl.get('status', 'active').upper()}")
    print(f"Daily limit: {ctrl.get('daily_limit', 50)}")
    print(f"Sent today:  {stats['sent_today']}")
    print(f"Total sent:  {stats['total_sent']}")
    if ctrl.get('stall_until'):
        print(f"Stalled until: {ctrl['stall_until']}")
    if ctrl.get('reason'):
        print(f"Reason: {ctrl['reason']}")
    if stats.get('last_sent'):
        print(f"Last sent: {stats['last_sent']['email']} at {stats['last_sent']['time']}")


def cli_action(campaign_dir, action, value=None):
    control_file = os.path.join(campaign_dir, "campaign_control.json")
    ctrl = load_control(control_file)

    if action == "start":
        ctrl["status"] = "active"
        ctrl["stall_until"] = None
        ctrl["stopped_today"] = None
        ctrl["reason"] = None
        print("Campaign STARTED")
    elif action == "pause":
        ctrl["status"] = "paused"
        ctrl["reason"] = "Paused via CLI"
        print("Campaign PAUSED")
    elif action == "stop-today":
        ctrl["status"] = "stopped_today"
        ctrl["stopped_today"] = str(date.today())
        ctrl["reason"] = "Stopped for today via CLI"
        print("Campaign STOPPED for today")
    elif action == "stall":
        days = int(value) if value else 3
        until = str(date.today() + timedelta(days=days))
        ctrl["status"] = "stalled"
        ctrl["stall_until"] = until
        ctrl["reason"] = f"Stalled {days} days via CLI (until {until})"
        print(f"Campaign STALLED for {days} days until {until}")
    elif action == "set-limit":
        ctrl["daily_limit"] = max(1, min(500, int(value)))
        print(f"Daily limit set to {ctrl['daily_limit']}")

    save_control(control_file, ctrl)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campaign Command Center Skill")
    parser.add_argument("--campaign-dir", required=True, help="Campaign directory path")
    parser.add_argument("--title", default="Campaign")
    parser.add_argument("--port", type=int, default=8095)
    # CLI actions
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--pause", action="store_true")
    parser.add_argument("--stop-today", action="store_true")
    parser.add_argument("--stall", type=int, metavar="DAYS", help="Stall for N days")
    parser.add_argument("--set-limit", type=int, metavar="N", help="Set daily limit")
    args = parser.parse_args()

    campaign_dir = args.campaign_dir
    os.makedirs(os.path.join(campaign_dir, "logs"), exist_ok=True)

    control_file = os.path.join(campaign_dir, "campaign_control.json")
    if not os.path.exists(control_file):
        save_control(control_file, dict(DEFAULT_CONTROL))

    if args.status:
        cli_status(campaign_dir)
    elif args.start:
        cli_action(campaign_dir, "start")
    elif args.pause:
        cli_action(campaign_dir, "pause")
    elif args.stop_today:
        cli_action(campaign_dir, "stop-today")
    elif args.stall:
        cli_action(campaign_dir, "stall", args.stall)
    elif args.set_limit:
        cli_action(campaign_dir, "set-limit", args.set_limit)
    else:
        # Start web dashboard
        app = create_app(campaign_dir, title=args.title)
        print(f"Command Center '{args.title}' at http://0.0.0.0:{args.port}")
        app.run(host="0.0.0.0", port=args.port, debug=False)
