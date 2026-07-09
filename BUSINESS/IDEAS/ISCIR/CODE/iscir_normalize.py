#!/usr/bin/env python3
"""Zero-token deterministic normalizer for ISCIR register PDFs -> CSV.

No LLM involved: pdfplumber tables + regex field extraction. Re-running monthly
after a fresh scrape costs zero model tokens. Handles every register layout
generically (keeps original columns) and additionally regex-extracts standard
lead fields (cui, j_number, email, phone, dates) from any cell. Text-only PDFs
(e.g. the CAEN comunicat) fall back to a line/regex extractor.
"""
import sys, re, csv, glob, pathlib, unicodedata
import pdfplumber

RE_J = re.compile(r'J\d{1,2}/\d{1,6}/\d{4}')
RE_CUI = re.compile(r'\b(?:RO)?\s?(\d{6,9})\b')
RE_EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
RE_PHONE = re.compile(r'(?:(?:\+?40|0)\s?7\d{2}|\(?0\d{2}\)?)[\s.\-]?\d{3}[\s.\-]?\d{3}')
RE_DATE = re.compile(r'\b\d{2}\.\d{2}\.\d{4}\b')
RE_CAEN = re.compile(r'\b(\d{4})\b\s*[-–]?\s*([A-Za-z].{3,80})')


def fold(s: str) -> str:
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s).strip()


def extract_fields(cells):
    """Pull standard lead fields out of a row's raw text (any cell)."""
    blob = ' '.join(c for c in cells if c)
    j = RE_J.search(blob)
    email = RE_EMAIL.search(blob)
    phone = RE_PHONE.search(blob)
    # CUI: prefer a number not part of a J-number/date
    cui = ''
    for m in RE_CUI.finditer(blob):
        v = m.group(1)
        ctx = blob[max(0, m.start() - 1):m.end() + 1]
        if '/' in ctx or '.' in ctx:  # likely J-number or date fragment
            continue
        cui = v; break
    dates = RE_DATE.findall(blob)
    return {
        'cui': cui,
        'j_number': j.group(0) if j else '',
        'email': email.group(0).lower() if email else '',
        'phone': re.sub(r'[\s.\-()]', '', phone.group(0)) if phone else '',
        'date_1': dates[0] if dates else '',
        'date_2': dates[1] if len(dates) > 1 else '',
    }


def normalize_table_pdf(path, out_csv):
    rows_out, header = [], None
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            for tbl in (pg.extract_tables() or []):
                for r in tbl:
                    cells = [fold(c) for c in r]
                    if not any(cells):
                        continue
                    first = cells[0].split(' ')[-1] if cells[0] else ''
                    if not first.isdigit():
                        if header is None and any('crt' in c.lower() or 'denumire' in c.lower()
                                                  or 'persoan' in c.lower() for c in cells):
                            header = cells
                        continue
                    rows_out.append(cells)
    if not rows_out:
        return 0
    header = header or [f'col{i}' for i in range(max(len(r) for r in rows_out))]
    ncol = len(header)
    std = ['cui', 'j_number', 'email', 'phone', 'date_1', 'date_2']
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(header[:ncol] + std)
        for r in rows_out:
            r = (r + [''] * ncol)[:ncol]
            fx = extract_fields(r)
            w.writerow(r + [fx[k] for k in std])
    return len(rows_out)


def normalize_caen_pdf(path, out_csv):
    """Anexa table: equipment | activity | emitent | CAEN code(s) | PT.
    Explode multi-code cells into one row per (equipment, caen)."""
    rows, last_equip = [], ''
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            for tbl in (pg.extract_tables() or []):
                for r in tbl:
                    c = [fold(x) for x in (r + [''] * 5)[:5]]
                    if not any(c) or c[0].lower().startswith('tip instalatie'):
                        continue
                    equip = c[0] or last_equip
                    if c[0]:
                        last_equip = c[0]
                    codes = re.findall(r'\b\d{4}\b', (r[3] or '') if len(r) > 3 else '')
                    for code in codes:
                        rows.append([equip[:60], c[1][:40], code, c[4][:20]])
    # dedupe
    seen, uniq = set(), []
    for row in rows:
        k = (row[0], row[2])
        if k not in seen:
            seen.add(k); uniq.append(row)
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['echipament', 'activitate', 'caen', 'pt_iscir'])
        w.writerows(uniq)
    return len(uniq)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'DATA/iscir_pdfs'
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else 'DATA/leads')
    out.mkdir(parents=True, exist_ok=True)
    # the 8 lead-value registers (skip 79 PT/legislation PDFs)
    targets = ['Operatori-RSVTI-PJ', 'RSVTIPJ', 'Autorizatii-suspendate', 'Registru',
               'firme-ROMANIA-autorizate-IMSP-CLASIC', 'firme-ROMANIA-autorizate-IR-CLASIC',
               'pj-avizate', 'comunicat-coduri-CAEN']
    total = 0
    for stem in targets:
        pdf = pathlib.Path(src) / f'{stem}.pdf'
        if not pdf.exists():
            print('MISSING', stem); continue
        dest = out / f'{stem.lower().replace("-", "_")}.csv'
        n = (normalize_caen_pdf if 'caen' in stem.lower() else normalize_table_pdf)(str(pdf), str(dest))
        print(f'{n:6}  {dest.name}')
        total += n
    print(f'\nTOTAL {total} rows across {len(targets)} registers.')


if __name__ == '__main__':
    main()
