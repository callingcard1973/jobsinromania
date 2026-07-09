import csv
from pathlib import Path
from collections import defaultdict

DATA = Path(r'D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ISCIR\DATA')
op = DATA / 'operatori_rsvti_pj_enriched.csv'
ce = DATA / 'rsvti_ce_face.csv'
clienti = DATA / 'clienti_iscir_enriched.csv'

# NDT operators
print('=== Operatori cu NDT/incercari/testari ===')
with open(op, 'r', encoding='utf-8') as f:
    ndt_ops = []
    for row in csv.DictReader(f):
        name = (row.get('name', '') or '').upper()
        caen_desc = (row.get('caen_description', '') or '').upper()
        seg = (row.get('segment', '') or '').upper()
        if any(k in name or k in caen_desc or k in seg for k in ['NDT', 'INCERCARE', 'TESTARI', 'LABORATOR', 'ULTRASUN', 'RADIOGRAF', 'NEDISTRUC']):
            ndt_ops.append(row)
    print(f'  Gasiti: {len(ndt_ops)} operatori')
    for r in ndt_ops:
        print(f'  {r["name"]} | {r.get("county","")} | {r.get("caen_description","")} | {r.get("email","")}')

# What services do operators offer?
print()
print('=== Servicii/web notes operators ===')
with open(ce, 'r', encoding='utf-8') as f:
    notes = defaultdict(list)
    for row in csv.DictReader(f):
        ns = (row.get('web_notes', '') or '').strip()
        ws = (row.get('web_services', '') or '').strip()
        seg = (row.get('segment', '') or '').strip()
        if ns:
            notes[seg].append(ns[:100])
    for seg, items in sorted(notes.items()):
        print(f'  [{seg}] {len(items)} cu note')
        for item in items[:5]:
            print(f'    {item}')

# What equipment types exist (CAEN)?
print()
print('=== Echipamente ISCIR pe CAEN (clienti) ===')
caen_map = {
    '4322': 'Instalatii sanitare/termice',
    '4321': 'Instalatii electrice',
    '2511': 'Fabricare produse metalice',
    '7120': 'Testari/analize tehnice',
    '2562': 'Operatiuni de sablare/metalizare',
    '3312': 'Reparare masini',
    '4329': 'Alte instalatii',
    '3320': 'Instalatii masini/utilaje',
    '3313': 'Reparare echipamente electronice',
    '2822': 'Utilaje de ridicat/manipulat',
    '2829': 'Alte utilaje',
    '2521': 'Cazane/radiatoare',
    '3530': 'Aeronave',
    '2814': 'Macarale/valvule',
}
cl = list(csv.DictReader(open(clienti, 'r', encoding='utf-8')))
caen_counts = defaultdict(int)
for row in cl:
    c = row.get('caen', '').strip()
    if c: caen_counts[c] += 1

for c, n in sorted(caen_counts.items(), key=lambda x: -x[1]):
    label = caen_map.get(c, 'Altele')
    print(f'  {c}: {n} ({label})')

# Firms with NDT-related CAEN
print()
print('=== Clienti cu CAEN testari/incercari (7120) ===')
testari = [r for r in cl if r.get('caen','').strip() == '7120']
print(f'  Total: {len(testari)}')
has_email = len([r for r in testari if r.get('email', '')])
has_phone = len([r for r in testari if r.get('phone', '')])
counties_n = len(set(r.get('county', '') for r in testari))
print(f'  Cu email: {has_email}')
print(f'  Cu telefon: {has_phone}')
print(f'  Judete: {counties_n}')

# Equipment repair firms (3312)
print()
print('=== Clienti reparatii echipamente (3312) ===')
rep = [r for r in cl if r.get('caen','').strip() == '3312']
print(f'  Total: {len(rep)}')
has_email_r = len([r for r in rep if r.get('email', '')])
has_phone_r = len([r for r in rep if r.get('phone', '')])
print(f'  Cu email: {has_email_r}')
print(f'  Cu telefon: {has_phone_r}')
