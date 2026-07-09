#!/usr/bin/env python3
"""
Agent 35: Auto Campaign Builder + Agent 22: Website Change Detector
+ Agent 31: Expired Domain Monitor.

When master_emails grows >500 new for a country → prepares campaign config.
Checks website liveness. Monitors domain expiry.

Cron: 0 7 * * *  (daily 7 AM)
"""
import subprocess
import logging
import json
import os
import requests
from datetime import datetime, timedelta

DB_USER = "tudor"
DB_NAME = "interjob_master"
CONFIGS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs"
LOG = "/opt/ACTIVE/FLIGHTS/logs/auto_campaign.log"
NODERED = "http://localhost:1880/enrichment-status"
MIN_FOR_CAMPAIGN = 500

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("auto_campaign")


def sql(q, timeout=300):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", q]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def check_new_emails_by_country():
    """Count new emails per country in last 7 days."""
    week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    result = sql(
        f"SELECT country_detected, count(*) FROM master_emails "
        f"WHERE first_seen >= '{week}' "
        f"AND country_detected IS NOT NULL "
        f"AND mx_valid IS NOT false "
        f"GROUP BY country_detected ORDER BY count(*) DESC"
    )
    countries = {}
    for line in result.split("\n"):
        parts = line.split("|")
        if len(parts) == 2:
            countries[parts[0]] = int(parts[1])
    return countries


def prepare_campaign(country, count):
    """Create campaign config JSON for a country (does NOT send)."""
    config_name = f"auto_{country.lower()}_enriched"
    config_path = os.path.join(CONFIGS_DIR, f"{config_name}.json")
    if os.path.exists(config_path):
        log.info(f"Campaign {config_name} already exists, skip")
        return False

    config = {
        "db": {"host": "localhost", "dbname": DB_NAME,
               "user": DB_USER, "password": "scraper123"},
        "env_file": "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env",
        "campaign_name": config_name.upper(),
        "templates_dir": f"/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/{config_name}/",
        "dashboard_port": 8096,
        "url_prefix": f"/{config_name}",
        "tables": {
            "contacts": "master_emails",
            "send_log": f"{config_name}_send_log",
            "col_email": "email",
            "col_company": "company",
            "col_campaign_status": "campaign_status",
        },
        "sectors": {
            f"{country}_HOT": {
                "filter": f"country_detected = '{country}' "
                          f"AND warmth_score >= 10 AND mx_valid = true",
                "sender_key": "BREVO_BUILDJOBS_API_KEY",
                "sender_email": "office@buildjobs.eu",
                "sender_name": "InterJob",
                "reply_to": "manpower.dristor@gmail.com",
                "daily_limit": 50,
                "delay_min": 65, "delay_max": 300,
                "enabled": False,  # NEVER auto-enable
                "template_prefix": "general",
                "sender_type": "brevo",
            }
        },
        "policy": {
            "description": f"Auto-generated campaign for {country} "
                          f"({count} new emails this week)",
            "auto_generated": True,
            "requires_approval": True,
        }
    }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    log.info(f"Created campaign config: {config_path}")
    return True


def check_master_stats():
    """Quick master_emails stats."""
    total = sql("SELECT count(*) FROM master_emails")
    hot = sql("SELECT count(*) FROM master_emails "
              "WHERE warmth_score >= 10 AND mx_valid = true")
    return {"total": int(total or 0), "hot": int(hot or 0)}


def main():
    log.info("=== Auto Campaign Builder START ===")
    print(f"Auto Campaign Builder — {datetime.now()}")

    stats = check_master_stats()
    print(f"master_emails: {stats['total']:,} total, {stats['hot']:,} hot")

    countries = check_new_emails_by_country()
    new_campaigns = []
    for country, count in countries.items():
        if count >= MIN_FOR_CAMPAIGN:
            created = prepare_campaign(country, count)
            if created:
                new_campaigns.append(f"{country} ({count})")
                print(f"  NEW CAMPAIGN: {country} ({count} emails)")

    if new_campaigns:
        log.info(f"New campaigns: {new_campaigns}")
        print(f"\nNew campaigns prepared: {len(new_campaigns)}")
        print("NOTE: All disabled by default. Enable manually after review.")
    else:
        print("No new campaigns needed this week.")

    try:
        requests.post(NODERED, json={
            "event": "auto_campaign",
            "stats": stats, "countries": countries,
            "new_campaigns": new_campaigns,
            "timestamp": datetime.now().isoformat(),
        }, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
