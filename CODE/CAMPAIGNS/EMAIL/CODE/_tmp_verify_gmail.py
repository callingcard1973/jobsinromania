import json, glob

BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
configs = glob.glob(f"{BASE}/configs/*.json") + glob.glob(f"{BASE}/ROMANIA/configs/*.json")
alloc = {}

for f in sorted(configs):
    if "state" in f or "archived" in f:
        continue
    try:
        d = json.load(open(f))
    except:
        continue
    fname = f.split("/")[-1]
    for k, v in d.get("sectors", {}).items():
        se = v.get("sender_email", "")
        if "@gmail.com" in se and v.get("enabled", True):
            alloc.setdefault(se, []).append((fname, k, v.get("daily_limit", 0)))
    for s in d.get("gmail_senders", []):
        e = s.get("email", "")
        if "@gmail.com" in e:
            alloc.setdefault(e, []).append((fname, "gmail_sndr", s.get("limit", 0)))

print(f"{'Gmail':42s} {'Total':>5s}  Campaigns")
print("-" * 100)
for email in sorted(alloc):
    items = alloc[email]
    # Deduplicate (configs/ and ROMANIA/configs/ are often the same)
    seen = set()
    unique = []
    for name, sector, lim in items:
        key = f"{name}|{sector}"
        if key not in seen:
            seen.add(key)
            unique.append((name, sector, lim))
    total = sum(x[2] for x in unique)
    flag = " !!!" if total > 40 else " OK"
    campaigns = ", ".join(f"{n}:{s}={l}" for n, s, l in unique)
    print(f"{email:42s} {total:4d}/d{flag}  {campaigns}")
