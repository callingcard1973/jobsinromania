#!/usr/bin/env python3
"""NanoClaw Monitors — Scraper, TED, disk, and campaign monitoring functions."""
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from nanoclaw_core import (
    SCRAPER_SCHEDULE, SCRAPER_LOG_DIR, GOVERNOR_STATE, TED_CSV_DIR,
    TED_WINNER_PATTERN, TED_STALE_DAYS, MISS_TOLERANCE_MINUTES,
    DISK_WARN_PCT, DISK_CLEAR_PCT, TaskStatus
)


def check_governor() -> Dict:
    try:
        if GOVERNOR_STATE.exists():
            return json.loads(GOVERNOR_STATE.read_text())
    except Exception:
        pass
    return {"health": {"all_healthy": True}}


def is_system_healthy() -> bool:
    return check_governor().get("health", {}).get("all_healthy", True)


def is_campaign_window() -> bool:
    return check_governor().get("health", {}).get("in_campaign_window", False)


def get_running_scrapers(locks) -> List[str]:
    return [name for name in SCRAPER_SCHEDULE if locks.is_locked(f"scraper_{name}")]


def orchestrate_scrapers(locks, logger):
    current_time = datetime.now().strftime("%H:%M")
    for scraper, scheduled_time in SCRAPER_SCHEDULE.items():
        if current_time == scheduled_time:
            if not locks.is_locked(f"scraper_{scraper}"):
                if is_system_healthy():
                    logger.info(f"Scraper {scraper} scheduled at {scheduled_time}")


def monitor_running_tasks(locks, tasks, logger, diagnose_fn, alert_fn):
    for name in SCRAPER_SCHEDULE:
        lock_name = f"scraper_{name}"
        if locks.is_locked(lock_name):
            pid = locks.get_lock_holder(lock_name)
            if name not in tasks or tasks[name].status != "running":
                logger.info(f"Detected running scraper: {name} (PID {pid})")
                tasks[name] = TaskStatus(
                    name=name, status="running",
                    started=datetime.now().isoformat(), finished=None,
                    pid=pid, lock_file=str(lock_name),
                    retries=0, last_error=None)
        else:
            if name in tasks and tasks[name].status == "running":
                tasks[name].status = "completed"
                tasks[name].finished = datetime.now().isoformat()
                logger.info(f"Scraper {name} completed")
                log_file = SCRAPER_LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
                if log_file.exists():
                    try:
                        content = log_file.read_text()[-2000:]
                        if any(err in content.lower() for err in
                               ['error', 'failed', 'exception', 'traceback']):
                            tasks[name].status = "failed"
                            tasks[name].last_error = "Error detected in log"
                            diagnosis = diagnose_fn(content)
                            alert_fn(f"Scraper *{name}* failed\n{diagnosis}", "error")
                    except Exception:
                        pass


def check_missed_scrapers(locks, tasks, logger, alert_fn, alerted_set):
    now = datetime.now()
    for name, scheduled_time in SCRAPER_SCHEDULE.items():
        if name in alerted_set:
            continue
        sched_h, sched_m = map(int, scheduled_time.split(':'))
        scheduled_today = now.replace(hour=sched_h, minute=sched_m, second=0)
        if now > scheduled_today + timedelta(minutes=MISS_TOLERANCE_MINUTES):
            if not locks.is_locked(f"scraper_{name}"):
                last = tasks.get(name)
                if not last or not last.finished:
                    alerted_set.add(name)
                    alert_fn(f"Scraper *{name}* missed run at {scheduled_time}", "warning")
                elif last.finished:
                    try:
                        fin = datetime.fromisoformat(last.finished)
                        if fin.date() < now.date():
                            alerted_set.add(name)
                            alert_fn(f"Scraper *{name}* missed run at {scheduled_time}", "warning")
                    except Exception:
                        pass


def enforce_campaign_priority(locks, logger):
    if is_campaign_window():
        running = get_running_scrapers(locks)
        if running:
            logger.warning(f"Campaign window active but scrapers running: {running}")


def watch_log_completion(watched_logs):
    SCRAPER_LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    for log_file in SCRAPER_LOG_DIR.glob(f"*{today}*.log"):
        if log_file.name not in watched_logs:
            watched_logs.add(log_file.name)
            try:
                content = log_file.read_text()[-2000:]
                if any(m in content.lower() for m in ["completed", "finished", "success", "done"]):
                    pass  # Just mark as watched
            except Exception:
                pass


def monitor_ted_data() -> Dict:
    status = {"healthy": True, "files": {}, "total_winners": 0, "issues": []}
    if not TED_CSV_DIR.exists():
        status["healthy"] = False
        status["issues"].append("TED CSV directory missing")
        return status
    winner_files = sorted(TED_CSV_DIR.glob(TED_WINNER_PATTERN))
    if not winner_files:
        status["healthy"] = False
        status["issues"].append("No TED winner files found")
        return status
    for wf in winner_files:
        try:
            stat = wf.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            with open(wf, 'rb') as f:
                row_count = sum(1 for _ in f) - 1
            year = wf.stem.replace("ted_winners_", "")
            status["files"][year] = {
                "rows": row_count,
                "size_mb": round(stat.st_size / 1024 / 1024, 1),
                "modified": mod_time.isoformat(),
                "age_days": (datetime.now() - mod_time).days,
            }
            status["total_winners"] += row_count
            if row_count == 0:
                status["issues"].append(f"ted_winners_{year}.csv is empty!")
                status["healthy"] = False
        except Exception as e:
            status["issues"].append(f"Error reading {wf.name}: {e}")
            status["healthy"] = False
    if winner_files:
        latest = max(winner_files, key=lambda f: f.stat().st_mtime)
        age = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
        if age > TED_STALE_DAYS:
            status["issues"].append(f"Latest TED data is {age} days old")
    return status


def check_disk(alerted_flag) -> tuple:
    usage = shutil.disk_usage('/')
    pct = usage.used / usage.total * 100
    alert_msg = None
    if pct > DISK_WARN_PCT and not alerted_flag:
        alert_msg = f"Disk at {pct:.0f}% — governor threshold is 70%"
        alerted_flag = True
    elif pct < DISK_CLEAR_PCT:
        alerted_flag = False
    return pct, alerted_flag, alert_msg
