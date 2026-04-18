import json, glob

configs = glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/*.json")
configs += glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*.json")

fixed = 0
for f in set(configs):
    try:
        cfg = json.load(open(f))
        changed = False
        for s, c in cfg.get("sectors", {}).items():
            sender = c.get("sender_email", "")
            reply = c.get("reply_to", "")
            if "@gmail.com" in sender and "@gmail.com" not in reply:
                c["reply_to"] = sender
                changed = True
                print(f"  {s}: reply_to {reply} -> {sender}")
        if changed:
            json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
            fixed += 1
    except:
        pass
print(f"\nFixed {fixed} configs")
