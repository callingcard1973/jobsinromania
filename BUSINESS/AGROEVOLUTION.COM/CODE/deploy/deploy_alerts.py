"""Deploy subscribe_alert.php and confirm_alert.php to agroevolution.com docroot."""

import urllib.request
import json
import ssl
import os
from pathlib import Path

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

CPANEL_HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
TOKEN = os.environ.get("CPANEL_TOKEN", "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U")
REMOTE_DIR = "/home/loaiidil/agroevolution.com"

PHP_DIR = Path(__file__).parent.parent / "php"

FILES = [
    "subscribe_alert.php",
    "confirm_alert.php",
]


def cpanel_upload_file(content_bytes: bytes, remote_dir: str, filename: str) -> int:
    boundary = "----FormBound"
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"dir\"\r\n\r\n{remote_dir}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\n1\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file-1\"; filename=\"{filename}\"\r\nContent-Type: text/plain\r\n\r\n".encode(),
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
    r = json.loads(urllib.request.urlopen(req, timeout=30, context=CTX).read())
    return r.get("data", {}).get("succeeded", 0)


def main() -> None:
    for filename in FILES:
        local_path = PHP_DIR / filename
        if not local_path.exists():
            print(f"ERROR: {local_path} not found")
            continue
        content = local_path.read_bytes()
        result = cpanel_upload_file(content, REMOTE_DIR, filename)
        status = "OK" if result else "FAILED"
        print(f"[{status}] {filename} -> {REMOTE_DIR}/{filename}")


if __name__ == "__main__":
    main()
