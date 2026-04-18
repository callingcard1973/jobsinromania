#!/usr/bin/env python3
"""
Campaign: Cos Legume Montan — email to produs montan producers
asking if they can prepare weekly/biweekly vegetable boxes
"""

import csv
import json
import os
import sys
import io
import time
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'DATA')
PRODUCERS_CSV = os.path.join(DATA_DIR, 'rnpm_producers_1331.csv')
STATE_FILE = os.path.join(DATA_DIR, 'campaign_cos_legume_state.json')

# -- Email template --
SUBJECT = "Propunere: Cos cu legume si fructe montane — livrare saptamanala"

BODY = """Buna ziua,

Ma numesc Tudor Seicarescu si conduc cooperativa Gospodarii de Altadata (CUI 51957925).

Am o retea de clienti — in special expati care locuiesc in Romania (peste 75.000 in comunitate) — care isi doresc produse montane autentice, certificate, livrate regulat.

Va propun urmatorul concept:

COS CU LEGUME SI FRUCTE MONTANE
- Cos saptamanal sau la 2 saptamani
- 5-8 kg legume/fructe de sezon, certificate produs montan
- Clientul alege: livrare la domiciliu SAU ridicare de la punct fix
- Zona: Bucuresti + orase mari (prin curier) sau local (ridicare directa)

Ce caut de la dumneavoastra:
1. Puteti pregati cosuri de 5-8 kg saptamanal? Ce legume/fructe aveti?
2. La ce pret per cos (fara transport)?
3. Aveti capacitate pentru 10-50 cosuri/saptamana?
4. Preferati sa livrati voi sau sa trimitem curier?

Cooperativa noastra se ocupa de:
- Gasirea clientilor (comunitate 75.000+ expati)
- Comenzi si facturare
- Coordonare livrari (Fan Courier / Sameday / ridicare)
- Promovare online (catalog, Facebook, Telegram, WhatsApp)

Dumneavoastra va ocupati doar de productie si pregatirea cosului.

Daca sunteti interesat/a, raspundeti la acest email cu:
- Ce produse aveti disponibile pe sezoane
- Pretul orientativ per cos 5-8 kg
- Zona din care livrati

Astept cu interes raspunsul dumneavoastra.

Cu stima,
Tudor Seicarescu
Gospodarii de Altadata Cooperativa Agricola
CUI 51957925
WhatsApp: +33 7 51 17 13 56
Email: cumparlegume@agroevolution.com
Catalog: https://agroevolution.com/catalog/
"""

# -- Categories to target (vegetable producers first, then all) --
TARGET_CATEGORIES = [
    'PRODUSE VEGETALE',
    'LEGUME',
    'FRUCTE',
]


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {'sent': [], 'failed': [], 'skipped': []}


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_producers():
    """Load producers with email, prioritize vegetable producers"""
    vegetal = []
    others = []
    with open(PRODUCERS_CSV, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            email = row.get('email', '').strip()
            if not email:
                continue
            cats = row.get('categories', '').upper()
            is_vegetal = any(t in cats for t in TARGET_CATEGORIES)
            entry = {
                'name': row.get('name', ''),
                'email': email,
                'county': row.get('county', ''),
                'categories': row.get('categories', ''),
                'products': row.get('products', ''),
            }
            if is_vegetal:
                vegetal.append(entry)
            else:
                others.append(entry)
    return vegetal + others


def preview():
    """Preview campaign stats"""
    producers = load_producers()
    state = load_state()
    sent_emails = set(state.get('sent', []))
    pending = [p for p in producers if p['email'] not in sent_emails]
    vegetal = [p for p in pending if any(
        t in p['categories'].upper() for t in TARGET_CATEGORIES
    )]
    print(f"Total cu email: {len(producers)}")
    print(f"Deja trimis: {len(sent_emails)}")
    print(f"De trimis: {len(pending)}")
    print(f"  - Producatori vegetale: {len(vegetal)}")
    print(f"  - Altii (lapte, miere, carne): {len(pending) - len(vegetal)}")
    print(f"\nSubject: {SUBJECT}")
    print(f"\nBody preview (first 500 chars):\n{BODY[:500]}...")
    print(f"\nReply-to: cumparlegume@agroevolution.com")
    print(f"\nTo send via Brevo on raspibig, copy this script there")
    print(f"and integrate with email_sending_skill.py")


if __name__ == '__main__':
    if '--preview' in sys.argv or len(sys.argv) == 1:
        preview()
    else:
        print("Usage: python campaign_cos_legume.py [--preview]")
        print("For actual sending, deploy to raspibig and use email_sending_skill.py")
