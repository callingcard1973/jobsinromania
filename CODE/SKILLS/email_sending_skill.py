
# EMAIL SAFETY CHECK - Added by safeguards
import sys
import os
sys.path.append('/opt/ACTIVE/SCRAPERS/NATIONAL')
from EMAIL_SAFEGUARDS import EmailSafeguards

safeguards = EmailSafeguards()
locked, lock_info = safeguards.check_safety_lock()
if locked:
    print("🔒 EMAIL SENDING BLOCKED BY SAFETY LOCK")
    print(lock_info)
    print("To unlock: python3 /opt/ACTIVE/SCRAPERS/NATIONAL/EMAIL_SAFEGUARDS.py --unlock")
    sys.exit(1)

#!/usr/bin/env python3
"""
Email Sending Skill — reusable functions for ALL email campaigns.
Import this instead of re-coding Yahoo/Gmail split, Brevo checks, failure handling.

Usage:
    from email_sending_skill import (
        brevo_pre_check, brevo_mid_check, handle_failure,
        send_brevo, send_gmail, get_gmail_sender,
        expand_template, is_yahoo, is_gmail,
        YAHOO_DOMAINS, GMAIL_CAP_PER_SENDER, MID_BATCH_CHECK_INTERVAL,
    )

Location: /opt/ACTIVE/INFRA/SKILLS/email_sending_skill.py
Created: 2026-03-01
"""

import os
import ssl
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText

# ── Constants ────────────────────────────────────────────

BREVO_API = "https://api.brevo.com/v3"

YAHOO_DOMAINS = {
    'yahoo.com', 'yahoo.no', 'yahoo.co.uk', 'yahoo.fr', 'yahoo.de',
    'yahoo.es', 'yahoo.it', 'yahoo.ca', 'yahoo.se', 'yahoo.dk',
    'yahoo.nl', 'yahoo.fi', 'yahoo.at', 'yahoo.ch', 'yahoo.pl',
    'yahoo.ie', 'yahoo.com.au', 'yahoo.co.in', 'yahoo.co.jp',
    'ymail.com', 'rocketmail.com',
}

# Max emails/day to @gmail.com addresses per Brevo sender
GMAIL_CAP_PER_SENDER = 150

# Run mid-batch Brevo health check every N sends
MID_BATCH_CHECK_INTERVAL = 15

# All Gmail SMTP senders (12 accounts, 470/day total capacity)
DEFAULT_GMAIL_SENDERS = [
    {'email': 'manpower.dristor@gmail.com', 'env_pass': 'GMAIL_APP_PASSWORD', 'name': 'InterJob Solutions Europe', 'limit': 50},
    {'email': 'manpowerdristor@gmail.com', 'env_pass': 'GMAIL_MANPOWERDRISTOR_APP_PASSWORD', 'name': 'InterJob Manpower Dristor', 'limit': 50},
    {'email': 'elena.manpower.dristor@gmail.com', 'env_pass': 'GMAIL_ELENA_PASSWORD', 'name': 'InterJob Recruitment', 'limit': 50},
    {'email': 'pamintstrabun@gmail.com', 'env_pass': 'GMAIL_PAMINTSTRABUN_PASSWORD', 'name': 'InterJob Solutions', 'limit': 50},
    {'email': 'manpowersearchromania@gmail.com', 'env_pass': 'GMAIL_MANPOWERSEARCH_PASSWORD', 'name': 'InterJob Manpower Search', 'limit': 20},
    {'email': 'expatsinromania@gmail.com', 'env_pass': 'GMAIL_EXPATS_PASSWORD', 'name': 'Expats in Romania', 'limit': 50},
    {'email': 'lucian.bpandp@gmail.com', 'env_pass': 'GMAIL_LUCIAN_APP_PASSWORD', 'name': 'InterJob HR', 'limit': 50},
    {'email': 'fructexportromania@gmail.com', 'env_pass': 'GMAIL_FRUCTEXPORT_PASSWORD', 'name': 'Fruct Export Romania', 'limit': 30},
    {'email': 'casafaurbucuresti@gmail.com', 'env_pass': 'GMAIL_CASAFAUR_PASSWORD', 'name': 'Casa Faur', 'limit': 30},
    {'email': 'cumparlegume@gmail.com', 'env_pass': 'GMAIL_CUMPARLEGUME_PASSWORD', 'name': 'Cumpar Legume', 'limit': 30},
    {'email': 'vegetablesbucharest@gmail.com', 'env_pass': 'GMAIL_VEGETABLESBUCHAREST_PASSWORD', 'name': 'Vegetables Bucharest', 'limit': 30},
    {'email': 'fruitnature4@gmail.com', 'env_pass': 'GMAIL_FRUITNATURE4_APP_PASSWORD', 'name': 'Fruit Nature', 'limit': 30},
]


# ── Domain checks ────────────────────────────────────────

def is_yahoo(email):
    """Check if email is a Yahoo domain (must send via Gmail SMTP, not Brevo)."""
    domain = email.strip().split('@')[-1].lower()
    return domain in YAHOO_DOMAINS


def is_gmail(email):
    """Check if email is @gmail.com (cap Brevo sends to these)."""
    return email.strip().split('@')[-1].lower() == 'gmail.com'


# ── Brevo health checks ─────────────────────────────────

def brevo_pre_check(api_key, logger=None):
    """
    Check Brevo account health BEFORE sending. Call once per batch.
    Returns (ok: bool, message: str).
    Abort if: bounce >10%, blocked >10%, any spam complaints today.
    """
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    try:
        r = requests.get(f"{BREVO_API}/smtp/statistics/aggregatedReport",
                         headers=headers, params={"days": 1}, timeout=15)
        if r.status_code != 200:
            return True, f"Could not check (HTTP {r.status_code}), proceeding"

        data = r.json()
        total = data.get("requests", 0)
        hard_bounces = data.get("hardBounces", 0)
        soft_bounces = data.get("softBounces", 0)
        blocked = data.get("blocked", 0)

        if total == 0:
            return True, "No sends in last 24h, clean"

        bounce_rate = (hard_bounces + soft_bounces) / total * 100
        blocked_rate = blocked / total * 100

        if bounce_rate > 10.0:
            return False, f"BOUNCE RATE {bounce_rate:.1f}% (>10% limit) -- {hard_bounces} hard + {soft_bounces} soft / {total} total"
        if blocked_rate > 10.0:
            return False, f"BLOCKED RATE {blocked_rate:.1f}% -- {blocked}/{total}"

        # Check spam complaints today
        r2 = requests.get(f"{BREVO_API}/smtp/statistics/events",
                          headers=headers,
                          params={"event": "complaint", "limit": 10,
                                  "startDate": datetime.now().strftime("%Y-%m-%d")},
                          timeout=15)
        spam_count = 0
        if r2.status_code == 200:
            spam_count = len(r2.json().get("events", []))

        if spam_count > 0:
            return False, f"SPAM COMPLAINTS TODAY: {spam_count} -- stopping to protect sender reputation"

        return True, f"OK: {total} sent, {bounce_rate:.1f}% bounce, {blocked_rate:.1f}% blocked, 0 spam"

    except Exception as e:
        return True, f"Check failed ({e}), proceeding anyway"


def brevo_mid_check(api_key, logger=None, batch_sent=0):
    """
    Mid-batch health check. Call every MID_BATCH_CHECK_INTERVAL sends.
    Returns (ok: bool, message: str).
    Stop if bounce rate >5%.
    """
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    try:
        r = requests.get(f"{BREVO_API}/smtp/statistics/aggregatedReport",
                         headers=headers, params={"days": 1}, timeout=10)
        if r.status_code != 200:
            return True, "mid-check skip"

        data = r.json()
        total = data.get("requests", 0)
        hard = data.get("hardBounces", 0)
        soft = data.get("softBounces", 0)

        if total == 0:
            return True, "ok"

        bounce_rate = (hard + soft) / total * 100
        if bounce_rate > 5.0:
            return False, f"MID-BATCH STOP: bounce rate spiked to {bounce_rate:.1f}% after {batch_sent} sends"

        return True, f"mid-check ok ({bounce_rate:.1f}% bounce)"
    except Exception:
        return True, "mid-check skip"


# ── Send functions ───────────────────────────────────────

def send_brevo(api_key, sender_email, sender_name, reply_to, to_email, subject, body):
    """
    Send one email via Brevo API.
    Returns (ok: bool, message: str).
    """
    url = f"{BREVO_API}/smtp/email"
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    html = "<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>"
    html += body.replace('\n', '<br>') + "</div>"
    data = {
        "sender": {"email": sender_email, "name": sender_name},
        "replyTo": {"email": reply_to},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": body,
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            return True, r.json().get('messageId', '')
        return False, f"HTTP_{r.status_code}:{r.text[:200]}"
    except Exception as e:
        return False, f"CONN_ERR:{str(e)[:200]}"


def send_gmail(sender_email, sender_password, sender_name, to_email, subject, body, reply_to):
    """
    Send one email via Gmail SMTP (for Yahoo recipients).
    Returns (ok: bool, message: str).

    Args:
        sender_email: Gmail address
        sender_password: Gmail app password
        sender_name: Display name
        to_email: Recipient
        subject, body: Email content
        reply_to: Reply-To address
    """
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = f'{sender_name} <{sender_email}>'
        msg['To'] = to_email
        msg['Reply-To'] = reply_to

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context, timeout=30) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, 'OK'
    except smtplib.SMTPAuthenticationError as e:
        return False, f"GMAIL_AUTH_ERR:{str(e)[:150]}"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"GMAIL_RECIPIENT_REFUSED:{str(e)[:150]}"
    except smtplib.SMTPSenderRefused as e:
        return False, f"GMAIL_SENDER_REFUSED:{str(e)[:150]}"
    except Exception as e:
        return False, f"GMAIL_ERR:{str(e)[:150]}"


def get_gmail_sender(state, gmail_senders=None):
    """
    Get Gmail sender using round-robin across ALL accounts (anti-spam).
    Each email goes to a different Gmail account, spreading load evenly.
    All 4 accounts send independently — looks like 4 different people.

    Args:
        state: campaign state dict (needs 'gmail_daily' and 'gmail_rr_index' keys)
        gmail_senders: list of sender dicts with keys: email, env_pass/password, name, limit
                       Defaults to DEFAULT_GMAIL_SENDERS.
    """
    senders = gmail_senders or DEFAULT_GMAIL_SENDERS
    valid = []
    for s in senders:
        email = s.get('email', '')
        password = s.get('password') or os.getenv(s.get('env_pass', ''), '')
        if email and password:
            valid.append({**s, 'password': password})
    if not valid:
        return None

    gmail_daily = state.get('gmail_daily', {})
    rr = state.get('gmail_rr_index', 0)

    # Try each sender starting from round-robin position
    for _ in range(len(valid)):
        chosen = valid[rr % len(valid)]
        rr += 1
        used = gmail_daily.get(chosen['email'], 0)
        if used < chosen.get('limit', 50):
            state['gmail_rr_index'] = rr  # advance for next call
            return chosen

    return None  # all exhausted


# ── Failure handling ─────────────────────────────────────

def handle_failure(email, error_msg, db_conn=None, table='norway_emails', dnc_table='norway_dnc'):
    """
    Investigate failure and take action.
    Returns action string: BOUNCED+DNC, SENDER_BLOCKED, RATE_LIMITED, TRANSIENT, UNKNOWN_FAIL.

    If db_conn is provided, updates DB directly.
    Otherwise just returns the classification (caller handles DB).
    """
    err = error_msg.lower()

    # Permanent failures -- mark bounced + add to DNC
    if any(k in err for k in ('invalid', '"code":400', 'http_400',
                               'does not exist', 'mailbox not found',
                               'user unknown', 'no such user',
                               'address rejected', 'recipient_refused',
                               'mailbox unavailable', 'mailbox disabled',
                               'account disabled')):
        if db_conn:
            try:
                cur = db_conn.cursor()
                cur.execute(f"UPDATE {table} SET campaign_status='bounced' WHERE LOWER(email)=%s", (email.lower(),))
                cur.execute(f"INSERT INTO {dnc_table} (email, reason, added_at) VALUES (%s, %s, NOW()) ON CONFLICT DO NOTHING",
                            (email.lower(), f"bounced: {error_msg[:100]}"))
                db_conn.commit()
            except Exception:
                pass
        return "BOUNCED+DNC"

    # Sender blocked -- critical, stop everything
    if any(k in err for k in ('blocked', 'blacklist', 'spam', 'complaint',
                               'http_401', 'http_403', 'sender_refused',
                               'auth_err')):
        return "SENDER_BLOCKED"

    # Rate limited -- pause and retry
    if any(k in err for k in ('http_429', 'rate limit', 'too many', 'throttl')):
        return "RATE_LIMITED"

    # Connection error -- transient, retry next time
    if any(k in err for k in ('conn_err', 'timeout', 'connection', 'network')):
        return "TRANSIENT"

    # Unknown -- mark failed
    if db_conn:
        try:
            cur = db_conn.cursor()
            cur.execute(f"UPDATE {table} SET campaign_status='failed' WHERE LOWER(email)=%s", (email.lower(),))
            db_conn.commit()
        except Exception:
            pass
    return "UNKNOWN_FAIL"


# ── Template expansion ───────────────────────────────────

def expand_template(subject, body, contact):
    """
    Replace template variables with contact data.
    Supports: {name}, {company_name}, {email}, {city}, {employees},
              {sector_name}, {org_number}, {country}
    """
    replacements = {
        '{company_name}': contact.get('name') or contact.get('company_name') or '',
        '{name}': contact.get('name') or contact.get('company_name') or '',
        '{email}': contact.get('email') or '',
        '{city}': contact.get('city') or '',
        '{employees}': str(contact.get('employees_count') or contact.get('employees') or ''),
        '{sector_name}': contact.get('sector_name') or contact.get('sector') or '',
        '{org_number}': str(contact.get('org_number') or ''),
        '{country}': contact.get('country') or '',
    }
    for old, new in replacements.items():
        subject = subject.replace(old, new)
        body = body.replace(old, new)
    return subject, body


# ── Utility: split contacts by domain ────────────────────

def split_yahoo_brevo(contacts, email_key='email'):
    """
    Split contacts list into (brevo_contacts, yahoo_contacts).
    Yahoo contacts must be sent via Gmail SMTP.
    """
    yahoo = [c for c in contacts if is_yahoo((c.get(email_key) or '').strip())]
    brevo = [c for c in contacts if not is_yahoo((c.get(email_key) or '').strip())]
    return brevo, yahoo


# ── Self-test ────────────────────────────────────────────

if __name__ == '__main__':
    print("Email Sending Skill loaded OK")
    print(f"  Yahoo domains: {len(YAHOO_DOMAINS)}")
    print(f"  Gmail cap/sender: {GMAIL_CAP_PER_SENDER}")
    print(f"  Mid-batch check interval: {MID_BATCH_CHECK_INTERVAL}")
    print(f"  Default Gmail senders: {len(DEFAULT_GMAIL_SENDERS)}")
    print()
    print("Functions available:")
    for fn in [brevo_pre_check, brevo_mid_check, send_brevo, send_gmail,
               get_gmail_sender, handle_failure, expand_template,
               is_yahoo, is_gmail, split_yahoo_brevo]:
        print(f"  {fn.__name__}: {fn.__doc__.strip().split(chr(10))[0] if fn.__doc__ else 'no doc'}")
