#!/usr/bin/env python3
"""Shortlist generator API — receives client requests, sends candidate shortlist via email."""
from flask import Flask, request, jsonify
import csv, json, re, random, os, logging
from collections import defaultdict
from datetime import datetime
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# --- Config ---
CV_FILE = "/opt/ACTIVE/WORKFORCE/cv_extracted.json"
APPS_CSV = "/opt/ACTIVE/EMAIL/ORDERS/applicants.csv"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
FROM_EMAIL = "office@factoryjobs.eu"
FROM_NAME = "FactoryJobs.eu"
LOG_FILE = "/opt/ACTIVE/WORKFORCE/shortlist_requests.log"

SECTOR_KEYWORDS = {
    'Constructii': ['weld','sudor','construction','builder','mason','carpenter',
        'plumb','pipe','scaffold','concrete','beton','steel','iron','electric','roofer'],
    'Productie': ['factory','machine','operator','cnc','assembl','packaging',
        'forklift','quality','production','electronic','automotive','warehouse'],
    'Alimentar': ['butcher','meat','slaughter','baker','cook','food','kitchen','chef','catering'],
    'Logistica': ['driver','truck','transport','courier','logistics','cargo','delivery'],
    'Healthcare': ['nurse','medical','infirm','hospital','care','pharma','health','clinic'],
    'Hospitality': ['hotel','waiter','bartender','barman','housekeep','receptionist','barista'],
    'Agricultura': ['farm','agri','harvest','picker','greenhouse','livestock','tractor','crop'],
}

SECTOR_COLORS = {
    'Constructii': '#FF5722', 'Productie': '#FF9800', 'Alimentar': '#E91E63',
    'Logistica': '#2196F3', 'Healthcare': '#00BCD4', 'Hospitality': '#9C27B0',
    'Agricultura': '#4CAF50', 'General': '#607D8B',
}

BAD_NAMES = {'resume','cv','manpower','dristor','tudor','apollo','interjob'}

CONTACT_RE = [
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\+?\d[\d\s\-().]{8,15}\d"),
    re.compile(r"https?://\S+"),
]

def mask_phone(text):
    return re.sub(r'(\+?[\d\s\-().]{7,})(\d{3})\b', lambda m: m.group(1)+'xxx', text)

def mask_passport(text):
    text = re.sub(r'\b[A-Z]{1,2}\d{6,9}\b', '[PASSPORT]', text)
    text = re.sub(r'passport\s*[:#]?\s*[\w\d]+', 'passport: [REDACTED]', text, flags=re.IGNORECASE)
    return text

def display_name(full_name):
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[0] + ' ' + parts[-1][0] + '.'
    return full_name

def load_candidates(sector, count):
    """Load candidates for a given sector from both sources."""
    candidates = []

    # Source 1: PDF CVs
    try:
        with open(CV_FILE, encoding='utf-8') as f:
            raw = json.load(f)
        for cv in raw:
            fname = cv.get('file', '')
            text = cv.get('text', '')
            blob = text.lower()
            kws = SECTOR_KEYWORDS.get(sector, [])
            if not any(kw in blob for kw in kws):
                continue
            # extract first name
            name = re.sub(r'^buildjobs\.eu_\d+_\d+_', '', fname.replace('.pdf',''))
            name = re.sub(r'^\d+_\d+_', '', name).replace('_',' ').replace('-',' ').strip()
            name = re.sub(r'\s*\(\d+\)\s*$', '', name).strip()
            words = name.split()
            if not words or len(words[0]) < 3:
                continue
            first = words[0].capitalize()
            if first.lower() in BAD_NAMES:
                continue
            if not re.search(r'\b' + re.escape(first) + r'\b', text, re.IGNORECASE):
                continue
            clean = text
            for p in CONTACT_RE:
                clean = p.sub('', clean)
            lines = [l.strip() for l in clean.split('\n') if l.strip() and len(l.strip()) > 2]
            body = '\n'.join(lines[:30])
            if len(body) < 50:
                continue
            candidates.append({'name': name, 'text': mask_passport(mask_phone(body)), 'source': 'pdf'})
    except Exception as e:
        logging.warning(f"CV load error: {e}")

    # Source 2: Email applicants
    try:
        sector_accounts = {
            'Constructii': ['buildjobs'], 'Productie': ['factoryjobs'],
            'Alimentar': ['meatworkers'], 'Logistica': ['gmail-mpd','yahoo-apa'],
            'Healthcare': ['careworkers'], 'Hospitality': ['horeca'],
            'Agricultura': ['farmworkers','gmail-fruitnature'],
        }
        accounts = sector_accounts.get(sector, ['interjob','gmail-mpd'])
        seen = set()
        with open(APPS_CSV, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                em = r['Email'].strip().lower()
                if em in {'manpowerdristor@gmail.com','fruitnature4@gmail.com'}:
                    continue
                if r['Account'].strip().lower() not in accounts:
                    continue
                nm = r['Name'].strip()
                if not nm or len(nm) < 3 or em in seen:
                    continue
                seen.add(em)
                subj = re.sub(r'^(subject:\s*)', '', r['Subject'].strip(), flags=re.IGNORECASE)[:80]
                candidates.append({'name': nm, 'text': subj, 'source': 'email'})
    except Exception as e:
        logging.warning(f"CSV load error: {e}")

    random.shuffle(candidates)
    return candidates[:count]


def generate_html_email(client_name, sector, count, candidates, ref_base):
    color = SECTOR_COLORS.get(sector, '#607D8B')
    prefix = sector[:4].upper()
    ref_nums = sorted(random.sample(range(ref_base, ref_base + 200), len(candidates)))

    rows = ""
    for cv, rnum in zip(candidates, ref_nums):
        dname = display_name(cv['name'])
        text = cv['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        ref = f"{prefix}-{rnum}"
        rows += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #2a2a3e;color:#00d4ff;font-weight:bold;white-space:nowrap">{dname}</td>
          <td style="padding:12px;border-bottom:1px solid #2a2a3e;color:#888;font-size:12px">{ref}</td>
          <td style="padding:12px;border-bottom:1px solid #2a2a3e;color:#ccc;font-size:13px;white-space:pre-line">{text[:300]}</td>
          <td style="padding:12px;border-bottom:1px solid #2a2a3e;text-align:center">
            <a href="mailto:office@factoryjobs.eu?subject=CV%20{ref}%20{cv['name'].replace(' ','%20')}"
               style="background:#00d4ff;color:#0f0f23;padding:6px 12px;border-radius:4px;text-decoration:none;font-size:12px;font-weight:bold">
              Solicita CV
            </a>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="background:#0f0f23;color:#e0e0e0;font-family:Segoe UI,Arial,sans-serif;padding:30px;margin:0">
<div style="max-width:800px;margin:0 auto">
  <div style="text-align:center;margin-bottom:30px">
    <h1 style="color:#00d4ff;margin:0">FactoryJobs.eu</h1>
    <p style="color:#888;margin:5px 0">Shortlist Candidati — {sector}</p>
  </div>
  <div style="background:#16213e;border-radius:10px;padding:20px;margin-bottom:25px;border-left:4px solid {color}">
    <p style="margin:0">Buna ziua{' ' + client_name if client_name else ''},</p>
    <p>Va trimitem shortlist-ul de <strong style="color:#00d4ff">{len(candidates)} candidati</strong>
    pentru sectorul <strong style="color:{color}">{sector}</strong>.</p>
    <p style="color:#888;font-size:13px">Pentru CV complet, click pe "Solicita CV" sau contactati-ne direct.</p>
  </div>
  <table style="width:100%;border-collapse:collapse;background:#16213e;border-radius:10px;overflow:hidden">
    <thead>
      <tr style="background:#1a2744">
        <th style="padding:12px;text-align:left;color:#888;font-size:12px">CANDIDAT</th>
        <th style="padding:12px;text-align:left;color:#888;font-size:12px">REF</th>
        <th style="padding:12px;text-align:left;color:#888;font-size:12px">PROFIL</th>
        <th style="padding:12px;text-align:center;color:#888;font-size:12px">CV</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <div style="background:linear-gradient(135deg,#ff6b35,#ff4500);border-radius:10px;padding:20px;text-align:center;margin-top:25px">
    <a href="https://wa.me/33751171356" style="color:white;text-decoration:none;font-size:18px;font-weight:bold">
      WhatsApp: +33 7 51 17 13 56
    </a>
    <p style="color:rgba(255,255,255,0.8);margin:8px 0 0;font-size:13px">office@factoryjobs.eu</p>
  </div>
  <p style="text-align:center;color:#555;font-size:12px;margin-top:20px">
    FactoryJobs.eu | careworkers.eu | buildjobs.eu | farmworkers.eu | horecaworkers.eu
  </p>
</div>
</body></html>"""


def send_brevo_email(to_email, to_name, subject, html_content):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "replyTo": {"email": FROM_EMAIL},
        "subject": subject,
        "htmlContent": html_content,
    }
    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    return r.status_code, r.text


def log_request(data, candidates_sent):
    entry = {
        "ts": datetime.now().isoformat(),
        "client_email": data.get("email"),
        "client_name": data.get("name"),
        "sector": data.get("sector"),
        "count": data.get("count"),
        "sent": candidates_sent,
    }
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')


@app.route('/shortlist', methods=['POST'])
def shortlist():
    try:
        data = request.get_json() or request.form.to_dict()
        client_email = data.get('email', '').strip()
        client_name = data.get('name', '').strip()
        sector = data.get('sector', 'General').strip()
        count = min(int(data.get('count', 5)), 20)

        if not client_email or '@' not in client_email:
            return jsonify({'error': 'Email invalid'}), 400
        if sector not in list(SECTOR_KEYWORDS.keys()) + ['General']:
            sector = 'General'

        candidates = load_candidates(sector, count)
        if not candidates:
            return jsonify({'error': 'Nu am gasit candidati pentru acest sector'}), 404

        ref_base = random.randint(56, 377)
        html = generate_html_email(client_name, sector, count, candidates, ref_base)
        subject = f"Shortlist {len(candidates)} candidati {sector} — FactoryJobs.eu"

        status, resp = send_brevo_email(client_email, client_name, subject, html)
        log_request(data, len(candidates))

        if status in (200, 201):
            logging.info(f"Shortlist sent to {client_email}: {len(candidates)} candidates ({sector})")
            return jsonify({'ok': True, 'sent': len(candidates), 'sector': sector})
        else:
            logging.error(f"Brevo error {status}: {resp}")
            return jsonify({'error': 'Email send failed', 'detail': resp}), 500

    except Exception as e:
        logging.exception("Shortlist error")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'service': 'shortlist-api'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5055, debug=False)
