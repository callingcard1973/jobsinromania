import csv, os
from pathlib import Path
from collections import defaultdict

DATA = Path(r'D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ISCIR\DATA')
OUT = DATA / 'campaigns'
OUT.mkdir(exist_ok=True)

# --- LOAD DATA ---
cl = list(csv.DictReader(open(DATA / 'clienti_iscir_enriched.csv', 'r', encoding='utf-8')))
op = list(csv.DictReader(open(DATA / 'operatori_rsvti_pj_enriched.csv', 'r', encoding='utf-8')))
sus = list(csv.DictReader(open(DATA / 'autorizatii_suspendate_enriched.csv', 'r', encoding='utf-8')))
idx = list(csv.DictReader(open(DATA.parent / 'websites_operatori' / '_index.csv', 'r', encoding='utf-8')))

# County firm counts
county_firms = defaultdict(int)
for row in cl:
    c = row.get('county', '').strip().upper()
    if c: county_firms[c] += 1

# Build name map from index (more reliable names)
idx_by_cui = {}
for r in idx:
    cui = r.get('cui', '').strip()
    if cui: idx_by_cui[cui] = r

# Operators with email + merge name from index
op_with_email = []
for row in op:
    email = row.get('email', '').strip()
    if not email: continue
    cui = row.get('cui', '').strip()
    name = (row.get('name', '') or '').strip()
    # If name is just a number, try index
    if not name or name.isdigit():
        if cui in idx_by_cui:
            name = idx_by_cui[cui].get('name', '') or ''
    if not name or name.isdigit():
        name = 'Operator RSVTI'
    row['_name'] = name
    op_with_email.append(row)

# Operators by county
op_by_county = defaultdict(list)
for row in op_with_email:
    c = row.get('county', '').strip().upper()
    if c:
        op_by_county[c].append(row)

# Sites by CUI
site_by_cui = {}
for row in idx:
    site_by_cui[row.get('cui', '').strip()] = row

def ascii(s):
    if not s: return ''
    s = s.replace('\u0218', 'S').replace('\u0219', 's').replace('\u021a', 'T').replace('\u021b', 't')
    s = s.replace('\u0102', 'A').replace('\u0103', 'a').replace('\u00c2', 'A').replace('\u00e2', 'a')
    s = s.replace('\u00ce', 'I').replace('\u00ee', 'i')
    return s

# ========== CAMPAIGN 1: LEAD PACKS ==========
rows1 = []
for op_row in op_with_email:
    op_name = op_row.get('_name', '').strip().split(',')[0].strip()
    op_cty = op_row.get('county', '').strip().upper()
    op_email = op_row.get('email', '').strip()
    if not op_email or not op_cty: continue
    firms_in_county = county_firms.get(op_cty, 0)
    if firms_in_county == 0: continue
    html = f'''Salut {ascii(op_name)},

Avem {firms_in_county} de firme cu echipament ISCIR reglementat in judetul {ascii(op_cty)}. Toate au nevoie de un operator RSVTI autorizat.

Lista completa include: nume firma, oras, telefon, email (unde exista), cod CAEN.

Pret pachet lunar: 99 RON / judet
Acces national (toate judetele): 499 RON / luna

Raspunde la acest email cu "DA {ascii(op_cty)}" si primesti lista in 24h.
Plata: transfer bancar / Revolut.

Pagina ta personalizata cu piata din {ascii(op_cty)}:
https://interjob.ro/iscir/operatori/{op_row.get('cui','').strip()}.html

Echipa InterJob SC'''
    rows1.append({'email': op_email, 'subject': f'{firms_in_county} clienti ISCIR in {ascii(op_cty)} - lista completa', 'body_plain': '', 'body_html': html})

with open(OUT / 'campania1_lead_packs.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['email', 'subject', 'body_plain', 'body_html'])
    w.writeheader()
    w.writerows(rows1)
print(f'Campania 1 (Lead Packs): {len(rows1)} emailuri')

# ========== CAMPAIGN 2: SITE-URI DEMO ==========
rows2 = []
op_email_by_cui = {}
for r in op:
    if r.get('email', ''):
        op_email_by_cui[r.get('cui','').strip()] = r.get('email','').strip()

for idx_row in idx:
    cui = idx_row.get('cui', '').strip()
    op_name = idx_row.get('name', '').strip().split(',')[0].strip()
    op_email = idx_row.get('email', '').strip() or op_email_by_cui.get(cui, '')
    op_phone = idx_row.get('phone', '').strip()
    if not op_email: continue
    site_url = f'https://interjob.ro/iscir/operatori/{cui}.html'
    html = f'''Salut {ascii(op_name)},

Am generat un site de prezentare pentru firma ta, pe baza datelor publice ISCIR. Il poti vedea aici:
{site_url}

Ce contine:
- Numele firmei si datele de contact
- Serviciile de inspectii/verificari tehnice
- Buton de apel direct
- Link la email

Oferta:
- Varianta gratuita: ramane pe subdomeniul interjob.ro (link-ul de mai sus)
- Varianta PRO: 29 RON/luna - site pe domeniul tau (ex: www.firma-ta.ro)
- Varianta BUSINESS: 99 RON/luna - site + SEO + lead-gen integration (primesti clienti direct pe site)

Raspunde cu "DA PRO" sau "DA BUSINESS" sau suna la {ascii(op_phone)}.

Echipa InterJob SC'''
    rows2.append({'email': op_email, 'subject': f'Site-ul {ascii(op_name)} e gata - vezi cum arata', 'body_plain': '', 'body_html': html})

with open(OUT / 'campania2_site_uri.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['email', 'subject', 'body_plain', 'body_html'])
    w.writeheader()
    w.writerows(rows2)
print(f'Campania 2 (Site-uri): {len(rows2)} emailuri')

# ========== CAMPAIGN 3: SUSPENDATI ==========
rows3 = []
for sus_row in sus:
    sus_name = sus_row.get('name', '').strip().split(',')[0].strip()
    sus_email = sus_row.get('email', '').strip()
    if not sus_email: continue
    html = f'''Buna ziua,

Conform datelor ISCIR, firma {ascii(sus_name)} are autorizatia suspendata/retrasa.

Iti putem oferi:
- Kit re-autorizare (ghid + formulare + workflow): 497 RON
- Asistenta full (noi facem tot dosarul): 1.497 RON
- Consultanta 30 min telefonic: 197 RON

Raspunde cu numarul tau de telefon si te sunam in 30 min.

Echipa InterJob SC'''
    rows3.append({'email': sus_email, 'subject': f'Autorizatia ISCIR {ascii(sus_name)} - ai nevoie de ajutor?', 'body_plain': '', 'body_html': html})

with open(OUT / 'campania3_suspendati.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['email', 'subject', 'body_plain', 'body_html'])
    w.writeheader()
    w.writerows(rows3)
print(f'Campania 3 (Suspendati): {len(rows3)} emailuri')

print(f'\nToate campaniile in: {OUT}')
