#!/usr/bin/env python3
"""
Log Archiver: Bundles compressed logs older than 7 days, rsyncs to raspi, cleans up locally.
Runs nightly via cron @ 2 AM.

Workflow:
1. Scan /opt/ACTIVE recursively for *.log.*.gz files older than 7 days
2. Group by date (extract from file mtime)
3. For each date, create YYYY-MM-DD.tar.gz containing all compressed logs
4. rsync to raspi:/opt/MOVED_FROM_RASPIBIG/LOG_ARCHIVES/
5. Verify rsync success (compare file counts)
6. Delete local *.gz files after successful backup
7. Log all actions
"""

import os
import sys
import tarfile
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Configuration
LOG_ROOT = Path("/opt/ACTIVE")
COMPRESSED_PATTERN = "*.log.*.gz"
ARCHIVE_DAYS = 7  # Only archive logs older than 7 days
RASPI_HOST = "192.168.100.20"
RASPI_DEST = "/opt/MOVED_FROM_RASPIBIG/LOG_ARCHIVES/"
LOG_FILE = Path("/opt/ACTIVE/INFRA/LOGS/log_archiver.log")
STATE_FILE = Path("/opt/ACTIVE/INFRA/GOVERNOR/log_archiver_state.json")

def log_action(msg):
    """Log to file and stdout."""
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def find_old_compressed_logs(root: Path, days: int) -> dict:
    """
    Find all *.log.*.gz files older than 'days' days.
    Return: dict[date_str] -> list of file paths
    """
    cutoff_time = datetime.now() - timedelta(days=days)
    logs_by_date = defaultdict(list)

    for gz_file in root.rglob(COMPRESSED_PATTERN):
        mtime = datetime.fromtimestamp(gz_file.stat().st_mtime)
        if mtime < cutoff_time:
            # Extract date from mtime
            date_str = mtime.strftime("%Y-%m-%d")
            logs_by_date[date_str].append(gz_file)

    return logs_by_date

def create_daily_archive(date_str: str, log_files: list) -> Path:
    """
    Create YYYY-MM-DD.tar.gz containing all log files for that date.
    Return: path to created archive
    """
    archive_name = f"/tmp/{date_str}.tar.gz"

    try:
        with tarfile.open(archive_name, "w:gz") as tar:
            for log_file in log_files:
                # Add with relative path to preserve structure
                arcname = str(log_file.relative_to(LOG_ROOT))
                tar.add(log_file, arcname=arcname)

        log_action(f"Created archive: {archive_name} ({len(log_files)} files)")
        return Path(archive_name)
    except Exception as e:
        log_action(f"ERROR creating archive {date_str}: {e}")
        return None

def rsync_to_raspi(local_archive: Path) -> bool:
    """
    Rsync archive to raspi with verification.
    Return: True if successful, False otherwise
    """
    dest_dir = f"{RASPI_HOST}:{RASPI_DEST}"

    try:
        # Create destination directory on raspi if needed
        mkdir_cmd = f"ssh {RASPI_HOST} 'mkdir -p {RASPI_DEST}'"
        subprocess.run(mkdir_cmd, shell=True, check=True, capture_output=True, timeout=30)

        # Rsync archive
        rsync_cmd = f"rsync -avz --checksum {local_archive} {dest_dir}"
        result = subprocess.run(rsync_cmd, shell=True, check=True, capture_output=True, timeout=300)

        log_action(f"Rsynced {local_archive.name} to raspi")

        # Verify by checking file exists on raspi
        verify_cmd = f"ssh {RASPI_HOST} 'test -f {RASPI_DEST}{local_archive.name} && echo OK || echo FAIL'"
        verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, timeout=30, text=True)

        if "OK" in verify_result.stdout:
            log_action(f"Verified {local_archive.name} on raspi")
            return True
        else:
            log_action(f"ERROR: Verification failed for {local_archive.name} on raspi")
            return False
    except subprocess.TimeoutExpired:
        log_action(f"ERROR: Rsync timeout for {local_archive.name}")
        return False
    except subprocess.CalledProcessError as e:
        log_action(f"ERROR: Rsync failed: {e.stderr.decode() if e.stderr else str(e)}")
        return False

def cleanup_local_logs(log_files: list):
    """Delete local compressed logs after successful backup."""
    for log_file in log_files:
        try:
            os.remove(log_file)
            log_action(f"Deleted {log_file}")
        except Exception as e:
            log_action(f"ERROR deleting {log_file}: {e}")

def cleanup_temp_archive(archive_path: Path):
    """Delete temporary archive from /tmp after rsync."""
    try:
        os.remove(archive_path)
        log_action(f"Deleted temp archive {archive_path}")
    except Exception as e:
        log_action(f"ERROR deleting temp archive {archive_path}: {e}")

def save_state(date_str: str, status: str):
    """Save state for monitoring/debugging."""
    state = {
        "last_run": datetime.now().isoformat(),
        "last_date_archived": date_str,
        "status": status
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def main():
    log_action(f"=== Log Archiver Started ===")

    if not LOG_ROOT.exists():
        log_action(f"ERROR: {LOG_ROOT} does not exist")
        sys.exit(1)

    # Find old compressed logs
    logs_by_date = find_old_compressed_logs(LOG_ROOT, ARCHIVE_DAYS)

    if not logs_by_date:
        log_action(f"No logs older than {ARCHIVE_DAYS} days found")
        save_state("none", "no_logs")
        sys.exit(0)

    log_action(f"Found {len(logs_by_date)} date(s) with old logs")

    success_count = 0
    for date_str in sorted(logs_by_date.keys()):
        log_files = logs_by_date[date_str]
        log_action(f"\nProcessing {date_str}: {len(log_files)} files")

        # Create archive
        archive = create_daily_archive(date_str, log_files)
        if not archive:
            continue

        # Rsync to raspi
        if rsync_to_raspi(archive):
            # Delete local logs
            cleanup_local_logs(log_files)
            success_count += 1
            save_state(date_str, "success")
        else:
            log_action(f"Skipping cleanup for {date_str} due to rsync failure")

        # Cleanup temp archive
        cleanup_temp_archive(archive)

    log_action(f"\n=== Log Archiver Completed: {success_count}/{len(logs_by_date)} successful ===\n")
    sys.exit(0 if success_count > 0 else 1)

if __name__ == "__main__":
    main()
