"""Deploy cumpara-ferma landing page to A2 Hosting."""
import json
import os
import ssl
import urllib.request
from pathlib import Path

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

CPANEL_HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
TOKEN = os.environ.get("CPANEL_TOKEN", "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U")
REMOTE_DIR = "/home/loaiidil/agroevolution.com/cumpara-ferma"

LOCAL_FILE = Path(__file__).parent.parent / "php" / "cumpara-ferma" / "index.php"


def cpanel_mkdir(path: str) -> None:
    parts = path.rsplit("/", 1)
    parent, name = (parts[0], parts[1]) if len(parts) == 2 else ("/", parts[0])
    data = f"path={parent}&name={name}".encode()
    req = urllib.request.Request(
        f"{CPANEL_HOST}/execute/Fileman/mkdir",
        data=data,
        method="POST",
        headers={"Authorization": f"cpanel {USER}:{TOKEN}"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15, context=CTX).read())
    print(f"mkdir {path}: {resp.get('status', resp)}")


def cpanel_upload_file(content_bytes: bytes, remote_dir: str, filename: str) -> int:
    boundary = "----FormBound7823"
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
    resp = json.loads(urllib.request.urlopen(req, timeout=30, context=CTX).read())
    succeeded = resp.get("data", {}).get("succeeded", 0)
    print(f"upload {filename}: {'OK' if succeeded else 'FAILED'} | {resp}")
    return succeeded


def main() -> None:
    print("=== Deploy cumpara-ferma ===")
    print(f"Local: {LOCAL_FILE}")
    content = LOCAL_FILE.read_bytes()
    print(f"Size: {len(content)} bytes")

    cpanel_mkdir(REMOTE_DIR)
    result = cpanel_upload_file(content, REMOTE_DIR, "index.php")
    if result:
        print(f"\nDEPLOYED: https://agroevolution.com/cumpara-ferma/")
    else:
        print("\nDEPLOY FAILED — check response above")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
