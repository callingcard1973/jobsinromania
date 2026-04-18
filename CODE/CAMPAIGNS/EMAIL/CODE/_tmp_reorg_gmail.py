"""Reorganize Gmail allocations: max 40/day per account."""
import json

BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

# === NEW ALLOCATION ===
# Each Gmail -> exactly which campaigns it serves, respecting 40/day max
GMAIL_MAP = {
    # ANOFM dedicated (40/day each, Romania only)
    "manpowersearchromania@gmail.com": {"anofm": "ANOFM_GMAIL1", "limit": 40},
    "pamintstrabun@gmail.com":         {"anofm": "ANOFM_GMAIL2", "limit": 40},
    "casafaurbucuresti@gmail.com":     {"anofm": "ANOFM_GMAIL3", "limit": 40},
    "elena.manpower.dristor@gmail.com":{"anofm": "ANOFM_GMAIL4", "limit": 40},
    # Romania sector (20) + EU TED (20) = 40
    "cumparlegume@gmail.com":       {"ro": "curierat_personal.json", "ted": "fr_ted_construction.json"},
    "vegetablesbucharest@gmail.com":{"ro": "romania_agricultura.json", "ted": "pl_ted_construction.json"},
    "icralbucuresti@gmail.com":     {"ro": "romania_caen.json", "ted": "cz_ted_construction.json"},
    "carteledeapel@gmail.com":      {"ro": "romania_general.json", "ted": "it_ted_construction.json"},
    "expatsinromania@gmail.com":    {"ro": "romania_horeca.json", "ted": "se_ted_construction.json"},
    "fructexportromania@gmail.com": {"ro": "romania_delivery.json", "ted": "es_ted_construction.json"},
    "manpowerdristor@gmail.com":    {"ro": "ro_ted_construction.json", "ted": "nl_ted_construction.json"},
    "muncaanglia2020@gmail.com":    {"ted1": "at_ted_construction.json", "ted2": "de_ted_construction.json"},
    # Lucian - ANOFM only
    "lucian.bpandp@gmail.com":      {"anofm": "ANOFM_LUCIAN", "limit": 40},
}

# Allowed gmail per config file
ALLOWED = {}
for email, mapping in GMAIL_MAP.items():
    for key, val in mapping.items():
        if key in ("limit", "anofm"):
            continue
        ALLOWED.setdefault(val, []).append(email)

# ENV passwords
GMAIL_PASSWORDS = {
    "manpowersearchromania@gmail.com": "GMAIL_MANPOWERSEARCH_PASSWORD",
    "pamintstrabun@gmail.com": "GMAIL_PAMINTSTRABUN_PASSWORD",
    "casafaurbucuresti@gmail.com": "GMAIL_CASAFAUR_PASSWORD",
    "elena.manpower.dristor@gmail.com": "GMAIL_ELENA_PASSWORD",
    "cumparlegume@gmail.com": "GMAIL_CUMPARLEGUME_PASSWORD",
    "vegetablesbucharest@gmail.com": "GMAIL_VEGETABLES_PASSWORD",
    "icralbucuresti@gmail.com": "GMAIL_ICRALBUCURESTI_PASSWORD",
    "carteledeapel@gmail.com": "GMAIL_CARTELEDEAPEL_PASSWORD",
    "expatsinromania@gmail.com": "GMAIL_EXPATS_PASSWORD",
    "fructexportromania@gmail.com": "GMAIL_FRUCTEXPORT_PASSWORD",
    "manpowerdristor@gmail.com": "GMAIL_MANPOWERDRISTOR_APP_PASSWORD",
    "muncaanglia2020@gmail.com": "GMAIL_MUNCAANGLIA2020_PASSWORD",
    "lucian.bpandp@gmail.com": "GMAIL_LUCIAN_APP_PASSWORD",
}

import glob
configs = glob.glob(f"{BASE}/configs/*.json")
configs += glob.glob(f"{BASE}/ROMANIA/configs/*.json")

changes = []
for f in sorted(configs):
    if "state" in f or "archived" in f:
        continue
    fname = f.split("/")[-1]
    try:
        d = json.load(open(f))
    except:
        continue

    modified = False

    # Fix PERSONAL sectors: set correct gmail sender + limit=20
    for k, v in d.get("sectors", {}).items():
        se = v.get("sender_email", "")
        if "@gmail.com" not in se:
            continue
        allowed_emails = ALLOWED.get(fname, [])
        if se not in allowed_emails and allowed_emails:
            new_email = allowed_emails[0]
            v["sender_email"] = new_email
            v["daily_limit"] = 20
            changes.append(f"  {fname} sector {k}: {se} -> {new_email} (20/day)")
            modified = True
        elif se in allowed_emails:
            if v.get("daily_limit", 0) != 20:
                v["daily_limit"] = 20
                changes.append(f"  {fname} sector {k}: limit -> 20/day")
                modified = True

    # Fix gmail_senders: only keep allowed, set limit=20
    gs = d.get("gmail_senders", [])
    if gs:
        allowed_emails = ALLOWED.get(fname, [])
        new_gs = []
        for s in gs:
            e = s.get("email", "")
            if e in allowed_emails:
                s["limit"] = 20
                new_gs.append(s)
            elif "lucian" in e:
                # Keep Lucian in his allowed configs
                if fname == "romania_warehouse.json":
                    s["limit"] = 40
                    new_gs.append(s)

        # Add missing allowed gmails
        existing = {s["email"] for s in new_gs}
        for ae in allowed_emails:
            if ae not in existing:
                name_part = ae.split("@")[0].replace(".", " ").title()
                new_gs.append({
                    "email": ae,
                    "env_pass": GMAIL_PASSWORDS.get(ae, ""),
                    "name": name_part,
                    "limit": 20
                })

        if len(new_gs) != len(gs) or any(s.get("limit") != gs[i].get("limit") if i < len(gs) else True for i, s in enumerate(new_gs)):
            removed = [s["email"] for s in gs if s["email"] not in {x["email"] for x in new_gs}]
            if removed:
                changes.append(f"  {fname} gmail_senders: removed {removed}")
            d["gmail_senders"] = new_gs
            modified = True

    # Special: ANOFM gmail sectors - keep at 40
    for k, v in d.get("sectors", {}).items():
        if "GMAIL" in k and "anofm" in fname.lower():
            v["daily_limit"] = 40

    # Special: norway/denmark/bulgaria - remove ALL gmail_senders (Brevo only)
    if fname in ("norway.json", "denmark.json", "bulgaria.json"):
        if d.get("gmail_senders"):
            changes.append(f"  {fname}: removed ALL {len(d['gmail_senders'])} gmail_senders (Brevo only)")
            d["gmail_senders"] = []
            modified = True

    # Special: fi_ted_construction - no dedicated gmail, Brevo only
    if fname == "fi_ted_construction.json":
        if d.get("gmail_senders"):
            changes.append(f"  {fname}: removed gmail_senders (Brevo only)")
            d["gmail_senders"] = []
            modified = True
        for k, v in d.get("sectors", {}).items():
            if "@gmail.com" in v.get("sender_email", ""):
                v["enabled"] = False
                changes.append(f"  {fname}: disabled PERSONAL gmail sector")
                modified = True

    if modified:
        with open(f, "w") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)

print("=== CHANGES MADE ===")
for c in changes:
    print(c)
print(f"\nTotal: {len(changes)} changes")
