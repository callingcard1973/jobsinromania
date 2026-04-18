#!/usr/bin/env python3
import requests
requests.packages.urllib3.disable_warnings()

# Test Google Drive file
url = "https://drive.google.com/uc?export=download&id=1JXjN2D0cXxBiU7r8FTv1oI47ydFogY7_"
r = requests.get(url, timeout=30, allow_redirects=True)
print("GDrive status:", r.status_code)
print("GDrive type:", r.headers.get("content-type"))
print("GDrive size:", len(r.content))
if b"confirm" in r.content or b"virus" in r.content.lower()[:5000]:
    print("-> NEEDS VIRUS SCAN CONFIRMATION")
    # Extract confirm token and retry
    import re
    m = re.search(r'confirm=([^&"]+)', r.text)
    if m:
        url2 = url + "&confirm=" + m.group(1)
        r2 = requests.get(url2, timeout=60, allow_redirects=True)
        print("Retry size:", len(r2.content))
        print("Retry type:", r2.headers.get("content-type"))
        print("Retry first 20:", r2.content[:20])
elif b"<html" in r.content[:100].lower():
    print("-> Got HTML page, not file")
    print(r.text[:300])
else:
    print("-> Got file directly")
    print("First 20:", r.content[:20])

print()

# Test Dropbox
url3 = "https://www.dropbox.com/s/feb5nrhw458sjrw/HalaOportun.rar?dl=1"
r3 = requests.get(url3, timeout=30, allow_redirects=True)
print("Dropbox status:", r3.status_code)
print("Dropbox type:", r3.headers.get("content-type"))
print("Dropbox size:", len(r3.content))
print("Dropbox first 20:", r3.content[:20])
