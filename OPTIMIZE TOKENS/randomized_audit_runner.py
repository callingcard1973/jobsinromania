#!/usr/bin/env python3
"""
Randomized Audit Runner — Execute daily_audit.py with random delay.

Instead of running at fixed 9 AM, this script:
1. Waits a random duration (0-59 minutes) at startup
2. Then runs the daily audit
3. Prevents synchronized load spikes and predictable patterns

Usage:
  python randomized_audit_runner.py    # Random delay then audit
"""

import subprocess
import time
import random
from datetime import datetime
from pathlib import Path

AUDIT_SCRIPT = Path(__file__).parent / "daily_audit.py"
LOG_DIR = Path(__file__).parent / "logs"


def run_randomized_audit():
    """Run audit with random delay"""

    # Generate random delay: 0-59 minutes
    delay_minutes = random.randint(0, 59)
    delay_seconds = delay_minutes * 60

    log_file = LOG_DIR / "randomized_audit.log"
    log_dir = LOG_DIR / "randomized"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Log the start
    start_time = datetime.now().isoformat()
    with open(log_file, 'a') as f:
        f.write(f"\n[{start_time}] Randomized audit started. Delay: {delay_minutes} min\n")

    # Sleep for random duration
    print(f"[AUDIT] Waiting {delay_minutes} minutes before running audit...")
    time.sleep(delay_seconds)

    # Run the audit
    actual_start = datetime.now().isoformat()
    with open(log_file, 'a') as f:
        f.write(f"[{actual_start}] Executing daily_audit.py\n")

    try:
        result = subprocess.run(
            ["python3", str(AUDIT_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=300
        )

        completion_time = datetime.now().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"[{completion_time}] Audit completed (exit code: {result.returncode})\n")

        if result.stdout:
            with open(log_file, 'a') as f:
                f.write(f"STDOUT:\n{result.stdout}\n")

        if result.stderr:
            with open(log_file, 'a') as f:
                f.write(f"STDERR:\n{result.stderr}\n")

        print(f"[AUDIT] Completed at {completion_time}")

    except subprocess.TimeoutExpired:
        error_time = datetime.now().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"[{error_time}] ERROR: Audit timed out after 5 minutes\n")
        print(f"[ERROR] Audit timeout")
    except Exception as e:
        error_time = datetime.now().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"[{error_time}] ERROR: {str(e)}\n")
        print(f"[ERROR] {str(e)}")


if __name__ == '__main__':
    run_randomized_audit()
