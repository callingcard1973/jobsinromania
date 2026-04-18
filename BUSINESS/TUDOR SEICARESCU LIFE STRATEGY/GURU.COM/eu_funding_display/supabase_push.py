#!/usr/bin/env python3
"""Push EU funding data from PostgreSQL to Supabase for web display."""
# --
import psycopg2
import requests
import json
import re
import unicodedata

DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql"}
SUPABASE_URL = "https://srgfzelqcehzidkzkjyx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNyZ2Z6ZWxxY2Voemlka3pranl4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDY1NTUyMCwiZXhwIjoyMDkwMjMxNTIwfQ.rAbu0WdET9GdnUL7o3b4wsdiQtRwx9-rLCy6Fy9fQww"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
           "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}

def to_ascii(t):
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii').strip()

def upsert(table, rows):
    """Upsert rows to Supabase in batches of 500."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    total = 0
    for i in range(0, len(rows), 500):
        batch = rows[i:i+500]
        r = requests.post(url, headers=HEADERS, json=batch)
        if r.status_code in (200, 201):
            total += len(batch)
        else:
            print(f"  Error {r.status_code}: {r.text[:200]}")
    return total

def push_anunturi():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""SELECT id, cod_smis, titlu_achizitie, beneficiar, email, telefon,
        judet, tip_contract, buget, data_publicare, data_limita, descriere,
        contractors, spec_url, url FROM beneficiari_privati
        WHERE email LIKE '%%@%%' ORDER BY id DESC""")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    for r in rows:
        for k in r:
            if isinstance(r[k], str): r[k] = to_ascii(r[k])
    print(f"Anunturi: {len(rows)} rows")
    n = upsert("anunturi", rows)
    print(f"  Pushed: {n}")

def push_proiecte():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""SELECT id, cod_smis, titlu_proiect, beneficiar, email, telefon,
        program_operational, axa, domeniu_interventie, data_contract,
        judet, contact, adresa, localitate, proceduri, url FROM proiecte
        WHERE email LIKE '%%@%%' ORDER BY id DESC""")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    for r in rows:
        for k in r:
            if isinstance(r[k], str): r[k] = to_ascii(r[k])
    print(f"Proiecte: {len(rows)} rows")
    n = upsert("proiecte", rows)
    print(f"  Pushed: {n}")

if __name__ == "__main__":
    push_anunturi()
    push_proiecte()
    print("Done!")
