#!/usr/bin/env python3
"""Clean bounce lists on ALL Brevo keys: unblock hard bounces, add to DNC."""
import requests, psycopg2, os
from dotenv import load_dotenv

load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

BREVO_KEYS = {
    "BREVO_BUILDJOBS_API_KEY": "buildjobs.eu",
    "BREVO_MIVROMANIA_API_KEY": "mivromania.info",
    "BREVO_CAREWORKERS_API_KEY": "careworkers.eu",
    "BREVO_SEICARESCU_API_KEY": "seicarescu.com",
    "BREVO_WAREHOUSEWORKERS_API_KEY": "warehouseworkers.eu",
    "BREVO_FACTORYJOBS_API_KEY": "factoryjobs.eu",
    "BREVO_INTERJOB_API_KEY": "interjob.ro",
    "BREVO_BPPLTD_API_KEY": "bppltd.co.uk",
    "BREVO_ELECTRICJOBS_API_KEY": "electricjobs.eu",
    "BREVO_NEPALEZI_API_KEY": "nepalezi.com",
    "BREVO_MEATWORKERS_API_KEY": "meatworkers.eu",
    "BREVO_EXPATSINROMANIA_API_KEY": "expatsinromania.org",
    "BREVO_HORECAWORKERS2026_EU_API_KEY": "horecaworkers2026.eu",
    "BREVO_MIVROMANIA_ONLINE_API_KEY": "mivromania.online",
    "BREVO_CIFN_API_KEY": "cifn.info",
    "BREVO_CUMPARLEGUME_API_KEY": "cumparlegume.com",
    "BREVO_AGROEVOLUTION_API_KEY": "agroevolution.com",
    "BREVO_HORECAWORKERS2026_COM_API_KEY": "horecaworkers2026.com",
}

# DNC connections
dnc_conns = [
    ("interjob_master", "INSERT INTO dnc_list(email,reason) VALUES(%s,%s) ON CONFLICT(email) DO NOTHING"),
    ("email_sender", "INSERT INTO dnc_emails(email,reason,source) VALUES(%s,%s,'brevo_cleanup') ON CONFLICT(email) DO NOTHING"),
    ("anofm", "INSERT INTO dnc(email,reason) VALUES(%s,%s) ON CONFLICT(email) DO NOTHING"),
]

total_unblocked = 0
total_dnc = 0

for env_key, domain in BREVO_KEYS.items():
    api_key = os.environ.get(env_key, "")
    if not api_key:
        continue

    headers = {"api-key": api_key}

    # Get all blocked
    blocked = []
    offset = 0
    while True:
        r = requests.get(f"https://api.brevo.com/v3/smtp/blockedContacts?limit=100&offset={offset}", headers=headers)
        if not r.ok: break
        contacts = r.json().get("contacts", [])
        if not contacts: break
        blocked.extend(contacts)
        offset += 100

    if not blocked:
        continue

    hard = [c for c in blocked if "hard bounce" in c.get("reason",{}).get("message","").lower()]
    unsub = [c for c in blocked if "unsubscribed" in c.get("reason",{}).get("message","").lower()]
    spam = [c for c in blocked if "junk" in c.get("reason",{}).get("message","").lower()]

    # Add ALL to DNC
    for db_name, sql in dnc_conns:
        try:
            conn = psycopg2.connect(dbname=db_name, user="tudor", host="localhost", password="tudor")
            cur = conn.cursor()
            for c in blocked:
                email = c.get("email","").lower()
                reason = "hard_bounce" if c in hard else "unsubscribed" if c in unsub else "spam_complaint"
                cur.execute(sql, (email, reason) if "%s,%s)" in sql else (email, reason, "brevo_cleanup"))
            conn.commit()
            conn.close()
        except:
            pass

    # Unblock hard bounces from Brevo
    unblocked = 0
    for c in hard:
        r = requests.delete(f"https://api.brevo.com/v3/smtp/blockedContacts/{c['email']}", headers=headers)
        if r.status_code in (204, 200):
            unblocked += 1

    total_unblocked += unblocked
    total_dnc += len(blocked)
    print(f"  {domain:25s} blocked:{len(blocked):>4} (hard:{len(hard)}, unsub:{len(unsub)}, spam:{len(spam)}) -> unblocked:{unblocked}")

print(f"\nTOTAL: {total_dnc} added to DNC, {total_unblocked} hard bounces unblocked from Brevo")
