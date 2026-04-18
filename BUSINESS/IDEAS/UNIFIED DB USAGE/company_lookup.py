#!/usr/bin/env python3
"""Romanian company bankruptcy risk scanner. Query by CUI or name search."""

import argparse
import json
import sys

from db_helper import get_conn, safe_query, anaf_lookup, safe_cui

# -- Risk scoring
RISK_LABELS = {0: 'LOW', 21: 'MEDIUM', 51: 'HIGH', 76: 'CRITICAL'}

def risk_label(score):
    label = 'LOW'
    for threshold, name in sorted(RISK_LABELS.items()):
        if score >= threshold:
            label = name
    return label

def calc_risk(data):
    """Calculate bankruptcy risk score 0-100 from merged company data."""
    score = 0
    reasons = []
    fal = data.get('insolvency', {})
    fin = data.get('financials', {})
    anaf = data.get('anaf', {})
    tenders = data.get('tenders', [])
    # -- Active insolvency (record exists in insolvency table)
    if fal:
        score += 50
        st = fal.get('status') or 'IN INSOLVENCY DB'
        reasons.append(f"Insolvency: {st} (filed {fal.get('date_filed','?')})")
    # -- Status inactive/radiated
    status = (fal.get('status') or anaf.get('stare') or '').upper()
    if any(s in status for s in ['INACTIV', 'RADIAT', 'DIZOLV']):
        score += 30
        reasons.append(f'Company status: {status}')
    # -- Financial signals
    cur = fin.get('current', {})
    prev = fin.get('previous', {})
    profit_cur = cur.get('profit_net', 0) or 0
    revenue_cur = cur.get('cifra_afaceri', 0) or 0
    emp_cur = cur.get('nr_angajati', 0) or 0
    if profit_cur < 0:
        score += 15
        reasons.append(f'Net loss: {profit_cur:,.0f} RON')
    if revenue_cur < 0:
        score += 10
        reasons.append(f'Negative revenue: {revenue_cur:,.0f} RON')
    if emp_cur == 0 and revenue_cur > 0:
        score += 10
        reasons.append('Zero employees with revenue (ghost company)')
    # -- YoY trends
    revenue_prev = prev.get('cifra_afaceri', 0) or 0
    emp_prev = prev.get('nr_angajati', 0) or 0
    if revenue_prev > 0 and revenue_cur > 0:
        rev_change = (revenue_cur - revenue_prev) / revenue_prev
        if rev_change < -0.20:
            score += 15
            reasons.append(f'Revenue declined {abs(rev_change)*100:.1f}% YoY')
    if emp_prev > 5 and emp_cur > 0:
        emp_change = (emp_cur - emp_prev) / emp_prev
        if emp_change < -0.30:
            score += 10
            reasons.append(f'Employee decline {abs(emp_change)*100:.1f}% YoY')
    # -- VAT
    if anaf and not anaf.get('platitor_tva'):
        score += 5
        reasons.append('Not VAT registered')
    # -- Lost government contracts
    if not tenders and fal:
        score += 5
        reasons.append('No SEAP/TED contracts found')
    return min(score, 100), reasons

# -- Data fetching
def fetch_company(conn, cui):
    """Fetch base company data from interjob_master.companies."""
    rows = safe_query(conn, '''
        SELECT name, cui, country, city, address, phone, email,
               website, sector, sector_name, employees_count, revenue
        FROM companies WHERE cui = %s LIMIT 1
    ''', (cui,))
    return dict(rows[0]) if rows else {}

def fetch_insolvency(conn, cui):
    """Fetch insolvency data from insolvency table."""
    rows = safe_query(conn, '''
        SELECT company_name, cui, status, date_filed, sector,
               liquidator_name, liquidator_email, liquidator_phone
        FROM insolvency WHERE cui = %s LIMIT 1
    ''', (cui,))
    return dict(rows[0]) if rows else {}

def fetch_financials(conn, cui):
    """Fetch bilant data for all available years (2022-2024)."""
    rows = safe_query(conn, '''
        SELECT year, cifra_afaceri, profit_net, nr_angajati,
               active_imobilizate, active_circulante, caen
        FROM bilant_years WHERE cui = %s ORDER BY year DESC LIMIT 3
    ''', (int(cui),))
    result = {'years': [dict(r) for r in rows]}
    if rows:
        result['current'] = dict(rows[0])
    if len(rows) > 1:
        result['previous'] = dict(rows[1])
    return result

def fetch_tenders(conn, cui):
    """Fetch SEAP/TED procurement history."""
    rows = safe_query(conn, '''
        SELECT title, value, currency, date_published, buyer_name
        FROM tenders WHERE winner_company_id = %s
        ORDER BY date_published DESC LIMIT 10
    ''', (cui,))
    return [dict(r) for r in rows]

def search_by_name(conn, name, limit=20):
    """Search companies by name substring."""
    rows = safe_query(conn, '''
        (SELECT cui, name, country, email FROM companies
         WHERE country = 'RO' AND name ILIKE %s LIMIT %s)
        UNION ALL
        (SELECT cui, company_name AS name, 'RO' AS country, NULL AS email
         FROM insolvency WHERE company_name ILIKE %s LIMIT %s)
    ''', (f'%{name}%', limit, f'%{name}%', limit))
    seen = set()
    unique = []
    for r in rows:
        key = r.get('cui', '')
        if key and key not in seen:
            seen.add(key)
            unique.append(dict(r))
    return unique[:limit]

def lookup(cui_or_name, as_json=False):
    """Full company lookup with risk scoring."""
    conn = get_conn()
    cui = safe_cui(cui_or_name)
    if not cui:
        results = search_by_name(conn, cui_or_name)
        conn.close()
        if as_json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"\nSearch results for '{cui_or_name}' ({len(results)} found):\n")
            for r in results:
                print(f"  CUI {r.get('cui','?'):>10}  {r.get('name','')[:50]:<50}  {r.get('email','') or ''}")
        return results
    # -- Full CUI lookup
    company = fetch_company(conn, cui)
    insolvency = fetch_insolvency(conn, cui)
    financials = fetch_financials(conn, cui)
    tenders = fetch_tenders(conn, cui)
    anaf = anaf_lookup(cui)
    conn.close()
    data = {
        'cui': cui,
        'company': company,
        'insolvency': insolvency,
        'financials': financials,
        'tenders': tenders,
        'anaf': anaf,
    }
    score, reasons = calc_risk(data)
    data['risk_score'] = score
    data['risk_label'] = risk_label(score)
    data['risk_reasons'] = reasons
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print_report(data)
    return data

# -- Terminal output
def print_report(data):
    """Print formatted terminal report."""
    cui = data['cui']
    co = data.get('company', {})
    fal = data.get('insolvency', {})
    anaf = data.get('anaf', {})
    fin = data.get('financials', {})
    tenders = data.get('tenders', [])
    name = co.get('name') or fal.get('company_name') or anaf.get('denumire') or '?'
    status = fal.get('status') or anaf.get('stare') or '?'
    vat = 'Yes' if anaf.get('platitor_tva') else 'No'
    caen = anaf.get('cod_caen') or '?'
    addr = anaf.get('adresa') or co.get('address') or '?'
    phone = anaf.get('telefon') or co.get('phone') or ''
    email = co.get('email') or ''
    w = 56
    print(f"\n{'=' * w}\n {name}  (CUI: {cui})\n{'=' * w}")
    print(f" Sector:     {(co.get('sector_name') or fal.get('sector') or '?'):<20} CAEN: {caen}")
    print(f" Status:     {status:<20} VAT:  {vat}")
    print(f" Address:    {addr}")
    contact = f" Phone: {phone}" if phone else ''
    contact += f"  Email: {email}" if email else ''
    if contact:
        print(contact)
    # -- Financials
    cur = fin.get('current', {})
    prev = fin.get('previous', {})
    if cur:
        print(f"\n FINANCIALS ({cur.get('year','?')} vs {prev.get('year','?')})")
        rc = cur.get('cifra_afaceri', 0) or 0
        rp = prev.get('cifra_afaceri', 0) or 0
        pc = cur.get('profit_net', 0) or 0
        pp = prev.get('profit_net', 0) or 0
        ec = cur.get('nr_angajati', 0) or 0
        ep = prev.get('nr_angajati', 0) or 0
        print(f" Revenue:    {rp:>12,.0f} -> {rc:>12,.0f} RON  {_arrow(rp, rc)}")
        print(f" Profit:     {pp:>12,.0f} -> {pc:>12,.0f} RON  {_arrow(pp, pc)}")
        print(f" Employees:  {ep:>12,} -> {ec:>12,}      {_arrow(ep, ec)}")
    # -- Insolvency
    insol_status = fal.get('status') or ('YES - in database' if fal else 'NONE')
    print(f"\n INSOLVENCY: {insol_status}")
    if fal:
        print(f"   Liquidator: {fal.get('liquidator_name') or '?'}  Filed: {fal.get('date_filed') or '?'}")
    # -- Tenders + Risk
    if tenders:
        tv = sum(float(t.get('value') or 0) for t in tenders)
        cur = tenders[0].get('currency', 'EUR')
        print(f" SEAP/TED: {len(tenders)} contracts, {tv:,.0f} {cur} (last: {tenders[0].get('date_published','?')})")
    else:
        print(f" SEAP/TED: NONE")
    score, label = data['risk_score'], data['risk_label']
    bar = '#' * (score * 10 // 100) + '-' * (10 - score * 10 // 100)
    print(f"\n RISK SCORE: {score}/100 [{bar}] {label}")
    for r in data.get('risk_reasons', []):
        print(f"   ! {r}")
    print(f"{'=' * w}\n")

def _arrow(old, new):
    if not old or not new:
        return ''
    if old == new:
        return '='
    return f"{'v' if new < old else '^'} {(new - old) / abs(old) * 100:+.1f}%"

def main():
    ap = argparse.ArgumentParser(description='Romanian company bankruptcy risk scanner')
    ap.add_argument('query', help='CUI number or company name to search')
    ap.add_argument('--json', action='store_true', help='JSON output')
    args = ap.parse_args()
    lookup(args.query, as_json=args.json)

if __name__ == '__main__':
    main()
