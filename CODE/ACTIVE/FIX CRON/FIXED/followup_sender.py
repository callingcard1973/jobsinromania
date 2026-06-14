#!/usr/bin/env python3
"""Process pipeline_followup_queue: send reminder emails to INTERESATI without recent reply.
Cron: 0 10 * * * python3 /opt/ACTIVE/INFRA/SKILLS/followup_sender.py
"""
import psycopg2, os, smtplib, ssl, sys
from email.mime.text import MIMEText
from datetime import datetime
sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED")
try:
    from send_utils import gdpr_footer_ro
except Exception:
    def gdpr_footer_ro(email, campaign="default"):
        return ""

DB = dict(host=os.environ.get("PGHOST","localhost"),
    dbname=os.environ.get("PGDATABASE","interjob_master"),
    user=os.environ.get("PGUSER","tudor"),
    password=os.environ.get("PGPASSWORD","REDACTED"))
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("FOLLOWUP_SMTP_USER", "manpower.dristor@gmail.com")
SMTP_PASS = os.environ.get("FOLLOWUP_SMTP_PASS")
FROM_NAME = "InterJob"

BODY_RO = """Buna ziua,

Va contactam pentru a continua discutia despre disponibilitatea muncitorilor pentru pozitiile mentionate.

Ne puteti spune daca mai aveti nevoie de personal sau daca discutia ramane deschisa?

Cu stima,
Echipa InterJob
office@interjob.ro
https://interjob.ro
"""

def main(dry=False):
    conn = psycopg2.connect(**DB)
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, email, classification, original_campaign FROM pipeline_followup_queue
                       WHERE sent_at IS NULL AND scheduled_for <= NOW()
                       ORDER BY scheduled_for LIMIT 50
                       FOR UPDATE SKIP LOCKED""")
        queue = cur.fetchall()
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] Follow-ups pending: {len(queue)}")
        if not queue:
            conn.commit(); return
        ctx = ssl.create_default_context()
        sent = 0
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls(context=ctx)
            s.login(SMTP_USER, SMTP_PASS)
            for fid, em, cls, camp in queue:
                try:
                    body = BODY_RO + gdpr_footer_ro(em, campaign=camp or "followup")
                    msg = MIMEText(body, "plain", "utf-8")
                    msg["Subject"] = "Continuare discutie - InterJob"
                    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
                    msg["To"] = em
                    msg["Reply-To"] = SMTP_USER
                    if not dry:
                        s.send_message(msg)
                        cur.execute("UPDATE pipeline_followup_queue SET sent_at=NOW() WHERE id=%s", (fid,))
                        conn.commit()
                    sent += 1
                    print(f"  -> {"[DRY]" if dry else "SENT"} {em} ({cls})")
                except Exception as e:
                    conn.rollback()
                    print(f"  FAIL {em}: {e}")
        print(f"Done: {sent}/{len(queue)} sent")
    finally:
        conn.close()

if __name__ == "__main__":
    main(dry="--dry-run" in sys.argv)
