#!/usr/bin/env python3
"""
Task Queue Runner for Laptop - processes next pending task
Run periodically (e.g., every 5 minutes) via Windows Task Scheduler
"""
import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
QUEUE_FILE = os.path.join(QUEUE_DIR, "tasks.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Map task types to commands
TASK_COMMANDS = {
    "seo_audit": "python3 seo_audit.py >> logs/audit.log 2>&1",
    "article_generator": "python3 article_generator.py >> logs/articles.log 2>&1",
    "job_listing_generator": "python3 job_listing_generator.py >> logs/jobs.log 2>&1",
    "faq_auto_builder": "python3 faq_auto_builder.py >> logs/faq.log 2>&1",
    "wp_seo_fixer": "python3 wp_seo_fixer_all.py >> logs/wp_seo.log 2>&1",
    "broken_link_fixer": "python3 broken_link_fixer.py >> logs/links.log 2>&1",
    "uptime_monitor": "python3 uptime_monitor.py >> logs/uptime.log 2>&1",
    "send_night_summary": "python3 send_night_summary.py >> logs/summary.log 2>&1",
}

def log(msg):
    """Log to both console and file"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    with open(os.path.join(LOGS_DIR, "runner.log"), "a") as f:
        f.write(log_msg + "\n")

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, 'r') as f:
        return json.load(f)

def save_queue(tasks):
    with open(QUEUE_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

def get_next_task(tasks):
    """Get next pending task by priority"""
    high = [t for t in tasks if t["status"]=="pending" and t["priority"]=="high"]
    normal = [t for t in tasks if t["status"]=="pending" and t["priority"]=="normal"]
    recurrent = [t for t in tasks if t["status"]=="pending" and t["priority"]=="recurrent"]

    return high[0] if high else (normal[0] if normal else (recurrent[0] if recurrent else None))

def run_task(task):
    """Run a single task"""
    task_type = task["type"]
    if task_type not in TASK_COMMANDS:
        log(f"[ERROR] Unknown task type: {task_type}")
        return False

    cmd = TASK_COMMANDS[task_type]
    log(f"[RUN] {task_type}")

    try:
        # Set environment variables for tasks that need them
        env = os.environ.copy()
        if task_type == "article_generator":
            env["RUN_MODE"] = "auto"

        result = subprocess.run(
            cmd,
            shell=True,
            cwd=BASE_DIR,
            capture_output=False,
            timeout=3600,
            env=env
        )

        # Update task status
        tasks = load_queue()
        for t in tasks:
            if t["id"] == task["id"]:
                t["status"] = "completed"
                t["result"] = result.returncode
                break
        save_queue(tasks)

        log(f"[OK] Completed: {task_type}")

        # Re-add recurrent tasks
        if task["priority"] == "recurrent":
            import time
            new_task = task.copy()
            new_task["id"] = f"{task_type}_{int(time.time())}"
            new_task["status"] = "pending"
            tasks.append(new_task)
            save_queue(tasks)

        return True
    except Exception as e:
        log(f"[ERROR] {task_type}: {e}")
        return False

def main():
    Path(LOGS_DIR).mkdir(exist_ok=True)
    tasks = load_queue()
    next_task = get_next_task(tasks)

    if next_task:
        run_task(next_task)
    else:
        log("[OK] Queue empty, no tasks to run")

if __name__ == "__main__":
    main()
