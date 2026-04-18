import csv
import time

start = time.time()

# ============================================
# SURSE DE DATE
# ============================================

# 1. Lista noastră de distribuitori (1,188 firme CAEN 4661/2830)
distri_file = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_agricole.csv'

# 2. ANAF enriched (are county, city, street separate)
anaf_enriched = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_enriched.csv'

# 3. DDG contacts (are website, email)
ddg_file = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\ddg_contacts.csv'

# 4. Harvested emails (are emails de pe site-uri)
harvested_file = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\harvested_emails.csv'

# 5. Romania agriculture companies (are tot: email, website, turnover, employees, county, MADR etc)
romagri_file = r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\romania_agriculture_companies.csv'

# ============================================
# PAS 1: Încarcă distribuitorii noștri
# ============================================
print('Pas 1: Încarc distribuitorii...')
distri = {}
with open(distri_file, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row['CUI'].strip()
        distri[cui] = {
            'cui': cui,
            'denumire': row['DENUMIRE'].strip(),
            'caen': row['CAEN'].strip(),
            'adresa': row['JUDET'].strip(),
            'telefon': row['TELEFON'].strip(),
            'stare': row['STARE'].strip(),
            # Enrichment fields
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
            'email_madr': '',
            'phone_madr': '',
            'email_dsvsa': '',
            'phone_dsvsa': '',
            'email_agri': '',
            'phone_agri': '',
            'website_onrc': '',
        }

print(f'  Distribuitori: {len(distri)}')

# ============================================
# PAS 2: Enrich cu ANAF enriched (county, city, forma juridica)
# ============================================
print('Pas 2: ANAF enriched...')
matched = 0
with open(anaf_enriched, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        if cui in distri:
            matched += 1
            d = distri[cui]
            if row.get('county'): d['judet'] = row['county'].strip()
            if row.get('city'): d['city'] = row['city'].strip()
            if row.get('legal_form'): d['forma_juridica'] = row['legal_form'].strip()

print(f'  Matched: {matched}')

# ============================================
# PAS 3: Enrich cu DDG contacts (website, email)
# ============================================
print('Pas 3: DDG contacts...')
matched = 0
ddg_by_cui = {}
with open(ddg_file, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        if not cui: continue
        
        email = row.get('email', '').strip()
        website = row.get('website', '').strip()
        
        if cui not in ddg_by_cui:
            ddg_by_cui[cui] = {'emails': [], 'websites': []}
        
        if email and '@' in email:
            ddg_by_cui[cui]['emails'].append(email)
        if website:
            ddg_by_cui[cui]['websites'].append(website)

for cui, data in ddg_by_cui.items():
    if cui in distri:
        matched += 1
        d = distri[cui]
        emails = list(set(data['emails']))
        websites = list(set(data['websites']))
        if emails:
            d['email'] = emails[0]
            if len(emails) > 1:
                d['email2'] = emails[1]
        if websites:
            d['website'] = websites[0]

print(f'  Matched: {matched}')

# ============================================
# PAS 4: Enrich cu Harvested emails
# ============================================
print('Pas 4: Harvested emails...')
matched = 0
with open(harvested_file, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        if cui in distri:
            email = row.get('email_found', '').strip()
            website = row.get('website', '').strip()
            if email and '@' in email and not distri[cui]['email']:
                distri[cui]['email'] = email
                matched += 1
            elif email and '@' in email and distri[cui]['email'] != email:
                distri[cui]['email2'] = email
            if website and not distri[cui]['website']:
                distri[cui]['website'] = website

print(f'  Matched: {matched}')

# ============================================
# PAS 5: Enrich cu Romania Agriculture (turnover, employees, email, website, MADR, DSVSA)
# ============================================
print('Pas 5: Romania Agriculture...')
matched = 0
with open(romagri_file, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        if cui in distri:
            matched += 1
            d = distri[cui]
            
            # Turnover & employees
            if row.get('turnover_ron'): d['cifra_afaceri_ron'] = row['turnover_ron'].strip()
            if row.get('turnover_eur'): d['cifra_afaceri_eur'] = row['turnover_eur'].strip()
            if row.get('nr_employees'): d['angajati'] = row['nr_employees'].strip()
            if row.get('profit_net'): d['profit_net'] = row['profit_net'].strip()
            if row.get('founding_year'): d['an_infiintare'] = row['founding_year'].strip()
            
            # Email/website principal
            email = row.get('email', '').strip()
            if email and '@' in email and not d['email']:
                d['email'] = email
            
            website = row.get('website', '').strip()
            if website and not d['website']:
                d['website'] = website
            
            # County/city if still empty
            county = row.get('county', '').strip()
            city = row.get('city', '').strip()
            if county and not d['judet']: d['judet'] = county
            if city and not d['city']: d['city'] = city
            
            # MADR (Ministerul Agriculturii)
            email_madr = row.get('email_madr', '').strip()
            phone_madr = row.get('phone_madr', '').strip()
            if email_madr and '@' in email_madr: d['email_madr'] = email_madr
            if phone_madr: d['phone_madr'] = phone_madr
            
            # DSVSA (Direcția Sanitar-Veterinară)
            email_dsvsa = row.get('email_dsvsa', '').strip()
            phone_dsvsa = row.get('phone_dsvsa', '').strip()
            if email_dsvsa and '@' in email_dsvsa: d['email_dsvsa'] = email_dsvsa
            if phone_dsvsa: d['phone_dsvsa'] = phone_dsvsa
            
            # Agri master
            email_agri = row.get('email_agri', '').strip()
            phone_agri = row.get('phone_agri', '').strip()
            if email_agri and '@' in email_agri: d['email_agri'] = email_agri
            if phone_agri: d['phone_agri'] = phone_agri
            
            # ONRC website
            website_onrc = row.get('website_onrc', '').strip()
            if website_onrc and not d['website']: d['website'] = website_onrc
            
            # Forma juridica
            fj = row.get('legal_form', '').strip()
            if fj and not d['forma_juridica']: d['forma_juridica'] = fj

print(f'  Matched: {matched}')

# ============================================
# PAS 6: Salvare CSV enriched
# ============================================
print('Pas 6: Salvare...')

fields = ['cui', 'denumire', 'caen', 'judet', 'city', 'adresa', 'telefon', 
          'email', 'email2', 'website',
          'cifra_afaceri_ron', 'cifra_afaceri_eur', 'angajati', 'profit_net',
          'an_infiintare', 'forma_juridica', 'stare',
          'email_madr', 'phone_madr', 'email_dsvsa', 'phone_dsvsa', 
          'email_agri', 'phone_agri']

out_file = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_ENRICHED.csv'

rows = sorted(distri.values(), key=lambda x: x['denumire'])

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

print(f'\n{"=" * 60}')
print(f'REZULTATE ENRICHMENT')
print(f'{"=" * 60}')
print(f'Total firme:        {len(rows):,}')
print(f'Cu email:           {with_email:,} ({with_email*100//len(rows)}%)')
print(f'Cu website:         {with_website:,} ({with_website*100//len(rows)}%)')
print(f'Cu telefon:         {with_phone:,} ({with_phone*100//len(rows)}%)')
print(f'Cu cifră afaceri:   {with_turnover:,} ({with_turnover*100//len(rows)}%)')
print(f'Cu angajați:        {with_employees:,} ({with_employees*100//len(rows)}%)')
print(f'\nSalvat: {out_file}')
print(f'Timp: {time.time()-start:.1f}s')
