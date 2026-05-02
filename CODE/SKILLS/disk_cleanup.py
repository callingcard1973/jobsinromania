#!/usr/bin/env python3
"""
Disk Cleanup Script
Cleans temporary files, old logs, and cache to free disk space.
"""

import os
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path

CLEANUP_TARGETS = [
    # (path, pattern, max_age_days)
    ("/tmp", "*.log", 1),
    ("/tmp", "*.tmp", 1),
    ("/opt/ACTIVE/INFRA/LOGS", "*.log.*", 7),
    ("/var/log", "*.gz", 14),
    ("/home/tudor/.cache", "*", 7),
]

LOG_DIRS = [
    "/opt/ACTIVE/INFRA/LOGS",
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/*/logs",
    "/opt/ACTIVE/SCRAPERS/EUROPE/*/logs",
]


def get_size(path):
    """Get size of file or directory."""
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except (OSError, FileNotFoundError):
                pass
    return total


def format_size(size):
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def clean_old_files(directory, pattern, max_age_days, dry_run=True):
    """Remove files matching pattern older than max_age_days."""
    cleaned = 0
    cleaned_size = 0
    cutoff = datetime.now() - timedelta(days=max_age_days)

    path = Path(directory)
    if not path.exists():
        return 0, 0

    for f in path.glob(pattern):
        if f.is_file():
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    size = f.stat().st_size
                    if dry_run:
                        print(f"  Would delete: {f} ({format_size(size)})")
                    else:
                        f.unlink()
                        print(f"  Deleted: {f} ({format_size(size)})")
                    cleaned += 1
                    cleaned_size += size
            except (OSError, FileNotFoundError):
                pass

    return cleaned, cleaned_size


def clean_log_rotations(dry_run=True):
    """Clean rotated log files."""
    cleaned = 0
    cleaned_size = 0

    for log_dir in LOG_DIRS:
        for path in Path("/").glob(log_dir.lstrip("/")):
            if path.is_dir():
                for pattern in ["*.log.[0-9]*", "*.log.gz", "*.log.old"]:
                    c, s = clean_old_files(str(path), pattern, 7, dry_run)
                    cleaned += c
                    cleaned_size += s

    return cleaned, cleaned_size


def get_disk_usage():
    """Get disk usage for key partitions."""
    result = []
    for mount in ["/", "/opt", "/home"]:
        try:
            stat = os.statvfs(mount)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            pct = (used / total) * 100 if total > 0 else 0
            result.append((mount, used, total, pct))
        except OSError:
            pass
    return result


def main():
    parser = argparse.ArgumentParser(description="Disk cleanup utility")
    parser.add_argument("--auto", action="store_true", help="Auto clean (not dry run)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = parser.parse_args()

    dry_run = not args.auto

    print("=" * 60)
    print("DISK CLEANUP REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Show current disk usage
    print("\nCurrent Disk Usage:")
    for mount, used, total, pct in get_disk_usage():
        status = "OK" if pct < 80 else "WARNING" if pct < 90 else "CRITICAL"
        print(f"  {mount}: {format_size(used)}/{format_size(total)} ({pct:.1f}%) [{status}]")

    # Clean temp files
    print(f"\nCleaning temporary files {'(DRY RUN)' if dry_run else ''}:")
    total_cleaned = 0
    total_size = 0

    for directory, pattern, max_age in CLEANUP_TARGETS:
        if os.path.exists(directory):
            c, s = clean_old_files(directory, pattern, max_age, dry_run)
            total_cleaned += c
            total_size += s

    # Clean log rotations
    print(f"\nCleaning old log rotations {'(DRY RUN)' if dry_run else ''}:")
    c, s = clean_log_rotations(dry_run)
    total_cleaned += c
    total_size += s

    print(f"\nSummary:")
    print(f"  Files {'would be ' if dry_run else ''}cleaned: {total_cleaned}")
    print(f"  Space {'would be ' if dry_run else ''}freed: {format_size(total_size)}")

    if dry_run:
        print("\nRun with --auto to actually delete files.")


if __name__ == "__main__":
    main()
