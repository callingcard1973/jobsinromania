#!/usr/bin/env python3
import json
p = "/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json"
d = json.load(open(p, encoding="utf-8"))
for c in d["campaigns"]:
    if c["name"] == "EXPORT_AT":
        c["enabled"] = True
        c["daily_limit"] = 25
        c["daily_cap"] = 25
        print("EXPORT_AT enabled, cap 25")
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("saved")
