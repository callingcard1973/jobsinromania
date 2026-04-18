#!/usr/bin/env python3
import requests, re
requests.packages.urllib3.disable_warnings()
BASE = "https://beneficiar.fonduri-ue.ro:8080"

data = {
    "option": "com_contentbuilder",
    "controller": "list",
    "view": "list",
    "Itemid": "107",
    "search_form_id": "2",
    "contentbuilder_filter_signal": "1",
    "cb_filter[48]": "Nu",
    "limit": "100",
}
r = requests.post(BASE + "/anunturi/2/entry?search_form_id=2", data=data, verify=False, timeout=30)
m = re.search(r"Pagina \d+ din (\d+)", r.text)
items = re.findall(r"details/2/(\d+)", r.text)
pages = re.findall(r"start=(\d+)", r.text)
max_p = max(int(p) for p in pages) if pages else 0
total_pages = m.group(1) if m else "unknown"
print(f"Pages: {total_pages}")
print(f"Items on page: {len(items)}")
print(f"Max start: {max_p}")
est = max_p + len(items) if max_p > 0 else len(items)
print(f"Estimated open anunturi: {est}")
