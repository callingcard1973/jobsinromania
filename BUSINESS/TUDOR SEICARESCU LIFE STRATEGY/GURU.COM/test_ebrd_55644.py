#!/usr/bin/env python3
import requests, re, time
from bs4 import BeautifulSoup

sess = requests.Session()
sess.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0'
time.sleep(3)
r = sess.get("https://www.ebrd.com/home/work-with-us/projects/psd/55644.html", timeout=30)
print("Status:", r.status_code)
if r.status_code != 200:
    print("Blocked. Body:", r.text[:200])
    exit()

soup = BeautifulSoup(r.text, "html.parser")
text = soup.get_text()

# Find Company Contact Information section
print("\n=== RAW TEXT around contact ===")
idx = text.find("Company Contact Information")
if idx >= 0:
    print(text[idx:idx+300])
else:
    print("NOT FOUND by text search")
    # Search for the contact name directly
    idx2 = text.find("Nevzat")
    if idx2 >= 0:
        print("Found Nevzat at:", text[max(0,idx2-50):idx2+200])
    # Search HTML structure
    for div in soup.find_all(["div", "section", "aside"]):
        cls = div.get("class", [])
        if any("contact" in c.lower() for c in cls):
            print(f"\nContact div ({cls}):", div.get_text(strip=True)[:200])

# Also check if it's loaded via JavaScript (not in initial HTML)
print("\n=== Search for ntogrul in HTML ===")
if "ntogrul" in r.text:
    idx = r.text.find("ntogrul")
    print("Found in raw HTML:", r.text[max(0,idx-100):idx+100])
else:
    print("NOT in raw HTML - loaded via JavaScript")
    # Check for data attributes or API calls
    api_calls = re.findall(r'(https?://[^"\']+(?:contact|psd|api)[^"\']*)', r.text)
    for url in api_calls[:5]:
        print(f"  API URL: {url}")
