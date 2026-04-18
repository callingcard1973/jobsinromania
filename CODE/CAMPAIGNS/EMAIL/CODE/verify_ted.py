import json, glob, os

for f in sorted(glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*_ted_construction.json")):
    name = os.path.basename(f).replace("_ted_construction.json","").upper()
    cfg = json.load(open(f))
    sectors = cfg.get("sectors", {})
    corp = sectors.get("CORPORATE", {})
    pers = sectors.get("PERSONAL", {}) or sectors.get("ALL", {})

    # Check template exists
    tpl_dir = cfg.get("templates_dir", "")
    tpl_prefix = corp.get("template_prefix", "template")
    tpl_file = os.path.join(tpl_dir, f"{tpl_prefix}1.txt")
    tpl_ok = os.path.exists(tpl_file)

    # Check DB/CSV
    db = cfg.get("db", {}).get("dbname", "")
    tbl = cfg.get("tables", {}).get("contacts", "")

    corp_ok = corp.get("sender_email") and corp.get("sender_key") and corp.get("enabled")
    pers_ok = pers.get("sender_email") and pers.get("enabled")
    bh = corp.get("business_hours", {}).get("enabled", False)

    status = "OK" if (corp_ok and pers_ok and tpl_ok and bh) else "ISSUE"
    issues = []
    if not corp_ok: issues.append("no CORPORATE")
    if not pers_ok: issues.append("no PERSONAL")
    if not tpl_ok: issues.append(f"template missing: {tpl_file}")
    if not bh: issues.append("no business_hours")

    print(f"{name:3s} | CORP: {corp.get('sender_email','?'):25s} {corp.get('daily_limit',0):>3}/day | PERS: {pers.get('sender_email','?'):35s} {pers.get('daily_limit',0):>3}/day | bh={bh} | {status} {' '.join(issues)}")
