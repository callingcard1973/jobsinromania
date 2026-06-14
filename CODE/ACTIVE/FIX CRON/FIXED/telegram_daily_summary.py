#!/usr/bin/env python3
"""Daily Telegram summary — emails primite + actiuni necesare. Cron 0 18 * * *."""
import psycopg2, sys, re
from datetime import date
sys.path.insert(0, "/opt/ACTIVE/INFRA/SKILLS")
from email_pipeline_db import send_telegram, DB_CFG as DB
import os, smtplib, ssl
from email.mime.text import MIMEText
import time
import csv as _csv
from pathlib import Path

SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = os.environ.get('SUMMARY_SMTP_USER', 'manpower.dristor@gmail.com')
SMTP_PASS = os.environ.get('SUMMARY_SMTP_PASS')
SUMMARY_TO = os.environ.get('SUMMARY_TO', 'manpowerdristor@gmail.com')

def send_email_summary(subject, body_markdown):
    body = re.sub(r'\*([^*]+)\*', r'', body_markdown)
    body = body.replace('_', '')
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = f'InterJob Daily <{SMTP_USER}>'
        msg['To'] = SUMMARY_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f'email send fail: {e}'); return False


def safe(cur, sql, args=()):
    try:
        cur.execute(sql, args); return cur.fetchall()
    except Exception:
        cur.connection.rollback(); return []

def main():
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    today = date.today()

    cur.execute("""SELECT COALESCE(SUM(orders),0), COALESCE(SUM(applicants),0),
        COALESCE(SUM(contacts),0), COALESCE(SUM(dnc),0), COALESCE(SUM(skipped),0)
        FROM pipeline_metrics WHERE run_date=%s""", (today,))
    o, a, c, d, sk = cur.fetchone()

    try:
        rows = list(_csv.DictReader(Path("/opt/ACTIVE/EMAIL/ORDERS/orders.csv").open(encoding="utf-8")))
        today_str = today.strftime("%d/%m/%Y")
        today_orders = [r for r in rows if r.get("Timestamp","").startswith(today_str)]
        comenzi = [r for r in today_orders if r.get("Clasificare")=="COMANDA"]
        interesati = [r for r in today_orders if r.get("Clasificare")=="INTERESAT"]
        parteneri = [r for r in today_orders if r.get("Clasificare")=="PARTENER"]
    except Exception:
        today_orders = []; comenzi = []; interesati = []; parteneri = []

    pcq = safe(cur, "SELECT COUNT(*) FROM phone_callback_queue WHERE called_at IS NULL")
    pcq_n = pcq[0][0] if pcq else 0
    pcq_top = safe(cur, """SELECT phone, company, source_campaign FROM phone_callback_queue
        WHERE called_at IS NULL ORDER BY priority DESC, added_at LIMIT 5""")

    fu_today = safe(cur, "SELECT COUNT(*) FROM pipeline_followup_queue WHERE sent_at::date=%s", (today,))
    fu_pending = safe(cur, "SELECT COUNT(*) FROM pipeline_followup_queue WHERE sent_at IS NULL AND scheduled_for <= NOW() + INTERVAL '1 day'")
    fu_t = fu_today[0][0] if fu_today else 0
    fu_p = fu_pending[0][0] if fu_pending else 0

    li = safe(cur, "SELECT COUNT(*) FROM linkedin_outreach_queue WHERE exported_at IS NULL")
    li_n = li[0][0] if li else 0

    cv_inbox = Path("/opt/ACTIVE/FARMWORKERS/CV_INBOX")
    cutoff = time.time() - 86400
    cvs_today = sum(1 for p in cv_inbox.rglob("*") if p.is_file() and p.stat().st_mtime > cutoff) if cv_inbox.exists() else 0

    br = safe(cur, "SELECT COUNT(*) FROM bounce_rate_check WHERE run_date=%s AND paused", (today,))
    paused_senders = br[0][0] if br else 0

    sent = safe(cur, "SELECT COUNT(*) FROM send_log WHERE sent_at::date=%s", (today,))
    sent_n = sent[0][0] if sent else 0

    actiuni = []
    if comenzi: actiuni.append(f"{len(comenzi)} COMENZI noi - de raspuns")
    if interesati: actiuni.append(f"{len(interesati)} INTERESATI - schedule follow-up")
    if parteneri: actiuni.append(f"{len(parteneri)} PARTENERI - evalueaza colaborare")
    if pcq_n > 0: actiuni.append(f"{pcq_n} telefoane de sunat")
    if fu_p > 0: actiuni.append(f"{fu_p} follow-ups scheduled maine")
    if li_n > 0: actiuni.append(f"{li_n} contacte LinkedIn de procesat")
    if cvs_today > 0: actiuni.append(f"{cvs_today} CV noi - review needed")
    if paused_senders > 0: actiuni.append(f"{paused_senders} senderi auto-pausati (bounce >5%)")

    msg = f"*InterJob Daily {today}*\n"

    if actiuni:
        msg += "\n*ACTIUNI NECESARE:*\n" + "\n".join(f"  - {a}" for a in actiuni) + "\n"
    else:
        msg += "\n_Nimic urgent astazi._\n"

    msg += f"\n*Emailuri primite azi ({len(today_orders) + a + sk} total):*\n"
    msg += f"  COMENZI: {len(comenzi)} | INTERESATI: {len(interesati)} | PARTENERI: {len(parteneri)}\n"
    msg += f"  Applicants: {a} | Skipped: {sk} | Bounce/DNC: {d}\n"

    msg += f"\n*Outbound:*\n"
    msg += f"  Trimise azi: {sent_n} | Follow-ups trimise: {fu_t}\n"

    if comenzi:
        msg += f"\n*COMENZI azi:*\n"
        for r in comenzi[:3]:
            co = (r.get("Denumire companie") or "?")[:30]
            ws = r.get("Număr persoane") or "?"
            pos = (r.get("Tip poziții") or "?")[:50]
            msg += f"  - {co} | {ws} pax | {pos}\n"

    if pcq_top:
        msg += f"\n*Top telefoane:*\n"
        for ph, co, camp in pcq_top[:5]:
            msg += f"  - {ph} ({(co or '?')[:25]})\n"

    msg += f"\n_Detalii: http://192.168.100.21:8096_"

    conn.close()
    send_telegram(msg)
    send_email_summary(f"InterJob Daily {today}", msg)
    print(msg)

if __name__ == "__main__": main()
