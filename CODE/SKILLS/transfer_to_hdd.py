#!/usr/bin/env python3
"""
Safe OPENDATA Transfer to HDD

Transfers /opt/ACTIVE/OPENDATA/DATA/ (79GB) from NVMe to HDD (/mnt/hdd)
with proper process checking, progress monitoring, and symlink creation.

Usage:
    python3 transfer_to_hdd.py --check    # Check what's running
    python3 transfer_to_hdd.py --dry-run  # Preview transfer
    python3 transfer_to_hdd.py --transfer # Execute transfer
    python3 transfer_to_hdd.py --status   # Check transfer status
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Paths
SOURCE = Path("/opt/ACTIVE/OPENDATA/DATA")
DEST = Path("/mnt/hdd/OPENDATA_DATA")
BACKUP = Path("/mnt/hdd/OPENDATA_DATA_backup")

# Processes that should be stopped before transfer
BLOCKING_PROCESSES = [
    "ted_extract",
    "ted_explorer",
    "cv_watcher",
    "scraper",
    "campaign",
]


def get_open_files(directory):
    """Get list of processes with open files in directory."""
    try:
        result = subprocess.run(
            ["lsof", "+D", str(directory)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.stdout:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            processes = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    cmd = parts[0]
                    pid = parts[1]
                    if cmd not in processes:
                        processes[cmd] = []
                    processes[cmd].append(pid)
            return processes
    except Exception as e:
        print(f"  Error checking open files: {e}")
    return {}


def check_blocking_processes():
    """Check for processes that might block transfer."""
    print("\n" + "="*60)
    print(" CHECKING BLOCKING PROCESSES")
    print("="*60)

    # Check open files
    print("\n  Files open in OPENDATA:")
    open_files = get_open_files(SOURCE)
    if open_files:
        for cmd, pids in open_files.items():
            print(f"    {cmd}: PIDs {', '.join(pids)}")
        return True, open_files
    else:
        print("    None")
        return False, {}


def check_disk_space():
    """Check available disk space."""
    print("\n" + "="*60)
    print(" DISK SPACE CHECK")
    print("="*60)

    # Source size
    total_size = 0
    file_count = 0
    for f in SOURCE.rglob("*"):
        if f.is_file():
            total_size += f.stat().st_size
            file_count += 1

    source_gb = total_size / (1024**3)
    print(f"\n  Source: {SOURCE}")
    print(f"    Files: {file_count:,}")
    print(f"    Size: {source_gb:.1f} GB")

    # Destination space
    dest_stat = shutil.disk_usage(DEST.parent)
    dest_free = dest_stat.free / (1024**3)
    print(f"\n  Destination: {DEST.parent}")
    print(f"    Free: {dest_free:.1f} GB")

    if dest_free < source_gb * 1.2:  # Need 20% buffer
        print(f"\n  WARNING: Not enough space! Need {source_gb*1.2:.1f} GB")
        return False, source_gb, file_count

    print(f"\n  OK: Sufficient space available")
    return True, source_gb, file_count


def transfer_with_rsync(dry_run=False):
    """Transfer using rsync with progress."""
    print("\n" + "="*60)
    print(" TRANSFER" + (" (DRY RUN)" if dry_run else ""))
    print("="*60)

    # Ensure destination exists
    DEST.mkdir(parents=True, exist_ok=True)

    # Build rsync command
    cmd = [
        "rsync",
        "-avh",
        "--progress",
        "--stats",
    ]

    if dry_run:
        cmd.append("--dry-run")

    cmd.extend([
        str(SOURCE) + "/",
        str(DEST) + "/"
    ])

    print(f"\n  Command: {' '.join(cmd)}")
    print(f"\n  Starting transfer...")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            timeout=7200  # 2 hours max
        )

        elapsed = time.time() - start_time
        print(f"\n  Transfer completed in {elapsed/60:.1f} minutes")

        if result.returncode == 0:
            return True
        else:
            print(f"  rsync returned code: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print("  TIMEOUT: Transfer took too long")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def create_symlink():
    """Create symlink from original location to new location."""
    print("\n" + "="*60)
    print(" CREATING SYMLINK")
    print("="*60)

    if SOURCE.is_symlink():
        print(f"  Source is already a symlink: {SOURCE} -> {SOURCE.resolve()}")
        return True

    # Backup original (just rename)
    if SOURCE.exists():
        backup_path = SOURCE.parent / "DATA_old"
        print(f"\n  Renaming original: {SOURCE} -> {backup_path}")
        SOURCE.rename(backup_path)

    # Create symlink
    print(f"  Creating symlink: {SOURCE} -> {DEST}")
    SOURCE.symlink_to(DEST)

    # Verify
    if SOURCE.is_symlink() and SOURCE.resolve() == DEST:
        print(f"  OK: Symlink created successfully")
        return True
    else:
        print(f"  ERROR: Symlink creation failed")
        return False


def verify_transfer():
    """Verify the transfer was successful."""
    print("\n" + "="*60)
    print(" VERIFYING TRANSFER")
    print("="*60)

    if not DEST.exists():
        print(f"  ERROR: Destination not found: {DEST}")
        return False

    # Count files in destination
    dest_files = list(DEST.rglob("*"))
    dest_count = len([f for f in dest_files if f.is_file()])
    dest_size = sum(f.stat().st_size for f in dest_files if f.is_file())

    print(f"\n  Destination: {DEST}")
    print(f"    Files: {dest_count:,}")
    print(f"    Size: {dest_size / (1024**3):.1f} GB")

    # Check a few key subdirectories
    key_dirs = ["EU_TENDERS", "ACHIZITII_PUBLICE", "AGENCIES", "ANOFM_FRESH"]
    for d in key_dirs:
        path = DEST / d
        if path.exists():
            files = len(list(path.rglob("*")))
            print(f"    {d}: {files} files")
        else:
            print(f"    {d}: MISSING!")

    return True


def cleanup_old():
    """Remove old data after successful transfer and symlink."""
    print("\n" + "="*60)
    print(" CLEANUP")
    print("="*60)

    old_path = SOURCE.parent / "DATA_old"
    if old_path.exists():
        size = sum(f.stat().st_size for f in old_path.rglob("*") if f.is_file())
        print(f"\n  Old data: {old_path}")
        print(f"  Size: {size / (1024**3):.1f} GB")
        print(f"\n  To remove, run:")
        print(f"    rm -rf {old_path}")
    else:
        print("  No old data to clean up")


def status():
    """Check current transfer status."""
    print("\n" + "="*60)
    print(" TRANSFER STATUS")
    print("="*60)

    # Check if source is symlink
    print(f"\n  Source: {SOURCE}")
    if SOURCE.is_symlink():
        target = SOURCE.resolve()
        print(f"    -> Symlink to: {target}")
    elif SOURCE.exists():
        size = sum(f.stat().st_size for f in SOURCE.rglob("*") if f.is_file())
        print(f"    -> Original directory: {size / (1024**3):.1f} GB")
    else:
        print(f"    -> NOT FOUND")

    # Check destination
    print(f"\n  Destination: {DEST}")
    if DEST.exists():
        size = sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file())
        files = len(list(DEST.rglob("*")))
        print(f"    -> Exists: {files} files, {size / (1024**3):.1f} GB")
    else:
        print(f"    -> NOT FOUND")

    # Check for old data
    old_path = SOURCE.parent / "DATA_old"
    if old_path.exists():
        size = sum(f.stat().st_size for f in old_path.rglob("*") if f.is_file())
        print(f"\n  Old data: {old_path}")
        print(f"    -> {size / (1024**3):.1f} GB (can be deleted)")


def full_transfer():
    """Execute full transfer workflow."""
    print("\n" + "="*60)
    print(" FULL TRANSFER WORKFLOW")
    print("="*60)
    print(f" Start: {datetime.now()}")

    # 1. Check blocking processes
    blocking, processes = check_blocking_processes()
    if blocking:
        print("\n  BLOCKING PROCESSES DETECTED!")
        print("  Please stop the following before transfer:")
        for cmd, pids in processes.items():
            print(f"    kill {' '.join(pids)}  # {cmd}")
        print("\n  Then run this script again with --transfer")
        return False

    # 2. Check disk space
    ok, size_gb, file_count = check_disk_space()
    if not ok:
        return False

    # 3. Transfer
    print("\n  Proceeding with transfer...")
    if not transfer_with_rsync(dry_run=False):
        print("  Transfer failed!")
        return False

    # 4. Verify
    if not verify_transfer():
        print("  Verification failed!")
        return False

    # 5. Create symlink
    if not create_symlink():
        print("  Symlink creation failed!")
        return False

    # 6. Show cleanup info
    cleanup_old()

    print("\n" + "="*60)
    print(" TRANSFER COMPLETE!")
    print("="*60)
    print(f" End: {datetime.now()}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safe OPENDATA Transfer to HDD")
    parser.add_argument("--check", action="store_true", help="Check blocking processes")
    parser.add_argument("--dry-run", action="store_true", help="Preview transfer (no changes)")
    parser.add_argument("--transfer", action="store_true", help="Execute full transfer")
    parser.add_argument("--verify", action="store_true", help="Verify transfer")
    parser.add_argument("--symlink", action="store_true", help="Create symlink only")
    parser.add_argument("--status", action="store_true", help="Check transfer status")
    args = parser.parse_args()

    if args.check:
        check_blocking_processes()
        check_disk_space()
    elif args.dry_run:
        check_blocking_processes()
        check_disk_space()
        transfer_with_rsync(dry_run=True)
    elif args.transfer:
        full_transfer()
    elif args.verify:
        verify_transfer()
    elif args.symlink:
        create_symlink()
    elif args.status:
        status()
    else:
        parser.print_help()
