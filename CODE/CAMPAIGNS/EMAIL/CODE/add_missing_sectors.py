#!/usr/bin/env python3
"""Add missing CORPORATE (Brevo) sectors to TED configs and PERSONAL (Gmail) to RO configs."""
import json, os

UNIFIED = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs"
ROMANIA = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs"

# TED configs: add Brevo CORPORATE sector (buildjobs.eu shared, 30/day each = safe)
ted_configs = [
    "at_ted_construction.json",
    "cz_ted_construction.json",
    "de_ted_construction.json",
    "es_ted_construction.json",
    "fi_ted_construction.json",
    "fr_ted_construction.json",
    "it_ted_construction.json",
    "nl_ted_construction.json",
    "pl_ted_construction.json",
    "se_ted_construction.json",
]

for name in ted_configs:
    f = os.path.join(UNIFIED, name)
    if not os.path.exists(f):
        continue
    cfg = json.load(open(f))
    # Rename existing ALL to PERSONAL
    if "ALL" in cfg["sectors"]:
        cfg["sectors"]["PERSONAL"] = cfg["sectors"].pop("ALL")
        cfg["sectors"]["PERSONAL"]["filter_type"] = "personal"
    # Add CORPORATE
    cfg["sectors"]["CORPORATE"] = {
        "sender_key": "BREVO_BUILDJOBS_API_KEY",
        "sender_email": "office@buildjobs.eu",
        "sender_name": "Tudor - InterJob Solutions",
        "reply_to": "office@buildjobs.eu",
        "daily_limit": 30,
        "delay_min": 360,
        "delay_max": 600,
        "enabled": True,
        "template_prefix": "template",
        "filter_type": "corporate",
        "business_hours": {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18},
    }
    json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
    gmail = cfg["sectors"]["PERSONAL"]["sender_email"]
    print(f"  TED {name:35s} CORPORATE: buildjobs.eu 30/day + PERSONAL: {gmail}")

# RO configs: add Gmail PERSONAL sector
ro_personal = {
    "romania_agricultura.json": ("fruitnature4@gmail.com", "GMAIL_FRUITNATURE"),
    "romania_delivery.json": ("manpowerdristor@gmail.com", "GMAIL_MANPOWERDRISTOR"),
    "romania_horeca.json": ("vegetablesbucharest@gmail.com", "GMAIL_VEGETABLES"),
}

for name, (gmail, key) in ro_personal.items():
    f = os.path.join(ROMANIA, name)
    if not os.path.exists(f):
        continue
    cfg = json.load(open(f))
    cfg["sectors"]["PERSONAL"] = {
        "sender_key": key,
        "sender_email": gmail,
        "sender_name": "Tudor - InterJob Solutions",
        "reply_to": gmail,
        "daily_limit": 30,
        "delay_min": 360,
        "delay_max": 600,
        "enabled": True,
        "template_prefix": cfg["sectors"].get("CORPORATE", {}).get("template_prefix", "template"),
        "filter_type": "personal",
        "sender_type": "gmail_only",
        "business_hours": {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18},
    }
    json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
    brevo = cfg["sectors"]["CORPORATE"]["sender_email"]
    print(f"  RO  {name:35s} CORPORATE: {brevo} + PERSONAL: {gmail} 30/day")

# Also RO confectii and lemn - add PERSONAL
for name, (gmail, key) in [
    ("romania_caen.json", ("cumparlegume@gmail.com", "GMAIL_CUMPARLEGUME")),
    ("romania_general.json", ("fructexportromania@gmail.com", "GMAIL_FRUCTEXPORT")),
]:
    f = os.path.join(ROMANIA, name)
    if not os.path.exists(f):
        continue
    cfg = json.load(open(f))
    if "PERSONAL" not in cfg["sectors"]:
        cfg["sectors"]["PERSONAL"] = {
            "sender_key": key,
            "sender_email": gmail,
            "sender_name": "Lucian - BP&P Partners",
            "reply_to": gmail,
            "daily_limit": 30,
            "delay_min": 360,
            "delay_max": 600,
            "enabled": True,
            "template_prefix": cfg["sectors"].get("CORPORATE", {}).get("template_prefix", "template"),
            "filter_type": "personal",
            "sender_type": "gmail_only",
            "business_hours": {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18},
        }
        json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
        brevo = cfg["sectors"]["CORPORATE"]["sender_email"]
        print(f"  RO  {name:35s} CORPORATE: {brevo} + PERSONAL: {gmail} 30/day")
