#!/usr/bin/env python3
"""Enrich + segment RSVTI PJ operators into sendable lead lists (no sending)."""
import csv, re, sys, unicodedata
from datetime import date

ROOT = "D:/MEMORY/BUSINESS/IDEAS/ISCIR"
MASTER = "D:/MEMORY/DATA/ACTIVE/ROMANIA_DB/master_romania_companies.csv"
DNC = ["D:/MEMORY/DATA/ARCHIVE/raspi_backup_extract/sqlite_out/dnc_list__dnc_list.csv",
       "D:/MEMORY/DATA/ARCHIVE/raspi_backup_extract/sqlite_out/elena__dnc_list.csv"]
TODAY = date(2026, 6, 26)
csv.field_size_limit(10**7)

J_RE = re.compile(r'J\d+/\d+/\d+')
CUI_RE = re.compile(r'CUI[:\s]*([0-9]{5,10})', re.I)
EMAIL_RE = re.compile(r'[\w.\-+]+@[\w\-]+\.[\w.\-]+')
PHONE_RE = re.compile(r'(?:tel|fax|mobil)[.:/ ]*([0-9 ]{8,})', re.I)
EMAIL_VALID = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')


def fold(s):
    if not s:
        return ""
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')


def norm_name(s):
    s = fold(s).upper()
    s = re.sub(r'\b(SRL|SA|SRL-D|PFA|II|SNC|SCS|SCA)\b', '', s)
    s = re.sub(r'[^A-Z0-9]', '', s)
    return s


def parse_date(s):
    m = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', s or "")
    if not m:
        return None
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


# --- load DNC ---
dnc = set()
for f in DNC:
    try:
        with open(f, encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                e = (r.get('email') or '').strip().lower()
                if e:
                    dnc.add(e)
    except Exception as e:
        print(f"DNC skip {f}: {e}", file=sys.stderr)

# --- load master index by j_number + normalized name ---
by_j, by_name = {}, {}
with open(MASTER, encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        j = (r.get('j_number') or '').strip().upper()
        rec = (r.get('email') or '').strip(), (r.get('phone') or '').strip(), (r.get('cui') or '').strip()
        if j and j not in by_j:
            by_j[j] = rec
        nn = norm_name(r.get('name') or '')
        if nn and nn not in by_name:
            by_name[nn] = rec
print(f"master: {len(by_j)} J-keys, {len(by_name)} name-keys, DNC={len(dnc)}", file=sys.stderr)

# --- iscir_ops index for non-compliant overlap ---
ops_j, ops_name = set(), set()
with open(f"{ROOT}/DATA/iscir_ops.csv", encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        j = (r.get('license_no') or '').strip().upper()
        if J_RE.fullmatch(j):
            ops_j.add(j)
        nn = norm_name(r.get('company_name') or '')
        if nn:
            ops_name.add(nn)

# --- parse rsvti rows ---
rows = []
match_j = match_name = 0
with open(f"{ROOT}/DATA/rsvti_pj.csv", encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        pj = r.get('persoana_juridica') or ''
        jm = J_RE.search(pj)
        jnum = jm.group(0) if jm else ''
        cm = CUI_RE.search(pj)
        cui_inline = cm.group(1) if cm else ''
        # name = text before first comma
        name = pj.split(',')[0].strip()
        emails_inline = EMAIL_RE.findall(pj)
        ph = PHONE_RE.search(pj)
        phone_inline = re.sub(r'\s+', '', ph.group(1)) if ph else ''
        exp = parse_date(r.get('data_expirarii'))
        if exp is None:
            status = 'UNKNOWN'
        elif exp >= TODAY:
            status = 'ACTIVE'
        else:
            status = 'EXPIRED'

        # resolve via master
        email = emails_inline[0] if emails_inline else ''
        phone = phone_inline
        cui = ''
        src_key = ''
        rec = by_j.get(jnum.upper()) if jnum else None
        if rec:
            src_key = 'j_number'
            match_j += 1
        else:
            rec = by_name.get(norm_name(name))
            if rec:
                src_key = 'name'
                match_name += 1
        if rec:
            m_email, m_phone, m_cui = rec
            email = email or m_email
            phone = phone or m_phone
            cui = m_cui
        cui = cui_inline or cui

        email = email.strip().lower()
        email_valid = bool(EMAIL_VALID.match(email)) if email else False

        # suppression: permanent only (DNC). NOT on temporal signals.
        supp = 'DNC' if email and email in dnc else ''

        # non-compliant overlap
        in_ops = (jnum.upper() in ops_j) or (norm_name(name) in ops_name)

        rows.append({
            'name': fold(name), 'j_number': jnum, 'cui': cui,
            'county': fold(r.get('it_iscir') or ''), 'email': fold(email),
            'email_valid': email_valid, 'phone': phone,
            'operator_person': fold(r.get('operatori_rsvti') or ''),
            'data_expirarii': r.get('data_expirarii') or '', 'status': status,
            'source_agency': 'ISCIR-RSVTI', 'suppressed_reason': supp,
            '_in_ops': in_ops,
        })

# --- live PG fill by CUI for rows still missing a valid email ---
pg_fill = 0
need = {r['cui'] for r in rows if r['cui'] and not r['email_valid']}
if need:
    try:
        import psycopg2
        conn = psycopg2.connect(host='127.0.0.1', port=5433, dbname='interjob_master',
                                user='tudor', password='tudor', connect_timeout=4)
        cur = conn.cursor()
        cur.execute("""select cui, coalesce(nullif(email,''),enriched_email),
                       coalesce(nullif(phone,''),enriched_phone) from companies_clean
                       where cui = any(%s)""", (list(need),))
        pgmap = {str(c): (e, p) for c, e, p in cur.fetchall()}
        conn.close()
        for r in rows:
            if not r['email_valid'] and r['cui'] in pgmap:
                e, p = pgmap[r['cui']]
                e = (e or '').strip().lower()
                if e:
                    r['email'] = fold(e)
                    r['email_valid'] = bool(EMAIL_VALID.match(e))
                    if r['email_valid']:
                        pg_fill += 1
                    if e in dnc:
                        r['suppressed_reason'] = 'DNC'
                if not r['phone'] and p:
                    r['phone'] = p.strip()
        print(f"PG companies_clean filled {pg_fill} emails by CUI", file=sys.stderr)
    except Exception as e:
        print(f"PG fill skipped: {e}", file=sys.stderr)

# --- write outputs ---
import os
os.makedirs(f"{ROOT}/DATA/leads", exist_ok=True)
os.makedirs(f"{ROOT}/_workspace", exist_ok=True)
SCHEMA = ['name', 'j_number', 'cui', 'county', 'email', 'email_valid', 'phone',
          'operator_person', 'data_expirarii', 'status', 'source_agency', 'suppressed_reason']


def write(path, recs):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=SCHEMA, extrasaction='ignore')
        w.writeheader()
        w.writerows(recs)


active = [r for r in rows if not r['suppressed_reason']]
write(f"{ROOT}/DATA/leads/rsvti_all_leads.csv", rows)
expired = [r for r in active if r['status'] == 'EXPIRED']
expired.sort(key=lambda r: (not r['email_valid'],))
write(f"{ROOT}/DATA/leads/rsvti_expired_segment.csv", expired)
hot = [r for r in expired if r['_in_ops']]
hot.sort(key=lambda r: (not r['email_valid'],))
write(f"{ROOT}/DATA/leads/rsvti_noncompliant_hot.csv", hot)

total = len(rows)
contactable = sum(1 for r in active if r['email_valid'])
n_exp = sum(1 for r in rows if r['status'] == 'EXPIRED')
n_act = sum(1 for r in rows if r['status'] == 'ACTIVE')
n_unk = sum(1 for r in rows if r['status'] == 'UNKNOWN')
n_supp = sum(1 for r in rows if r['suppressed_reason'])
pct = 100*contactable/total if total else 0

summary = f"""# 02 RSVTI Leads Summary

- Total RSVTI PJ rows: {total}
- Contactable by valid email (post-suppression): {contactable} ({pct:.1f}%)
- Status: ACTIVE={n_act}, EXPIRED={n_exp}, UNKNOWN={n_unk}
- Suppressed (DNC permanent only): {n_supp}

## Enrichment source
- Source: master_romania_companies.csv (2.9M ONRC rows, local)
- Match key J-number: {match_j} ; fallback normalized name: {match_name} (master CSV j_number subset = 55k rows, low overlap with RSVTI firms).
- Inline emails parsed from registru text = primary contact source.
- Inline CUI parsed, joined to live PG companies_clean (localhost:5433) by CUI: {pg_fill} additional valid emails filled.

## Non-compliant hot overlap (EXPIRED in iscir_ops equipment registry)
- Expired segment: {len(expired)}
- Non-compliant hot leads (expired AND in iscir_ops): {len(hot)}

## Suppression policy
- DNC entries: {len(dnc)}. Suppressed only on permanent signals (opt-out/bounce/DNC).
- NO suppression on temporal/negative signals (ANAF debt etc).

## Outputs
- DATA/leads/rsvti_all_leads.csv ({total})
- DATA/leads/rsvti_expired_segment.csv ({len(expired)})
- DATA/leads/rsvti_noncompliant_hot.csv ({len(hot)})
"""
open(f"{ROOT}/_workspace/02_leads_summary.md", 'w', encoding='utf-8').write(summary)
print(summary)
