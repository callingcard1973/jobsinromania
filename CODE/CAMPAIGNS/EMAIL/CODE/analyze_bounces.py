#!/usr/bin/env python3
import requests, os
from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

keys = [
    ("BREVO_MIVROMANIA_API_KEY", "mivromania.info"),
    ("BREVO_BUILDJOBS_API_KEY", "buildjobs.eu"),
    ("BREVO_CAREWORKERS_API_KEY", "careworkers.eu"),
    ("BREVO_SEICARESCU_API_KEY", "seicarescu.com"),
    ("BREVO_BPPLTD_API_KEY", "bppltd.co.uk"),
]

for key_name, domain in keys:
    key = os.environ.get(key_name, "")
    if not key: continue
    h = {"api-key": key}

    r = requests.get("https://api.brevo.com/v3/smtp/statistics/aggregatedReport", headers=h)
    d = r.json()
    total = d.get("requests", 1)
    hard = d.get("hardBounces", 0)
    soft = d.get("softBounces", 0)
    rate = (hard + soft) / max(total, 1) * 100

    r2 = requests.get("https://api.brevo.com/v3/smtp/blockedContacts?limit=1", headers=h)
    blocked = r2.json().get("count", "?")

    status = "PASS" if rate < 10 else "FAIL"
    print(f"{domain:25s} sent:{total:>5} hard:{hard:>4} soft:{soft:>4} rate:{rate:>5.1f}% blocked:{blocked:>3} {status}")

    # Show recent hard bounce reasons
    r3 = requests.get("https://api.brevo.com/v3/smtp/statistics/events?limit=5&event=hardBounces", headers=h)
    events = r3.json().get("events", [])
    for e in events[:3]:
        em = e.get("email", "?")
        reason = e.get("reason", "?")
        print(f"  -> {em}: {reason[:80]}")
