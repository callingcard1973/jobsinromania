#!/usr/bin/env python3
"""Test email decoding from beneficiar.fonduri-ue.ro"""
import requests
import re
import html as H

requests.packages.urllib3.disable_warnings()

def decode_email(text):
    """Decode obfuscated email from beneficiar.fonduri-ue.ro JavaScript."""
    # Find the addy variable name
    m = re.search(r"var (addy\d+)", text)
    if not m:
        return ""
    var_name = m.group(1)
    # Get all lines mentioning this variable
    lines = [l.strip() for l in text.split("\n") if var_name in l]
    # Extract all quoted strings from these lines
    all_strings = []
    for line in lines:
        if "document.write" in line:
            continue
        strings = re.findall(r"'([^']*)'", line)
        all_strings.extend(strings)
    # Join and decode HTML entities
    raw = "".join(all_strings)
    email = H.unescape(raw)
    # Clean any remaining numeric entities
    email = re.sub(r"&#(\d+);", lambda x: chr(int(x.group(1))), email)
    email = email.strip()
    if "@" not in email:
        return ""
    return email

# Test on multiple pages
for eid in [51902, 51900, 51898, 51895, 51890, 51885, 51880, 51870, 51860, 51850]:
    url = f"https://beneficiar.fonduri-ue.ro:8080/anunturi/details/2/{eid}/"
    r = requests.get(url, verify=False, timeout=30)
    email = decode_email(r.text)
    print(f"  {eid}: {email}")
