import json, glob

configs = glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*.json")
configs += glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/*.json")

for f in sorted(configs):
    if "state" in f or "archived" in f:
        continue
    try:
        d = json.load(open(f))
        name = f.split("/")[-1]
        # Check sectors
        for k, v in d.get("sectors", {}).items():
            if "lucian" in str(v).lower() or "lucian" in k.lower():
                lim = v.get("daily_limit", "?")
                en = v.get("enabled", "?")
                se = v.get("sender_email", "?")
                print(f"{name:35s} sector: {k:25s} limit={lim} enabled={en} sender={se}")
        # Check gmail_senders
        for k, v in d.get("gmail_senders", {}).items():
            if "lucian" in str(v).lower() or "lucian" in k.lower():
                print(f"{name:35s} gmail:  {k:25s} email={v.get('email','?')} limit={v.get('daily_limit','?')}")
        # Check senders list
        for s in d.get("senders", []):
            if "lucian" in str(s).lower():
                print(f"{name:35s} sender: {s.get('email','?'):25s} limit={s.get('daily_limit','?')}")
    except:
        pass
