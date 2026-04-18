#!/usr/bin/env python3
"""Full campaign status report: senders, sent counts, failures, bounces."""
import json, glob, os, subprocess

print("=" * 80)
print("CAMPAIGN STATUS REPORT - 8 April 2026")
print("=" * 80)

# Check all active processes
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
active = [l for l in result.stdout.split('\n') if 'send_campaign' in l or 'quick_campaign' in l]
print(f"\nActive sending processes: {len(active)}")

# TED campaigns
print("\n--- TED EU Construction (10 countries) ---")
for c in ['at','cz','de','es','fi','fr','it','nl','pl','se']:
    for sector in ['CORPORATE','PERSONAL']:
        log = f"/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/ted_{c}_{sector}.log"
        if os.path.exists(log):
            content = open(log).read()
            ok = content.count('] OK')
            fail = content.count('ABORT') + content.count('exhausted') + content.count('FAIL')
            skip = content.count('SKIP')
            print(f"  TED {c.upper()} {sector:10s}: {ok:>3} sent, {skip:>3} skip, {fail} issues")

# RO campaigns
print("\n--- Romania Campaigns ---")
for log_pattern in ["/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/logs/curierat_*.log",
                     "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/logs/ro_construction*.log"]:
    for log in sorted(glob.glob(log_pattern)):
        name = os.path.basename(log).replace('.log','')
        content = open(log).read()
        ok = content.count('] OK') + content.count('✅')
        fail = content.count('❌') + content.count('ABORT')
        print(f"  {name:30s}: {ok:>3} sent, {fail} issues")

# Refused emails (bounces from Brevo)
print("\n--- Refused/Bounced Emails ---")
import requests
from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

keys = {
    "BREVO_BUILDJOBS_API_KEY": "buildjobs.eu",
    "BREVO_MIVROMANIA_API_KEY": "mivromania.info",
    "BREVO_CAREWORKERS_API_KEY": "careworkers.eu",
    "BREVO_SEICARESCU_API_KEY": "seicarescu.com",
    "BREVO_BPPLTD_API_KEY": "bppltd.co.uk",
    "BREVO_NEPALEZI_API_KEY": "nepalezi.com",
}

for env_key, domain in keys.items():
    key = os.environ.get(env_key, "")
    if not key: continue
    h = {"api-key": key}
    r = requests.get("https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
        headers=h, params={"days": 1})
    if r.ok:
        d = r.json()
        total = d.get("requests", 0)
        hard = d.get("hardBounces", 0)
        soft = d.get("softBounces", 0)
        blocked = d.get("blocked", 0)
        delivered = d.get("delivered", 0)
        if total > 0:
            print(f"  {domain:25s} today: {total:>4} sent, {delivered:>4} delivered, {hard:>3} hard, {soft:>3} soft, {blocked:>3} blocked")

# A2 SMTP sends
print("\n--- A2 SMTP Sends ---")
for log in glob.glob("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/logs/*quick*.log"):
    content = open(log).read()
    ok = content.count('✅')
    fail = content.count('❌')
    name = os.path.basename(log).replace('.log','')
    if ok > 0 or fail > 0:
        print(f"  {name:30s}: {ok:>3} sent, {fail} failed")

# DKIM status
print("\n--- A2 DKIM/SPF Status ---")
print("  A2 Hosting default: SPF yes (shared), DKIM NO (not configured)")
print("  Brevo senders: SPF+DKIM configured per domain")
print("  Why no DKIM on A2: cPanel shared hosting, DKIM requires DNS TXT records")
print("  Fix: Add DKIM records via cPanel → Email Deliverability for each domain")
