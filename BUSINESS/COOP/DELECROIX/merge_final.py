import csv

# Load enrichment results
enrich = {}
with open(r'D:\MEMORY\DELECROIX\email_enrich_results.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row['cui']
        email = row.get('email', '').strip()
        website = row.get('website', '').strip()
        enrich[cui] = {'email': email, 'website': website}

print(f'Enrichment results: {len(enrich)}')
print(f'  With email: {sum(1 for v in enrich.values() if v["email"])}')
print(f'  With website: {sum(1 for v in enrich.values() if v["website"])}')

# Load enriched CSV and update
rows = []
fields = None
with open(r'D:\MEMORY\DELECROIX\distribuitori_utilaje_ENRICHED.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    for row in reader:
        cui = row['cui']
        if cui in enrich:
            e = enrich[cui]
            if e['email'] and not row.get('email'):
                row['email'] = e['email']
            if e['website'] and not row.get('website'):
                row['website'] = e['website']
        rows.append(row)

# Save final CSV
out = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_FINAL.csv'
with open(out, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

# Stats
with_email = sum(1 for r in rows if r.get('email'))
with_website = sum(1 for r in rows if r.get('website'))
with_phone = sum(1 for r in rows if r.get('telefon_anaf'))
has_any_contact = sum(1 for r in rows if r.get('email') or r.get('telefon_anaf'))

print(f'\n{"="*60}')
print(f'FINAL CSV STATS')
print(f'{"="*60}')
print(f'Total firme:       {len(rows):,}')
print(f'Cu email:          {with_email:,} ({with_email*100//len(rows)}%)')
print(f'Cu website:        {with_website:,}')
print(f'Cu telefon:        {with_phone:,}')
print(f'Cu email SAU tel:  {has_any_contact:,} ({has_any_contact*100//len(rows)}%)')
print(f'\nSalvat: {out}')
