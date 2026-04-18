"""Upload fix_duplicates.php to cifn.eu via cPanel API, run it, then delete it."""
import urllib.request, urllib.parse, json, ssl, os, time

API_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
HOME = "/home/loaiidil"
DOMAIN = "cifn.eu"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def cpanel_upload(content_bytes, remote_dir, filename):
    """Upload file via cPanel Fileman/upload_files (multipart)."""
    boundary = "----PythonBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="dir"\r\n\r\n'
        f"{remote_dir}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
        f"1\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file-1"; filename="{filename}"\r\n'
        f"Content-Type: application/x-php\r\n\r\n"
    ).encode("utf-8") + content_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{HOST}/execute/Fileman/upload_files"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"cpanel {USER}:{API_TOKEN}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    r = urllib.request.urlopen(req, timeout=30, context=CTX)
    return r.read().decode()

def cpanel_delete(filepath):
    """Delete file via cPanel Fileman."""
    url = f"{HOST}/execute/Fileman/trash?files={urllib.parse.quote(filepath)}"
    req = urllib.request.Request(url, headers={"Authorization": f"cpanel {USER}:{API_TOKEN}"})
    r = urllib.request.urlopen(req, timeout=30, context=CTX)
    return r.read().decode()

# Step 1: Upload
print("Step 1: Uploading fix_duplicates.php...")
script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fix_duplicates.php')
with open(script_path, 'rb') as f:
    content = f.read()

remote_dir = f"{HOME}/{DOMAIN}"
result = cpanel_upload(content, remote_dir, "fix_duplicates.php")
print(f"  Upload: {result[:200]}")

# Step 2: Run via HTTP
print("\nStep 2: Running fix script...")
time.sleep(2)
try:
    url = f"https://{DOMAIN}/fix_duplicates.php"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
        output = r.read().decode()
    print(output)
except Exception as e:
    print(f"  Error: {e}")
    print(f"  Run manually: https://{DOMAIN}/fix_duplicates.php")

# Step 3: Delete
print("\nStep 3: Deleting fix_duplicates.php from server...")
try:
    result = cpanel_delete(f"{remote_dir}/fix_duplicates.php")
    print(f"  Deleted: {result[:200]}")
except Exception as e:
    print(f"  Delete error: {e}")
    print(f"  MANUALLY DELETE: fix_duplicates.php from cifn.eu root!")
