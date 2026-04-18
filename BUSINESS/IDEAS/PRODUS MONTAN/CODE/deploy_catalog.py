#!/usr/bin/env python3
"""Deploy catalog/ to agroevolution.com/catalog/ via cPanel API."""
import urllib.request
import urllib.parse
import json
import ssl
import os
import time

# --
API_TOKEN = "KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453"
HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
HOME = f"/home/{USER}"
SITE = "agroevolution.com"
REMOTE_DIR = f"{HOME}/{SITE}/catalog"
LOCAL_DIR = os.path.join(os.path.dirname(__file__), "catalog")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def cpanel_upload(content_bytes, filename, remote_dir):
    """Upload file via cPanel Fileman/upload_files (proven method from seo_deploy)."""
    boundary = "----FormBound7MA4YWxk"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="dir"\r\n\r\n'
        f"{remote_dir}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
        f"1\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file-1"; filename="{filename}"\r\n'
        f"Content-Type: text/html\r\n\r\n"
    ).encode("utf-8") + content_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{HOST}/execute/Fileman/upload_files"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"cpanel {USER}:{API_TOKEN}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=60, context=CTX)
            return True
        except Exception as e:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                print(f"  ERR {filename}: {e}")
                return False


def main():
    # First upload a dummy file to create the catalog dir implicitly
    # cPanel upload_files auto-creates the target dir
    files = sorted(f for f in os.listdir(LOCAL_DIR) if f.endswith(".html"))
    print(f"Uploading {len(files)} files to {REMOTE_DIR}...")

    ok = 0
    for fname in files:
        local_path = os.path.join(LOCAL_DIR, fname)
        size_kb = os.path.getsize(local_path) // 1024
        print(f"  {fname} ({size_kb}KB)...", end=" ", flush=True)
        with open(local_path, "rb") as f:
            content = f.read()
        if cpanel_upload(content, fname, REMOTE_DIR):
            print("OK")
            ok += 1
        else:
            print("FAILED")

    print(f"\nDone: {ok}/{len(files)} files uploaded")
    if ok > 0:
        print(f"Live: https://agroevolution.com/catalog/")


if __name__ == "__main__":
    main()
