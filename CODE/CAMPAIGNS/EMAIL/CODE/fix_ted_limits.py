import json, glob

# buildjobs.eu shared across 11 TED configs (10 EU + 1 RO)
# Brevo free = 300/day. 11 x 27 = 297, safe.
for f in sorted(glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*_ted_construction.json")):
    cfg = json.load(open(f))
    corp = cfg.get("sectors", {}).get("CORPORATE", {})
    if corp.get("sender_email") == "office@buildjobs.eu":
        corp["daily_limit"] = 27
        json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)

# RO construction is in ROMANIA/configs, also uses buildjobs
f2 = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/ro_ted_construction.json"
cfg = json.load(open(f2))
corp = cfg["sectors"].get("CORPORATE", {})
if corp.get("sender_email") == "office@buildjobs.eu":
    corp["daily_limit"] = 27
    json.dump(cfg, open(f2, "w"), indent=2, ensure_ascii=False)

print("All buildjobs.eu CORPORATE set to 27/day (11 x 27 = 297, under 300 limit)")
