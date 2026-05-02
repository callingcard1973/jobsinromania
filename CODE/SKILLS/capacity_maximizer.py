#!/usr/bin/env python3
"""
Capacity Maximizer - Orchestrator for maximum email sending utilization.

Runs every 30 minutes to:
1. Check all sender capacities
2. Check all campaigns with contacts remaining
3. Match campaigns to best available senders
4. Send batches while respecting limits
5. Report utilization metrics

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_maximizer.py --once           # Run one cycle
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_maximizer.py --once --dry-run # Preview only
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_maximizer.py --daemon         # Run continuously
    python3 /opt/ACTIVE/INFRA/SKILLS/capacity_maximizer.py --status         # Show status
"""
import os
import sys
import csv
import json
import time
import glob
import argparse
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from collections import defaultdict

# Add shared modules
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
from skills_common import to_ascii
from alerting import send_telegram
from capacity_tracker import (
    get_sender_capacity,
    get_total_capacity,
    SENDER_LIMITS,
    SECTOR_MAPPING,
)
from smart_sender import (
    get_best_sender,
    get_sender_for_campaign,
    CAMPAIGN_SECTOR_MAP,
)

# Import campaign config
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS')
from config import AVAILABLE_SENDERS, CAMPAIGNS, CAMPAIGNS_DIR

# Import sector config if available
try:
    from config import CAMPAIGN_SECTORS
except ImportError:
    CAMPAIGN_SECTORS = {}

# ============================================================
# CONFIGURATION
# ============================================================

# Orchestrator settings
BATCH_SIZE = 50           # Emails per batch
MIN_DELAY_SECONDS = 180   # Minimum 3 minutes between sends
CYCLE_INTERVAL = 1800     # 30 minutes between full cycles
BATCH_DELAY = 300         # 5 minutes between batches

# Priority levels for campaigns (lower = higher priority)
CAMPAIGN_PRIORITY = {
    # Instant campaigns (fresh leads) - highest priority
    "ANOFM_INSTANT": 1,
    "EURES_INSTANT": 1,
    "MIV_IMM": 1,
    # High volume active campaigns
    "horeca2026": 2,
    "CONSTRUCT2026": 2,
    "poland_kraz": 2,
    # Active segment campaigns
    "ANOFM_SEGMENTS": 3,
    "EUFUNDS2026": 3,
    "SEAP2025": 3,
    # General outreach
    "EURES_AGENCIES": 4,
    "factoryjobs": 4,
    "cifn_nepal": 4,
    "bulgaria": 4,
    # Lower priority
    "recruitment_md_agencies": 5,
    "outreach": 6,
}

# Use imported sector config, with fallback
def get_campaign_sector(campaign_name: str) -> str:
    """Get sector for a campaign from config or CAMPAIGN_SECTOR_MAP."""
    if campaign_name in CAMPAIGN_SECTORS:
        return CAMPAIGN_SECTORS[campaign_name]
    return CAMPAIGN_SECTOR_MAP.get(campaign_name, "GENERAL")

# State file
STATE_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/DATA/capacity_maximizer_state.json"
LOG_DIR = "/opt/ACTIVE/INFRA/LOGS/capacity_maximizer"

# ============================================================
# STATE MANAGEMENT
# ============================================================

def load_state() -> dict:
    """Load orchestrator state."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_run": None,
        "daily_sends": {},
        "campaign_last_batch": {},
    }


def save_state(state: dict):
    """Save orchestrator state."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ============================================================
# CAMPAIGN SCRIPT DISCOVERY
# ============================================================

def find_campaign_send_script(campaign_name: str) -> Optional[str]:
    """Find the send script for a campaign."""
    # Try multiple case variations
    variations = [
        campaign_name,
        campaign_name.upper(),
        campaign_name.lower(),
        campaign_name.title(),
        campaign_name.replace("_", ""),
    ]

    for name in variations:
        campaign_dir = f"/opt/ACTIVE/EMAIL/CAMPAIGNS/{name}"
        if os.path.isdir(campaign_dir):
            # Find send scripts in this folder
            scripts = glob.glob(os.path.join(campaign_dir, "send_*.py"))
            if scripts:
                # Prefer a2_safe, then combined, then brevo, then any
                for pref in ["a2_safe", "combined", "brevo", "a2"]:
                    for s in scripts:
                        if pref in s:
                            return s
                return scripts[0]

    # Special mappings for mismatched names
    name_map = {
        "poland_kraz": "POLAND",
        "factoryjobs": "FACTORY_EU",
        "recruitment_md_agencies": "RECRUITMENT_EU",
    }

    if campaign_name in name_map:
        mapped = name_map[campaign_name]
        campaign_dir = f"/opt/ACTIVE/EMAIL/CAMPAIGNS/{mapped}"
        if os.path.isdir(campaign_dir):
            scripts = glob.glob(os.path.join(campaign_dir, "send_*.py"))
            if scripts:
                return scripts[0]

    # Check for non-standard script names (kraz_campaign.py, etc.)
    alt_scripts = {
        "poland_kraz": "/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND/kraz_campaign.py",
    }
    if campaign_name in alt_scripts and os.path.exists(alt_scripts[campaign_name]):
        return alt_scripts[campaign_name]

    return None


# Campaigns that have working send scripts
CAMPAIGNS_WITH_SCRIPTS = {
    "horeca2026": "/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026/send_horeca_a2_safe.py",
    "EURES_AGENCIES": "/opt/ACTIVE/EMAIL/CAMPAIGNS/EURES_AGENCIES/send_eures_agencies.py",
    "cifn_nepal": "/opt/ACTIVE/EMAIL/CAMPAIGNS/CIFN_NEPAL/send_nepal.py",
    "bulgaria": "/opt/ACTIVE/EMAIL/CAMPAIGNS/BULGARIA/send_bulgaria_new.py",
    "factoryjobs": "/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/send_factory_brevo.py",
    "AGRI": "/opt/ACTIVE/EMAIL/CAMPAIGNS/AGRI/send_agri_brevo.py",
    "ANOFM": "/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/send_anofm_brevo.py",
    "ANOFM_SEGMENTS": "/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_SEGMENTS/send_segments.py",
    # Added new campaigns
    "CONSTRUCT2026": "/opt/ACTIVE/EMAIL/CAMPAIGNS/CONSTRUCT2026/send_construct_a2.py",
    "ELECTRICJOBS_A2": "/opt/ACTIVE/EMAIL/CAMPAIGNS/ELECTRICJOBS_A2/send_electric_a2.py",
    "CAREWORKERS_BREVO": "/opt/ACTIVE/EMAIL/CAMPAIGNS/CAREWORKERS_BREVO/send_careworkers_brevo.py",
    "BUILDJOBS_BREVO": "/opt/ACTIVE/EMAIL/CAMPAIGNS/BUILDJOBS_BREVO/send_buildjobs_brevo.py",
}


# ============================================================
# CAMPAIGN ANALYSIS
# ============================================================

def count_contacts(csv_path: str) -> int:
    """Count contacts in a CSV file."""
    if not os.path.exists(csv_path):
        return 0
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def count_sent_today(campaign_name: str) -> int:
    """Count emails sent today for a campaign."""
    today_file = date.today().strftime("%Y%m%d")

    # Check multiple log locations
    log_patterns = [
        f"/opt/ACTIVE/EMAIL/CAMPAIGNS/{campaign_name}/logs/sent_{today_file}.log",
        f"/opt/ACTIVE/EMAIL/CAMPAIGNS/DATA/{campaign_name}/logs/sent_{today_file}.log",
    ]

    count = 0
    for pattern in log_patterns:
        if os.path.exists(pattern):
            try:
                with open(pattern, "r") as f:
                    for line in f:
                        if " | OK | " in line:
                            count += 1
            except Exception:
                pass

    return count


def get_campaign_status(campaign_name: str, config: dict) -> dict:
    """Get detailed status of a campaign."""
    contacts_path = config.get("contacts", "")

    # Handle segment directories
    if os.path.isdir(contacts_path):
        total_contacts = 0
        for csv_file in glob.glob(os.path.join(contacts_path, "*.csv")):
            total_contacts += count_contacts(csv_file)
    else:
        total_contacts = count_contacts(contacts_path)

    sent_today = count_sent_today(campaign_name)
    daily_limit = config.get("daily_limit", 290)
    remaining_limit = max(0, daily_limit - sent_today)

    # Get sector
    sector = get_campaign_sector(campaign_name)

    # Get priority
    priority = CAMPAIGN_PRIORITY.get(campaign_name, 5)

    return {
        "name": campaign_name,
        "enabled": config.get("enabled", False),
        "total_contacts": total_contacts,
        "sent_today": sent_today,
        "daily_limit": daily_limit,
        "remaining_limit": remaining_limit,
        "senders": config.get("senders", []),
        "primary_sender": config.get("primary_sender"),
        "sector": sector,
        "priority": priority,
        "contacts_path": contacts_path,
        "can_send": config.get("enabled", False) and remaining_limit > 0 and total_contacts > 0,
    }


def get_all_campaign_status() -> List[dict]:
    """Get status of all campaigns."""
    campaigns = []

    for campaign_name, config in CAMPAIGNS.items():
        status = get_campaign_status(campaign_name, config)
        campaigns.append(status)

    # Sort by priority (lower first), then by remaining contacts
    campaigns.sort(key=lambda x: (x["priority"], -x["remaining_limit"]))

    return campaigns


# ============================================================
# SENDER ASSIGNMENT ENGINE
# ============================================================

def get_optimal_assignments() -> List[dict]:
    """
    Generate optimal sender-campaign assignments.
    Only includes campaigns with working send scripts.

    Returns list of assignments:
    [
        {"campaign": "HORECA2026", "sender": "a2_horecaworkers", "batch_size": 50},
        ...
    ]
    """
    assignments = []

    # Get all campaign statuses
    campaigns = get_all_campaign_status()

    # Get all sender capacities
    capacities = get_sender_capacity()

    # Track assigned capacity
    assigned = defaultdict(int)

    for campaign in campaigns:
        if not campaign["can_send"]:
            continue

        # Check if campaign has a send script
        send_script = find_campaign_send_script(campaign["name"])
        if not send_script:
            # Check hardcoded list
            if campaign["name"] not in CAMPAIGNS_WITH_SCRIPTS:
                continue
            send_script = CAMPAIGNS_WITH_SCRIPTS[campaign["name"]]

        if not os.path.exists(send_script):
            continue

        # Get best sender for this campaign's sector
        best = get_best_sender(
            sector=campaign["sector"],
            min_capacity=10,
            exclude=[]  # Allow reuse for now
        )

        if not best:
            continue

        sender = best["sender"]
        remaining = capacities[sender]["remaining"] - assigned[sender]

        if remaining < 10:
            continue

        # Calculate batch size
        batch = min(
            BATCH_SIZE,
            remaining,
            campaign["remaining_limit"],
        )

        if batch < 10:
            continue

        assignments.append({
            "campaign": campaign["name"],
            "sender": sender,
            "batch_size": batch,
            "sector": campaign["sector"],
            "priority": campaign["priority"],
            "send_script": send_script,
        })

        assigned[sender] += batch

    return assignments


# ============================================================
# EXECUTION ENGINE - PARALLEL SENDERS
# ============================================================

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Track running sender processes
RUNNING_SENDERS = {}
SENDER_LOCK = threading.Lock()


def run_sender_worker(
    campaign_name: str,
    sender: str,
    dry_run: bool = False,
    send_script: str = None,
) -> None:
    """
    Worker that continuously sends emails for a campaign/sender pair.
    Runs in its own thread, sends 1 email every 3 minutes.
    """
    log(f"[{sender}] Starting worker for {campaign_name}")

    while True:
        try:
            # Check if we should stop
            with SENDER_LOCK:
                if sender not in RUNNING_SENDERS:
                    log(f"[{sender}] Worker stopped")
                    return

            # Check remaining capacity
            capacity = get_sender_capacity()
            if sender not in capacity or capacity[sender]["remaining"] <= 0:
                log(f"[{sender}] Daily limit reached, stopping")
                with SENDER_LOCK:
                    RUNNING_SENDERS.pop(sender, None)
                return

            if dry_run:
                log(f"[{sender}] [DRY-RUN] Would send 1 email for {campaign_name}")
                time.sleep(10)  # Short delay for dry-run
                continue

            # Use provided script or find one
            script = send_script or find_campaign_send_script(campaign_name)
            if not script or not os.path.exists(script):
                # Check hardcoded list
                script = CAMPAIGNS_WITH_SCRIPTS.get(campaign_name)

            if not script or not os.path.exists(script):
                log(f"[{sender}] No send script found for {campaign_name}")
                with SENDER_LOCK:
                    RUNNING_SENDERS.pop(sender, None)
                return

            # Send 1 email via campaign-specific script
            cmd = [
                "/opt/ACTIVE/INFRA/venv/bin/python3",
                script,
                "--limit", "1",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=os.path.dirname(script),
            )

            if result.returncode == 0:
                log(f"[{sender}] Sent 1 email for {campaign_name}")
            else:
                err = (result.stderr or result.stdout or "Unknown error")[:200]
                log(f"[{sender}] Send failed: {err}")

            # Wait 3 minutes before next email
            log(f"[{sender}] Waiting 180s...")
            time.sleep(MIN_DELAY_SECONDS)

        except Exception as e:
            log(f"[{sender}] Worker error: {e}")
            time.sleep(60)  # Wait 1 min on error


def start_parallel_senders(dry_run: bool = False) -> int:
    """
    Start parallel sender workers based on optimal assignments.
    Each sender runs in its own thread.
    Returns number of workers started.
    """
    assignments = get_optimal_assignments()

    if not assignments:
        log("No assignments available")
        return 0

    started = 0
    for assignment in assignments:
        sender = assignment["sender"]
        campaign = assignment["campaign"]
        send_script = assignment.get("send_script")

        with SENDER_LOCK:
            if sender in RUNNING_SENDERS:
                continue  # Already running
            RUNNING_SENDERS[sender] = {
                "campaign": campaign,
                "send_script": send_script,
                "started": datetime.now().isoformat(),
            }

        # Start worker thread
        thread = threading.Thread(
            target=run_sender_worker,
            args=(campaign, sender, dry_run, send_script),
            daemon=True,
            name=f"sender-{sender}",
        )
        thread.start()
        started += 1
        log(f"Started worker: {sender} -> {campaign} ({os.path.basename(send_script) if send_script else 'auto'})")

    return started


def stop_all_senders():
    """Stop all running sender workers."""
    with SENDER_LOCK:
        count = len(RUNNING_SENDERS)
        RUNNING_SENDERS.clear()
    log(f"Stopped {count} sender workers")
    return count


def run_maximizer_cycle(dry_run: bool = True) -> dict:
    """
    Run one maximizer cycle - starts parallel senders.
    In daemon mode, this runs once and workers continue.
    """
    cycle_start = datetime.now()
    results = {
        "start_time": cycle_start.isoformat(),
        "assignments": [],
        "total_sent": 0,
        "errors": [],
    }

    log(f"=== CAPACITY MAXIMIZER CYCLE START ({cycle_start}) ===")

    # Get optimal assignments
    assignments = get_optimal_assignments()

    if not assignments:
        log("No assignments available - all campaigns at limit or no capacity")
        results["message"] = "No assignments available"
        return results

    log(f"Generated {len(assignments)} assignments")

    for a in assignments:
        log(f"  {a['campaign']} -> {a['sender']}")
        results["assignments"].append(a)

    if dry_run:
        log("[DRY-RUN] Would start parallel senders")
        return results

    # Start parallel senders
    started = start_parallel_senders(dry_run=False)
    log(f"Started {started} parallel sender workers")

    results["workers_started"] = started

    # Save state
    state = load_state()
    state["last_run"] = cycle_start.isoformat()
    state["active_workers"] = list(RUNNING_SENDERS.keys())
    save_state(state)

    return results


# ============================================================
# DAEMON MODE - PARALLEL SENDERS
# ============================================================

def run_daemon(dry_run: bool = False):
    """Run maximizer daemon with parallel senders."""
    log("Starting capacity maximizer daemon (PARALLEL MODE)...")
    send_telegram("Capacity Maximizer started (parallel senders)")

    # Initial startup - start all sender workers
    results = run_maximizer_cycle(dry_run=dry_run)
    workers = results.get("workers_started", 0)
    send_telegram(f"Started {workers} parallel sender workers")

    while True:
        try:
            # Monitor workers and restart if needed
            time.sleep(60)  # Check every minute

            with SENDER_LOCK:
                active = len(RUNNING_SENDERS)

            # Log status every 10 minutes
            if datetime.now().minute % 10 == 0 and datetime.now().second < 60:
                totals = get_total_capacity()
                log(f"Status: {active} workers active, {totals['total']['used']}/{totals['total']['limit']} sent today ({totals['total']['utilization']:.1f}%)")

            # Check if all senders exhausted for today
            totals = get_total_capacity()
            if totals["total"]["remaining"] < 100:
                log("All senders nearly exhausted - sleeping until midnight")
                stop_all_senders()
                send_telegram(f"Daily capacity exhausted: {totals['total']['used']} emails sent. Sleeping until midnight.")
                sleep_until_midnight()

                # Restart workers after midnight
                log("Midnight - restarting workers")
                results = run_maximizer_cycle(dry_run=dry_run)
                send_telegram(f"New day: Started {results.get('workers_started', 0)} workers")

            # Restart stopped workers (e.g., if campaign ran out of contacts)
            if active < workers and totals["total"]["remaining"] > 100:
                log(f"Only {active}/{workers} workers active - checking for restarts")
                new_started = start_parallel_senders(dry_run=dry_run)
                if new_started > 0:
                    log(f"Restarted {new_started} workers")

        except KeyboardInterrupt:
            log("Daemon interrupted - stopping all workers")
            stop_all_senders()
            send_telegram("Capacity Maximizer stopped")
            break
        except Exception as e:
            log(f"Daemon error: {e}")
            time.sleep(60)


def sleep_until_midnight():
    """Sleep until midnight when quotas reset."""
    now = datetime.now()
    tomorrow = now.replace(hour=0, minute=1, second=0, microsecond=0)
    if tomorrow <= now:
        tomorrow = tomorrow.replace(day=now.day + 1)
    sleep_seconds = (tomorrow - now).total_seconds()
    log(f"Sleeping {sleep_seconds:.0f}s until midnight...")
    time.sleep(sleep_seconds)


# ============================================================
# LOGGING
# ============================================================

def log(message: str):
    """Log message to file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)

    # Write to log file
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"maximizer_{date.today().strftime('%Y%m%d')}.log")
    with open(log_file, "a") as f:
        f.write(line + "\n")


# ============================================================
# STATUS DISPLAY
# ============================================================

def print_status():
    """Print current status."""
    print(f"\n=== CAPACITY MAXIMIZER STATUS ({datetime.now()}) ===\n")

    # Load state
    state = load_state()
    last_run = state.get("last_run", "Never")
    daily = state.get("daily_sends", {}).get(date.today().isoformat(), 0)

    print(f"Last run: {last_run}")
    print(f"Sent today: {daily}")

    # Capacity summary
    totals = get_total_capacity()
    print(f"\nCapacity Summary:")
    print(f"  A2 SMTP:  {totals['a2']['used']:>6}/{totals['a2']['limit']:<6} ({totals['a2']['utilization']:.1f}%)")
    print(f"  Brevo:    {totals['brevo']['used']:>6}/{totals['brevo']['limit']:<6} ({totals['brevo']['utilization']:.1f}%)")
    print(f"  Gmail:    {totals['gmail']['used']:>6}/{totals['gmail']['limit']:<6} ({totals['gmail']['utilization']:.1f}%)")
    print(f"  TOTAL:    {totals['total']['used']:>6}/{totals['total']['limit']:<6} ({totals['total']['utilization']:.1f}%)")

    # Campaign summary
    print(f"\nEnabled Campaigns:")
    campaigns = get_all_campaign_status()
    for c in campaigns:
        if c["enabled"]:
            status = "READY" if c["can_send"] else "BLOCKED"
            print(f"  {c['name']:<25} {c['sent_today']:>4}/{c['daily_limit']:<4} {status}")

    # Optimal assignments
    print(f"\nOptimal Assignments (preview):")
    assignments = get_optimal_assignments()
    for a in assignments[:10]:
        print(f"  {a['campaign']:<25} -> {a['sender']:<25} (batch {a['batch_size']})")
    if len(assignments) > 10:
        print(f"  ... and {len(assignments) - 10} more")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Capacity Maximizer Orchestrator")
    parser.add_argument("--once", action="store_true", help="Run one cycle")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't send")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.status:
        if args.json:
            data = {
                "state": load_state(),
                "totals": get_total_capacity(),
                "campaigns": get_all_campaign_status(),
                "assignments": get_optimal_assignments(),
            }
            print(json.dumps(data, indent=2, default=str))
        else:
            print_status()
    elif args.once:
        results = run_maximizer_cycle(dry_run=args.dry_run)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"\nCycle complete: {results['total_sent']} emails sent")
            if results["errors"]:
                print(f"Errors: {len(results['errors'])}")
    elif args.daemon:
        run_daemon(dry_run=args.dry_run)
    else:
        print_status()


if __name__ == "__main__":
    main()
