#!/usr/bin/env python3
"""
OIPA WordPress Deployment Skill
Deploy static files to oipa.ro via Claude API plugin

Usage:
    python3 oipa_deploy.py --deploy /path/to/build
    python3 oipa_deploy.py --list [path]
    python3 oipa_deploy.py --upload local_file remote_path
    python3 oipa_deploy.py --delete remote_path
    python3 oipa_deploy.py --ping
"""

import os
import sys
import json
import base64
import argparse
import requests
from pathlib import Path

API_URL = "https://oipa.ro/"
API_KEY = "oipa-claude-2026-xK9mP2vL"
DEPLOY_PATH = "new/"

def api_call(action, params=None, data=None):
    """Make API call to Claude API plugin"""
    headers = {"X-Claude-Key": API_KEY}
    url = f"{API_URL}?claude_api={action}"
    if params:
        url += "&" + "&".join(f"{k}={v}" for k, v in params.items())

    if data:
        r = requests.post(url, headers=headers, data=data, timeout=30)
    else:
        r = requests.get(url, headers=headers, timeout=30)

    try:
        return r.json()
    except:
        return {"error": r.text[:200]}

def ping():
    """Test API connection"""
    result = api_call("ping")
    print(json.dumps(result, indent=2))
    return result.get("status") == "ok"

def list_files(path=""):
    """List files in directory"""
    result = api_call("list", {"path": DEPLOY_PATH + path})
    if "files" in result:
        for f in result["files"]:
            if f not in [".", ".."]:
                print(f)
    else:
        print(result)
    return result

def upload_file(local_path, remote_path):
    """Upload a single file"""
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    result = api_call("upload", data={
        "path": DEPLOY_PATH + remote_path,
        "content": content
    })
    return result

def delete_file(remote_path):
    """Delete a file"""
    result = api_call("delete", {"path": DEPLOY_PATH + remote_path})
    print(json.dumps(result, indent=2))
    return result

def mkdir(remote_path):
    """Create directory"""
    result = api_call("mkdir", {"path": DEPLOY_PATH + remote_path})
    return result

def deploy_directory(local_dir):
    """Deploy entire directory to oipa.ro/new/"""
    local_path = Path(local_dir)
    if not local_path.exists():
        print(f"Error: {local_dir} not found")
        return False

    files = list(local_path.rglob("*"))
    total = len([f for f in files if f.is_file()])
    uploaded = 0

    print(f"Deploying {total} files to {API_URL}{DEPLOY_PATH}")

    for file_path in files:
        if file_path.is_file():
            relative = file_path.relative_to(local_path)
            remote = str(relative)

            # Create parent dirs
            parent = str(relative.parent)
            if parent != ".":
                mkdir(parent)

            # Upload file
            result = upload_file(file_path, remote)
            uploaded += 1
            status = "OK" if result.get("status") == "ok" else "FAIL"
            print(f"[{uploaded}/{total}] {status} {remote}")

    print(f"\nDeployed {uploaded} files to https://oipa.ro/{DEPLOY_PATH}")
    return True

def main():
    parser = argparse.ArgumentParser(description="OIPA Deployment Tool")
    parser.add_argument("--ping", action="store_true", help="Test API connection")
    parser.add_argument("--list", nargs="?", const="", help="List files")
    parser.add_argument("--deploy", metavar="DIR", help="Deploy directory")
    parser.add_argument("--upload", nargs=2, metavar=("LOCAL", "REMOTE"), help="Upload file")
    parser.add_argument("--delete", metavar="PATH", help="Delete file")

    args = parser.parse_args()

    if args.ping:
        ping()
    elif args.list is not None:
        list_files(args.list)
    elif args.deploy:
        deploy_directory(args.deploy)
    elif args.upload:
        result = upload_file(args.upload[0], args.upload[1])
        print(json.dumps(result, indent=2))
    elif args.delete:
        delete_file(args.delete)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
