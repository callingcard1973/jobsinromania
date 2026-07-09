#!/usr/bin/env python3
"""Enrich Brazil companies via ReceitaWS API (using Tor)"""
import subprocess
import json
import time
import random
import psycopg2
from datetime import datetime

# ReceitaWS API (free, works via Tor)
API_URL = "https://receitaws.com.br/v1/cnpj/{cnpj}"

def fetch_cnpj(cnpj: str) -> dict:
    """Fetch company data from ReceitaWS via Tor"""
    cnpj_clean = ''.join(c for c in cnpj if c.isdigit())[:14]
    if len(cnpj_clean) != 14:
        return None

    url = API_URL.format(cnpj=cnpj_clean)
    cmd = f'torsocks curl -sL --max-time 30 "{url}"'

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=35)
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            if data.get('status') == 'OK':
                return data
    except:
        pass
    return None

def main():
    conn = psycopg2.connect(dbname='interjob_master', user='tudor')
    cur = conn.cursor()

    # Get Brazil companies with CNPJ but missing email/phone
    cur.execute("""
        SELECT id, name, cui, email, phone
        FROM companies
        WHERE country IN ('BR', 'Brazil')
        AND cui IS NOT NULL AND cui != ''
        AND LENGTH(cui) >= 14
        AND (email IS NULL OR email = '' OR phone IS NULL OR phone = '')
        AND name NOT ILIKE '%prefeitura%'
        AND name NOT ILIKE '%municipio%'
        AND name NOT ILIKE '%secretaria%'
        AND name NOT ILIKE '%fundacao%'
        LIMIT 100
    """)

    companies = cur.fetchall()
    print(f"Found {len(companies)} Brazil companies to enrich")

    enriched = 0
    for id, name, cnpj, email, phone in companies:
        print(f"[{enriched+1}] {name[:50]}...", end=" ", flush=True)

        data = fetch_cnpj(cnpj)
        if data:
            new_email = data.get('email', '').lower() if not email else email
            new_phone = data.get('telefone', '') if not phone else phone

            if new_email or new_phone:
                cur.execute("""
                    UPDATE companies
                    SET email = COALESCE(NULLIF(%s, ''), email),
                        phone = COALESCE(NULLIF(%s, ''), phone),
                        updated_at = NOW()
                    WHERE id = %s
                """, (new_email, new_phone, id))
                conn.commit()
                enriched += 1
                print(f"OK - {new_email or 'no email'}, {new_phone or 'no phone'}")
            else:
                print("no data")
        else:
            print("API error")

        # Rate limit: 3 requests per minute (free tier) = 20s between requests
        time.sleep(random.uniform(22, 28))

    print(f"\nEnriched: {enriched}/{len(companies)}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
