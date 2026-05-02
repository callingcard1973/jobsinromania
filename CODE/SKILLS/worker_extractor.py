#!/usr/bin/env python3
"""Worker Extractor Skill - Interface to raspibig worker database.

Commands:
    python3 /opt/ACTIVE/INFRA/SKILLS/worker_extractor.py stats
    python3 /opt/ACTIVE/INFRA/SKILLS/worker_extractor.py search --nationality Nepal
    python3 /opt/ACTIVE/INFRA/SKILLS/worker_extractor.py search --job warehouse
    python3 /opt/ACTIVE/INFRA/SKILLS/worker_extractor.py export
    python3 /opt/ACTIVE/INFRA/SKILLS/worker_extractor.py process
    python3 /opt/ACTIVE/INFRA/SKILLS/worker_extractor.py review
"""

import subprocess
import sys
import json

RASPIBIG = "raspibig"
WORKERS_PATH = "/opt/WORKERS/scripts"
VENV_PYTHON = "/opt/ACTIVE/INFRA/venv/bin/python3"

def run_remote(script: str, args: str = "") -> str:
    """Run script on raspibig."""
    cmd = f"ssh {RASPIBIG} '{VENV_PYTHON} {WORKERS_PATH}/{script} {args}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

def stats():
    """Show database statistics."""
    output = run_remote("worker_db.py", "stats")
    print(output)

def search(nationality: str = None, job: str = None, skills: str = None):
    """Search workers by criteria."""
    args = "search"
    if nationality:
        args += f" --nationality {nationality}"
    if job:
        args += f" --job {job}"
    if skills:
        args += f" --skills {skills}"
    output = run_remote("worker_db.py", args)
    print(output)

def export():
    """Export workers to CSV."""
    output = run_remote("worker_db.py", "export")
    print(output)
    print("\nFile: raspibig:/opt/WORKERS/data/workers_export.csv")

def process():
    """Process new CVs."""
    output = run_remote("cv_watcher.py", "")
    print(output)

def review():
    """List records needing review."""
    output = run_remote("worker_review.py", "list --filter review")
    print(output)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Worker Database Interface")
    subparsers = parser.add_subparsers(dest="command")

    # Stats
    subparsers.add_parser("stats", help="Show database statistics")

    # Search
    search_parser = subparsers.add_parser("search", help="Search workers")
    search_parser.add_argument("--nationality", "-n", help="Filter by nationality")
    search_parser.add_argument("--job", "-j", help="Filter by target job")
    search_parser.add_argument("--skills", "-s", help="Filter by skills")

    # Export
    subparsers.add_parser("export", help="Export to CSV")

    # Process
    subparsers.add_parser("process", help="Process new CVs")

    # Review
    subparsers.add_parser("review", help="List records needing review")

    args = parser.parse_args()

    if args.command == "stats":
        stats()
    elif args.command == "search":
        search(args.nationality, args.job, args.skills)
    elif args.command == "export":
        export()
    elif args.command == "process":
        process()
    elif args.command == "review":
        review()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
