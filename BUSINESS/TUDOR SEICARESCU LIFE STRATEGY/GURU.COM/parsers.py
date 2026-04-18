#!/usr/bin/env python3
"""Parsers for beneficiar.fonduri-ue.ro scraper."""
# --
import re
import os
import html as html_module
import unicodedata
import subprocess
import tempfile
from bs4 import BeautifulSoup

BASE_URL = "https://beneficiar.fonduri-ue.ro:8080"
SPEC_DIR = "/opt/ACTIVE/EU_FUNDING/DATA/SPECS"
os.makedirs(SPEC_DIR, exist_ok=True)

# --
def to_ascii(t):
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii')

def normalize_phone(phone):
    if not phone: return ''
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 10 and digits.startswith('0'): return '+40' + digits[1:]
    elif len(digits) == 9: return '+40' + digits
    elif len(digits) == 11 and digits.startswith('40'): return '+' + digits
    elif len(digits) == 12 and digits.startswith('0040'): return '+40' + digits[4:]
    return phone.strip()

def clean(t):
    return to_ascii(re.sub(r'\s+', ' ', str(t or '')).strip()[:500]) if t else ''

# --
def decode_email(text):
    """Decode JS-obfuscated email: var addyN = 'x' + '@' + 'domain';"""
    m = re.search(r"var (addy\d+)", text)
    if not m:
        return ""
    var_name = m.group(1)
    addy_lines = [l.strip() for l in text.split("\n") if var_name in l]
    all_strings = []
    for line in addy_lines:
        if "document.write" in line:
            continue
        strings = re.findall(r"'([^']*)'", line)
        all_strings.extend(strings)
    raw = "".join(all_strings)
    email = html_module.unescape(raw)
    email = re.sub(r"&#(\d+);", lambda x: chr(int(x.group(1))), email)
    email = email.strip()
    return email if "@" in email else ""

# --
def extract_pdf_text(path):
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=30)
        return r.stdout[:5000] if r.returncode == 0 else ""
    except Exception: return ""

def extract_docx_text(path):
    try:
        from docx import Document
        return "\n".join(p.text for p in Document(path).paragraphs)[:5000]
    except Exception: return ""

def extract_file_text(data, filename=""):
    """Extract text from PDF, DOCX, or ZIP (recursive)."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if data[:5] == b"%PDF-" or ext == "pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data); tmp = f.name
        text = extract_pdf_text(tmp); os.unlink(tmp); return text
    if ext == "docx" or (data[:2] == b"PK" and b"word/" in data[:2000]):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(data); tmp = f.name
        text = extract_docx_text(tmp); os.unlink(tmp); return text
    if data[:2] == b"PK":
        import zipfile, io
        z = zipfile.ZipFile(io.BytesIO(data))
        texts = [extract_file_text(z.read(n), n) for n in z.namelist()]
        return "\n---\n".join(t for t in texts if t)
    return ""

def fetch_spec(eid, lot_id):
    """Download spec (PDF/DOCX/ZIP), extract text, return (url, text)."""
    import requests
    requests.packages.urllib3.disable_warnings()
    spec_url = f"{BASE_URL}/dwl-spec?ann={eid}&lot={lot_id}"
    try:
        r = requests.get(spec_url, verify=False, timeout=60)
        if r.status_code != 200 or len(r.content) < 100:
            return spec_url, ""
        filename = ""
        cd = r.headers.get("content-disposition", "")
        m = re.search(r"filename=(.+)", cd)
        if m:
            filename = m.group(1).strip().strip('"')
        spec_text = extract_file_text(r.content, filename)[:5000]
        return spec_url, to_ascii(spec_text.strip())
    except Exception:
        return spec_url, ""

# --
def parse_contact_div(soup, d):
    """Extract contact info from contact_benef div."""
    cdiv = soup.find('div', {'id': 'contact_benef'})
    if not cdiv:
        return
    for li in cdiv.find_all('li'):
        t = li.get_text(strip=True)
        if t.startswith('Adresa:'): d['adresa'] = clean(t[7:])
        elif t.startswith('Contact:'): d['contact'] = clean(t[8:])
        elif t.startswith('Telefon:'): d['telefon'] = normalize_phone(t[8:])
        elif t.startswith('Regiune:'): d['regiune'] = clean(t[8:])
        elif t.startswith('Judet:') and not d['judet']: d['judet'] = clean(t[6:])
        elif t.startswith('Localitate:'): d['localitate'] = clean(t[12:])

# --
def parse_anunt(html, eid, listing_info=None):
    """Parse a single anunt (procurement notice) page."""
    from datetime import datetime
    import requests
    requests.packages.urllib3.disable_warnings()
    soup = BeautifulSoup(html, 'html.parser')
    fields = ['data_publicare', 'data_limita', 'ora_limita', 'judet', 'tip_contract',
              'beneficiar', 'cui', 'adresa', 'contact', 'telefon', 'email', 'regiune',
              'localitate', 'titlu_achizitie', 'descriere', 'durata_contract', 'buget',
              'cod_smis', 'status_procedura', 'spec_url', 'spec_text', 'contractors']
    d = {'id': eid, 'url': f"{BASE_URL}/anunturi/details/2/{eid}/",
         'scraped_at': datetime.now().isoformat()}
    for f in fields:
        d[f] = ''
    # SMIS code from "Proiect [XXXXXX]:" pattern
    sm = re.search(r'Proiect\s*\[(\d+)\]', html)
    if sm:
        d['cod_smis'] = sm.group(1)
    # Table fields
    for td in soup.find_all('td'):
        txt, nxt = td.get_text(strip=True), td.find_next_sibling('td')
        if nxt:
            if 'Data publicare' in txt: d['data_publicare'] = clean(nxt.get_text())
            elif 'Data limita' in txt: d['data_limita'] = clean(nxt.get_text())
            elif 'Tip contract' in txt: d['tip_contract'] = clean(nxt.get_text())
            elif 'Judet' in txt and not d['judet']: d['judet'] = clean(nxt.get_text())
    # Contact
    parse_contact_div(soup, d)
    cdiv = soup.find('div', {'id': 'contact_benef'})
    if cdiv:
        m = re.search(r'>([A-Z][A-Z0-9\s\-\.&;]+(?:SRL|SA|PFA|II|SNC))\s*\(SMIS\)', str(cdiv))
        if m:
            d['beneficiar'] = clean(m.group(1))
    d['email'] = decode_email(html)
    # Title -- clean, no prefix
    for div in soup.find_all('div', style=re.compile(r'background:#444')):
        raw = div.get_text(strip=True)
        title = re.sub(r'^Anun.*?privat[ie]\]?\s*:?\s*', '', raw, flags=re.I).strip()
        if title:
            d['titlu_achizitie'] = clean(title[:200])
            break
    # Lot description (fast, HTML only)
    lm = re.search(r'desc-lot\?d=(\d+)', html)
    if lm:
        lot_id = lm.group(1)
        lhtml = requests.get(f"{BASE_URL}/desc-lot?d={lot_id}", verify=False, timeout=30).text
        cs = BeautifulSoup(lhtml, 'html.parser').find('section', class_='article-content')
        if cs:
            d['descriere'] = clean(cs.get_text()[:2000])
        sm2 = re.search(r'dwl-spec\?ann=(\d+)&lot=(\d+)', html)
        if sm2:
            d['spec_url'] = f"{BASE_URL}/dwl-spec?ann={eid}&lot={lot_id}"
    # Budget + fallback description
    for li in soup.find_all('li'):
        t = li.get_text()
        if 'Buget' in t:
            m = re.search(r'[\d.,]+\s*lei', t)
            d['buget'] = m.group() if m else ''
        elif 'Descriere:' in t and '[Click' not in t:
            d['descriere'] = clean(t.replace('Descriere:', '').strip()[:500]) or d['descriere']
    # Contractors (winners) - "Denumire contractor: COMPANY SRL"
    ctr = re.findall(r'Denumire contractor:\s*([A-Z][A-Z0-9\s\.\-&,]+(?:SRL|S\.R\.L|SA|S\.A|PFA|II|SNC))', soup.get_text())
    d['contractors'] = ', '.join(clean(c) for c in set(ctr)) if ctr else ''
    # Override with listing dates
    if listing_info:
        if listing_info.get('data_publicare'): d['data_publicare'] = clean(listing_info['data_publicare'])
        if listing_info.get('data_limita'): d['data_limita'] = clean(listing_info['data_limita'])
    return d

# --
def parse_proiect(html, eid):
    """Parse a single proiect (funded project) page -- all fields."""
    from datetime import datetime
    soup = BeautifulSoup(html, 'html.parser')
    fields = ['cod_smis', 'program_operational', 'titlu_proiect', 'beneficiar', 'cui',
              'adresa', 'contact', 'telefon', 'email', 'regiune', 'judet', 'localitate',
              'axa', 'domeniu_interventie', 'numar_contract', 'data_contract', 'proceduri']
    d = {'id': eid, 'url': f"{BASE_URL}/proiecte/details/1/{eid}/",
         'scraped_at': datetime.now().isoformat()}
    for f in fields:
        d[f] = ''
    # Key-value pairs from structured list
    FIELD_MAP = {
        'Cod SMIS': 'cod_smis', 'Program': 'program_operational',
        'Axa': 'axa', 'Domeniul': 'domeniu_interventie',
        'Opera': 'numar_contract', 'Beneficiar': 'beneficiar',
        'Data contract': 'data_contract',
    }
    for li in soup.find_all('li', class_='cat-list-row0'):
        strong = li.find('strong')
        val_div = li.find_next('div')
        if not strong or not val_div:
            continue
        key = strong.get_text(strip=True)
        val = val_div.get_text(strip=True)
        for prefix, field in FIELD_MAP.items():
            if key.startswith(prefix) and not d[field]:
                d[field] = clean(val)
                break
    # Contact
    parse_contact_div(soup, d)
    d['email'] = decode_email(html)
    # Title -- clean prefix
    t = soup.find('title')
    if t:
        raw = t.get_text(strip=True)
        title = re.sub(r'^.*?privat[ie]\]\s*:?\s*', '', raw, flags=re.I)
        title = re.sub(r'^.*?achizi.*?\]\s*:?\s*', '', title, flags=re.I)
        title = re.sub(r'^Proiecte\s*:?\s*', '', title, flags=re.I).strip()
        d['titlu_proiect'] = clean(title[:200]) if title else ''
    import json; procs = []  # Procedures list with status
    for a in soup.find_all('a', href=True):
        if 'anunturi/details' not in a['href']:
            continue
        name = clean(a.get_text(strip=True))
        anunt_id = re.search(r'details/2/(\d+)', a['href'])
        # Get surrounding text for dates and status
        parent = a.find_parent(['li', 'div', 'tr', 'p'])
        ctx = parent.get_text(strip=True) if parent else ''
        pub = re.search(r'Publicare:\s*([\d.]+)', ctx)
        deadline = re.search(r'Data limit[aă]\s*ofertare:\s*([\d.]+)', ctx)
        status = 'inchisa' if 'nchis' in ctx else 'ofertare' if 'ofertare' in ctx else ''
        procs.append({
            'name': name[:100], 'anunt_id': anunt_id.group(1) if anunt_id else '',
            'publicare': pub.group(1) if pub else '',
            'deadline': deadline.group(1) if deadline else '',
            'status': status})
    d['proceduri'] = json.dumps(procs, ensure_ascii=True) if procs else ''
    return d
