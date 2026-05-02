#!/usr/bin/env python3
"""
Brevo Warmup Continuous Supervisor - 24/7 email warmup.

Launches all warmup campaigns as background processes and monitors them.
Restarts campaigns when they complete (with delay).
Resets daily counts at midnight.

Usage:
    brevo_warmup_continuous.py              # Run as supervisor
    brevo_warmup_continuous.py --status     # Show status
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import time
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from alerting import send_telegram

# Configuration
LOG_DIR = "/opt/ACTIVE/INFRA/LOGS"
STATE_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/brevo_warmup_continuous_state.json"
PID_FILE = "/opt/ACTIVE/INFRA/SKILLS/brevo_warmup_continuous.pid"
WARMUP_SCRIPT = "/opt/ACTIVE/INFRA/SKILLS/brevo_warmup.py"
PYTHON = "/opt/ACTIVE/INFRA/venv/bin/python3"

# Campaigns (same as CAMPAIGN_SENDERS in brevo_warmup.py)
CAMPAIGNS = {
    "CAREWORKERS_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "BUILDJOBS_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "FACTORYJOBS_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "WAREHOUSE_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "SEICARESCU_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "CUMPARLEGUME_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "NORWAY_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "SWEDEN_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "FINLAND_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "CIFN_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "NEPALEZI_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
    "HORECAWORKERS2026_EU_BREVO": {"enabled": True, "daily_limit": 290, "restart_delay": 600},
}

# Global state
running_processes: Dict[str, subprocess.Popen] = {}
should_stop = False


def log(msg: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"brevo_warmup_continuous_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")


def load_state() -> dict:
    """Load supervisor state."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {
        "last_reset": datetime.now().strftime("%Y-%m-%d"),
        "last_start": {},
        "last_complete": {},
    }


def save_state(state: dict):
    """Save supervisor state."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def reset_daily_if_needed(state: dict) -> dict:
    """Reset at midnight."""
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_reset") != today:
        log("New day - resetting daily counts")
        state["last_reset"] = today
        save_state(state)
    return state


def get_campaign_daily_sent(campaign: str) -> int:
    """Get today's sent count from brevo_warmup_state.json."""
    state_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/brevo_warmup_state.json")
    if not state_file.exists():
        return 0
    try:
        data = json.loads(state_file.read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        return data.get(campaign, {}).get("daily_sends", {}).get(today, 0)
    except:
        return 0


def start_campaign(name: str, config: dict, state: dict) -> Optional[subprocess.Popen]:
    """Start a campaign as background process."""
    if not config.get("enabled"):
        return None

    # Check daily limit
    sent_today = get_campaign_daily_sent(name)
    daily_limit = config.get("daily_limit", 290)
    if sent_today >= daily_limit:
        return None  # Quota exhausted, silent skip

    remaining = daily_limit - sent_today
    log(f"  {name}: Starting ({sent_today}/{daily_limit} sent, {remaining} left)")

    log_file = os.path.join(LOG_DIR, f"brevo_{name}_{datetime.now().strftime('%Y%m%d')}.log")

    try:
        with open(log_file, "a") as f:
            process = subprocess.Popen(
                [PYTHON, WARMUP_SCRIPT, "send", name],
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd="/opt/ACTIVE/INFRA/SKILLS",
                start_new_session=True,
            )

        state["last_start"][name] = datetime.now().isoformat()
        save_state(state)
        return process
    except Exception as e:
        log(f"  {name}: FAILED to start - {e}")
        return None


def check_process(process: subprocess.Popen) -> bool:
    """Check if process is running. Returns True if running."""
    if process is None:
        return False
    return process.poll() is None


def handle_signal(signum, frame):
    """Handle shutdown signals."""
    global should_stop
    log(f"Received signal {signum}, shutting down...")
    should_stop = True


def all_quotas_exhausted() -> bool:
    """Check if all campaigns have hit daily limits."""
    for name, config in CAMPAIGNS.items():
        if not config.get("enabled"):
            continue
        sent = get_campaign_daily_sent(name)
        if sent < config.get("daily_limit", 290):
            return False
    return True


def supervisor_loop(state: dict):
    """Main supervisor loop."""
    global running_processes, should_stop

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    log("=" * 50)
    log("BREVO WARMUP SUPERVISOR STARTING (24/7)")
    log(f"Campaigns: {len([c for c in CAMPAIGNS.values() if c.get('enabled')])}")
    log("=" * 50)

    restart_after: Dict[str, float] = {}

    try:
        while not should_stop:
            state = reset_daily_if_needed(state)
            now = time.time()

            # Check if all quotas exhausted
            if all_quotas_exhausted():
                # Calculate time until midnight
                tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = tomorrow.replace(day=tomorrow.day + 1) if tomorrow <= datetime.now() else tomorrow
                sleep_secs = min((tomorrow - datetime.now()).total_seconds(), 3600)
                log(f"All quotas exhausted. Sleeping {int(sleep_secs)}s until midnight...")
                time.sleep(sleep_secs)
                continue

            # Check each campaign
            for name, config in CAMPAIGNS.items():
                if not config.get("enabled"):
                    continue

                # Check if waiting for restart
                if name in restart_after and now < restart_after[name]:
                    continue

                # Check if process running
                if name in running_processes:
                    if check_process(running_processes[name]):
                        continue  # Still running
                    else:
                        # Process completed
                        exit_code = running_processes[name].poll()
                        log(f"  {name}: Completed (exit {exit_code})")
                        state["last_complete"][name] = datetime.now().isoformat()
                        save_state(state)

                        # Schedule restart
                        delay = config.get("restart_delay", 600)
                        restart_after[name] = now + delay
                        log(f"  {name}: Restart in {delay}s")
                        del running_processes[name]
                        continue

                # Start campaign
                process = start_campaign(name, config, state)
                if process:
                    running_processes[name] = process
                else:
                    # Quota exhausted or error - check again later
                    restart_after[name] = now + 1800  # 30 min

            time.sleep(30)

    except Exception as e:
        log(f"SUPERVISOR ERROR: {e}")
        send_telegram(f"Brevo Warmup Supervisor CRASHED\n\nError: {e}")
        raise
    finally:
        log("Shutting down, terminating campaigns...")
        for name, process in running_processes.items():
            try:
                process.terminate()
                process.wait(timeout=10)
            except:
                process.kill()

        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        log("Supervisor stopped")


def show_status():
    """Show current status."""
    state = load_state()

    print("\n" + "=" * 70)
    print("BREVO WARMUP SUPERVISOR STATUS")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if running
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = f.read().strip()
        try:
            os.kill(int(pid), 0)
            print(f"Supervisor: RUNNING (PID {pid})")
        except:
            print("Supervisor: STOPPED (stale PID)")
    else:
        print("Supervisor: STOPPED")

    print()
    print(f"{'Campaign':<28} {'Enabled':<8} {'Sent':<6} {'Limit':<6} {'Last Start':<20}")
    print("-" * 70)

    total_sent = 0
    for name, config in sorted(CAMPAIGNS.items()):
        enabled = "Yes" if config.get("enabled") else "No"
        sent = get_campaign_daily_sent(name)
        total_sent += sent
        limit = config.get("daily_limit", 290)

        last_start = state.get("last_start", {}).get(name, "Never")
        if last_start != "Never":
            try:
                dt = datetime.fromisoformat(last_start)
                last_start = dt.strftime("%m-%d %H:%M:%S")
            except:
                pass

        print(f"{name:<28} {enabled:<8} {sent:<6} {limit:<6} {last_start:<20}")

    print("-" * 70)
    print(f"Total sent today: {total_sent}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Brevo Warmup 24/7 Supervisor")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    state = load_state()
    supervisor_loop(state)


if __name__ == "__main__":
    main()
