#!/usr/bin/env python3
"""Deploy fixed decode_email into the scraper."""
import re

path = "/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/SCRAPER_beneficiar.fonduri-ue/beneficiar_fonduri_ue_scraper.py"
with open(path) as f:
    lines = f.readlines()

new_func = '''def decode_email(text):
    """Decode obfuscated email from beneficiar.fonduri-ue.ro JavaScript."""
    import html as html_module
    import re as re2
    m = re2.search(r"var (addy\\d+)", text)
    if not m:
        return ""
    var_name = m.group(1)
    addy_lines = [l.strip() for l in text.split("\\n") if var_name in l]
    all_strings = []
    for line in addy_lines:
        if "document.write" in line:
            continue
        strings = re2.findall(r"'([^']*)'", line)
        all_strings.extend(strings)
    raw = "".join(all_strings)
    email = html_module.unescape(raw)
    email = re2.sub(r"&#(\\d+);", lambda x: chr(int(x.group(1))), email)
    email = email.strip()
    if "@" not in email:
        return ""
    return email

'''

start = None
end = None
for i, line in enumerate(lines):
    if line.startswith("def decode_email"):
        start = i
    elif start is not None and line.startswith("def ") and i > start:
        end = i
        break

if start is not None:
    lines[start:end] = [new_func]
    with open(path, "w") as f:
        f.writelines(lines)
    print(f"FIXED: replaced lines {start}-{end}")
    # Verify
    with open(path) as f:
        content = f.read()
    if "addy_lines" in content and "all_strings" in content:
        print("Verified: new decode_email is in place")
    else:
        print("WARNING: verification failed")
else:
    print("ERROR: decode_email function not found")
