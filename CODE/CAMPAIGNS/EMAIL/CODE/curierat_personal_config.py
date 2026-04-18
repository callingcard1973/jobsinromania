import json

cfg = {
    "db": {"host": "localhost", "dbname": "anofm", "user": "tudor", "password": "tudor"},
    "env_file": "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env",
    "campaign_name": "RO_CURIERAT_PERSONAL",
    "templates_dir": "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/templates/curierat/",
    "tables": {
        "contacts": "curierat_personal",
        "send_log": "send_log",
        "dnc": "dnc",
        "responses": "responses",
        "col_email": "email",
        "col_name": "company_name",
        "col_company": "company_name",
        "col_city": "city",
        "col_employees": "id",
        "col_sector": "sector",
        "col_sector_name": "sector",
        "col_org_number": "email",
        "col_tier": "sector",
        "col_caen": "sector",
        "col_campaign_status": "campaign_status",
        "col_last_contacted": "last_contacted",
    },
    "sectors": {
        "GMAIL": {
            "filter": "1=1",
            "sender_type": "gmail_only",
            "sender_key": "GMAIL_MANPOWERSEARCH",
            "sender_email": "manpowersearchromania@gmail.com",
            "sender_name": "Tudor - InterJob Solutions",
            "reply_to": "manpowersearchromania@gmail.com",
            "daily_limit": 30,
            "delay_min": 360,
            "delay_max": 600,
            "enabled": True,
            "template_prefix": "tudor_template",
            "filter_type": "personal",
            "business_hours": {"enabled": True, "days": [0,1,2,3,4], "start": 8, "end": 18},
        }
    }
}

f = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/curierat_personal.json"
json.dump(cfg, open(f, "w"), indent=2, ensure_ascii=False)
print(f"Created {f}")
print(f"  DB: anofm.curierat_personal (1,622 emails)")
print(f"  Sender: manpowersearchromania@gmail.com 30/day")
