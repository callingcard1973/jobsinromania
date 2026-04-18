"""Fix all gmail_sender limits to 20 (except ANOFM which stays at 40)."""
import json, glob

BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
configs = glob.glob(f"{BASE}/configs/*.json") + glob.glob(f"{BASE}/ROMANIA/configs/*.json")
fixes = 0

for f in sorted(configs):
    if "state" in f or "archived" in f:
        continue
    try:
        d = json.load(open(f))
    except:
        continue

    modified = False
    fname = f.split("/")[-1]

    for s in d.get("gmail_senders", []):
        if "@gmail.com" in s.get("email", ""):
            old = s.get("limit", 0)
            if old > 20 and "anofm" not in fname.lower():
                s["limit"] = 20
                modified = True
                fixes += 1
            elif old > 40 and "anofm" in fname.lower():
                s["limit"] = 40
                modified = True
                fixes += 1

    if modified:
        with open(f, "w") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
        print(f"Fixed: {fname}")

print(f"\n{fixes} gmail_sender limits corrected")
