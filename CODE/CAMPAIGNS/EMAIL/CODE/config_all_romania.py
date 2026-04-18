#!/usr/bin/env python3
"""Configure all Romania dormant campaigns with deduped CSVs and senders."""
import json, os

BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA"

CAMPAIGNS = {
    "romania_agricultura.json": {
        "csv": f"{BASE}/ro_agricultura_6558.csv",
        "campaign_name": "RO_AGRICULTURA",
        "template_dir": f"{BASE}/templates/agricultura/",
        "sectors": {
            "CORPORATE": {
                "sender_key": "BREVO_CIFN_API_KEY",
                "sender_email": "office@cifn.info",
                "sender_name": "Lucian - BP&P Partners",
                "reply_to": "manpower.dristor@gmail.com",
                "template_prefix": "lucian_template",
                "daily_limit": 290,
                "filter_type": "corporate",
            },
        }
    },
    "romania_caen.json": {
        "csv": f"{BASE}/ro_confectii_667.csv",
        "campaign_name": "RO_CONFECTII",
        "template_dir": f"{BASE}/templates/confectii/",
        "sectors": {
            "CORPORATE": {
                "sender_key": "BREVO_CUMPARLEGUME_API_KEY",
                "sender_email": "cumparlegume@cumparlegume.com",
                "sender_name": "Lucian - BP&P Partners",
                "reply_to": "manpower.dristor@gmail.com",
                "template_prefix": "lucian_template",
                "daily_limit": 290,
                "filter_type": "corporate",
            },
        }
    },
    "romania_general.json": {
        "csv": f"{BASE}/ro_lemn_468.csv",
        "campaign_name": "RO_LEMN",
        "template_dir": f"{BASE}/templates/lemn/",
        "sectors": {
            "CORPORATE": {
                "sender_key": "BREVO_AGROEVOLUTION_API_KEY",
                "sender_email": "office@agroevolution.com",
                "sender_name": "Lucian - BP&P Partners",
                "reply_to": "manpower.dristor@gmail.com",
                "template_prefix": "lucian_template",
                "daily_limit": 290,
                "filter_type": "corporate",
            },
        }
    },
    "romania_delivery.json": {
        "csv": f"{BASE}/ro_curierat_2751.csv",
        "campaign_name": "RO_CURIERAT",
        "template_dir": f"{BASE}/templates/curierat/",
        "sectors": {
            "CORPORATE": {
                "sender_key": "BREVO_MIVROMANIA_API_KEY",
                "sender_email": "office@mivromania.info",
                "sender_name": "Tudor - InterJob Solutions",
                "reply_to": "manpower.dristor@gmail.com",
                "template_prefix": "tudor_template",
                "daily_limit": 290,
                "filter_type": "corporate",
            },
        }
    },
    "romania_horeca.json": {
        "csv": f"{BASE}/ro_horeca_9603.csv",
        "campaign_name": "RO_HORECA",
        "template_dir": f"{BASE}/templates/romania_horeca/",
        "sectors": {
            "CORPORATE": {
                "sender_key": "BREVO_CAREWORKERS_API_KEY",
                "sender_email": "office@careworkers.eu",
                "sender_name": "Tudor - InterJob Solutions",
                "reply_to": "manpower.dristor@gmail.com",
                "template_prefix": "template",
                "daily_limit": 290,
                "filter_type": "corporate",
            },
        }
    },
}

for fname, camp in CAMPAIGNS.items():
    fpath = f"{BASE}/configs/{fname}"
    cfg = json.load(open(fpath))

    cfg["csv_file"] = camp["csv"]
    cfg["campaign_name"] = camp["campaign_name"]
    cfg["templates_dir"] = camp["template_dir"]

    cfg["sectors"] = {}
    for sname, scfg in camp["sectors"].items():
        cfg["sectors"][sname] = {
            "sender_key": scfg["sender_key"],
            "sender_email": scfg["sender_email"],
            "sender_name": scfg["sender_name"],
            "reply_to": scfg["reply_to"],
            "daily_limit": scfg["daily_limit"],
            "delay_min": 360,
            "delay_max": 600,
            "enabled": True,
            "template_prefix": scfg["template_prefix"],
            "filter_type": scfg.get("filter_type", ""),
            "business_hours": {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18},
        }

    json.dump(cfg, open(fpath, "w"), indent=2, ensure_ascii=False)
    total = sum(s["daily_limit"] for s in cfg["sectors"].values())
    print(f"  {camp['campaign_name']:20s} | {cfg['sectors'][list(cfg['sectors'].keys())[0]]['sender_email']:30s} | {total}/day | {camp['csv'].split('/')[-1]}")
