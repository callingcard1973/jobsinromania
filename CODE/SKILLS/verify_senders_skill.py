#!/usr/bin/env python3
"""
Full Sender Audit — Cross-references A2 domains, Brevo accounts, Gmail senders.
Skill: /opt/ACTIVE/INFRA/SKILLS/verify_senders_skill.py
"""
import os, json, ssl, smtplib, requests
from dotenv import load_dotenv

load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
load_dotenv("/opt/ACTIVE/SCRAPERS/EUROPE/.env")

BREVO_API = "https://api.brevo.com/v3"
CPANEL_USER = "loaiidil"
CPANEL_SERVER = "nl1-cl8-ats1.a2hosting.com"
CPANEL_TOKEN = os.getenv("A2_CPANEL_API_TOKEN", "")

# ── 1. Get all domains from A2 Hosting ──
print("=" * 110)
print("  STEP 1: ALL DOMAINS ON A2 HOSTING")
print("=" * 110)

a2_domains = set()
try:
    url = f"https://{CPANEL_SERVER}:2083/execute/DomainInfo/list_domains"
    r = requests.get(url, headers={"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"}, timeout=15, verify=True)
    if r.status_code == 200:
        data = r.json().get("data", {})
        main_domain = data.get("main_domain", "")
        if main_domain:
            a2_domains.add(main_domain)
        for d in data.get("addon_domains", []):
            a2_domains.add(d)
        for d in data.get("sub_domains", []):
            # sub_domains include addon domain subdomains, extract actual domain
            pass
        for d in data.get("parked_domains", []):
            a2_domains.add(d)
except Exception as e:
    print(f"  ERROR fetching A2 domains: {e}")

# Filter to only .eu, .com, .org, .info, .online, .ro domains (skip subdomains)
real_domains = sorted([d for d in a2_domains if "." in d and not d.startswith("cpcalendars") and not d.startswith("cpcontacts")])
print(f"  Found {len(real_domains)} domains on A2:")
for d in real_domains:
    print(f"    {d}")

# ── 2. Get all Brevo accounts and their senders ──
print()
print("=" * 110)
print("  STEP 2: ALL BREVO ACCOUNTS + SENDERS")
print("=" * 110)

brevo_keys = {}
env_path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env"
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        if "BREVO_" in line and "API_KEY" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"')
            if v and len(v) > 20:
                brevo_keys[k] = v

brevo_senders = {}  # domain -> {key_name, senders[], stats}
brevo_all_sender_emails = set()

for key_name, api_key in sorted(brevo_keys.items()):
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    try:
        r = requests.get(f"{BREVO_API}/account", headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"  FAIL  {key_name:45s} | HTTP {r.status_code}")
            continue

        acct = r.json()
        acct_email = acct.get("email", "?")

        # Get senders
        r2 = requests.get(f"{BREVO_API}/senders", headers=headers, timeout=10)
        senders = []
        if r2.status_code == 200:
            senders = r2.json().get("senders", [])

        active = [s for s in senders if s.get("active")]
        sender_emails = [s["email"] for s in active]
        brevo_all_sender_emails.update(sender_emails)

        # Get stats
        r3 = requests.get(f"{BREVO_API}/smtp/statistics/aggregatedReport",
                          headers=headers, params={"days": 7}, timeout=10)
        stats = r3.json() if r3.status_code == 200 else {}
        total = stats.get("requests", 0)
        bounces = stats.get("hardBounces", 0) + stats.get("softBounces", 0)
        bounce_pct = (bounces / total * 100) if total > 0 else 0

        sender_str = ", ".join(sender_emails[:4])
        if len(sender_emails) > 4:
            sender_str += f" +{len(sender_emails)-4}"

        status = "OK"
        if bounce_pct > 10:
            status = "WARN"
        print(f"  {status:4s}  {key_name:45s} | acct: {acct_email:30s} | senders: {sender_str}")
        print(f"        {'':45s} | 7d: {total} sent, {bounce_pct:.1f}% bounce")

        # Map domains
        for se in sender_emails:
            domain = se.split("@")[-1]
            brevo_senders[domain] = {"key_name": key_name, "sender": se, "bounce_pct": bounce_pct}

    except Exception as e:
        print(f"  ERR   {key_name:45s} | {str(e)[:60]}")

# ── 3. Cross-reference: A2 domains vs Brevo senders ──
print()
print("=" * 110)
print("  STEP 3: A2 DOMAINS vs BREVO — CROSS-REFERENCE")
print("=" * 110)

for domain in real_domains:
    if domain in brevo_senders:
        info = brevo_senders[domain]
        bounce_warn = " *** HIGH BOUNCE" if info["bounce_pct"] > 10 else ""
        print(f"  OK    {domain:35s} | Brevo: {info['sender']:35s} | {info['key_name']}{bounce_warn}")
    else:
        print(f"  MISS  {domain:35s} | NO BREVO ACCOUNT")

# Reverse: Brevo senders not on A2
print()
brevo_domains = set(brevo_senders.keys())
extra_brevo = brevo_domains - set(real_domains)
if extra_brevo:
    print("  Brevo senders with domains NOT on A2:")
    for d in sorted(extra_brevo):
        info = brevo_senders[d]
        print(f"    {d:35s} | {info['sender']:35s} | {info['key_name']}")

# ── 4. Gmail senders ──
print()
print("=" * 110)
print("  STEP 4: GMAIL SENDERS VERIFICATION")
print("=" * 110)

gmail_accounts = [
    ("manpower.dristor@gmail.com", "GMAIL_APP_PASSWORD"),
    ("manpowerdristor@gmail.com", "GMAIL_MANPOWERDRISTOR_APP_PASSWORD"),
    ("elena.manpower.dristor@gmail.com", "GMAIL_ELENA_PASSWORD"),
    ("pamintstrabun@gmail.com", "GMAIL_PAMINTSTRABUN_PASSWORD"),
    ("manpowersearchromania@gmail.com", "GMAIL_MANPOWERSEARCH_PASSWORD"),
    ("expatsinromania@gmail.com", "GMAIL_EXPATS_PASSWORD"),
    ("lucian.bpandp@gmail.com", "GMAIL_LUCIAN_APP_PASSWORD"),
    ("fructexportromania@gmail.com", "GMAIL_FRUCTEXPORT_PASSWORD"),
    ("casafaurbucuresti@gmail.com", "GMAIL_CASAFAUR_PASSWORD"),
    ("cumparlegume@gmail.com", "GMAIL_CUMPARLEGUME_PASSWORD"),
    ("vegetablesbucharest@gmail.com", "GMAIL_VEGETABLESBUCHAREST_PASSWORD"),
]

gmail_ok = 0
for email, env_var in gmail_accounts:
    password = os.getenv(env_var, "").strip().strip('"')
    if not password or password == "NEEDS_APP_PASSWORD":
        print(f"  SKIP  {email:42s} | {env_var} NOT SET")
        continue
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=10) as server:
            server.login(email, password)
        print(f"  OK    {email:42s} | login success")
        gmail_ok += 1
    except smtplib.SMTPAuthenticationError:
        print(f"  FAIL  {email:42s} | AUTH ERROR")
    except Exception as e:
        print(f"  FAIL  {email:42s} | {str(e)[:60]}")

print(f"\n  Gmail: {gmail_ok}/{len(gmail_accounts)} working")

# ── Summary ──
print()
print("=" * 110)
print("  SUMMARY")
print("=" * 110)
print(f"  A2 domains:        {len(real_domains)}")
print(f"  Brevo accounts:    {len(brevo_keys)}")
print(f"  Brevo senders:     {len(brevo_all_sender_emails)} active")
print(f"  Domains with Brevo:{len(brevo_domains & set(real_domains))}/{len(real_domains)}")
print(f"  Domains NO Brevo:  {len(set(real_domains) - brevo_domains)}")
print(f"  Gmail senders:     {gmail_ok}/{len(gmail_accounts)}")
print("=" * 110)
