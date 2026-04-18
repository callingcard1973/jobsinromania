"""Step 45: Auto-send followup emails to warm leads with no reply after 7 days.
Reads warm_leads_followup.csv, checks if already followed up, sends via Brevo.
"""
import csv
import os
import json
import requests
import psycopg2
from datetime import datetime, timedelta

BREVO_KEY = os.environ.get('BREVO_API_KEY', '')
DB = dict(host='127.0.0.1', port=5433, dbname='interjob_master', user='tudor', password='tudor')
CSV_PATH = '/d/MEMORY/EMAIL PERSONAL/DATA/warm_leads_followup.csv'
DAILY_LIMIT = 50
FROM_EMAIL = 'office@interjob.ro'
FROM_NAME = 'Tudor - InterJob'
REPLY_TO = 'manpower.dristor@gmail.com'

FOLLOWUP_TEMPLATE = """Subject: Following up - worker placement for {name}

Dear {first_name},

I wanted to follow up on my previous message regarding worker placement services.

We have qualified candidates ready for {sector} roles — available to start within 2-4 weeks.

Would you have 10 minutes this week for a quick call?

Best regards,
Tudor
InterJob European Recruitment
www.interjob.ro | +40 ...
"""

def send_email(to_email, to_name, subject, body):
    if not BREVO_KEY:
        print(f"  [DRY RUN] Would send to {to_email}")
        return True
    payload = {
        "sender": {"email": FROM_EMAIL, "name": FROM_NAME},
        "to": [{"email": to_email, "name": to_name}],
        "replyTo": {"email": REPLY_TO},
        "subject": subject,
        "textContent": body
    }
    r = requests.post('https://api.brevo.com/v3/smtp/email',
                      headers={'api-key': BREVO_KEY, 'Content-Type': 'application/json'},
                      json=payload, timeout=10)
    return r.status_code in (200, 201)

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # Create followup log table if needed
    cur.execute("""
        CREATE TABLE IF NOT EXISTS followup_log (
            email text PRIMARY KEY,
            sent_at timestamp DEFAULT now(),
            campaign text
        )
    """)
    conn.commit()

    if not os.path.exists(CSV_PATH):
        print(f"No file: {CSV_PATH}")
        return

    sent = 0
    cutoff = datetime.now() - timedelta(days=7)

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if sent >= DAILY_LIMIT:
                break

            email = row.get('email', '').strip()
            if not email:
                continue

            # Check already followed up
            cur.execute("SELECT 1 FROM followup_log WHERE email=%s", (email,))
            if cur.fetchone():
                continue

            # Parse responded_at
            responded_str = row.get('responded_at', '')
            try:
                responded_at = datetime.fromisoformat(responded_str[:19])
                if responded_at > cutoff:
                    continue  # too recent
            except Exception:
                continue

            name = row.get('sender_email', email).split('@')[0].title()
            first_name = name.split('.')[0] if '.' in name else name
            sector = row.get('sector', 'your sector')

            subject = f"Following up - worker placement for {name}"
            body = FOLLOWUP_TEMPLATE.format(
                name=name, first_name=first_name, sector=sector
            )

            if send_email(email, name, subject, body):
                cur.execute("INSERT INTO followup_log(email, campaign) VALUES(%s,'warm_followup') ON CONFLICT DO NOTHING",
                            (email,))
                conn.commit()
                sent += 1
                print(f"  Sent followup -> {email}")

    print(f"\nFollowup: {sent} emails sent today.")
    cur.close()
    conn.close()

main()
