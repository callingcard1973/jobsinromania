import csv
import re

def normalize(name):
    """Normalize company name for fuzzy matching"""
    n = name.upper().strip()
    # Remove common suffixes
    for suffix in [' S.R.L.', ' S.R.L', ' SRL', ' S.A.', ' S.A', ' SA', ' S.C.', ' S.C', 
                   ' SOCIETATE CU RASPUNDERE LIMITATA', ' SOCIETATE PE ACTIUNI',
                   ' INTREPRINDERE INDIVIDUALA', ' PERSOANA FIZICA AUTORIZATA']:
        n = n.replace(suffix, '')
    # Remove dots, commas, extra spaces
    n = re.sub(r'[^A-Z0-9\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

# ============================================
# PAS 1: Load our distributors
# ============================================
print('Loading distributors...')
distri = {}
distri_names = {}
with open(r'D:\MEMORY\DELECROIX\distribuitori_utilaje_agricole.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row['CUI'].strip()
        name = row['DENUMIRE'].strip()
        norm = normalize(name)
        distri[cui] = {
            'cui': cui,
            'denumire': name,
            'caen': row['CAEN'].strip(),
            'adresa': row['JUDET'].strip(),
            'telefon': row['TELEFON'].strip(),
            'stare': row['STARE'].strip(),
            'email': '',
            'email2': '',
            'website': '',
            'judet': '',
            'city': '',
            'cifra_afaceri_ron': '',
            'cifra_afaceri_eur': '',
            'angajati': '',
            'profit_net': '',
            'an_infiintare': '',
            'forma_juridica': '',
        }
        distri_names[norm] = cui

print(f'Distributors: {len(distri)}')

# ============================================
# PAS 2: Enrich from DDG (match on CUI + name)
# ============================================
print('Enriching from DDG...')
ddg_matched = 0
ddg_email = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\ddg_contacts.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        email = row.get('email', '').strip()
        website = row.get('website', '').strip()
        
        # Try CUI match first
        if cui in distri:
            d = distri[cui]
            if email and '@' in email and not d['email']:
                d['email'] = email
                ddg_email += 1
            elif email and '@' in email and d['email'] != email:
                d['email2'] = email
            if website and not d['website']:
                d['website'] = website
            ddg_matched += 1
            continue
        
        # Try name match
        name = row.get('company_name', '').strip()
        if name:
            norm = normalize(name)
            if norm in distri_names:
                match_cui = distri_names[norm]
                d = distri[match_cui]
                if email and '@' in email and not d['email']:
                    d['email'] = email
                    ddg_email += 1
                elif email and '@' in email and d['email'] != email:
                    d['email2'] = email
                if website and not d['website']:
                    d['website'] = website
                ddg_matched += 1

print(f'  DDG matched: {ddg_matched}, emails added: {ddg_email}')

# ============================================
# PAS 3: Enrich from Harvested emails (CUI + name)
# ============================================
print('Enriching from Harvested emails...')
harv_matched = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\harvested_emails.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        email = row.get('email_found', '').strip()
        website = row.get('website', '').strip()
        
        matched_cui = None
        if cui in distri:
            matched_cui = cui
        else:
            name = row.get('company_name', '').strip()
            if name:
                norm = normalize(name)
                if norm in distri_names:
                    matched_cui = distri_names[norm]
        
        if matched_cui:
            d = distri[matched_cui]
            if email and '@' in email and not d['email']:
                d['email'] = email
                harv_matched += 1
            elif email and '@' in email and d['email'] != email:
                d['email2'] = email
            if website and not d['website']:
                d['website'] = website

print(f'  Harvested matched: {harv_matched}')

# ============================================
# PAS 4: Enrich from Romania Agriculture (CUI + name)
# ============================================
print('Enriching from Romania Agriculture...')
ragri_matched = 0
ragri_email = 0
ragri_turnover = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\romania_agriculture_companies.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        name = row.get('company_name', '').strip()
        
        matched_cui = None
        if cui and cui in distri:
            matched_cui = cui
        elif name:
            norm = normalize(name)
            if norm in distri_names:
                matched_cui = distri_names[norm]
        
        if not matched_cui:
            continue
        
        ragri_matched += 1
        d = distri[matched_cui]
        
        # Email from any source
        for field in ['email', 'email_madr', 'email_dsvsa', 'email_agri', 'email_eu']:
            e = row.get(field, '').strip()
            if e and '@' in e:
                if not d['email']:
                    d['email'] = e
                    ragri_email += 1
                elif d['email'] != e:
                    d['email2'] = e
        
        # Website
        for field in ['website', 'website_eu', 'website_onrc']:
            w = row.get(field, '').strip()
            if w and not d['website']:
                d['website'] = w
        
        # Turnover & employees
        if row.get('turnover_ron'): 
            d['cifra_afaceri_ron'] = row['turnover_ron'].strip()
            ragri_turnover += 1
        if row.get('turnover_eur'): d['cifra_afaceri_eur'] = row['turnover_eur'].strip()
        if row.get('nr_employees'): d['angajati'] = row['nr_employees'].strip()
        if row.get('profit_net'): d['profit_net'] = row['profit_net'].strip()
        if row.get('founding_year'): d['an_infiintare'] = row['founding_year'].strip()
        
        # County/city
        if row.get('county') and not d['judet']: d['judet'] = row['county'].strip()
        if row.get('city') and not d['city']: d['city'] = row['city'].strip()
        if row.get('legal_form') and not d['forma_juridica']: d['forma_juridica'] = row['legal_form'].strip()

print(f'  Romania Agri matched: {ragri_matched}, emails: {ragri_email}, turnover: {ragri_turnover}')

# ============================================
# PAS 5: Enrich from ANAF enriched (county, city)
# ============================================
print('Enriching from ANAF enriched...')
anaf_matched = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_enriched.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        name = row.get('company_name', '').strip()
        
        matched_cui = None
        if cui in distri:
            matched_cui = cui
        elif name:
            norm = normalize(name)
            if norm in distri_names:
                matched_cui = distri_names[norm]
        
        if matched_cui:
            d = distri[matched_cui]
            if row.get('county') and not d['judet']: d['judet'] = row['county'].strip()
            if row.get('city') and not d['city']: d['city'] = row['city'].strip()
            if row.get('legal_form') and not d['forma_juridica']: d['forma_juridica'] = row['legal_form'].strip()
            anaf_matched += 1

print(f'  ANAF enriched matched: {anaf_matched}')

# ============================================
# PAS 6: Save CSV
# ============================================
print('\nSaving enriched CSV...')

fields = ['cui', 'denumire', 'caen', 'judet', 'city', 'adresa', 'telefon',
          'email', 'email2', 'website',
          'cifra_afaceri_ron', 'cifra_afaceri_eur', 'angajati', 'profit_net',
          'an_infiintare', 'forma_juridica', 'stare']

rows = sorted(distri.values(), key=lambda x: x['denumire'])

out_file = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_ENRICHED.csv'
with open(out_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

# Stats
with_email = sum(1 for r in rows if r['email'])
with_website = sum(1 for r in rows if r['website'])
with_phone = sum(1 for r in rows if r['telefon'])
with_turnover = sum(1 for r in rows if r['cifra_afaceri_ron'])
with_employees = sum(1 for r in rows if r['angajati'])
with_county = sum(1 for r in rows if r['judet'])
with_city = sum(1 for r in rows if r['city'])

print(f'\n{"=" * 60}')
print(f'REZULTATE ENRICHMENT')
print(f'{"=" * 60}')
print(f'Total firme:        {len(rows):,}')
print(f'Cu email:           {with_email:,} ({with_email*100//len(rows)}%)')
print(f'Cu website:         {with_website:,} ({with_website*100//len(rows)}%)')
print(f'Cu telefon:         {with_phone:,} ({with_phone*100//len(rows)}%)')
print(f'Cu cifra afaceri:   {with_turnover:,}')
print(f'Cu angajati:        {with_employees:,}')
print(f'Cu judet:           {with_county:,}')
print(f'Cu city:            {with_city:,}')
print(f'\nSalvat: {out_file}')
