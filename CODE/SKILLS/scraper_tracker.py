#!/usr/bin/env python3
"""Scraper Tracker - Logs scraper runs to JSON for dashboard display."""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

TRACKER_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/scraper_runs.json")

SCHEDULE = {
    "ANOFM": "08:32, 14:17 Mon-Fri",
    "BULGARIA": "03:30 daily",
    "DENMARK": "02:00 daily",
    "EURES": "05:00, 11:00, 17:00, 23:00",
    "EURES_BENELUX": "06:00, 12:00, 18:00",
    "EURES_DACH": "05:30, 11:30, 17:30, 23:30",
    "FINLAND": "06:30 daily",
    "IAJOB": "06:03 daily",
    "ICELAND": "02:30 daily",
    "MALTA": "04:30 daily",
    "NETHERLANDS": "03:00 daily",
    "NORTH_MACEDONIA": "04:00 daily",
    "NORWAY": "07:00 daily",
    "POLAND": "04:00 Sunday",
    "SWEDEN": "08:00 enricher",
}

def load_data():
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text())
    return {"runs": {}, "schedule": SCHEDULE}

def save_data(data):
    data["schedule"] = SCHEDULE
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(data, indent=2, default=str))

def start_run(name):
    data = load_data()
    data["runs"][name] = {"started": datetime.now().isoformat(), "finished": None, "status": "running", "rows": 0, "message": ""}
    save_data(data)
    print("[TRACKER] " + name + " started")

def finish_run(name, status="ok", rows=0, msg=""):
    data = load_data()
    if name not in data["runs"]:
        data["runs"][name] = {"started": datetime.now().isoformat()}
    data["runs"][name].update({"finished": datetime.now().isoformat(), "status": status, "rows": rows, "message": msg})
    save_data(data)
    print("[TRACKER] " + name + " finished: " + status + ", " + str(rows) + " rows")

def show_status():
    data = load_data()
    header = "Scraper".ljust(18) + "Schedule".ljust(24) + "Last_Run".ljust(18) + "Status".ljust(8) + "Rows"
    print(header)
    print("-" * 80)
    for name in sorted(SCHEDULE.keys()):
        sched = SCHEDULE[name]
        run = data["runs"].get(name, {})
        last = run.get("finished", run.get("started", "Never"))
        if last and last != "Never":
            last = last[:16].replace("T", " ")
        status = run.get("status", "-")
        rows = str(run.get("rows", "-"))
        print(name.ljust(18) + sched.ljust(24) + str(last).ljust(18) + str(status).ljust(8) + rows)


def cleanup_stale():
    """Mark scrapers as timeout if running > 4 hours."""
    data = load_data()
    now = datetime.now()
    fixed = []
    
    for name, run in data["runs"].items():
        if run.get("status") == "running":
            try:
                started = datetime.fromisoformat(run["started"])
                age_hours = (now - started).total_seconds() / 3600
                if age_hours > 4:
                    run["status"] = "timeout"
                    run["finished"] = now.isoformat()
                    run["message"] = f"Auto-timeout after {age_hours:.1f}h"
                    fixed.append(f"{name}: {age_hours:.1f}h")
            except (ValueError, KeyError):
                pass
    
    if fixed:
        save_data(data)
        print(f"Cleaned up {len(fixed)} stale scrapers:")
        for f in fixed:
            print(f"  {f}")
    else:
        print("No stale scrapers found")
    
    return fixed


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["start", "finish", "status", "cleanup"])
    p.add_argument("name", nargs="?")
    p.add_argument("--status", default="ok")
    p.add_argument("--rows", type=int, default=0)
    p.add_argument("--msg", default="")
    args = p.parse_args()
    
    if args.action == "start": start_run(args.name)
    elif args.action == "finish": finish_run(args.name, args.status, args.rows, args.msg)
    elif args.action == "status": show_status()
    elif args.action == "cleanup": cleanup_stale()
