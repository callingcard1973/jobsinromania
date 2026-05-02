#!/usr/bin/env python3
"""Scrape EBRD PSD pages. Saves every 10. Retries 404s. 10-30s delays."""
# --
import sys; sys.stdout.reconfigure(line_buffering=True)
import requests
import re
import csv
import time
import json
import random
import unicodedata
from bs4 import BeautifulSoup
from pathlib import Path

OUT_DIR = Path("/opt/ACTIVE/SCRAPERS/EBRD/data")
OUT_CSV = OUT_DIR / "ebrd_psd_details.csv"
STATE_FILE = OUT_DIR / "psd_state.json"
MIN_ID, MAX_ID = 40000, 57000
AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/131.0.2903.86',
]
COLS = ['psd_id', 'project_id', 'title', 'country', 'sector', 'notice_type',
        'status', 'ebrd_finance', 'finance_desc', 'total_cost', 'overview',
        'contact_name', 'contact_email', 'contact_phone', 'contact_website',
        'contact_address', 'company_contact_raw', 'url']

def to_ascii(t):
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii').strip()

def parse_psd(html, pid):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    d = {'psd_id': pid, 'url': f"https://www.ebrd.com/home/work-with-us/projects/psd/{pid}.html"}
    # Contact
    h2 = soup.find('h2', string=re.compile(r'Company Contact'))
    if h2:
        p = h2.find_next('p')
        if p:
            lines = [to_ascii(l.strip()) for l in p.get_text(separator='\n').split('\n') if l.strip()]
            d['company_contact_raw'] = ' | '.join(lines)
            d['contact_name'] = lines[0] if lines else ''
            em = re.search(r'[\w.+-]+@[\w.-]+\.\w+', d['company_contact_raw'])
            d['contact_email'] = em.group() if em else ''
            ph = re.search(r'\+[\d\s()-]{8,20}', d['company_contact_raw'])
            d['contact_phone'] = ph.group().strip() if ph else ''
            www = re.search(r'www\.[\w.-]+\.\w+', d['company_contact_raw'])
            d['contact_website'] = www.group() if www else ''
            addr = [l for l in lines if not re.match(r'^[\w.+-]+@|^\+|^www\.', l) and l != d['contact_name']]
            d['contact_address'] = ', '.join(addr) if addr else ''
    for k in ['company_contact_raw','contact_name','contact_email','contact_phone','contact_website','contact_address']:
        d.setdefault(k, '')
    # Fields
    m = re.search(r'Project ID\s*(\d+)', text); d['project_id'] = m.group(1) if m else str(pid)
    m = re.search(r'Status\s+(Signed|Complete|Implementing|Approved|Repaying|Exploratory|Concept Review)', text); d['status'] = m.group(1) if m else ''
    m = re.search(r'Location\s+([A-Za-z\s]+?)(?:\s{2}|Industry)', text); d['country'] = to_ascii(m.group(1).strip()) if m else ''
    m = re.search(r'Industry Sector\s+(.+?)(?:\s{2}|\n|Notice)', text); d['sector'] = to_ascii(m.group(1).strip()[:100]) if m else ''
    m = re.search(r'Notice Type\s+(\w+)', text); d['notice_type'] = m.group(1) if m else ''
    m = re.search(r'EBRD Finance Summary\s*([A-Z]{3}\s+[\d,.]+)', text); d['ebrd_finance'] = m.group(1) if m else ''
    m = re.search(r'EBRD Finance Summary[A-Z\d,. ]+(.+?)(?:Total [Pp]roject|$)', text, re.S); d['finance_desc'] = to_ascii(m.group(1).strip()[:300]) if m else ''
    m = re.search(r'Total [Pp]roject [Cc]ost\s*([A-Z]{3}\s+[\d,.]+)', text); d['total_cost'] = m.group(1) if m else ''
    title = soup.find('title'); d['title'] = to_ascii(title.get_text(strip=True).replace('| EBRD', '').strip()) if title else ''
    # Overview + Project Description + Objectives (grab all useful sections)
    overview = ''
    for heading in ['Overview', 'Project Description', 'Project Objectives', 'Transition Impact']:
        for h in soup.find_all('h2'):
            if heading in h.get_text():
                for sib in h.find_next_siblings(['p', 'div']):
                    if sib.name == 'h2': break
                    t = sib.get_text(strip=True)
                    if len(t) > 30 and 'cookie' not in t.lower() and 'EBRD' not in t[:10]:
                        overview += t + ' '
                    if len(overview) > 2000: break
                break
        if len(overview) > 2000: break
    d['overview'] = to_ascii(overview.strip()[:2000])
    return d

def load_state():
    if STATE_FILE.exists():
        return json.load(open(STATE_FILE))
    return {'done': {}, 'not_found': [], 'current': MIN_ID}

def save_state(state):
    json.dump(state, open(STATE_FILE, 'w'))

def save_csv(results):
    if not results: return
    with open(OUT_CSV, 'w', newline='', encoding='ascii', errors='replace') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        w.writerows(results.values())
    print(f"  CSV: {len(results)} saved")

def main():
    state = load_state()
    results = state['done']
    sess = requests.Session()
    # First pass: scan all IDs
    pid = state.get('current', MIN_ID)
    print(f"Starting from {pid}, {len(results)} already done")
    while pid < MAX_ID:
        if str(pid) in results:
            pid += 1; continue
        sess.headers['User-Agent'] = random.choice(AGENTS)
        delay = random.uniform(10, 30)
        time.sleep(delay)
        try:
            r = sess.get(f"https://www.ebrd.com/home/work-with-us/projects/psd/{pid}.html", timeout=30)
            if r.status_code == 404:
                pid += 1; continue
            if r.status_code != 200:
                print(f"  {pid}: HTTP {r.status_code}, sleeping 60s")
                time.sleep(60); sess = requests.Session(); continue
            d = parse_psd(r.text, pid)
            results[str(pid)] = d
            has = "YES" if d['contact_email'] else "no"
            print(f"  {pid}: {d['country']:15} {d['status']:12} {has:3} {d['title'][:50]}")
        except requests.exceptions.ConnectionError:
            print(f"  {pid}: blocked, sleeping 90s")
            time.sleep(90); sess = requests.Session(); continue
        except Exception as e:
            print(f"  {pid}: {e}"); pid += 1; continue
        if len(results) % 5 == 0:
            save_csv(results)
            state['done'] = results; state['current'] = pid; save_state(state)
        pid += 1
    save_csv(results)
    state['done'] = results; state['current'] = pid; save_state(state)
    with_email = sum(1 for r in results.values() if r.get('contact_email'))
    print(f"Done! {len(results)} projects, {with_email} with contact email")

if __name__ == "__main__":
    main()
