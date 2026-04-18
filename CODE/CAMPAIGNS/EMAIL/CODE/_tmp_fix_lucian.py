import json

for fname in ["/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/norway.json",
              "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/denmark.json"]:
    d = json.load(open(fname))
    gs = d.get("gmail_senders", [])
    before = len(gs)
    gs_new = [s for s in gs if "lucian" not in s.get("email","").lower()]
    d["gmail_senders"] = gs_new
    with open(fname, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    removed = before - len(gs_new)
    print(f"{fname.split('/')[-1]}: removed {removed} Lucian sender(s), {len(gs_new)} gmail senders remain")
