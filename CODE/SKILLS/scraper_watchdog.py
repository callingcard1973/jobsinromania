#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Scraper Watchdog - Alert on stale data or failures

Monitors ALL scrapers, not just EURES. Sends Telegram alerts when data is stale.
Rate-limited to avoid spam (max 1 alert per scraper per 6 hours).

Usage:
    python3 scraper_watchdog.py           # Check all scrapers, alert if stale
    python3 scraper_watchdog.py --quiet   # No output if all OK
    python3 scraper_watchdog.py --test    # Test mode (print but don't send)
    python3 scraper_watchdog.py --force   # Force alert even if recently sent
"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from alerting import send_telegram

# Alert rate limiting
ALERT_STATE_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/.scraper_watchdog_alerts.json")
ALERT_COOLDOWN_HOURS = 6  # Don't re-alert same scraper within 6 hours

# Scraper configurations: name -> (path, pattern, max_age_hours)
SCRAPERS = {
    # Nordic (USB storage)
    "SWEDEN": (Path("/mnt/hdd/SCRAPER_DATA/csv/SWEDEN"), "Sweden_*.csv", 48),

    # Nordic (local storage)
    "NORWAY": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/OUTPUT"), "Norway_*.csv", 720),  # 30 days - job postings don't change daily
    "DENMARK": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT"), "*.csv", 48),
    "FINLAND": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/output"), "jobs_fi_*.csv", 48),
    "ICELAND": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ICELAND/ALFRED/OUTPUT"), "alfred_*.csv", 72),

    # EURES (EU jobs - USB storage)
    "EURES": (Path("/mnt/hdd/SCRAPER_DATA/csv/EURES"), "*/*.csv", 48),

    # Romania (USB storage)
    "ANOFM": (Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM"), "anofm_*.csv", 48),
    "DSVSA": (Path("/mnt/hdd/SCRAPER_DATA/csv/DSVSA"), "*.csv", 720),  # 30 days OK

    # UK (local storage)
    "UK_NHS": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK/results"), "nhs_jobs_*.csv", 168),  # weekly
    "UK_CQC": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK/CQC/data"), "cqc_*.csv", 4320),  # 6 months

    # Other EU (local storage)
    "POLAND": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/POLAND/OUTPUT"), "kraz_*.csv", 168),  # weekly
    "NORTH_MACEDONIA": (Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORTH_MACEDONIA/dockerized/output"), "north_macedonia_*.csv", 168),

    # Romania OLX
    "OLX_JOBS": (Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/OLX_JOBS"), "olx_jobs_*.csv", 72),
    # IAJOB (runs on raspi)
    "IAJOB": (Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB"), "jobs.csv", 48),
}


def check_scraper(name: str, path: Path, pattern: str, max_age_hours: int) -> dict:
    """Check a single scraper's health."""
    result = {
        "name": name,
        "status": "unknown",
        "age_hours": None,
        "latest_file": None,
        "message": ""
    }

    if not path.exists():
        result["status"] = "missing"
        result["message"] = f"Path not found: {path}"
        return result

    # Find latest file
    files = list(path.glob(pattern))
    if not files:
        result["status"] = "no_data"
        result["message"] = f"No files matching {pattern}"
        return result

    latest = max(files, key=lambda f: f.stat().st_mtime)
    age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
    age_hours = age.total_seconds() / 3600

    result["latest_file"] = latest.name
    result["age_hours"] = round(age_hours, 1)

    if age_hours > max_age_hours:
        result["status"] = "stale"
        result["message"] = f"{int(age_hours)}h old (max {max_age_hours}h)"
    else:
        result["status"] = "ok"
        result["message"] = f"{int(age_hours)}h old"

    return result


def check_all_scrapers() -> list:
    """Check all configured scrapers."""
    results = []
    for name, (path, pattern, max_age) in SCRAPERS.items():
        result = check_scraper(name, path, pattern, max_age)
        results.append(result)
    return results


def load_alert_state() -> dict:
    """Load alert state for rate limiting."""
    if ALERT_STATE_FILE.exists():
        try:
            with open(ALERT_STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"last_alerts": {}}


def save_alert_state(state: dict):
    """Save alert state."""
    with open(ALERT_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def should_alert(scraper_name: str, state: dict, force: bool = False) -> bool:
    """Check if we should send alert for this scraper (rate limiting)."""
    if force:
        return True

    last_alerts = state.get("last_alerts", {})
    last_alert = last_alerts.get(scraper_name)

    if not last_alert:
        return True

    try:
        last_time = datetime.fromisoformat(last_alert)
        if datetime.now() - last_time > timedelta(hours=ALERT_COOLDOWN_HOURS):
            return True
    except:
        return True

    return False


def record_alert(scraper_name: str, state: dict):
    """Record that we sent an alert for this scraper."""
    if "last_alerts" not in state:
        state["last_alerts"] = {}
    state["last_alerts"][scraper_name] = datetime.now().isoformat()


def main():
    parser = argparse.ArgumentParser(description='Scraper Watchdog')
    parser.add_argument('--quiet', '-q', action='store_true', help='No output if all OK')
    parser.add_argument('--test', '-t', action='store_true', help='Test mode, no alerts')
    parser.add_argument('--force', '-f', action='store_true', help='Force alert (ignore cooldown)')
    args = parser.parse_args()

    results = check_all_scrapers()
    alert_state = load_alert_state()

    # Categorize results
    stale = [r for r in results if r["status"] == "stale"]
    no_data = [r for r in results if r["status"] == "no_data"]
    ok = [r for r in results if r["status"] == "ok"]

    # Filter to only scrapers that should be alerted (rate limiting)
    stale_to_alert = [r for r in stale if should_alert(r["name"], alert_state, args.force)]
    no_data_to_alert = [r for r in no_data if should_alert(r["name"], alert_state, args.force)]

    # Build alert if needed
    alerts = []
    alerted_scrapers = []

    if stale_to_alert:
        alerts.append("STALE DATA:")
        for r in stale_to_alert:
            alerts.append(f"  {r['name']}: {r['message']}")
            alerted_scrapers.append(r["name"])

    if no_data_to_alert:
        alerts.append("NO DATA:")
        for r in no_data_to_alert:
            alerts.append(f"  {r['name']}: {r['message']}")
            alerted_scrapers.append(r["name"])

    # Send alert if issues found
    if alerts:
        msg = "SCRAPER WATCHDOG ALERT\n" + "\n".join(alerts)
        print(msg)
        if not args.test:
            try:
                send_telegram(msg)
                # Record alerts for rate limiting
                for name in alerted_scrapers:
                    record_alert(name, alert_state)
                save_alert_state(alert_state)
                print(f"\nTelegram alert sent for: {', '.join(alerted_scrapers)}")
            except Exception as e:
                print(f"\nFailed to send Telegram: {e}")
        else:
            print("\n[TEST MODE] Would send Telegram alert")
    elif stale or no_data:
        # Issues exist but already alerted recently
        print(f"Issues found but already alerted within {ALERT_COOLDOWN_HOURS}h:")
        for r in stale:
            print(f"  {r['name']}: {r['message']}")
        for r in no_data:
            print(f"  {r['name']}: {r['message']}")
    elif not args.quiet:
        print(f"All {len(ok)} scrapers OK ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
        for r in ok:
            print(f"  {r['name']}: {r['age_hours']}h old")

    # Return exit code
    return 1 if (stale or no_data) else 0


if __name__ == "__main__":
    sys.exit(main())
