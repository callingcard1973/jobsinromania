#!/usr/bin/env python3
"""Enhanced bounce processor: classify + DNS check + auto-action on CSVs."""
import csv, re, socket, sys, logging, psycopg2, urllib.request, urllib.error
from pathlib import Path
from io import StringIO

sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED')
from dnc_utils import add_to_dnc

log = logging.getLogger(__name__)
_REDIRECT_CACHE: dict = {}

CAMPAIGN_CSVS = [
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/PRIMARII/DATA/primarii_campanie_clean.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_RO/DATA/factory_ro_master.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/SME_DEFICIT/DATA/sme_deficit_master.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/DEFICIT_OCUPATII/DATA/constructii.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/DEFICIT_OCUPATII/DATA/horeca.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/DEFICIT_OCUPATII/DATA/productie.csv',
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/DEFICIT_OCUPATII/DATA/transport.csv',
]

_PERMANENT_RE = re.compile(
    r'550\s+5\.1\.[12]|user\s+unknown|no\s+such\s+user|'
    r'recipient\s+(address\s+)?rejected|mailbox\s+(not\s+found|does\s+not\s+exist)|'
    r'address.*rejected|invalid\s+(recipient|address)|does\s+not\s+exist', re.I)
_DNS_RE = re.compile(
    r'550\s+5\.4\.4|host\s+not\s+found|domain\s+not\s+found|'
    r'name\s+(or\s+service\s+not\s+known|lookup\s+failed)|'
    r'nxdomain|unresolvable\s+address|cannot\s+find.*mx', re.I)
_FULL_RE = re.compile(
    r'452|mailbox\s+full|quota\s+exceeded|over\s+quota|'
    r'out\s+of\s+storage|inbox\s+full|storage\s+limit', re.I)
_BLOCKED_RE = re.compile(
    r'550\s+5\.7\.[01]|policy\s+reject|access\s+denied|'
    r'spam\s+(blocked|detected)|blacklist|spamhaus|barracuda|'
    r'421\s+4\.7\.|sender\s+blocked', re.I)


def extract_smtp_code(body):
    m = re.search(r'\b([45]\d{2})\b', body)
    return m.group(1) if m else None


def classify_body(body):
    if _DNS_RE.search(body): return 'domain_dead'
    if _PERMANENT_RE.search(body): return 'permanent'
    if _FULL_RE.search(body): return 'mailbox_full'
    if _BLOCKED_RE.search(body): return 'blocked'
    code = extract_smtp_code(body)
    if code and code.startswith('4'): return 'temporary'
    if code and code.startswith('5'): return 'permanent'
    return 'unknown'


def _is_private_domain(domain):
    """Guard against SSRF ├ö├ç├Â reject domains that resolve to private IPs."""
    try:
        ip = socket.gethostbyname(domain)
        import ipaddress
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return True  # fail closed


def dns_check(domain):
    """True if domain has a public A record."""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(5)
        socket.getaddrinfo(domain, None)
        return True
    except (socket.gaierror, socket.timeout):
        return False
    finally:
        socket.setdefaulttimeout(old_timeout)


def http_redirect_check(domain):
    """Return (redirects_elsewhere: bool, redirect_domain: str). Cached per domain."""
    if domain in _REDIRECT_CACHE:
        return _REDIRECT_CACHE[domain]
    if _is_private_domain(domain):
        _REDIRECT_CACHE[domain] = (False, '')
        return False, ''
    try:
        req = urllib.request.Request(
            f'http://{domain}/', method='HEAD',
            headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=5)
        final = resp.url or ''
    except urllib.error.HTTPError as e:
        final = e.url or ''
    except Exception:
        _REDIRECT_CACHE[domain] = (False, '')
        return False, ''
    m = re.search(r'https?://([^/]+)', final)
    final_domain = m.group(1).lower().removeprefix('www.') if m else ''
    orig = domain.lower().removeprefix('www.')
    result = bool(final_domain and final_domain != orig), final_domain
    _REDIRECT_CACHE[domain] = result
    return result


def _remove_rows_from_csv(p, predicate, label):
    raw = p.read_text(encoding='utf-8', errors='replace')
    rows = list(csv.reader(raw.splitlines()))
    if not rows: return 0
    header = rows[0]
    email_col = next((i for i, h in enumerate(header) if 'email' in h.lower()), 1)
    kept, removed = [header], 0
    for row in rows[1:]:
        if not row: continue
        cell = row[email_col].strip().lower() if len(row) > email_col else ''
        if predicate(cell):
            removed += 1
        else:
            kept.append(row)
    if removed:
        bak = p.with_suffix('.csv.bak')
        tmp = p.with_suffix('.csv.tmp')
        out = StringIO()
        csv.writer(out).writerows(kept)
        tmp.write_text(out.getvalue(), encoding='utf-8')
        if bak.exists():
            bak.unlink()
        p.rename(bak)
        tmp.rename(p)
        log.info(f'  CSV {p.name}: -{removed} rows [{label}]')
    return removed


def remove_from_csvs(emails):
    emails_lower = {e.lower() for e in emails}
    total = 0
    for path in CAMPAIGN_CSVS:
        p = Path(path)
        if p.exists():
            total += _remove_rows_from_csv(p, lambda c, s=emails_lower: c in s, 'permanent')
    return total


def remove_domain_from_csvs(domain):
    domain = domain.lower()
    suffix = '@' + domain
    total = 0
    for path in CAMPAIGN_CSVS:
        p = Path(path)
        if p.exists():
            total += _remove_rows_from_csv(
                p, lambda c, sfx=suffix: c.endswith(sfx), f'domain_dead:{domain}')
    return total


def _ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bounce_actions (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                category TEXT,
                smtp_code TEXT,
                action TEXT,
                csv_removed INT DEFAULT 0,
                processed_at TIMESTAMPTZ DEFAULT NOW()
            )""")
    conn.commit()


def log_action(email, category, smtp_code, action, csv_removed, conn=None):
    if conn is None:
        try:
            conn = psycopg2.connect(host='localhost', dbname='interjob_master', user='tudor')
            _ensure_table(conn)
            own_conn = True
        except Exception as e:
            log.warning(f'bounce_actions connect: {e}')
            return
    else:
        own_conn = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO bounce_actions (email,category,smtp_code,action,csv_removed) '
                'VALUES (%s,%s,%s,%s,%s)',
                (email, category, smtp_code, action, csv_removed))
        conn.commit()
    except Exception as e:
        log.warning(f'bounce_actions insert: {e}')
    finally:
        if own_conn:
            conn.close()


def process_bounce(bounced_email, body, dry_run=False, _conn=None):
    """Classify bounce + DNS check + take action. Returns result dict."""
    bounced_email = bounced_email.lower().strip()
    domain = bounced_email.split('@')[-1] if '@' in bounced_email else ''
    smtp_code = extract_smtp_code(body)
    category = classify_body(body)

    redirect_to = ''
    # DNS fallback for ambiguous cases
    if category in ('unknown', 'permanent') and domain:
        if not dns_check(domain):
            category = 'domain_dead'
        else:
            redirects, redirect_to = http_redirect_check(domain)
            if redirects:
                category = 'domain_redirect'
                log.warning(f'DOMAIN REDIRECT: {domain} ├ö├Ñ├å {redirect_to}')

    action = 'none'
    csv_removed = 0

    if not dry_run:
        if category in ('domain_dead', 'domain_redirect'):
            action = 'remove_domain'
            csv_removed = remove_domain_from_csvs(domain)
            src = f'redirect:{redirect_to}' if category == 'domain_redirect' else f'smtp:{smtp_code or "?"}'
            add_to_dnc(bounced_email, reason='bounce_domain_dead', source=src)
            log.warning(f'DOMAIN {category.upper()}: {domain} ├ö├ç├Â removed {csv_removed} rows')


        elif category == 'permanent':
            action = 'remove_address'
            csv_removed = remove_from_csvs({bounced_email})
            add_to_dnc(bounced_email, reason='bounce_permanent',
                       source=f'smtp:{smtp_code or "?"}')

        elif category == 'blocked':
            action = 'dnc_30d'
            add_to_dnc(bounced_email, reason='bounce_blocked',
                       source=f'smtp:{smtp_code or "?"}')

        elif category == 'mailbox_full':
            action = 'retry_14d'

        else:
            action = 'retry'

        log_action(bounced_email, category, smtp_code, action, csv_removed, conn=_conn)
    else:
        action = {
            'domain_dead': 'remove_domain', 'domain_redirect': 'remove_domain',
            'permanent': 'remove_address', 'blocked': 'dnc_30d', 'mailbox_full': 'retry_14d'
        }.get(category, 'retry')

    result = {
        'email': bounced_email, 'domain': domain, 'smtp_code': smtp_code,
        'category': category, 'action': action, 'csv_removed': csv_removed,
    }
    log.info(
        f'BOUNCE {bounced_email} | {category} | smtp:{smtp_code} | '
        f'action:{action} | removed:{csv_removed}')
    return result




def process_bounce_batch(entries, dry_run=False):
    """Process a list of (email, body) tuples sharing one DB connection."""
    conn = None
    if not dry_run:
        try:
            conn = psycopg2.connect(host='localhost', dbname='interjob_master', user='tudor')
            _ensure_table(conn)
        except Exception as e:
            log.warning(f'Batch connect failed: {e}')
    results = []
    try:
        for email, body in entries:
            r = process_bounce(email, body, dry_run, _conn=conn)
            results.append(r)
        if conn:
            conn.commit()
    finally:
        if conn:
            conn.close()
    return results


if __name__ == '__main__':
    import argparse, json
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    ap = argparse.ArgumentParser(description='Enhanced bounce processor')
    ap.add_argument('--email', help='Bounced email address')
    ap.add_argument('--body', help='Bounce notification body text')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--stats', action='store_true', help='Show bounce_actions table stats')
    ap.add_argument('--batch-file', type=str, help='JSONL file with {\"email\":...,\"body\":...} lines')
    args = ap.parse_args()

    if args.stats:
        conn = psycopg2.connect(host='localhost', dbname='interjob_master', user='tudor')
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("""SELECT category, action, COUNT(*), COALESCE(SUM(csv_removed),0)
                          FROM bounce_actions GROUP BY category, action ORDER BY COUNT(*) DESC""")
            print(f'{"Category":<15} {"Action":<15} {"Count":>6} {"CSV removed":>12}')
            print('-' * 52)
            for cat, act, cnt, rem in cur.fetchall():
                print(f'{cat:<15} {act:<15} {cnt:>6} {rem:>12}')
        conn.close()
    elif args.batch_file:
        entries = []
        with open(args.batch_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    entries.append((rec['email'], rec.get('body', '')))
        results = process_bounce_batch(entries, dry_run=args.dry_run)
        print(json.dumps(results, indent=2))
    elif args.email:
        result = process_bounce(args.email, args.body or '', args.dry_run)
        print(json.dumps(result, indent=2))
    else:
        ap.print_help()

