#!/usr/bin/env python3
"""Gentle enrichment - 45s between requests to avoid rate limits"""
import subprocess
import json
import time
import csv
from datetime import datetime

OUTPUT = "/opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/data/brazil/brazil_exporters_full.csv"
DELAY = 45  # Gentle: 1.3 requests per minute

# All known exporters with CNPJs
EXPORTERS = [
    ("JBS S.A.", "02916265000160"),
    ("BRF S.A.", "01838723000227"),
    ("Marfrig Global Foods", "03853896000169"),
    ("Minerva Foods", "67620377000174"),
    ("Vale S.A.", "33592510000154"),
    ("Petrobras", "33000167000101"),
    ("Suzano", "16404287000155"),
    ("Klabin", "89637490000145"),
    ("Embraer", "07689002000189"),
    ("WEG", "84429695000111"),
    ("Gerdau", "33611500000119"),
    ("Usiminas", "60894730000105"),
    ("CSN", "33042730000104"),
    ("Braskem", "42150391000170"),
    ("Ambev", "07526557000100"),
    ("Cargill Brasil", "60498706000114"),
    ("Bunge Brasil", "84046101000357"),
    ("ADM Brasil", "02003402000140"),
    ("Louis Dreyfus", "47067525000160"),
    ("Amaggi", "77294254000300"),
    ("Citrosuco", "55555792000107"),
    ("Cutrale", "55115507000120"),
    ("Raizen", "08070508001570"),
    ("Copersucar", "11742455000107"),
    ("Tereos", "01685326000137"),
    ("Cooxupe", "20696418000181"),
    ("Aurora Alimentos", "83310441000117"),
    ("Sadia", "01838723000308"),
    ("Seara", "02916265004207"),
    ("3tentos", "94813102000108"),
    ("Jalles Machado", "01536594000166"),
    ("Cocamar", "79114450000163"),
    ("Coamo", "75904383000128"),
    ("Caramuru", "00080671000111"),
    ("Fibria", "60643228000121"),
    ("Eldorado Brasil", "07401436000164"),
    ("CMPC", "92823068000163"),
    ("Camil Alimentos", "64904295000103"),
    ("M Dias Branco", "07206816000115"),
    ("SLC Agricola", "89096457000155"),
]

def fetch(cnpj):
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        r = subprocess.run(f'curl -sL --max-time 30 "{url}"',
                          shell=True, capture_output=True, text=True, timeout=35)
        if r.stdout and "Too many" not in r.stdout:
            d = json.loads(r.stdout)
            if d.get('status') == 'OK':
                return d
    except:
        pass
    return None

def ascii(t):
    if not t: return ""
    import unicodedata
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii')

print(f"Gentle enrichment: {len(EXPORTERS)} companies, {DELAY}s delay")
print(f"Estimated time: {len(EXPORTERS) * DELAY / 60:.0f} minutes")
print("-" * 50)

rows = []
for i, (name, cnpj) in enumerate(EXPORTERS, 1):
    print(f"[{i:2d}/{len(EXPORTERS)}] {name[:35]}...", end=" ", flush=True)

    d = fetch(cnpj)
    if d:
        email = d.get('email', '')
        phone = d.get('telefone', '')
        rows.append({
            'name': ascii(d.get('nome', name)),
            'cnpj': d.get('cnpj', ''),
            'email': email.lower() if email else '',
            'phone': phone,
            'domain': email.split('@')[1] if '@' in email else '',
            'city': ascii(d.get('municipio', '')),
            'state': d.get('uf', ''),
            'activity': ascii(d.get('atividade_principal', [{}])[0].get('text', ''))[:60],
            'capital': d.get('capital_social', ''),
        })
        print(f"OK - {email or 'no email'}")
    else:
        print("FAIL")

    if i < len(EXPORTERS):
        time.sleep(DELAY)

# Save
with open(OUTPUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

print("-" * 50)
print(f"Saved: {OUTPUT}")
print(f"Total: {len(rows)}, With email: {sum(1 for r in rows if r['email'])}")
print("\nDomains:")
domains = {}
for r in rows:
    if r['domain']:
        domains[r['domain']] = domains.get(r['domain'], 0) + 1
for d in sorted(domains, key=lambda x: -domains[x]):
    print(f"  {d}")
