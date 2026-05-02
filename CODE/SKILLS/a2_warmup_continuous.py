#!/usr/bin/env python3
"""
A2 SMTP Warmup Continuous Supervisor - 24/7 email warmup for A2 domains.

Launches all A2 warmup domains as background processes and monitors them.
Restarts when complete (with delay). Resets daily counts at midnight.

Usage:
    a2_warmup_continuous.py              # Run as supervisor
    a2_warmup_continuous.py --status     # Show status
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
STATE_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_warmup_continuous_state.json"
PID_FILE = "/opt/ACTIVE/INFRA/SKILLS/a2_warmup_continuous.pid"
WARMUP_SCRIPT = "/opt/ACTIVE/INFRA/SKILLS/a2_warmup.py"
PYTHON = "/opt/ACTIVE/INFRA/venv/bin/python3"

# A2 Domains (7 domains x 350/day on day 23 = 2,450/day capacity)
DOMAINS = {
    "horecaworkers.eu": {"enabled": True, "restart_delay": 300},
    "meatworkers.eu": {"enabled": True, "restart_delay": 300},
    "electricjobs.eu": {"enabled": True, "restart_delay": 300},
    "mechanicjobs.eu": {"enabled": True, "restart_delay": 300},
    "farmworkers.eu": {"enabled": True, "restart_delay": 300},
    "factoryjobs.eu": {"enabled": True, "restart_delay": 300},
    "warehouseworkers.eu": {"enabled": True, "restart_delay": 300},
}

# Global state
running_processes: Dict[str, subprocess.Popen] = {}
should_stop = False


def log(msg: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"a2_warmup_continuous_{datetime.now().strftime('%Y%m%d')}.log")
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


def get_domain_daily_sent(domain: str) -> int:
    """Get today's sent count from a2_warmup_state.json."""
    state_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_warmup_state.json")
    if not state_file.exists():
        return 0
    try:
        data = json.loads(state_file.read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        return data.get(domain, {}).get("daily_sends", {}).get(today, 0)
    except:
        return 0


def get_daily_limit() -> int:
    """Get current daily limit based on warmup day."""
    from datetime import datetime
    WARMUP_START = datetime(2026, 1, 15)
    day = (datetime.now() - WARMUP_START).days + 1

    WARMUP_SCHEDULE = [
        (1, 3, 20),
        (4, 7, 50),
        (8, 14, 100),
        (15, 21, 200),
        (22, 28, 350),
        (29, 999, 500),
    ]

    for start, end, limit in WARMUP_SCHEDULE:
        if start <= day <= end:
            return limit
    return 500


def start_domain(domain: str, config: dict, state: dict) -> Optional[subprocess.Popen]:
    """Start a domain warmup as background process."""
    if not config.get("enabled"):
        return None

    # Check daily limit
    sent_today = get_domain_daily_sent(domain)
    daily_limit = get_daily_limit()
    if sent_today >= daily_limit:
        return None  # Quota exhausted, silent skip

    remaining = daily_limit - sent_today
    log(f"  {domain}: Starting ({sent_today}/{daily_limit} sent, {remaining} left)")

    log_file = os.path.join(LOG_DIR, f"a2_{domain.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.log")

    try:
        with open(log_file, "a") as f:
            process = subprocess.Popen(
                [PYTHON, WARMUP_SCRIPT, "send", domain],
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd="/opt/ACTIVE/INFRA/SKILLS",
                start_new_session=True,
            )

        state["last_start"][domain] = datetime.now().isoformat()
        save_state(state)
        return process
    except Exception as e:
        log(f"  {domain}: FAILED to start - {e}")
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
    """Check if all domains have hit daily limits."""
    daily_limit = get_daily_limit()
    for domain, config in DOMAINS.items():
        if not config.get("enabled"):
            continue
        sent = get_domain_daily_sent(domain)
        if sent < daily_limit:
            return False
    return True


def supervisor_loop(state: dict):
    """Main supervisor loop."""
    global running_processes, should_stop

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    daily_limit = get_daily_limit()
    log("=" * 50)
    log("A2 SMTP WARMUP SUPERVISOR STARTING (24/7)")
    log(f"Domains: {len([d for d in DOMAINS.values() if d.get('enabled')])}")
    log(f"Daily limit per domain: {daily_limit}")
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

            # Check each domain
            for domain, config in DOMAINS.items():
                if not config.get("enabled"):
                    continue

                # Check if waiting for restart
                if domain in restart_after and now < restart_after[domain]:
                    continue

                # Check if process running
                if domain in running_processes:
                    if check_process(running_processes[domain]):
                        continue  # Still running
                    else:
                        # Process completed
                        exit_code = running_processes[domain].poll()
                        log(f"  {domain}: Completed (exit {exit_code})")
                        state["last_complete"][domain] = datetime.now().isoformat()
                        save_state(state)

                        # Schedule restart
                        delay = config.get("restart_delay", 300)
                        restart_after[domain] = now + delay
                        log(f"  {domain}: Restart in {delay}s")
                        del running_processes[domain]
                        continue

                # Start domain
                process = start_domain(domain, config, state)
                if process:
                    running_processes[domain] = process
                else:
                    # Quota exhausted or error - check again later
                    restart_after[domain] = now + 1800  # 30 min

            time.sleep(30)

    except Exception as e:
        log(f"SUPERVISOR ERROR: {e}")
        send_telegram(f"A2 Warmup Supervisor CRASHED\n\nError: {e}")
        raise
    finally:
        log("Shutting down, terminating domains...")
        for domain, process in running_processes.items():
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
    daily_limit = get_daily_limit()

    print("\n" + "=" * 70)
    print("A2 SMTP WARMUP SUPERVISOR STATUS")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Daily limit per domain: {daily_limit}")

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
    print(f"{'Domain':<25} {'Enabled':<8} {'Sent':<6} {'Limit':<6} {'Last Start':<20}")
    print("-" * 70)

    total_sent = 0
    for domain, config in sorted(DOMAINS.items()):
        enabled = "Yes" if config.get("enabled") else "No"
        sent = get_domain_daily_sent(domain)
        total_sent += sent

        last_start = state.get("last_start", {}).get(domain, "Never")
        if last_start != "Never":
            try:
                dt = datetime.fromisoformat(last_start)
                last_start = dt.strftime("%m-%d %H:%M:%S")
            except:
                pass

        print(f"{domain:<25} {enabled:<8} {sent:<6} {daily_limit:<6} {last_start:<20}")

    print("-" * 70)
    print(f"Total sent today: {total_sent}")
    print(f"Total capacity: {daily_limit * len([d for d in DOMAINS.values() if d.get('enabled')])}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="A2 SMTP Warmup 24/7 Supervisor")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    state = load_state()
    supervisor_loop(state)


if __name__ == "__main__":
    main()
