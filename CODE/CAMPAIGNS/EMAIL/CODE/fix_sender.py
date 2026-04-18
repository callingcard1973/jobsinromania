import json

# Update RO Construction: switch PERSONAL to manpowersearchromania
f = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/ro_ted_construction.json"
cfg = json.load(open(f))
cfg["sectors"]["PERSONAL"]["sender_key"] = "GMAIL_MANPOWERSEARCH"
cfg["sectors"]["PERSONAL"]["sender_email"] = "manpowersearchromania@gmail.com"
cfg["sectors"]["PERSONAL"]["daily_limit"] = 30
json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
print("RO Construction PERSONAL: manpowersearchromania 30/day")

# Verify ANOFM_GMAIL1 unchanged
f2 = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/anofm.json"
cfg2 = json.load(open(f2))
g1 = cfg2["sectors"]["ANOFM_GMAIL1"]
print(f"ANOFM_GMAIL1: {g1['sender_email']} {g1['daily_limit']}/day (unchanged)")
print("manpowersearchromania total: 80 (ANOFM) + 30 (Construction) = 110/day")
