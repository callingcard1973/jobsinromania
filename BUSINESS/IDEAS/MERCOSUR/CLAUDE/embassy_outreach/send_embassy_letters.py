#!/usr/bin/env python3
"""Send OIPA embassy letters via Brevo API"""

import os
import sys
import requests
from pathlib import Path
from datetime import datetime

# Load environment
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

BREVO_API_KEY = os.getenv('BREVO_OIPA_API_KEY')
SENDER_EMAIL = 'tudor@oipa.ro'
SENDER_NAME = 'Tudor Seicarescu - OIPA'

LETTERS = [
    # Brazilia + Guyana + Suriname (aceeasi ambasada)
    {
        'file': 'letter_brazil_guyana_suriname_ro.txt',
        'to_email': 'brasilia@mae.ro',
        'to_name': 'Ambasada Romaniei in Brazilia',
        'subject': 'Oportunitati de export Romania-Brazilia, Guyana si Suriname in cadrul Acordului UE-Mercosur'
    },
    # Argentina + Paraguay (aceeasi ambasada)
    {
        'file': 'letter_argentina_paraguay_ro.txt',
        'to_email': 'buenosaires@mae.ro',
        'to_name': 'Ambasada Romaniei in Argentina',
        'subject': 'Oportunitati de export Romania-Argentina si Paraguay in cadrul Acordului UE-Mercosur'
    },
    # Uruguay
    {
        'file': 'letter_uruguay_ro.txt',
        'to_email': 'montevideo@mae.ro',
        'to_name': 'Ambasada Romaniei in Uruguay',
        'subject': 'Oportunitati de export Romania-Uruguay in cadrul Acordului UE-Mercosur'
    },
    # Chile
    {
        'file': 'letter_chile_ro.txt',
        'to_email': 'santiagodechile@mae.ro',
        'to_name': 'Ambasada Romaniei in Chile',
        'subject': 'Oportunitati de export Romania-Chile in cadrul Acordului UE-Mercosur'
    },
    # Peru + Bolivia + Ecuador (aceeasi ambasada)
    {
        'file': 'letter_peru_bolivia_ecuador_ro.txt',
        'to_email': 'lima@mae.ro',
        'to_name': 'Ambasada Romaniei in Peru',
        'subject': 'Oportunitati de export Romania-Peru, Bolivia si Ecuador in cadrul Acordului UE-Mercosur'
    },
    # Columbia
    {
        'file': 'letter_colombia_ro.txt',
        'to_email': 'bogota@mae.ro',
        'to_name': 'Ambasada Romaniei in Columbia',
        'subject': 'Oportunitati de export Romania-Columbia in cadrul Acordului UE-Mercosur'
    }
]

def send_email(to_email, to_name, subject, body):
    """Send email via Brevo API"""
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
    script_dir = Path(__file__).parent
    log_file = script_dir / 'send_log.txt'

    with open(log_file, 'a') as log:
        log.write(f"\n{'='*50}\n")
        log.write(f"Send started: {datetime.now()}\n")

        for letter in LETTERS:
            letter_path = script_dir / letter['file']

            if not letter_path.exists():
                log.write(f"ERROR: {letter['file']} not found\n")
                continue

            body = letter_path.read_text(encoding='utf-8')
            # Remove header lines (Catre, Email, Ref) - start from actual greeting
            lines = body.split('\n')
            # Find the greeting line (Stimate/Stimata)
            start_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('Stim'):
                    start_idx = i
                    break
            body_clean = '\n'.join(lines[start_idx:])

            status, response = send_email(
                letter['to_email'],
                letter['to_name'],
                letter['subject'],
                body_clean
            )

            log.write(f"{letter['to_email']}: {status} - {response}\n")
            print(f"Sent to {letter['to_email']}: {status}")

    print(f"Done. Log: {log_file}")

if __name__ == '__main__':
    main()
