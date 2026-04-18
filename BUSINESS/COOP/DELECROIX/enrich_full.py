import csv
import time

start = time.time()

# ============================================
# PAS 1: Load distributors
# ============================================
print('Pas 1: Loading distributors...')
distri = {}
with open(r'D:\MEMORY\DELECROIX\distribuitori_utilaje_agricole.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row['CUI'].strip()
        distri[cui] = {
            'cui': cui,
            'denumire': row['DENUMIRE'].strip(),
            'caen': row['CAEN'].strip(),
            'adresa': row['JUDET'].strip(),
            'telefon_anaf': row['TELEFON'].strip(),
            'stare': row['STARE'].strip(),
            'fax': '',
            'cod_postal': '',
            'nr_reg_com': '',
            'forma_juridica': '',
            'sediu_strada': '',
            'sediu_nr': '',
            'sediu_localitate': '',
            'sediu_judet': '',
            'sediu_cod_postal': '',
            'data_inregistrare': '',
            'status_tva': '',
            'email': '',
            'email2': '',
            'website': '',
            'cifra_afaceri_ron': '',
            'cifra_afaceri_eur': '',
            'angajati': '',
            'an_infiintare': '',
        }
print(f'  Loaded: {len(distri)}')

# ============================================
# PAS 2: Full ANAF enrichment (55 cols)
# ============================================
print('Pas 2: ANAF full enrichment (2.78M rows)...')
matched = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        if cui not in distri:
            continue
        matched += 1
        d = distri[cui]
        
        # Address details
        if row.get('fax'): d['fax'] = row['fax'].strip()
        if row.get('cod_postal'): d['cod_postal'] = row['cod_postal'].strip()
        if row.get('nr_reg_com'): d['nr_reg_com'] = row['nr_reg_com'].strip()
        if row.get('forma_juridica'): d['forma_juridica'] = row['forma_juridica'].strip()
        if row.get('sediu_strada'): d['sediu_strada'] = row['sediu_strada'].strip()
        if row.get('sediu_nr'): d['sediu_nr'] = row['sediu_nr'].strip()
        if row.get('sediu_localitate'): d['sediu_localitate'] = row['sediu_localitate'].strip()
        if row.get('sediu_judet'): d['sediu_judet'] = row['sediu_judet'].strip()
        if row.get('sediu_cod_postal'): d['sediu_cod_postal'] = row['sediu_cod_postal'].strip()
        if row.get('data_inregistrare'): d['data_inregistrare'] = row['data_inregistrare'].strip()
        
        # TVA status
        if row.get('scp_tva'): d['status_tva'] = row['scp_tva'].strip()

print(f'  ANAF matched: {matched}')

# ============================================
# PAS 3: DDG contacts (name matching)
# ============================================
print('Pas 3: DDG contacts enrichment...')

def normalize(name):
    import re
    n = name.upper().strip()
    for sfx in [' S.R.L.', ' S.R.L', ' SRL', ' S.A.', ' S.A', ' SA', ' S.C.', ' S.C']:
        n = n.replace(sfx, '')
    n = re.sub(r'[^A-Z0-9\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

distri_names = {normalize(d['denumire']): cui for cui, d in distri.items()}

ddg_match = 0
ddg_email = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\ddg_contacts.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        name = row.get('company_name', '').strip()
        email = row.get('email', '').strip()
        website = row.get('website', '').strip()
        
        match_cui = None
        if cui in distri:
            match_cui = cui
        elif name:
            norm = normalize(name)
            if norm in distri_names:
                match_cui = distri_names[norm]
        
        if match_cui:
            d = distri[match_cui]
            if email and '@' in email:
                if not d['email']:
                    d['email'] = email
                    ddg_email += 1
                elif d['email'] != email:
                    d['email2'] = email
            if website and not d['website']:
                d['website'] = website
            ddg_match += 1

print(f'  DDG matched: {ddg_match}, emails: {ddg_email}')

# ============================================
# PAS 4: Romania Agriculture enrichment
# ============================================
print('Pas 4: Romania Agriculture enrichment...')
ragri_match = 0
ragri_email = 0
ragri_turnover = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\romania_agriculture_companies.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        name = row.get('company_name', '').strip()
        
        match_cui = None
        if cui and cui in distri:
            match_cui = cui
        elif name:
            norm = normalize(name)
            if norm in distri_names:
                match_cui = distri_names[norm]
        
        if not match_cui:
            continue
        
        ragri_match += 1
        d = distri[match_cui]
        
        # Emails from all sources
        for field in ['email', 'email_madr', 'email_dsvsa', 'email_agri', 'email_eu']:
            e = row.get(field, '').strip()
            if e and '@' in e:
                if not d['email']:
                    d['email'] = e
                    ragri_email += 1
                elif d['email'] != e and not d['email2']:
                    d['email2'] = e
        
        # Website
        for field in ['website', 'website_eu', 'website_onrc']:
            w = row.get(field, '').strip()
            if w and not d['website']:
                d['website'] = w
        
        # Turnover
        if row.get('turnover_ron'):
            d['cifra_afaceri_ron'] = row['turnover_ron'].strip()
            ragri_turnover += 1
        if row.get('turnover_eur'): d['cifra_afaceri_eur'] = row['turnover_eur'].strip()
        if row.get('nr_employees'): d['angajati'] = row['nr_employees'].strip()
        if row.get('founding_year'): d['an_infiintare'] = row['founding_year'].strip()

print(f'  Romania Agri matched: {ragri_match}, emails: {ragri_email}, turnover: {ragri_turnover}')

# ============================================
# PAS 5: Save enriched CSV
# ============================================
print('\nPas 5: Saving...')

fields = ['cui', 'denumire', 'caen', 'nr_reg_com', 'forma_juridica',
          'sediu_judet', 'sediu_localitate', 'sediu_strada', 'sediu_nr', 'sediu_cod_postal',
          'adresa', 'telefon_anaf', 'fax', 'cod_postal',
          'data_inregistrare', 'stare', 'status_tva',
          'email', 'email2', 'website',
          'cifra_afaceri_ron', 'cifra_afaceri_eur', 'angajati', 'an_infiintare']

rows = sorted(distri.values(), key=lambda x: x['denumire'])

out_file = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_ENRICHED.csv'
with open(out_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

# Stats
with_email = sum(1 for r in rows if r['email'])
with_website = sum(1 for r in rows if r['website'])
with_phone = sum(1 for r in rows if r['telefon_anaf'])
with_judet = sum(1 for r in rows if r['sediu_judet'])
with_city = sum(1 for r in rows if r['sediu_localitate'])
with_turnover = sum(1 for r in rows if r['cifra_afaceri_ron'])
with_nr_reg = sum(1 for r in rows if r['nr_reg_com'])

print(f'\n{"=" * 60}')
print(f'REZULTATE ENRICHMENT FINAL')
print(f'{"=" * 60}')
print(f'Total firme:          {len(rows):,}')
print(f'Cu email:             {with_email:,}')
print(f'Cu website:           {with_website:,}')
print(f'Cu telefon:           {with_phone:,}')
print(f'Cu judet:             {with_judet:,}')
print(f'Cu localitate:        {with_city:,}')
print(f'Cu CUI + nr reg com:  {with_nr_reg:,}')
print(f'Cu cifra afaceri:     {with_turnover:,}')
print(f'Lipsa email:          {len(rows) - with_email:,}')
print(f'\nSalvat: {out_file}')
print(f'Timp: {time.time()-start:.1f}s')

# ============================================
# PAS 6: Generate DDG search list for email enrichment
# ============================================
print('\nPas 6: Generating DDG search targets...')
need_email = [r for r in rows if not r['email'] and r['telefon_anaf']]
print(f'Firme cu telefon dar fara email: {need_email.__len__():,}')

# Save search list
search_file = r'D:\MEMORY\DELECROIX\ddg_search_targets.csv'
with open(search_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['cui', 'denumire', 'telefon_anaf', 'sediu_judet', 'sediu_localitate'])
    writer.writeheader()
    for r in sorted(need_email, key=lambda x: x['denumire']):
        writer.writerow({
            'cui': r['cui'],
            'denumire': r['denumire'],
            'telefon_anaf': r['telefon_anaf'],
            'sediu_judet': r['sediu_judet'],
            'sediu_localitate': r['sediu_localitate']
        })

print(f'Search targets saved: {search_file} ({len(need_email)} firme)')
