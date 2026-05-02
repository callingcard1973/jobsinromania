#!/usr/bin/env python3
"""
Alert Configuration - Controls which alerts get sent via Telegram.
Edit this file to enable/disable specific alert sources.

Used by: agent_governor.py, daily_digest.py, credential_validator.py, etc.

Usage:
    from alert_config import should_alert

    if should_alert("governor_briefing"):
        send_telegram(msg)
"""

import os
from datetime import datetime

# Master switch - set False to silence ALL Telegram alerts
ALERTS_ENABLED = True

# Per-source control: True = send, False = log only
ALERT_SOURCES = {
    "governor_started": False,      # "Agent Governor started" - noisy, not useful
    "governor_briefing": False,     # Daily agent briefings - disable if not using agents
    "governor_stale_leads": False,  # Stale lead alerts - disable if not actively using CRM
    "daily_digest": True,           # Daily system digest - keep (1x/day)
    "credential_validator": False,  # Credential checks - only alert on failures
    "sender_healthcheck": True,     # Sender health - keep (important)
    "campaign_needs_human": True,   # Campaign errors needing human fix - keep
    "reply_monitor": True,          # New replies detected - keep (actionable)
    "bounce_classifier": False,     # Bounce classification results - just log
    "spam_learner": False,          # Spam learning results - just log
    "weekly_report": True,          # Monthly report - keep
    "followup_digest": False,       # Follow-up suggestions - disable
    "followup_propose": False,      # Follow-up proposals - disable
}

# Quiet hours: no alerts between these times (24h format)
QUIET_START = 22  # 10 PM
QUIET_END = 7     # 7 AM


def should_alert(source: str) -> bool:
    """Check if an alert source should send Telegram notifications."""
    if not ALERTS_ENABLED:
        return False

    # Check quiet hours
    hour = datetime.now().hour
    if QUIET_START <= hour or hour < QUIET_END:
        # During quiet hours, only critical alerts
        if source not in ("campaign_needs_human", "sender_healthcheck"):
            return False

    return ALERT_SOURCES.get(source, True)


def get_status():
    """Print current alert configuration."""
    print("Alert Configuration:")
    print(f"  Master switch: {"ON" if ALERTS_ENABLED else "OFF"}")
    print(f"  Quiet hours: {QUIET_START}:00 - {QUIET_END}:00")
    print(f"\n  Sources:")
    for source, enabled in sorted(ALERT_SOURCES.items()):
        status = "ON" if enabled else "OFF"
        print(f"    {source:<30} {status}")


if __name__ == "__main__":
    get_status()
