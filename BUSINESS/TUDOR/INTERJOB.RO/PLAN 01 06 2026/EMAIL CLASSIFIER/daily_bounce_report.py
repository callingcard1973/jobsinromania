#!/usr/bin/env python3
"""Daily bounce digest sent to fruitnature4@gmail.com."""
import os, smtplib, psycopg2, sys
from datetime import date, timedelta
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/.env')


def main(dry_run=False):
    today = date.today()

    conn = psycopg2.connect(host='localhost', dbname='interjob_master', user='tudor')
    with conn.cursor() as cur:
        cur.execute("""
            SELECT reason, COUNT(*), LEFT(STRING_AGG(email, ', ' ORDER BY email), 1000)
            FROM dnc_list WHERE added_at::date = %s
            GROUP BY reason ORDER BY COUNT(*) DESC
        """, (today,))
        dnc_rows = cur.fetchall()
        cur.execute('SELECT COUNT(*) FROM dnc_list')
        total_dnc = cur.fetchone()[0]
        try:
            cur.execute("""
                SELECT category, action, COUNT(*), COALESCE(SUM(csv_removed),0),
                       LEFT(STRING_AGG(email, ', ' ORDER BY email), 1000)
                FROM bounce_actions WHERE processed_at::date = %s
                GROUP BY category, action ORDER BY COUNT(*) DESC
            """, (today,))
            action_rows = cur.fetchall()
        except Exception:
            action_rows = []
    conn.close()

    if not dnc_rows and not action_rows:
        print('No bounce activity today ├ö├ç├Â skipping report')
        return

    new_today = sum(r[1] for r in dnc_rows)
    csv_total = sum(r[3] for r in action_rows)

    lines = [
        f'=== Bounce Report {today} ===',
        f'Total DNC: {total_dnc} | New today: {new_today} | CSV rows removed: {csv_total}',
        '',
    ]

    if action_rows:
        lines.append('--- Bounce Actions (by category) ---')
        for cat, act, cnt, removed, emails in action_rows:
            lines.append(f'{cat:<15} -> {act:<15} x{cnt}  csv_removed:{removed}')
            for e in (emails or '').split(', ')[:3]:
                lines.append(f'  {e}')
            if cnt > 3:
                lines.append(f'  ... +{cnt - 3} more')
        lines.append('')

    if dnc_rows:
        lines.append('--- DNC entries by reason ---')
        for reason, count, emails in dnc_rows:
            lines.append(f'{reason}: {count}')
            for e in (emails or '').split(', ')[:3]:
                lines.append(f'  - {e}')
            if count > 3:
                lines.append(f'  ... +{count - 3} more')

    body = '\n'.join(lines)

    pw = os.environ.get('GMAIL_SEARCH_PASSWORD', '').replace(' ', '')
    if not pw:
        print('No GMAIL_SEARCH_PASSWORD')
        return

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = 'fruitnature4@gmail.com'
    msg['To'] = 'fruitnature4@gmail.com'
    msg['Subject'] = f'Bounce Report {today} ├ö├ç├Â {new_today} new, {csv_total} CSV removed'
    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as s:
        s.starttls()
        s.login('fruitnature4@gmail.com', pw)
        s.send_message(msg)
    print(f'Report sent: {new_today} DNC, {csv_total} CSV removed')


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    main(dry_run=dry_run)

