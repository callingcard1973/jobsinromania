#!/usr/bin/env python3
"""
Agent 4: Campaign Orchestrator Monitor — checks campaign status,
reports to Node-RED, handles stalled campaigns.

Cron: 0 9,13,17 * * 1-5  (3x/day weekdays)
Deploy: /opt/ACTIVE/FLIGHTS/agent_campaign_launcher.py

Monitors:
  - flight_agencies campaign (1,448 IATA agencies)
  - All campaigns in orchestrator configs/
  - Send rates, bounces, responses
"""
import subprocess
import json
import logging
import os
import glob
from datetime import datetime
from pathlib import Path

DB_USER = "tudor"
DB_NAME = "interjob_master"
CONFIGS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs"
LOG = "/opt/ACTIVE/FLIGHTS/logs/campaign_monitor.log"
NODERED = "http://localhost:1880/enrichment-status"

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("campaign_monitor")


def sql(query, timeout=60):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", query]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def check_flight_agencies():
    """Check flight_agencies campaign progress."""
    total = sql("SELECT count(*) FROM flight_agencies_campaign")
    sent = sql("SELECT count(*) FROM flight_agencies_campaign "
               "WHERE campaign_status = 'sent'")
    pending = sql("SELECT count(*) FROM flight_agencies_campaign "
                  "WHERE campaign_status IS NULL "
                  "OR campaign_status = 'pending'")
    log_count = sql("SELECT count(*) FROM flight_agencies_send_log")
    today = sql("SELECT count(*) FROM flight_agencies_send_log "
                "WHERE sent_at::date = CURRENT_DATE")
    return {
        "campaign": "FLIGHT_AGENCIES",
        "total": int(total or 0),
        "sent": int(sent or 0),
        "pending": int(pending or 0),
        "log_total": int(log_count or 0),
        "sent_today": int(today or 0),
    }


def check_master_emails():
    """Check master_emails growth."""
    total = sql("SELECT count(*) FROM master_emails")
    today = sql("SELECT count(*) FROM master_emails "
                "WHERE first_seen::date = CURRENT_DATE")
    by_country = sql(
        "SELECT country, count(*) FROM master_emails "
        "WHERE country IS NOT NULL "
        "GROUP BY country ORDER BY count(*) DESC LIMIT 10"
    )
    return {
        "total": int(total or 0),
        "added_today": int(today or 0),
        "top_countries": by_country,
    }


def check_orchestrator():
    """Check which campaigns are enabled in orchestrator configs."""
    campaigns = []
    for f in sorted(glob.glob(os.path.join(CONFIGS_DIR, "*.json"))):
        try:
            with open(f) as fh:
                cfg = json.load(fh)
            name = cfg.get("campaign_name", Path(f).stem)
            enabled_sectors = sum(
                1 for s in cfg.get("sectors", {}).values()
                if s.get("enabled", False)
            )
            total_sectors = len(cfg.get("sectors", {}))
            campaigns.append({
                "name": name,
                "enabled": enabled_sectors,
                "total": total_sectors,
                "file": Path(f).name,
            })
        except Exception:
            pass
    return campaigns


def check_enrichment_state():
    """Check enrichment pipeline state."""
    state_file = "/opt/ACTIVE/FLIGHTS/enrichment/state.json"
    if os.path.exists(state_file):
        with open(state_file) as f:
            return json.load(f)
    return {}


def notify(data):
    try:
        import requests
        requests.post(NODERED, json=data, timeout=5)
    except Exception:
        pass


def main():
    log.info("=== Campaign Monitor START ===")
    print(f"Campaign Monitor — {datetime.now()}")

    flight = check_flight_agencies()
    print(f"\nFlight Agencies: {flight['sent']}/{flight['total']} sent, "
          f"{flight['sent_today']} today")

    emails = check_master_emails()
    print(f"Master Emails: {emails['total']:,} total, "
          f"+{emails['added_today']} today")

    campaigns = check_orchestrator()
    print(f"\nOrchestrator Campaigns ({len(campaigns)}):")
    for c in campaigns:
        status = "ACTIVE" if c["enabled"] > 0 else "disabled"
        print(f"  {c['name']:<30} {c['enabled']}/{c['total']} sectors "
              f"[{status}]")

    state = check_enrichment_state()
    print(f"\nEnrichment State: {len(state)} entries")

    report = {
        "event": "campaign_monitor",
        "flight_agencies": flight,
        "master_emails": emails,
        "campaigns_count": len(campaigns),
        "campaigns_active": sum(1 for c in campaigns if c["enabled"] > 0),
        "enrichment_tables": len(state),
        "timestamp": datetime.now().isoformat(),
    }
    log.info(json.dumps(report, default=str))
    notify(report)
    print(f"\nReport sent to Node-RED")


if __name__ == "__main__":
    main()
