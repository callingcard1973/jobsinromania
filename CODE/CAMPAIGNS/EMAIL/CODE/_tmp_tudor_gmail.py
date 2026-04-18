import json, glob

configs = glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*.json")
configs += glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/*.json")

tudor_gmails = [
    "manpowersearchromania@gmail.com", "pamintstrabun@gmail.com",
    "casafaurbucuresti@gmail.com", "elena.manpower.dristor@gmail.com",
    "cumparlegume@gmail.com", "fructexportromania@gmail.com",
    "carteledeapel@gmail.com", "vegetablesbucharest@gmail.com",
    "expatsinromania@gmail.com", "icralbucuresti@gmail.com",
    "manpowerdristor@gmail.com", "manpower.dristor@gmail.com",
    "fruitnature4@gmail.com", "muncaanglia2020@gmail.com",
]

seen = set()
for f in sorted(configs):
    if "state" in f or "archived" in f:
        continue
    try:
        d = json.load(open(f))
        name = f.split("/")[-1]
        # sectors
        for k, v in d.get("sectors", {}).items():
            se = v.get("sender_email", "")
            if se in tudor_gmails or any(g in se for g in tudor_gmails):
                key = f"{name}|{k}"
                if key not in seen:
                    seen.add(key)
                    print(f"{name:35s} {k:25s} | {se:40s} | limit={v.get('daily_limit','?')} enabled={v.get('enabled','?')}")
        # gmail_senders
        for s in d.get("gmail_senders", []):
            e = s.get("email", "")
            if e in tudor_gmails and "lucian" not in e:
                key = f"{name}|{e}"
                if key not in seen:
                    seen.add(key)
                    print(f"{name:35s} {'gmail_sender':25s} | {e:40s} | limit={s.get('limit', s.get('daily_limit','?'))}")
    except:
        pass
