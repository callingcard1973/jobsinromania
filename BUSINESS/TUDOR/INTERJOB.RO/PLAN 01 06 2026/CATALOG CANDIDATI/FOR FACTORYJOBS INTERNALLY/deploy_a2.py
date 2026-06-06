#!/usr/bin/env python3
"""Deploy pentru-angajatori page to A2 Hosting cPanel."""
import os
import json
import subprocess
import sys
from pathlib import Path

# Config
A2_HOST = "nl1-cl8-ats1.a2hosting.com:2083"
A2_USER = "loaiidil"
A2_TOKEN = "K9ATCMHPKVSKUV2M97447JLY45EH29KQ"
DOMAIN = "factoryjobs.eu"
DOCROOT = f"/home/{A2_USER}/{DOMAIN}/pentru-angajatori"

# Local files to deploy
LOCAL_DIR = Path(__file__).parent
FILES_TO_DEPLOY = [
    ("pentru-angajatori.html", f"{DOCROOT}/index.html"),
    ("assets/employer.css", f"{DOCROOT}/assets/employer.css"),
    ("assets/employer.js", f"{DOCROOT}/assets/employer.js"),
]

def deploy_file(local_path, remote_path):
    """Upload file via cPanel API."""
    local_full = LOCAL_DIR / local_path
    if not local_full.exists():
        print(f"✗ File not found: {local_full}")
        return False

    with open(local_full, 'rb') as f:
        content = f.read()

    # cPanel Fileman API call
    cmd = [
        "curl", "-s",
        "-u", f"{A2_USER}:{A2_TOKEN}",
        f"https://{A2_HOST}/cpsess0/execute/Fileman/save_file",
        "-d", f"file={remote_path}",
        "-d", f"content={content.decode('utf-8')}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✓ {remote_path}")
            return True
        else:
            print(f"✗ {remote_path}: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ {remote_path}: {e}")
        return False

def main():
    print(f"Deploying to https://{DOMAIN}/pentru-angajatori/\n")

    success_count = 0
    for local, remote in FILES_TO_DEPLOY:
        if deploy_file(local, remote):
            success_count += 1

    print(f"\n✓ Deployed {success_count}/{len(FILES_TO_DEPLOY)} files")

    if success_count == len(FILES_TO_DEPLOY):
        print(f"\n✓ Live: https://{DOMAIN}/pentru-angajatori/")
        return 0
    else:
        print(f"\n✗ Deployment incomplete")
        return 1

if __name__ == "__main__":
    sys.exit(main())
