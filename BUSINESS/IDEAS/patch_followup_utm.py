#!/usr/bin/env python3
import re

content = open("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_followup.py").read()

DOMAINS = ["interjob.ro", "careworkers.eu", "factoryjobs.eu", "buildjobs.eu"]
for domain in DOMAINS:
    pattern = rf'(https?://(?:www\.)?{re.escape(domain)}[^\s"\'\\)]*)'
    def replacer(m):
        url = m.group(1)
        if "utm_" in url or "unsubscribe" in url:
            return url
        sep = "&" if "?" in url else "?"
        return url + sep + "utm_source=email&utm_medium=followup&utm_campaign=followup"
    content = re.sub(pattern, replacer, content)

open("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_followup.py", "w").write(content)
print("followup utm done")
