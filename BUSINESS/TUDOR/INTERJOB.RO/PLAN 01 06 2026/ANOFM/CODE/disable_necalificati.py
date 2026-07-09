#!/usr/bin/env python3
import json
p = "/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json"
d = json.load(open(p, encoding="utf-8"))
for c in d["campaigns"]:
    if c["name"] == "NECALIFICATI":
        c["enabled"] = False
        if "Brevo key" not in c.get("description", ""):
            c["description"] = c.get("description", "") + " - DEZACTIVAT (Brevo key 401 invalid)"
        print("NECALIFICATI disabled")
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("saved")
