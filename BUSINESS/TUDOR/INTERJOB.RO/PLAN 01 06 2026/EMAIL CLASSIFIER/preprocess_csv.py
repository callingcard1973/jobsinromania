#!/usr/bin/env python3
"""Cur─â╚ø─â CSV campanie ├«nainte de import: format, rol, DNC, domenii blacklist, dedup."""
import csv, re, sys, argparse, psycopg2
from pathlib import Path
from io import StringIO

sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED')
try:
    from email_validator import is_valid_email
except ImportError:
    def is_valid_email(e):
        return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', e)), 'ok'

ROLE_PREFIXES = {
    'info', 'contact', 'office', 'admin', 'noreply', 'no-reply', 'support',
    'hr', 'jobs', 'careers', 'help', 'sales', 'marketing', 'newsletter',
    'webmaster', 'postmaster', 'abuse', 'legal', 'press', 'media',
}

BAD_TLDS = {'.xyz', '.top', '.click', '.loan', '.work', '.date', '.review', '.win', '.bid'}

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def is_role_email(email):
    local = email.split('@')[0].lower().rstrip('0123456789')
    return local in ROLE_PREFIXES


def has_bad_tld(email):
    domain = email.split('@')[-1].lower()
    return any(domain.endswith(t) for t in BAD_TLDS)


def load_dnc(conn):
    with conn.cursor() as cur:
        cur.execute('SELECT lower(email) FROM dnc_list')
        return {r[0] for r in cur.fetchall()}


def get_email_col(header):
    for i, h in enumerate(header):
        if 'email' in h.lower():
            return i
    return 1


def process(path, dry_run=False):
    p = Path(path)
    rows = list(csv.reader(p.read_text(encoding='utf-8', errors='replace').splitlines()))
    if not rows:
        print('CSV gol')
        return

    header = rows[0]
    data = rows[1:]
    col = get_email_col(header)

    try:
        conn = psycopg2.connect(host='localhost', dbname='interjob_master', user='tudor')
        dnc = load_dnc(conn)
        conn.close()
    except Exception:
        dnc = set()
        print('WARN: nu am putut conecta la DB ÔÇö DNC check s─ârit')

    kept, removed = [], {'format': 0, 'role': 0, 'bad_tld': 0, 'dnc': 0, 'dup': 0}
    seen = set()

    for row in data:
        if not row:
            continue
        raw = row[col].strip() if len(row) > col else ''
        email = raw.lower().replace('%20', '').replace(' ', '')

        if not _EMAIL_RE.match(email):
            removed['format'] += 1
            continue
        if is_role_email(email):
            removed['role'] += 1
            continue
        if has_bad_tld(email):
            removed['bad_tld'] += 1
            continue
        if email in dnc:
            removed['dnc'] += 1
            continue
        if email in seen:
            removed['dup'] += 1
            continue

        seen.add(email)
        row[col] = email  # normalizat
        kept.append(row)

    total_removed = sum(removed.values())
    print(f'Input: {len(data)} | Kept: {len(kept)} | Removed: {total_removed}')
    for reason, count in removed.items():
        if count:
            print(f'  -{count} {reason}')

    if not dry_run and total_removed > 0:
        bak = p.with_suffix('.csv.bak')
        tmp = p.with_suffix('.csv.tmp')
        out = StringIO()
        w = csv.writer(out)
        w.writerow(header)
        w.writerows(kept)
        tmp.write_text(out.getvalue(), encoding='utf-8')
        if bak.exists():
            bak.unlink()
        p.rename(bak)
        tmp.rename(p)
        print(f'Salvat: {p.name}  (backup: {p.stem}.csv.bak)')
    elif dry_run:
        print('[dry-run] nicio modificare f─âcut─â')


def main():
    ap = argparse.ArgumentParser(description='Preprocess CSV campanie anti-spam')
    ap.add_argument('csv', help='Calea c─âtre CSV')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    process(args.csv, args.dry_run)


if __name__ == '__main__':
    main()

