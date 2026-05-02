#!/usr/bin/env python3
"""
Self-Healer - Automatic problem detection and resolution

Checks and auto-fixes:
1. Stale GLOBAL_SEND_LOCK (> 24h) -> auto-expire
2. Stuck tracker states (running > 4h) -> mark timeout
3. Campaign state dates -> reset if stale

Runs every 30 minutes via cron.
"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Try to import alerting, fallback to print
try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

LOCK_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK")
TRACKER_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/scraper_runs.json")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")

MAX_LOCK_AGE_HOURS = 24
MAX_RUNNING_HOURS = 4


def check_global_lock():
    """Check and auto-expire stale GLOBAL_SEND_LOCK."""
    if not LOCK_FILE.exists():
        return None
    
    content = LOCK_FILE.read_text().strip()
    if not content:
        return None
    
    age_hours = (datetime.now().timestamp() - LOCK_FILE.stat().st_mtime) / 3600
    
    if age_hours > MAX_LOCK_AGE_HOURS:
        # Backup and remove
        backup = LOCK_FILE.with_suffix(f".expired.{datetime.now().strftime("%Y%m%d_%H%M%S")}")
        LOCK_FILE.rename(backup)
        return f"LOCK: Auto-expired after {age_hours:.0f}h (was: {content[:50]})"
    
    return None  # Lock exists but not expired yet


def check_tracker_states():
    """Check for stuck scraper states and mark as timeout."""
    if not TRACKER_FILE.exists():
        return []
    
    fixes = []
    try:
        data = json.loads(TRACKER_FILE.read_text())
        now = datetime.now()
        
        for name, run in data.get("runs", {}).items():
            if run.get("status") == "running":
                try:
                    started = datetime.fromisoformat(run["started"])
                    age_hours = (now - started).total_seconds() / 3600
                    
                    if age_hours > MAX_RUNNING_HOURS:
                        run["status"] = "timeout"
                        run["finished"] = now.isoformat()
                        run["message"] = f"Auto-timeout after {age_hours:.1f}h"
                        fixes.append(f"TRACKER: {name} marked timeout ({age_hours:.1f}h)")
                except (ValueError, KeyError):
                    pass
        
        if fixes:
            TRACKER_FILE.write_text(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        fixes.append("TRACKER: JSON decode error, file may be corrupt")
    
    return fixes


def check_campaign_contacts():
    """Check campaign contact counts and report low ones."""
    issues = []
    
    campaigns_to_check = [
        "POLAND", "FACTORY_EU", "CAREWORKERS_BREVO", "BUILDJOBS_BREVO",
        "NORWAY_BREVO", "SWEDEN_BREVO", "FINLAND_BREVO"
    ]
    
    for camp in campaigns_to_check:
        contacts_file = CAMPAIGNS_DIR / camp / "contacts" / "contacts.csv"
        if not contacts_file.exists():
            contacts_file = CAMPAIGNS_DIR / camp / "contacts" / "all_contacts.csv"
        
        if contacts_file.exists():
            try:
                count = sum(1 for _ in open(contacts_file, errors="ignore")) - 1
                if count < 50:
                    issues.append(f"LOW: {camp} has only {count} contacts")
            except Exception:
                pass
    
    return issues


def check_scraper_staleness():
    """Check for stale scraper outputs."""
    issues = []
    
    scrapers = {
        "DENMARK": ("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT", "*.csv", 48),
        "IAJOB": ("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB", "jobs.csv", 48),
        "ANOFM": ("/mnt/hdd/SCRAPER_DATA/csv/ANOFM", "anofm_*.csv", 48),
    }
    
    now = datetime.now()
    
    for name, (path, pattern, max_hours) in scrapers.items():
        p = Path(path)
        if not p.exists():
            continue
        
        files = list(p.glob(pattern))
        if not files:
            issues.append(f"STALE: {name} has no output files")
            continue
        
        newest = max(files, key=lambda f: f.stat().st_mtime)
        age_hours = (now.timestamp() - newest.stat().st_mtime) / 3600
        
        if age_hours > max_hours:
            issues.append(f"STALE: {name} output is {age_hours:.0f}h old (max {max_hours}h)")
    
    return issues


def run_all_checks():
    """Run all health checks and report."""
    fixes = []
    issues = []
    
    # 1. Check lock
    lock_fix = check_global_lock()
    if lock_fix:
        fixes.append(lock_fix)
    
    # 2. Check tracker
    tracker_fixes = check_tracker_states()
    fixes.extend(tracker_fixes)
    
    # 3. Check campaign contacts
    contact_issues = check_campaign_contacts()
    issues.extend(contact_issues)
    
    # 4. Check scraper staleness
    stale_issues = check_scraper_staleness()
    issues.extend(stale_issues)
    
    # Report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if fixes or issues:
        msg = f"SELF-HEALER [{timestamp}]\n"
        
        if fixes:
            msg += "\nFIXED:\n" + "\n".join(f"  {f}" for f in fixes)
        
        if issues:
            msg += "\nISSUES:\n" + "\n".join(f"  {i}" for i in issues)
        
        print(msg)
        send_telegram(msg)
        return {"fixes": fixes, "issues": issues}
    else:
        print(f"[{timestamp}] All systems OK")
        return {"fixes": [], "issues": []}


def get_status():
    """Get current system status for dashboard API."""
    status = {
        "lock": None,
        "tracker_stuck": [],
        "low_contacts": [],
        "stale_scrapers": []
    }
    
    # Check lock
    if LOCK_FILE.exists():
        content = LOCK_FILE.read_text().strip()
        if content:
            age_hours = (datetime.now().timestamp() - LOCK_FILE.stat().st_mtime) / 3600
            status["lock"] = {
                "content": content[:100],
                "age_hours": round(age_hours, 1),
                "will_expire": age_hours > MAX_LOCK_AGE_HOURS
            }
    
    # Check tracker
    if TRACKER_FILE.exists():
        try:
            data = json.loads(TRACKER_FILE.read_text())
            now = datetime.now()
            for name, run in data.get("runs", {}).items():
                if run.get("status") == "running":
                    try:
                        started = datetime.fromisoformat(run["started"])
                        age_hours = (now - started).total_seconds() / 3600
                        if age_hours > 1:  # Report if running > 1h
                            status["tracker_stuck"].append({
                                "name": name,
                                "age_hours": round(age_hours, 1)
                            })
                    except (ValueError, KeyError):
                        pass
        except json.JSONDecodeError:
            pass
    
    # Check contacts
    for camp in ["POLAND", "FACTORY_EU", "CAREWORKERS_BREVO"]:
        contacts_file = CAMPAIGNS_DIR / camp / "contacts" / "contacts.csv"
        if not contacts_file.exists():
            contacts_file = CAMPAIGNS_DIR / camp / "contacts" / "all_contacts.csv"
        if contacts_file.exists():
            try:
                count = sum(1 for _ in open(contacts_file, errors="ignore")) - 1
                if count < 100:
                    status["low_contacts"].append({"campaign": camp, "count": count})
            except Exception:
                pass
    
    # Check staleness
    scrapers = {
        "DENMARK": ("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT", "*.csv", 48),
        "IAJOB": ("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB", "jobs.csv", 48),
    }
    now = datetime.now()
    for name, (path, pattern, max_hours) in scrapers.items():
        p = Path(path)
        if p.exists():
            files = list(p.glob(pattern))
            if files:
                newest = max(files, key=lambda f: f.stat().st_mtime)
                age_hours = (now.timestamp() - newest.stat().st_mtime) / 3600
                if age_hours > max_hours:
                    status["stale_scrapers"].append({
                        "name": name,
                        "age_hours": round(age_hours, 0),
                        "max_hours": max_hours
                    })
    
    return status


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Self-Healer")
    parser.add_argument("--status", action="store_true", help="Get status JSON")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    if args.status:
        import json
        print(json.dumps(get_status(), indent=2))
    else:
        result = run_all_checks()
        if args.json:
            print(json.dumps(result, indent=2))
