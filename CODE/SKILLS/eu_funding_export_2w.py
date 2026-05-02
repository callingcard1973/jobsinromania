#!/usr/bin/env python3
"""Export last 2 weeks EU funding leads: verified, ASCII, phones normalized."""
import psycopg2
import csv
import re
import unicodedata
import sys
from datetime import datetime, timedelta

DB = {"dbname": "european_funds", "user": "tudor", "host": "localhost"}
CUTOFF = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
OUT_ANUNTURI = "/opt/ACTIVE/INFRA/SKILLS/eu_funding_anunturi_2w.csv"
OUT_PROIECTE = "/opt/ACTIVE/INFRA/SKILLS/eu_funding_proiecte_2w.csv"

# -- Helpers --
def to_ascii(s):
    if not s:
        return ""
    s = s.replace("\u0219", "s").replace("\u021b", "t").replace("\u0218", "S").replace("\u021a", "T")
    s = s.replace("\u0103", "a").replace("\u00e2", "a").replace("\u00ee", "i")
    s = s.replace("\u0102", "A").replace("\u00c2", "A").replace("\u00ce", "I")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

def normalize_phone(p):
    if not p:
        return ""
    p = re.sub(r"[^\d+]", "", p)
    if p.startswith("0") and len(p) == 10:
        p = "+40" + p[1:]
    elif p.startswith("40") and len(p) == 11:
        p = "+" + p
    elif len(p) == 9 and not p.startswith("+"):
        p = "+40" + p
    return p

def verify_email(e):
    if not e:
        return ""
    e = e.strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", e):
        return ""
    try:
        e.encode("ascii")
    except Exception:
        return ""
    return e

def clean_row(row, cols):
    d = dict(zip(cols, row))
    d["email"] = verify_email(d.get("email", ""))
    d["telefon"] = normalize_phone(d.get("telefon", ""))
    for k in d:
        if isinstance(d[k], str):
            d[k] = to_ascii(d[k]).strip()
    return d

# -- Export --
conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Anunturi
cur.execute("""SELECT * FROM beneficiari_privati
    WHERE scraped_at >= %s OR created_at >= %s
    ORDER BY scraped_at DESC""", (CUTOFF, CUTOFF))
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
valid = 0
with open(OUT_ANUNTURI, "w", newline="", encoding="ascii", errors="replace") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for row in rows:
        d = clean_row(row, cols)
        if d["email"]:
            w.writerow(d)
            valid += 1
print(f"Anunturi: {len(rows)} total, {valid} with verified email -> {OUT_ANUNTURI}")

# Proiecte
cur.execute("""SELECT * FROM proiecte
    WHERE scraped_at >= %s OR created_at >= %s
    ORDER BY scraped_at DESC""", (CUTOFF, CUTOFF))
cols2 = [d[0] for d in cur.description]
rows2 = cur.fetchall()
valid2 = 0
with open(OUT_PROIECTE, "w", newline="", encoding="ascii", errors="replace") as f:
    w = csv.DictWriter(f, fieldnames=cols2)
    w.writeheader()
    for row in rows2:
        d = clean_row(row, cols2)
        if d["email"]:
            w.writerow(d)
            valid2 += 1
print(f"Proiecte: {len(rows2)} total, {valid2} with verified email -> {OUT_PROIECTE}")

conn.close()
print("Done!")
