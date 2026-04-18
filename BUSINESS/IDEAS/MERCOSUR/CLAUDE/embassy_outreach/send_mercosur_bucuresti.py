#!/usr/bin/env python3
"""Send OIPA letters to Mercosur embassies in Bucharest via Brevo API"""

import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

BREVO_API_KEY = os.getenv('BREVO_OIPA_API_KEY')
SENDER_EMAIL = 'tudor@oipa.ro'
SENDER_NAME = 'Tudor Seicarescu - OIPA'

EMBASSIES = [
    {
        'country': 'Brazilia',
        'ambassador': 'Maria Laura da Rocha',
        'salutation': 'Stimata Doamna Ambasador',
        'email': 'brasemb.bucareste@itamaraty.gov.br'
    },
    {
        'country': 'Argentina',
        'ambassador': 'Felipe Alvarez de Toledo',
        'salutation': 'Stimate Domnule Ambasador',
        'email': 'eruma@mrecic.gov.ar'
    },
    {
        'country': 'Chile',
        'ambassador': 'Maria Pia Busta Diaz',
        'salutation': 'Stimata Doamna Ambasador',
        'email': 'echile.rumania@minrel.gob.cl'
    },
    {
        'country': 'Peru',
        'ambassador': 'Maria Eugenia Echeverria Herrera',
        'salutation': 'Stimata Doamna Ambasador',
        'email': 'embajadaperu@embajadaperu.ro'
    },
    {
        'country': 'Colombia',
        'ambassador': 'Divia Desideria Cepeda Rojas',
        'salutation': 'Stimata Doamna Ambasador',
        'email': 'ebucarest@cancilleria.gov.co'
    },
    {
        'country': 'Uruguay',
        'ambassador': '',
        'salutation': 'Excelenta',
        'email': 'urubuca@montevideo.com.uy'
    }
]

BODY_TEMPLATE = """{salutation} {ambassador},

OIPA (Organizatia Interprofesionala a Producatorilor de Legume si Fructe) doreste sa exploreze oportunitatile de export create de Acordul UE-Mercosur, in vigoare din mai 2026.

Reprezentam producatori romani de legume, fructe, conserve si produse traditionale. 15 produse romanesti cu indicatie geografica protejata sunt recunoscute in acord (vinuri, palinca, salam de Sibiu, magiun Topoloveni).

Va rugam sa ne indicati contacte de afaceri sau camere de comert din {country} interesate de produse agroalimentare europene.

Cu respect,
Tudor Seicarescu, Coordonator Export OIPA
Tel: +40 722 789 938 | tudor@oipa.ro | www.oipa.ro
"""

def send_email(to_email, to_name, subject, body):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "textContent": body
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code, response.text

def main():
    log_file = '/opt/ACTIVE/IDEAS/MERCOSUR/CLAUDE/embassy_outreach/send_bucuresti_log.txt'

    with open(log_file, 'a') as log:
        log.write(f"\n{'='*50}\n")
        log.write(f"Send Bucuresti started: {datetime.now()}\n")

        for emb in EMBASSIES:
            body = BODY_TEMPLATE.format(
                salutation=emb['salutation'],
                ambassador=emb['ambassador'],
                country=emb['country']
            )
            subject = f"Colaborare export Romania - {emb['country']} in cadrul Acordului UE-Mercosur"

            status, response = send_email(
                emb['email'],
                f"Ambasada {emb['country']}",
                subject,
                body
            )
            log.write(f"{emb['email']}: {status} - {response}\n")
            print(f"Sent to {emb['country']} ({emb['email']}): {status}")

    print(f"Done. Log: {log_file}")

if __name__ == '__main__':
    main()
