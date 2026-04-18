#!/usr/bin/env python3
"""Enrich ALL 11K Brazil companies via ReceitaWS API - saves incrementally"""
import subprocess
import json
import time
import csv
import os
import psycopg2
from datetime import datetime

# Config
OUTPUT_CSV = "/opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/data/brazil/brazil_all_enriched.csv"
PROGRESS_FILE = "/opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/data/brazil/.enrich_progress.json"
API_URL = "https://receitaws.com.br/v1/cnpj/{}"
DELAY = 21  # 3 requests per minute

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"processed": [], "failed": [], "last_id": 0}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def fetch_cnpj(cnpj):
    cnpj_clean = ''.join(c for c in str(cnpj) if c.isdigit())[:14]
    if len(cnpj_clean) != 14:
        return None

    url = API_URL.format(cnpj_clean)
    try:
        result = subprocess.run(
            f'curl -sL --max-time 25 "{url}"',
            shell=True, capture_output=True, text=True, timeout=30
        )
        if result.stdout and result.stdout.strip():
            if "Too many requests" in result.stdout:
                return "RATE_LIMITED"
            data = json.loads(result.stdout)
            if data.get('status') == 'OK':
                return data
    except:
        pass
    return None

def to_ascii(text):
    if not text:
        return ""
    import unicodedata
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

def main():
    print("=" * 60)
    print("BRAZIL COMPANY ENRICHMENT - ALL 11K")
    print(f"Started: {datetime.now()}")
    print(f"Output: {OUTPUT_CSV}")
    print("=" * 60)

    # Load progress
    progress = load_progress()
    processed_ids = set(progress["processed"])

    # Connect to DB
    conn = psycopg2.connect(dbname='interjob_master', user='tudor')
    cur = conn.cursor()

    # Get all Brazil companies with valid CNPJs
    cur.execute("""
        SELECT id, name, cui, email, phone
        FROM companies
        WHERE country IN ('BR', 'Brazil')
        AND cui IS NOT NULL AND cui != ''
        AND LENGTH(cui) >= 14
        AND name NOT ILIKE '%prefeitura%'
        AND name NOT ILIKE '%municipio%'
        AND name NOT ILIKE '%secretaria%'
        AND name NOT ILIKE '%fundacao%'
        AND name NOT ILIKE '%camara%'
        AND name NOT ILIKE '%fundo %'
        ORDER BY id
    """)

    companies = cur.fetchall()
    total = len(companies)
    print(f"Total companies to process: {total}")
    print(f"Already processed: {len(processed_ids)}")
    print("-" * 60)

    # Prepare CSV
    csv_exists = os.path.exists(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 0
    csvfile = open(OUTPUT_CSV, 'a', newline='', encoding='utf-8')
    fieldnames = ['id', 'name', 'cnpj', 'email', 'phone', 'domain', 'city', 'state',
                  'status', 'activity', 'capital', 'enriched_at']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    if not csv_exists:
        writer.writeheader()

    enriched = 0
    skipped = 0
    failed = 0

    for i, (id, name, cui, existing_email, existing_phone) in enumerate(companies, 1):
        # Skip already processed
        if id in processed_ids:
            skipped += 1
            continue

        print(f"[{i:5d}/{total}] {to_ascii(name)[:45]}...", end=" ", flush=True)

        data = fetch_cnpj(cui)

        if data == "RATE_LIMITED":
            print("RATE LIMITED - waiting 60s")
            time.sleep(60)
            data = fetch_cnpj(cui)

        if data and data != "RATE_LIMITED":
            email = data.get('email', '') or existing_email or ''
            phone = data.get('telefone', '') or existing_phone or ''
            domain = email.split('@')[1] if '@' in email else ''

            row = {
                'id': id,
                'name': to_ascii(data.get('nome', name)),
                'cnpj': data.get('cnpj', cui),
                'email': email.lower() if email else '',
                'phone': phone,
                'domain': domain,
                'city': to_ascii(data.get('municipio', '')),
                'state': data.get('uf', ''),
                'status': data.get('situacao', ''),
                'activity': to_ascii(data.get('atividade_principal', [{}])[0].get('text', ''))[:100],
                'capital': data.get('capital_social', ''),
                'enriched_at': datetime.now().isoformat()
            }
            writer.writerow(row)
            csvfile.flush()

            # Update DB
            if email or phone:
                cur.execute("""
                    UPDATE companies
                    SET email = COALESCE(NULLIF(%s, ''), email),
                        phone = COALESCE(NULLIF(%s, ''), phone),
                        enriched_email = CASE WHEN %s != '' THEN TRUE ELSE enriched_email END,
                        enriched_phone = CASE WHEN %s != '' THEN TRUE ELSE enriched_phone END,
                        updated_at = NOW()
                    WHERE id = %s
                """, (email, phone, email, phone, id))
                conn.commit()

            enriched += 1
            progress["processed"].append(id)
            print(f"OK - {email or 'no email'}")
        else:
            failed += 1
            progress["failed"].append(id)
            print("FAILED")

        # Save progress every 10 companies
        if (enriched + failed) % 10 == 0:
            save_progress(progress)

        # Status every 50
        if (enriched + failed) % 50 == 0:
            elapsed = (enriched + failed) * DELAY / 60
            remaining = (total - i) * DELAY / 60
            print(f"\n--- Progress: {enriched} enriched, {failed} failed, ~{remaining:.0f} min remaining ---\n")

        time.sleep(DELAY)

    csvfile.close()
    cur.close()
    conn.close()
    save_progress(progress)

    print("=" * 60)
    print(f"COMPLETE: {datetime.now()}")
    print(f"Enriched: {enriched}")
    print(f"Failed: {failed}")
    print(f"Skipped (already done): {skipped}")
    print(f"Output: {OUTPUT_CSV}")
    print("=" * 60)

if __name__ == "__main__":
    main()
