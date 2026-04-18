import json, glob

# Fix TED PERSONAL sectors: add business hours, set gentle delays
for f in sorted(glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*_ted_construction.json")):
    cfg = json.load(open(f))
    for s, c in cfg.get("sectors", {}).items():
        if s == "PERSONAL":
            c["business_hours"] = {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18}
            c["delay_min"] = 360
            c["delay_max"] = 600
    json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)

print("Fixed all TED PERSONAL: business hours 8-18 + delays 360-600s")

# Also fix TED templates pitch (they're in /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/ templates)
import os
for f in sorted(glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*_ted_construction.json")):
    cfg = json.load(open(f))
    tpl_dir = cfg.get("templates_dir", "")
    for tpl in glob.glob(os.path.join(tpl_dir, "*.txt")):
        content = open(tpl).read()
        if "piata din Franta" not in content:
            for marker in ["Best regards", "Kind regards", "Tudor", "InterJob"]:
                if marker in content:
                    parts = content.split(marker, 1)
                    pitch = "\nDe asemenea, suntem interesati sa aflam daca firma dumneavoastra este producator sau distribuitor. Daca aveti produse disponibile pentru export, am dori sa discutam posibilitati de colaborare pentru piata din Franta.\nCautam si furnizori de forta de munca pentru detasare in Europa, unde colaboram direct cu santiere si beneficiari finali.\n\n"
                    content = parts[0].rstrip() + pitch + marker + parts[1]
                    open(tpl, "w").write(content)
                    print(f"  PITCH added: {tpl}")
                    break

# Fix RO configs that reference templates outside ROMANIA dir
for f in sorted(glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/*.json")):
    cfg = json.load(open(f))
    tpl_dir = cfg.get("templates_dir", "")
    for tpl in glob.glob(os.path.join(tpl_dir, "*.txt")):
        content = open(tpl).read()
        if "piata din Franta" not in content:
            print(f"  STILL MISSING pitch: {tpl}")
