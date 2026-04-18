#!/usr/bin/env python3
"""Enforce rule: corporate emails only from Brevo, Gmail only to personal domains.
Scans ALL campaign configs and fixes any Gmail sector that sends to corporate."""
import json, glob, os

configs = set()
for pattern in ["/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*.json",
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/*.json"]:
    configs.update(glob.glob(pattern))

fixed = 0
for f in sorted(configs):
    try:
        cfg = json.load(open(f))
        changed = False
        for s, c in cfg.get("sectors", {}).items():
            sender = c.get("sender_email", "")
            if "@gmail.com" in sender and not c.get("filter_type"):
                # Gmail sender without filter_type = sends to everyone including corporate
                c["filter_type"] = "personal"
                changed = True
                print(f"  FIXED {os.path.basename(f)} / {s}: {sender} -> personal only")
            elif "@gmail.com" not in sender and "zoho" not in sender.lower() and not c.get("filter_type"):
                # Brevo sender without filter_type - should be corporate
                # But some campaigns intentionally send to all via Brevo (like ANOFM Brevo sectors)
                # Only set corporate if there's also a Gmail sector in same config
                has_gmail = any("@gmail.com" in cc.get("sender_email","") for cc in cfg.get("sectors",{}).values())
                if has_gmail:
                    c["filter_type"] = "corporate"
                    changed = True
                    print(f"  FIXED {os.path.basename(f)} / {s}: {sender} -> corporate only")
        if changed:
            json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
            fixed += 1
    except Exception as e:
        pass

print(f"\nFixed {fixed} configs")
