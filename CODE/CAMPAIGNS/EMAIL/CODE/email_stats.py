#!/usr/bin/env python3
"""Breakdown corporate/gmail/yahoo/other for all campaigns."""
import psycopg2, csv, glob

def classify(e):
    d = e.lower().split("@")[1] if "@" in e else ""
    if d == "gmail.com": return "gmail"
    if d.startswith("yahoo."): return "yahoo"
    if d in ("hotmail.com","hotmail.ro","hotmail.fr","outlook.com","outlook.de","live.com","live.ro"): return "outlook"
    if d in ("aol.com","ymail.com","mail.ru","protonmail.com","web.de","gmx.de","gmx.net",
        "t-online.de","orange.fr","free.fr","laposte.net","wp.pl","o2.pl","seznam.cz",
        "email.cz","mail.com","zoho.com","icloud.com"): return "other_personal"
    return "corporate"

def show(name, emails):
    cats = {}
    for e in emails:
        cats[classify(e)] = cats.get(classify(e), 0) + 1
    total = len(emails)
    if not total: return
    print(f"\n{name} ({total:,})")
    for c in ["corporate","gmail","yahoo","outlook","other_personal"]:
        n = cats.get(c, 0)
        if n: print(f"  {c:16s} {n:>6,}  {n/total*100:5.1f}%")

# ANOFM remaining
conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
cur = conn.cursor()
cur.execute("SELECT DISTINCT LOWER(email) FROM jobs WHERE email IS NOT NULL AND email != '' AND (campaign_status IS NULL OR campaign_status = '')")
anofm = {r[0] for r in cur.fetchall()}
conn.close()
show("ANOFM (remaining)", anofm)

# Sector CSVs
base = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA"
all_emails = set(anofm)
for f in sorted(glob.glob(f"{base}/ro_*.csv")):
    with open(f) as fh:
        emails = {r["email"].lower().strip() for r in csv.DictReader(fh) if r.get("email")}
    show(f.split("/")[-1].replace(".csv",""), emails)
    all_emails.update(emails)

show("GRAND TOTAL", all_emails)
