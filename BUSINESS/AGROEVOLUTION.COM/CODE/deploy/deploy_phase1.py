"""
deploy_phase1.py — Deploy save_lead.php + create_tables.php to A2 Hosting,
then trigger create_tables.php via HTTP to create MySQL tables.

Usage:
    python CODE/deploy/deploy_phase1.py
"""

import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

CPANEL_HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
TOKEN = os.environ.get("CPANEL_TOKEN", "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U")
REMOTE_DIR = "/home/loaiidil/agroevolution.com"
SITE_URL = "https://agroevolution.com"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PHP_DIR = Path(__file__).parent.parent / "php"


def cpanel_upload(content_bytes: bytes, remote_dir: str, filename: str) -> bool:
    boundary = "----FormBound7x9k"
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"dir\"\r\n\r\n{remote_dir}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\n1\r\n".encode(),
        (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file-1\"; filename=\"{filename}\"\r\n"
            f"Content-Type: text/plain\r\n\r\n"
        ).encode(),
        content_bytes,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        f"{CPANEL_HOST}/execute/Fileman/upload_files",
        data=body,
        method="POST",
        headers={
            "Authorization": f"cpanel {USER}:{TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=30, context=CTX).read())
    succeeded = resp.get("data", {}).get("succeeded", 0)
    if not succeeded:
        print(f"  Upload error: {resp}")
    return bool(succeeded)


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "deploy_phase1/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"


def main() -> int:
    files = [
        ("save_lead.php", REMOTE_DIR),
        ("create_tables.php", REMOTE_DIR),
    ]

    print("=== deploy_phase1: uploading PHP files ===")
    for filename, remote_dir in files:
        local_path = PHP_DIR / filename
        if not local_path.exists():
            print(f"  MISSING: {local_path}")
            return 1
        content = local_path.read_bytes()
        ok = cpanel_upload(content, remote_dir, filename)
        status = "OK" if ok else "FAILED"
        print(f"  {filename} -> {remote_dir}  [{status}]")
        if not ok:
            return 1

    print("\n=== Triggering create_tables.php ===")
    time.sleep(2)  # brief pause for file propagation
    url = f"{SITE_URL}/create_tables.php?key=agro2026create"
    print(f"  GET {url}")
    body = http_get(url)
    print(f"  Response: {body}")

    try:
        result = json.loads(body)
        if result.get("ok"):
            print("  Tables created successfully.")
            tables = result.get("results", {}).get("tables_found", [])
            print(f"  Tables found: {tables}")
        else:
            print("  WARNING: create_tables.php returned ok=false")
            return 1
    except json.JSONDecodeError:
        print(f"  WARNING: Non-JSON response from create_tables.php: {body[:300]}")
        return 1

    print("\n=== deploy_phase1 complete ===")
    print("  save_lead.php deployed. Test with a real POST from the site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
