#!/usr/bin/env python3
"""
Scraper Recovery - Auto-restart failed scrapers

Features:
- Restart commands for each scraper
- Max 3 retries per day per scraper
- Integrates with watchdog

Usage:
    python3 scraper_recovery.py check           # Check all scrapers
    python3 scraper_recovery.py restart DENMARK # Restart specific
    python3 scraper_recovery.py status          # Show retry counts
"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/scraper_recovery_state.json")
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")

# Scraper restart commands
SCRAPER_COMMANDS = {
    "DENMARK": {
        "cmd": "/opt/ACTIVE/INFRA/SKILLS/run_scraper.sh DENMARK /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/danish_scraper.py",
        "output_dir": "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT",
        "max_age_hours": 48
    },
    "FINLAND": {
        "cmd": "/opt/ACTIVE/INFRA/SKILLS/run_scraper.sh FINLAND /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/run.sh",
        "output_dir": "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/output",
        "max_age_hours": 48
    },
    "NORWAY": {
        "cmd": "/opt/ACTIVE/INFRA/SKILLS/run_scraper.sh NORWAY /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/run_norway.sh",
        "output_dir": "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/OUTPUT",
        "max_age_hours": 48
    },
    "ICELAND": {
        "cmd": "/opt/ACTIVE/INFRA/SKILLS/run_scraper.sh ICELAND /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ICELAND/run_iceland.sh",
        "output_dir": "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ICELAND/ALFRED/OUTPUT",
        "max_age_hours": 72
    },
    "NETHERLANDS": {
        "cmd": "/opt/ACTIVE/INFRA/SKILLS/run_scraper.sh NETHERLANDS /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NETHERLANDS/nl_scraper.py",
        "output_dir": "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NETHERLANDS/OUTPUT",
        "max_age_hours": 48
    },
    "BULGARIA": {
        "cmd": "/opt/ACTIVE/INFRA/SKILLS/run_scraper.sh BULGARIA /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/BULGARIA/bg_scraper.py",
        "output_dir": "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/BULGARIA/OUTPUT",
        "max_age_hours": 48
    },
    "IAJOB": {
        "cmd": "/opt/ACTIVE/INFRA/SKILLS/run_scraper.sh IAJOB /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/IAJOB/src/iajob_scraper.py",
        "output_dir": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB",
        "max_age_hours": 48
    },
    "SWEDEN_ENRICHER": {
        "cmd": "/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/sweden_enricher.py --limit 500",
        "output_dir": "/opt/ACTIVE/OPENDATA/DATA/ENRICHED",
        "max_age_hours": 48
    },
}

MAX_RETRIES_PER_DAY = 3


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"retries": {}, "last_reset": datetime.now().strftime("%Y-%m-%d")}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def can_retry(name):
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Reset daily counts
    if state.get("last_reset") != today:
        state["retries"] = {}
        state["last_reset"] = today
        save_state(state)
    
    count = state["retries"].get(name, 0)
    return count < MAX_RETRIES_PER_DAY, count


def record_retry(name):
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_reset") != today:
        state["retries"] = {}
        state["last_reset"] = today
    state["retries"][name] = state["retries"].get(name, 0) + 1
    save_state(state)
    return state["retries"][name]


def check_scraper_age(name):
    """Check if scraper output is stale."""
    if name not in SCRAPER_COMMANDS:
        return None, "Unknown scraper"
    
    config = SCRAPER_COMMANDS[name]
    output_dir = Path(config["output_dir"])
    max_age = config["max_age_hours"]
    
    if not output_dir.exists():
        return True, f"Output dir missing: {output_dir}"
    
    # Find newest file
    files = list(output_dir.glob("*.csv"))
    if not files:
        return True, "No CSV files found"
    
    newest = max(files, key=lambda f: f.stat().st_mtime)
    age_hours = (datetime.now().timestamp() - newest.stat().st_mtime) / 3600
    
    if age_hours > max_age:
        return True, f"{age_hours:.0f}h old (max {max_age}h)"
    
    return False, f"OK ({age_hours:.0f}h old)"


def restart_scraper(name, force=False):
    """Restart a scraper."""
    if name not in SCRAPER_COMMANDS:
        return False, f"Unknown scraper: {name}"
    
    can, count = can_retry(name)
    if not can and not force:
        return False, f"Max retries ({MAX_RETRIES_PER_DAY}) reached today ({count} used)"
    
    config = SCRAPER_COMMANDS[name]
    cmd = config["cmd"]
    
    # Create log file
    log_dir = LOG_DIR / name.lower()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log"
    
    print(f"Restarting {name}...")
    print(f"  Command: {cmd}")
    print(f"  Log: {log_file}")
    
    try:
        # Run in background
        with open(log_file, "w") as f:
            subprocess.Popen(
                cmd,
                shell=True,
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        retry_count = record_retry(name)
        return True, f"Started (retry {retry_count}/{MAX_RETRIES_PER_DAY})"
    except Exception as e:
        return False, str(e)


def check_all():
    """Check all scrapers and report status."""
    print(f"Scraper Recovery Status [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("-" * 60)
    
    state = load_state()
    results = []
    
    for name in sorted(SCRAPER_COMMANDS.keys()):
        is_stale, msg = check_scraper_age(name)
        can, count = can_retry(name)
        
        status = "STALE" if is_stale else "OK"
        retry_info = f"[{count}/{MAX_RETRIES_PER_DAY}]"
        
        results.append({
            "name": name,
            "stale": is_stale,
            "message": msg,
            "retries_used": count,
            "can_retry": can
        })
        
        print(f"  {name:20} {status:6} {retry_info:8} {msg}")
    
    return results


def auto_restart_stale():
    """Check all scrapers and restart stale ones."""
    results = check_all()
    
    restarted = []
    failed = []
    
    for r in results:
        if r["stale"] and r["can_retry"]:
            success, msg = restart_scraper(r["name"])
            if success:
                restarted.append(f"{r[name]}: {msg}")
            else:
                failed.append(f"{r[name]}: {msg}")
    
    if restarted or failed:
        alert = "SCRAPER RECOVERY\n"
        if restarted:
            alert += "\nRESTARTED:\n" + "\n".join(f"  {r}" for r in restarted)
        if failed:
            alert += "\nFAILED:\n" + "\n".join(f"  {f}" for f in failed)
        
        print(alert)
        send_telegram(alert)
    
    return {"restarted": restarted, "failed": failed}


def get_status_json():
    """Get status as JSON for dashboard API."""
    state = load_state()
    scrapers = []
    
    for name in sorted(SCRAPER_COMMANDS.keys()):
        is_stale, msg = check_scraper_age(name)
        can, count = can_retry(name)
        
        scrapers.append({
            "name": name,
            "stale": is_stale,
            "message": msg,
            "retries_used": count,
            "max_retries": MAX_RETRIES_PER_DAY,
            "can_restart": can and is_stale
        })
    
    return {"scrapers": scrapers, "last_reset": state.get("last_reset")}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Recovery")
    parser.add_argument("action", nargs="?", default="check",
                       choices=["check", "restart", "auto", "status", "json"])
    parser.add_argument("scraper", nargs="?", help="Scraper name for restart")
    parser.add_argument("--force", action="store_true", help="Ignore retry limits")
    args = parser.parse_args()
    
    if args.action == "check":
        check_all()
    elif args.action == "restart":
        if not args.scraper:
            print("Error: Specify scraper name")
            sys.exit(1)
        success, msg = restart_scraper(args.scraper.upper(), args.force)
        print(f"{OK if success else FAILED}: {msg}")
    elif args.action == "auto":
        auto_restart_stale()
    elif args.action == "status":
        state = load_state()
        print(json.dumps(state, indent=2))
    elif args.action == "json":
        print(json.dumps(get_status_json(), indent=2))
