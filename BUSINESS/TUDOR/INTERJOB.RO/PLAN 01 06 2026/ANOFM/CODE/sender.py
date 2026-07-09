#!/usr/bin/env python3
"""Shared email sender for all campaigns.

Single source of truth for the Brevo API call and Gmail SMTP call, plus the
common argparse contract the orchestrator relies on (--limit/--dry-run/--delay
/--daily-cap/--gmail-only). Per-campaign identity (keys, sender, templates)
stays in each campaign script and is passed in here.
"""
import json
import smtplib
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from email.utils import formataddr

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def add_common_args(ap, default_limit=50):
    ap.add_argument("--limit", type=int, default=default_limit)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=int, default=0)
    ap.add_argument("--daily-cap", type=int, default=0)
    ap.add_argument("--gmail-only", action="store_true")
    return ap


def effective_limit(args):
    cap = getattr(args, "daily_cap", 0)
    return min(args.limit, cap) if cap else args.limit


def send_brevo(api_key, sender_email, sender_name, to_email, subject, body,
               reply_to=None, attachment=None, headers=None):
    """Return (ok, status). status is 'HTTP n' on success or 'HTTP_code:body' / err on failure.

    headers: optional dict of custom SMTP headers (e.g. List-Unsubscribe) — required
    by Gmail/Yahoo bulk-sender rules."""
    payload = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    if attachment:
        payload["attachment"] = attachment
    if headers:
        payload["headers"] = headers
    req = urllib.request.Request(
        BREVO_URL, data=json.dumps(payload).encode(),
        headers={"api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status in (200, 201), f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP_{e.code}:{e.read().decode(errors='replace')[:200]}"
    except Exception as e:
        return False, str(e)


def send_gmail(gmail_user, app_password, sender_name, to_email, to_name,
               subject, body, reply_to=None):
    """Return (ok, status). Raises nothing; SMTP refusals reported via status."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = formataddr((sender_name, gmail_user))
    msg["To"] = formataddr((to_name or "", to_email))
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as srv:
            srv.starttls()
            srv.login(gmail_user, app_password)
            srv.send_message(msg)
        return True, "sent"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"refused:{e}"
    except Exception as e:
        return False, str(e)


def send_smtp(host, user, password, sender_name, to_email, subject, body,
              reply_to=None, headers=None, port=465):
    """Send via a normal SMTP mailbox (e.g. A2 cPanel mail.<domain>:465 SSL).
    Used when a segment's Brevo account is not activated. Returns (ok, status)."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = formataddr((sender_name, user))
    msg["To"] = to_email
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    for k, v in (headers or {}).items():
        msg[k] = v
    try:
        with smtplib.SMTP_SSL(host, port, timeout=30) as srv:
            srv.login(user, password)
            srv.send_message(msg)
        return True, "sent"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"refused:{e}"
    except Exception as e:
        return False, str(e)
