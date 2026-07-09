import sys
#!/usr/bin/env python3
"""Campanie DEFICIT_OCUPATII - transport (Brevo API). Sender: office@careworkers.eu"""
import csv, json, logging, os, time
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED')
import sender
try:
    from dnc_utils import add_to_dnc as _add_to_dnc
except ImportError:
    _add_to_dnc = None
from datetime import date
from pathlib import Path

BASE         = Path(__file__).parent.parent
CSV_FILE     = BASE / 'DATA/transport.csv'
SENT_FILE    = BASE / 'DATA/sent_transport.json'
LOG_FILE     = BASE / 'LOGS/transport.log'
SENDER       = 'office@careworkers.eu'
SENDER_NAME  = 'InterJob - CareWorkers.eu'
BREVO_KEY    = os.environ.get('BREVO_CAREWORKERS_API_KEY', 'REDACTED')
DAILY_CAP    = 50
DELAY_S      = 480

TEMPLATE_FILE = Path(__file__).parent.parent / "TEMPLATES/template_transport.txt"
_lines = TEMPLATE_FILE.read_text(encoding="utf-8").splitlines()
SUBJECT = _lines[0].split(":", 1)[1].strip()
BODY    = "\n".join(_lines[2:])

def send_brevo(to_email, subject, body):
    ok, status = sender.send_brevo(BREVO_KEY, SENDER, SENDER_NAME, to_email, subject, body)
    if not ok:
        raise RuntimeError(status)
    return ok


def load_sent():
    return json.loads(SENT_FILE.read_text()) if SENT_FILE.exists() else {'total':0,'by_date':{},'emails':[]}


def save_sent(s):
    SENT_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))


def load_dnc():
    dnc = set()
    try:
        import psycopg2
        conn = psycopg2.connect(host='localhost', dbname='interjob_master', user='tudor')
        with conn.cursor() as cur:
            for t in ['dnc_list', 'master_dnc', 'dnc_global']:
                try:
                    cur.execute(f'SELECT email FROM {t} WHERE email IS NOT NULL')
                    dnc.update(r[0].lower().strip() for r in cur.fetchall())
                except Exception:
                    pass
        conn.close()
    except Exception as e:
        logging.warning(f'DNC load: {e}')
    return dnc


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int, default=DAILY_CAP)
    ap.add_argument('--delay', type=int, default=DELAY_S)
    ap.add_argument('--daily-cap', type=int, default=DAILY_CAP)
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()],
    )
    log = logging.getLogger(__name__)

    rows     = list(csv.DictReader(open(CSV_FILE, encoding='utf-8')))
    sent     = load_sent()
    dnc      = load_dnc()
    today    = str(date.today())
    sent_all = {e.lower() for e in sent['emails']} | dnc
    already  = len(sent['by_date'].get(today, []))
    eff_lim  = max(0, min(args.limit, args.daily_cap - already))
    log.info(f'sector=transport rows={len(rows)} already_today={already} eff_limit={eff_lim} dnc={len(dnc)}')

    sent_run = consec_fail = 0
    for row in rows:
        if sent_run >= eff_lim:
            break
        email = (row.get('email') or '').strip()
        if not email or email.lower() in sent_all:
            continue
        body_msg = BODY.format(greeting='Buna ziua,')
        if args.dry_run:
            log.info(f'[DRY-RUN] -> {email}')
            sent_run += 1
            continue
        try:
            ok = send_brevo(email, SUBJECT, body_msg)
            if not ok:
                raise RuntimeError("send failed")
            log.info(f"SENT {email}")
            sent_run += 1
            consec_fail = 0
            sent_all.add(email.lower())
            sent["emails"].append(email)
            sent["by_date"].setdefault(today, []).append(email)
            sent["total"] += 1
            save_sent(sent)
            if sent_run < eff_lim:
                time.sleep(args.delay)
        except Exception as e:
            err_str = str(e)
            log.error(f"FAIL {email} - {err_str}")
            if 'invalid' in err_str.lower() and ('400' in err_str or '422' in err_str) and _add_to_dnc:
                _add_to_dnc(email, reason='bounce_brevo_invalid', source='brevo_send')
            consec_fail += 1
            if consec_fail >= 5:
                log.error("5 fail consecutive - stop")
                break

    log.info(f'DONE run={sent_run} total={sent["total"]}')


if __name__ == '__main__':
    main()
