import json, glob, os

configs_dir = "/opt/ACTIVE/EMAIL/CAMPAIGNS/ROMANIA/configs"
old_tpl_base = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/"
new_tpl_base = "/opt/ACTIVE/EMAIL/CAMPAIGNS/ROMANIA/templates/"

for cf in sorted(glob.glob(f"{configs_dir}/*.json")):
    try:
        d = json.load(open(cf))
        changed = False

        # Fix templates_dir
        tpl = d.get("templates_dir", "")
        if old_tpl_base in tpl:
            d["templates_dir"] = tpl.replace(old_tpl_base, new_tpl_base)
            changed = True

        # Fix any other paths referencing UNIFIED
        txt = json.dumps(d)
        if "/UNIFIED/" in txt:
            txt = txt.replace("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/", new_tpl_base)
            d = json.loads(txt)
            changed = True

        if changed:
            json.dump(d, open(cf, "w"), indent=2, ensure_ascii=False)
            print(f"FIXED {os.path.basename(cf)}: {d.get('templates_dir','')}")
        else:
            print(f"OK   {os.path.basename(cf)}: {d.get('templates_dir','')}")
    except Exception as e:
        print(f"ERR  {os.path.basename(cf)}: {e}")
