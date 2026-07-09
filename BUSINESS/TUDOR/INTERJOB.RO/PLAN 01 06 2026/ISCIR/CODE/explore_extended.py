import csv
from pathlib import Path
from collections import defaultdict

DATA = Path(r'D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ISCIR\DATA')
cl_path = DATA / 'clienti_iscir_enriched.csv'
op_path = DATA / 'operatori_rsvti_pj_enriched.csv'
sus_path = DATA / 'autorizatii_suspendate_enriched.csv'

cl = list(csv.DictReader(open(cl_path, 'r', encoding='utf-8')))
op = list(csv.DictReader(open(op_path, 'r', encoding='utf-8')))
sus = list(csv.DictReader(open(sus_path, 'r', encoding='utf-8')))

# NDT labs (CAEN 7120) by county
print('=== CAEN 7120 (Testari/analize) pe judet ===')
testeri = [r for r in cl if r.get('caen', '').strip() == '7120']
by_county = defaultdict(list)
for r in testeri:
    by_county[r.get('county', '')].append(r)
for c, firms in sorted(by_county.items(), key=lambda x: -len(x[1])):
    if c:
        has_email = len([f for f in firms if f.get('email', '')])
        has_phone = len([f for f in firms if f.get('phone', '')])
        print(f'  {c}: {len(firms)} firme (email: {has_email}, tel: {has_phone})')

# Equipment manufacturers (CAEN 2511, 2822, 2829, 2521, 2814)
print()
print('=== Producatori/utilaje pe CAEN ===')
for caen in ['2511', '2822', '2829', '2521', '2814']:
    firms = [r for r in cl if r.get('caen', '').strip() == caen]
    if firms:
        he = len([f for f in firms if f.get('email', '')])
        hp = len([f for f in firms if f.get('phone', '')])
        print(f'  CAEN {caen}: {len(firms)} firme (email: {he}, tel: {hp})')

# ANAF inactive firms (potential risk data product)
print()
print('=== ANAF Inactive/Suspended/Radiated ===')
inactive = [r for r in cl if r.get('anaf_inactive', '').strip().upper() in ('TRUE', '1', 'DA')]
suspended = [r for r in cl if 'SUSPENDARE' in (r.get('anaf_status', '').upper())]
radiated = [r for r in cl if 'RADIERE' in (r.get('anaf_status', '').upper())]
print(f'  Inactive: {len(inactive)}')
print(f'  Suspendate: {len(suspended)}')
print(f'  Radiate: {len(radiated)}')
vat_count = len([r for r in cl if r.get('anaf_vat', '')])
print(f'  Cu TVA: {vat_count}')

# Operators by segment - who needs what
print()
print('=== Operatori pe segment ===')
for seg in ['TESTARI/INGINERIE/CONSULTANTA', 'TERMIC/PRESIUNE', 'RIDICAT (macarale/stivuitoare/lifturi)',
            'CONSTRUCTII/INSTALATII/MONTAJ', 'CONSULTANTA/FORMARE/SUPORT', 'ALTELE/NECLAR']:
    firms = [r for r in op if r.get('segment', '') == seg]
    if firms:
        he = len([f for f in firms if f.get('email', '')])
        hp = len([f for f in firms if f.get('phone', '')])
        print(f'  {seg}: {len(firms)} (email: {he}, tel: {hp})')

# Expired operators
print()
print('=== Operatori cu autorizatie expirata ===')
expired = [r for r in op if r.get('status', '').strip() == 'expirat']
print(f'  Total: {len(expired)}')
if expired:
    exp_email = len([f for f in expired if f.get('email', '')])
    exp_phone = len([f for f in expired if f.get('phone', '')])
    print(f'  Cu email: {exp_email}')
    print(f'  Cu telefon: {exp_phone}')

# Operators who need websites (no current site)
print()
print('=== Operatori fara website (potential) ===')
ce_path = DATA / 'rsvti_ce_face.csv'
ce = list(csv.DictReader(open(ce_path, 'r', encoding='utf-8')))
no_site = [r for r in ce if not r.get('website_target', '').strip()]
print(f'  Fara site: {len(no_site)} din {len(ce)} operatori')
