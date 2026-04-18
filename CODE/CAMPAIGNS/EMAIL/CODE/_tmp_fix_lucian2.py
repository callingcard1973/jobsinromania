import json

fname = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/romania_warehouse.json"
d = json.load(open(fname))
gs = d.get("gmail_senders", [])
d["gmail_senders"] = [s for s in gs if "lucian" not in s.get("email","").lower()]
with open(fname, "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print(f"romania_warehouse.json: removed Lucian, {len(d['gmail_senders'])} gmail senders remain")
