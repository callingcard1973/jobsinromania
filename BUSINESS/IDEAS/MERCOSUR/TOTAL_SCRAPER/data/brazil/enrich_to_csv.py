#!/usr/bin/env python3
"""Enrich Brazil companies via ReceitaWS and save to CSV"""
import subprocess
import json
import time
import csv
from datetime import datetime

OUTPUT = f"brazil_enriched_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
API_URL = "https://receitaws.com.br/v1/cnpj/{}"

# Known major Brazil exporters with CNPJs
EXPORTERS = [
    ("JBS S.A.", "02916265000160"),
    ("Marfrig Global Foods", "03853896000169"),
    ("BRF S.A.", "01838723000227"),
    ("Minerva Foods", "67620377000174"),
    ("Vale S.A.", "33592510000154"),
    ("Petrobras", "33000167000101"),
    ("Suzano Papel", "16404287000155"),
    ("Klabin", "89637490000145"),
    ("Embraer", "07689002000189"),
    ("WEG S.A.", "84429695000111"),
    ("Gerdau", "33611500000119"),
    ("Usiminas", "60894730000105"),
    ("CSN", "33042730000104"),
    ("Braskem", "42150391000170"),
    ("Ambev", "07526557000100"),
]

def fetch_cnpj(cnpj):
    url = API_URL.format(cnpj)
    try:
        result = subprocess.run(
            f'curl -sL --max-time 25 "{url}"',
            shell=True, capture_output=True, text=True, timeout=30
        )
        if result.stdout and result.stdout.strip():
            data = json.loads(result.stdout)
            if data.get('status') == 'OK':
                return data
    except Exception as e:
        print(f"  Error: {e}")
    return None

print(f"Enriching {len(EXPORTERS)} Brazil exporters...")
print(f"Output: {OUTPUT}")
print("-" * 60)

rows = []
for i, (name, cnpj) in enumerate(EXPORTERS, 1):
    print(f"[{i:2d}/{len(EXPORTERS)}] {name[:40]}...", end=" ", flush=True)
    
    data = fetch_cnpj(cnpj)
    if data:
        email = data.get('email', '')
        phone = data.get('telefone', '')
        domain = email.split('@')[1] if '@' in email else ''
        
        row = {
            'name': data.get('nome', name),
            'cnpj': data.get('cnpj', cnpj),
            'email': email,
            'phone': phone,
            'domain': domain,
            'city': data.get('municipio', ''),
            'state': data.get('uf', ''),
            'status': data.get('situacao', ''),
            'activity': data.get('atividade_principal', [{}])[0].get('text', '')[:80],
            'capital': data.get('capital_social', ''),
        }
        rows.append(row)
        print(f"OK - {email or 'no email'}")
    else:
        print("FAILED")
    
    if i < len(EXPORTERS):
        time.sleep(21)  # Rate limit: 3/min

# Save CSV
if rows:
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print("-" * 60)
    print(f"Saved: {OUTPUT}")
    print(f"Companies: {len(rows)}")
    
    # Domain stats
    domains = {}
    for r in rows:
        d = r.get('domain', '')
        if d:
            domains[d] = domains.get(d, 0) + 1
    
    print("\nDOMAINS:")
    for d, c in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"  {d}: {c}")
else:
    print("No data enriched")
