"""Remove gmail_senders where a PERSONAL sector already uses the same Gmail.
The orchestrator uses sectors, not gmail_senders — gmail_senders is legacy."""
import json, glob

BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
configs = glob.glob(f"{BASE}/configs/*.json") + glob.glob(f"{BASE}/ROMANIA/configs/*.json")
seen_files = set()

for f in sorted(configs):
    if "state" in f or "archived" in f:
        continue
    fname = f.split("/")[-1]
    if fname in seen_files:
        continue
    seen_files.add(fname)
    try:
        d = json.load(open(f))
    except:
        continue

    # Find Gmail emails used in sectors
    sector_gmails = set()
    for k, v in d.get("sectors", {}).items():
        se = v.get("sender_email", "")
        if "@gmail.com" in se:
            sector_gmails.add(se)

    # Remove gmail_senders that duplicate sector assignments
    gs = d.get("gmail_senders", [])
    if gs and sector_gmails:
        new_gs = [s for s in gs if s.get("email", "") not in sector_gmails]
        removed = len(gs) - len(new_gs)
        if removed > 0:
            d["gmail_senders"] = new_gs
            # Write to BOTH locations
            for path in [f"{BASE}/configs/{fname}", f"{BASE}/ROMANIA/configs/{fname}"]:
                try:
                    json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
                except:
                    pass
            print(f"{fname}: removed {removed} duplicate gmail_senders (already in sectors)")

print("\nDone")
