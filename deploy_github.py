#!/usr/bin/env python3
"""Commit and push generated HTML pages to GitHub daily."""

import os
import sys
import subprocess
from datetime import datetime

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(REPO_DIR, "docs")
JOBS_FILE = os.path.join(REPO_DIR, "data", "jobs.json")


def run_cmd(cmd: str, check: bool = True) -> str:
    """Run shell command, return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=REPO_DIR, capture_output=True, text=True, check=check
        )
        return result.stdout.strip() if result.stdout else result.stderr.strip()
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Command failed: {cmd}\n{e.stderr}")
            sys.exit(1)
        return e.stderr.strip()


def check_git_config():
    """Verify git user is configured."""
    name = run_cmd("git config user.name", check=False)
    email = run_cmd("git config user.email", check=False)
    if not name or not email:
        run_cmd("git config user.name 'JobsInRomania Bot'", check=False)
        run_cmd("git config user.email 'bot@jobsinromania.github.io'", check=False)


def commit_and_push():
    """Stage, commit, and push changes."""
    check_git_config()

    # Check if docs dir has changes
    status = run_cmd("git status --porcelain", check=False)
    if not status:
        print("No changes to deploy.")
        return False

    # Stage changes
    run_cmd("git add docs/ data/jobs.json")

    # Commit
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    run_cmd(f'git commit -m "jobs: update {timestamp}"')

    # Push
    run_cmd("git push origin main")
    print(f"Deployed to GitHub ({timestamp})")
    return True


def main():
    if not os.path.isdir(REPO_DIR):
        print(f"Error: Repo dir not found: {REPO_DIR}")
        sys.exit(1)

    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        print(f"Error: Not a git repo: {REPO_DIR}")
        sys.exit(1)

    commit_and_push()


if __name__ == "__main__":
    main()
