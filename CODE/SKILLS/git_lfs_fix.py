#!/usr/bin/env python3
"""
Git LFS Push Fix Skill

Diagnoses and fixes Git LFS push failures when pushing to GitHub.

Common issues:
1. "unknown Git LFS objects" - files tracked by LFS but never uploaded
2. "pack exceeds maximum allowed size (2.00 GiB)" - commit too large
3. "exceeds GitHub's file size limit of 100.00 MB" - single file too big

Usage:
    python3 git_lfs_fix.py --diagnose
    python3 git_lfs_fix.py --find-large-files
    python3 git_lfs_fix.py --find-missing-lfs
    python3 git_lfs_fix.py --exclude-and-push
"""

import subprocess
import sys
import os
import argparse

# Directories commonly causing issues (data, node_modules, backups)
EXCLUDE_PATTERNS = [
    "node_modules/",
    "*.log",
    "*.log.*",
    "csv_archive/",
    "backup/",
    "backups/",
    "__pycache__/",
    ".git/",
]

# Known large data directories to exclude from pushes
LARGE_DATA_DIRS = [
    "ACTIVE/N8N/node_modules/",
    "ACTIVE/AVOCATI/",
    "ACTIVE/MAUTIC/",
    "ACTIVE/COMMS/",
    "INACTIVE/",
    "DATA/csv_archive/",
    "DATA/ROMANIA/BILANT/",
    "LOGS/",
    "ACTIVE/EMAIL/backup/",
    "ACTIVE/CASABUZAU/",
    "ACTIVE/DB/ASOCIATII/",
    "ACTIVE/IDEAS/LLM/",
    "ACTIVE/SCRAPERS/EUROPE/GOOGLE/",
    "ACTIVE/PROJECTS/LAW/",
    "DATA_IMPORT/",
    "ACTIVE/INFRA/REQUESTS/",
]


def run_cmd(cmd, capture=True):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    return result.stdout.strip() if capture else result.returncode


def get_commits_ahead():
    """Get number of commits ahead of origin/main."""
    run_cmd("git fetch origin")
    count = run_cmd("git rev-list --count HEAD ^origin/main 2>/dev/null")
    return int(count) if count.isdigit() else 0


def find_large_files(min_mb=50):
    """Find files larger than min_mb in staged changes."""
    print(f"\n=== Files larger than {min_mb}MB in staged changes ===\n")

    files = run_cmd("git diff --cached --name-only").split("\n")
    large_files = []

    for f in files:
        if f and os.path.exists(f):
            size_bytes = os.path.getsize(f)
            size_mb = size_bytes / (1024 * 1024)
            if size_mb >= min_mb:
                large_files.append((f, size_mb))

    large_files.sort(key=lambda x: x[1], reverse=True)

    for f, size in large_files[:20]:
        print(f"{size:8.1f} MB  {f}")

    if not large_files:
        print("No large files found in staged changes.")

    return large_files


def find_missing_lfs():
    """Find LFS pointer files that reference missing objects."""
    print("\n=== LFS Pointer Files (may have missing objects) ===\n")

    # Find files that are LFS pointers (small files with LFS header)
    lfs_extensions = [".pdf", ".xlsx", ".pkl", ".zip"]
    missing = []

    for ext in lfs_extensions:
        files = run_cmd(f"find . -name '*{ext}' -size -1k 2>/dev/null").split("\n")
        for f in files:
            if f and os.path.exists(f):
                try:
                    with open(f, 'r') as fp:
                        content = fp.read(100)
                        if content.startswith("version https://git-lfs"):
                            missing.append(f)
                except:
                    pass

    for f in missing[:30]:
        print(f"  {f}")

    print(f"\nTotal LFS pointers found: {len(missing)}")
    return missing


def diagnose():
    """Diagnose Git LFS push issues."""
    print("=== Git LFS Push Diagnostics ===\n")

    # Check commits ahead
    ahead = get_commits_ahead()
    print(f"Commits ahead of origin/main: {ahead}")

    if ahead == 0:
        print("Already in sync with origin/main!")
        return

    # Check staged changes
    stats = run_cmd("git diff --cached --shortstat")
    if stats:
        print(f"Staged changes: {stats}")

    # Check for LFS files
    lfs_count = run_cmd("git lfs ls-files 2>/dev/null | wc -l")
    print(f"LFS tracked files: {lfs_count}")

    # Check .gitattributes
    print("\nLFS tracking rules (.gitattributes):")
    attrs = run_cmd("cat .gitattributes 2>/dev/null | grep lfs")
    print(attrs if attrs else "  (none)")

    # Check for large directories
    print("\n=== Directories with most changes ===")
    dir_counts = run_cmd(
        "git diff --cached --name-only | cut -d'/' -f1-2 | sort | uniq -c | sort -rn | head -10"
    )
    print(dir_counts)

    # Find large files
    find_large_files()

    print("\n=== Recommended Actions ===")
    print("1. Exclude large data directories: git reset HEAD -- <dir>/")
    print("2. Push in smaller batches")
    print("3. Add node_modules/, *.log to .gitignore")
    print("4. For missing LFS objects, exclude those directories")


def exclude_and_push():
    """Exclude problematic directories and push in batches."""
    print("=== Exclude Large Directories and Push ===\n")

    ahead = get_commits_ahead()
    if ahead == 0:
        print("Already in sync!")
        return

    # Soft reset to squash
    print("Soft reset to origin/main...")
    run_cmd("git reset --soft origin/main", capture=False)

    # Stage all
    run_cmd("git add -A", capture=False)

    # Exclude large directories
    print("Excluding large directories...")
    for d in LARGE_DATA_DIRS:
        run_cmd(f"git reset HEAD -- {d} 2>/dev/null", capture=False)

    # Check remaining
    stats = run_cmd("git diff --cached --shortstat")
    print(f"Remaining staged: {stats}")

    # Commit
    print("\nCommitting...")
    run_cmd('git commit -m "Squashed update (excluded large data dirs)"', capture=False)

    # Push
    print("Pushing...")
    result = subprocess.run("git push origin main", shell=True)

    if result.returncode == 0:
        print("\nPush successful!")
    else:
        print("\nPush failed. Try running --diagnose for more info.")


def main():
    parser = argparse.ArgumentParser(description="Git LFS Push Fix Tool")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose push issues")
    parser.add_argument("--find-large-files", action="store_true", help="Find large files in staged changes")
    parser.add_argument("--find-missing-lfs", action="store_true", help="Find LFS pointers with missing objects")
    parser.add_argument("--exclude-and-push", action="store_true", help="Exclude large dirs and push")

    args = parser.parse_args()

    # Change to repo root
    repo_root = run_cmd("git rev-parse --show-toplevel")
    if repo_root:
        os.chdir(repo_root)

    if args.find_large_files:
        find_large_files()
    elif args.find_missing_lfs:
        find_missing_lfs()
    elif args.exclude_and_push:
        exclude_and_push()
    else:
        diagnose()


if __name__ == "__main__":
    main()
