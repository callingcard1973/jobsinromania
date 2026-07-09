#!/usr/bin/env python3
"""EURES employer outreach (ANOFM-style multi-sender, gentle ramp, DB-unique suppression)."""
import os
import re
import sys
import json
import time
import random
import argparse
import unicodedata
from datetime import date
import psycopg2

BASE = '/opt/ACTIVE/EURES'
DB = {'dbname': 'interjob_master', 'user': 'tudor'}
SECTOR_TEMPLATE = {
    'manufacturing': 'manufacturing', 'construction': 'construction',
    'healthcare': 'healthcare', 'hospitality': 'hospitality',
    'transport': 'transport', 'agriculture': 'agriculture',
}

sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED')
try:
    from sender import send_brevo  # noqa: F401
except Exception:
    send_brevo = None


import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def _load_env():
    """Load /opt/ACTIVE/EURES/.env (KEY=VALUE) into os.environ."""
    path = os.path.join(BASE, '.env')
    if not os.path.exists(path):
        return
    for line in open(path, encoding='ascii'):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())


def send_smtp(dom, to_email, subject, body):
    """Send via Brevo SMTP relay using per-domain creds in .env. Returns (ok, status)."""
    key = dom.split('.')[0].upper()
    login = os.environ.get(f"SMTP_{key}_LOGIN")
    passw = os.environ.get(f"SMTP_{key}_PASS")
    sender = os.environ.get(f"SMTP_{key}_FROM", f"office@{dom}")
    if not (login and passw):
        raise RuntimeError(f"missing SMTP creds for {dom}")
    msg = MIMEText(body, 'plain', 'us-ascii')
    msg['Subject'] = subject
    msg['From'] = formataddr(("InterJob.ro Team", sender))
    msg['To'] = to_email
    msg['Reply-To'] = sender
    msg['List-Unsubscribe'] = f"<mailto:{sender}?subject=unsubscribe>, <https://interjob.ro/unsubscribe?e={to_email}>"
    host = os.environ.get('SMTP_HOST', 'smtp-relay.brevo.com')
    port = int(os.environ.get('SMTP_PORT', '587'))
    with smtplib.SMTP(host, port, timeout=30) as srv:
        srv.starttls()
        srv.login(login, passw)
        srv.sendmail(sender, [to_email], msg.as_string())
    return True, 'SMTP_OK'


def log(msg):
    print(f"[{date.today()}] {msg}", flush=True)


def ascii_fold(s):
    if not s:
        return ''
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')


def load_template(name):
    path = os.path.join(BASE, 'templates', f'{name}.txt')
    with open(path, encoding='ascii') as f:
        raw = f.read()
    subject = raw.splitlines()[0].replace('Subject:', '', 1).strip()
    body = raw.split('\n', 1)[1].lstrip('\n')
    return subject, body


def render(text, row):
    out = text
    fallbacks = {'{company}': 'your company', '{country}': 'Europe'}
    jt = row[4] if len(row) > 4 else None
    for tok, val in (('{company}', row[1]), ('{country}', row[2]),
                     ('{sector}', row[3] or 'your sector'), ('{email}', row[0]),
                     ('{job_title}', jt or 'open')):
        rep = ascii_fold(val).strip() if val else ''
        if rep.lower() in ('unknown', 'none', 'n/a', 'null'):
            rep = ''
        out = out.replace(tok, rep or fallbacks.get(tok, ''))
    return out


def ramp_cap(cfg, dom):
    """Current daily cap from ramp_state.json, clamped to [start, max]."""
    state_path = os.path.join(BASE, 'ramp_state.json')
    state = {}
    if os.path.exists(state_path):
        state = json.load(open(state_path))
    cap = state.get(dom, {}).get('cap', cfg['start_daily_cap'])
    return min(cap, cfg['max_daily_cap'])


def main():
    ap = argparse.ArgumentParser(description='EURES employer outreach')
    ap.add_argument('--dry-run', action='store_true', help='Print what would send; claim/send nothing')
    # Accepted for campaign-orchestrator compatibility (per-sender caps live in senders.json).
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--delay', type=int, default=None)
    ap.add_argument('--daily-cap', dest='daily_cap', type=int, default=None)
    args = ap.parse_args()
    # Refresh the audience first so everything runs from one entrypoint (no separate timer).
    if not args.dry_run:
        try:
            subprocess.run(['python3', os.path.join(BASE, 'build_audience.py')],
                           env={**os.environ, 'PGHOST': 'localhost'}, timeout=600)
        except Exception as e:
            log(f'build_audience failed (continuing): {e}')

    _load_env()
    senders = json.load(open(os.path.join(BASE, 'senders.json')))
    active = {d: c for d, c in senders.items() if c.get('enabled')}
    if not active:
        log("all senders disabled - nothing to do")
        return 0

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    total_sent = 0
    for dom, cfg in active.items():
        cur.execute("SELECT count(*) FROM eures_send_log WHERE sender_domain=%s AND sent_at::date=current_date", (dom,))
        sent_today = cur.fetchone()[0]
        cap = ramp_cap(cfg, dom)
        remaining = max(0, cap - sent_today)
        if remaining == 0:
            log(f"{dom}: cap {cap} reached ({sent_today})")
            continue
        cur.execute(
            "SELECT a.email,a.company,a.country,a.sector,a.job_title FROM eures_audience_sendable a "
            "LEFT JOIN eures_send_log s ON s.email=a.email "
            "WHERE a.sender_domain=%s AND s.email IS NULL ORDER BY random() LIMIT %s", (dom, remaining))
        queue = cur.fetchall()
        tmpl = 'generic'  # single general template for all (user choice 2026-06-26)
        subject_t, body_t = load_template(tmpl)
        log(f"{dom}: cap={cap} sent_today={sent_today} queue={len(queue)} template={tmpl}")

        for row in queue:
            email = row[0]
            if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
                continue
            subj, body = render(subject_t, row), render(body_t, row)
            if args.dry_run:
                log(f"  DRYRUN -> {email} | {subj[:60]}")
                continue
            # claim atomically; skip if another run already took it
            cur.execute("INSERT INTO eures_send_log (email,company,country,sector,sender_domain,status) "
                        "VALUES (%s,%s,%s,%s,%s,'claimed') ON CONFLICT (email) DO NOTHING", row[:4] + (dom,))
            if cur.rowcount == 0:
                continue
            conn.commit()
            if cfg.get('provider') == 'smtp':
                send_smtp(dom, email, subj, body)
            else:
                if send_brevo is None:
                    raise NotImplementedError("sender.send_brevo unavailable")
                key = os.environ.get(f"BREVO_{dom.split('.')[0].upper()}_API_KEY")
                send_brevo(key, f"office@{dom}", "InterJob.ro Team", email, subj, body)
            cur.execute("UPDATE eures_send_log SET status='sent' WHERE email=%s", (email,))
            conn.commit()
            total_sent += 1
            time.sleep(random.uniform(cfg['min_delay_sec'], cfg['max_delay_sec']))

    log(f"done: total_sent={total_sent}")
    cur.close()
    conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
