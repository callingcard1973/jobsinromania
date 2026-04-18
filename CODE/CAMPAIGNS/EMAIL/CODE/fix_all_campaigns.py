#!/usr/bin/env python3
"""Fix ALL campaign configs: business hours, gentle delays, pitch in templates."""
import json, glob, os

PITCH = """
De asemenea, suntem interesati sa aflam daca firma dumneavoastra este producator sau distribuitor. Daca aveti produse disponibile pentru export, am dori sa discutam posibilitati de colaborare pentru piata din Franta.
Cautam si furnizori de forta de munca pentru detasare in Europa, unde colaboram direct cu santiere si beneficiari finali.
"""

# Fix all configs
configs = set()
for p in ["/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*.json",
          "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/*.json"]:
    configs.update(glob.glob(p))

fixed_configs = 0
for f in sorted(configs):
    real = os.path.realpath(f)
    try:
        cfg = json.load(open(real))
    except:
        continue
    changed = False
    for s, c in cfg.get("sectors", {}).items():
        if not c.get("enabled"):
            continue
        if not c.get("business_hours", {}).get("enabled"):
            c["business_hours"] = {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18}
            changed = True
        if c.get("delay_min", 0) < 300:
            c["delay_min"] = 360
            c["delay_max"] = max(c.get("delay_max", 600), 600)
            changed = True
    if changed:
        json.dump(cfg, open(real, "w"), indent=2, ensure_ascii=False)
        fixed_configs += 1

print(f"Fixed {fixed_configs} configs (business hours + gentle delays)")

# Fix all templates - add pitch where missing
tpl_dirs = set()
for f in configs:
    real = os.path.realpath(f)
    try:
        cfg = json.load(open(real))
        td = cfg.get("templates_dir", "")
        if td and os.path.isdir(td):
            tpl_dirs.add(td)
    except:
        pass

fixed_tpls = 0
for td in tpl_dirs:
    for tpl in glob.glob(os.path.join(td, "**/*.txt"), recursive=True):
        try:
            content = open(tpl, encoding="utf-8").read()
        except:
            continue
        if "piata din Franta" in content:
            continue
        # Find insertion point
        for marker in ["Cu stima", "Multumesc", "Best regards", "Kind regards",
                       "Tudor", "Lucian", "Virgil", "Elena", "InterJob",
                       "BP&P", "seicarescu", "Pentru dezabonare", "Pentru a nu mai"]:
            if marker in content:
                idx = content.index(marker)
                before = content[:idx].rstrip()
                after = content[idx:]
                content = before + "\n" + PITCH + "\n" + after
                open(tpl, "w", encoding="utf-8").write(content)
                fixed_tpls += 1
                print(f"  PITCH: {tpl.split('/templates/')[-1] if '/templates/' in tpl else tpl}")
                break

print(f"\nFixed {fixed_tpls} templates (added pitch)")
