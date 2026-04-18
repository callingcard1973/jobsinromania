#!/usr/bin/env python3
"""Patch send_campaign.py to add Zoho SMTP as a third email provider."""
import sys

filepath = "/opt/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Add ZOHO constants after GMAIL_CAP_PER_SENDER
zoho_constants = """
# Zoho SMTP config (warmup: start at 50/day, increase gradually)
ZOHO_DAILY_LIMIT = int(os.environ.get("ZOHO_DAILY_LIMIT", "50"))
ZOHO_SMTP_HOST = os.environ.get("ZOHO_SMTP_HOST", "smtp.zoho.com")
ZOHO_SMTP_PORT = int(os.environ.get("ZOHO_SMTP_PORT", "587"))
"""
content = content.replace(
    "GMAIL_CAP_PER_SENDER = 150\n",
    "GMAIL_CAP_PER_SENDER = 150\n" + zoho_constants
)

# 2. Add send_zoho() function before gmail_health_check
send_zoho_func = '''
def send_zoho(to_email, subject, body, reply_to, sender_name=None):
    """Send one email via Zoho SMTP."""
    zoho_user = os.environ.get("ZOHO_SMTP_USER", "")
    zoho_pass = os.environ.get("ZOHO_SMTP_PASSWORD", "")
    if not zoho_user or not zoho_pass:
        return False, "ZOHO_NO_CREDS"
    if not sender_name:
        sender_name = os.environ.get("ZOHO_SENDER_NAME", "InterJob Transport Europe")
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{zoho_user}>"
        msg["To"] = to_email
        msg["Reply-To"] = reply_to
        context = ssl.create_default_context()
        with smtplib.SMTP(ZOHO_SMTP_HOST, ZOHO_SMTP_PORT, timeout=30) as server:
            server.starttls(context=context)
            server.login(zoho_user, zoho_pass)
            server.send_message(msg)
        return True, "OK"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"ZOHO_AUTH_ERR:{str(e)[:150]}"
    except smtplib.SMTPDataError as e:
        return False, f"ZOHO_DATA_ERR:{str(e)[:150]}"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"ZOHO_RECIPIENT_REFUSED:{str(e)[:150]}"
    except Exception as e:
        return False, f"ZOHO_ERR:{str(e)[:150]}"


'''
marker = "\ndef gmail_health_check(sender, state, logger):"
if marker not in content:
    print("ERROR: could not find gmail_health_check marker")
    sys.exit(1)
content = content.replace(marker, send_zoho_func + "def gmail_health_check(sender, state, logger):")

# 3. Add zoho_daily to state reset
content = content.replace(
    "        state['brevo_gmail_daily'] = 0\n    return state",
    "        state['brevo_gmail_daily'] = 0\n        state['zoho_daily'] = 0\n    return state"
)

# 4. Add zoho_daily to default state
content = content.replace(
    "            'gmail_daily': {}, 'brevo_gmail_daily': 0}",
    "            'gmail_daily': {}, 'brevo_gmail_daily': 0, 'zoho_daily': 0}"
)

# 5. Add Zoho routing in contact splitting
old_split = '        logger.info(f"{campaign}: {len(contacts)} contacts ({len(brevo_contacts)} Brevo, {len(yahoo_contacts)} Yahoo)")'

new_split = '''        # Zoho overflow: route some non-Yahoo contacts via Zoho SMTP
        zoho_user = os.environ.get("ZOHO_SMTP_USER", "")
        zoho_pass = os.environ.get("ZOHO_SMTP_PASSWORD", "")
        zoho_limit = ZOHO_DAILY_LIMIT - state.get('zoho_daily', 0)
        zoho_contacts = []
        if zoho_user and zoho_pass and zoho_limit > 0 and cfg.get("sender_type") != "brevo_only":
            # Take up to zoho_limit contacts from end of brevo list for Zoho
            zoho_take = min(zoho_limit, len(brevo_contacts) // 3)  # max 1/3 of batch
            if zoho_take > 0:
                zoho_contacts = brevo_contacts[-zoho_take:]
                brevo_contacts = brevo_contacts[:-zoho_take]

        logger.info(f"{campaign}: {len(contacts)} contacts ({len(brevo_contacts)} Brevo, {len(zoho_contacts)} Zoho, {len(yahoo_contacts)} Yahoo)")'''

if old_split not in content:
    print("ERROR: could not find contact split log line")
    sys.exit(1)
content = content.replace(old_split, new_split)

# 6. Add Zoho sending loop before final summary
old_final = '    summary = f"{campaign}: {sent_count} sent, {fail_count} fail, {skip_count} skip | {state[\'daily_count\']}/{daily_limit}"'

zoho_loop = '''    # Zoho SMTP contacts
    if zoho_contacts and not stopped and not dry_run:
        logger.info(f"{campaign}: sending {len(zoho_contacts)} via Zoho SMTP")

    for i, c in enumerate(zoho_contacts, 1):
        if stopped:
            break
        email_addr = c['email'].strip().lower()
        company = c.get('company_name') or c.get('name') or ''
        subj, body = expand_template(subj_tpl, body_tpl, c)

        if dry_run:
            logger.info(f"[Z {i}/{len(zoho_contacts)}] DRY: {company} <{email_addr}>")
            sent_count += 1
            continue

        if HAS_TRACKER and was_recently_sent(email_addr, days=14):
            logger.info(f"[Z {i}] SKIP(recent): {email_addr}")
            skip_count += 1
            continue

        if rules:
            ok_r, reason = rules.check_send_allowed(email_addr)
            if not ok_r:
                logger.info(f"[Z {i}] SKIP: {email_addr} -- {reason}")
                skip_count += 1
                continue

        ok, msg = send_zoho(email_addr, subj, body, reply_to)
        if ok:
            logger.info(f"[Z {i}/{len(zoho_contacts)}] OK: {company} <{email_addr}>")
            state['daily_count'] += 1
            state['total_sent'] = state.get('total_sent', 0) + 1
            state['zoho_daily'] = state.get('zoho_daily', 0) + 1
            sent_count += 1
            log_to_db(email_addr, company, campaign, tpl_num, msg, 'sent', os.environ.get('ZOHO_SMTP_USER', 'zoho'))
            if HAS_TRACKER:
                try: global_log_send(email_addr, campaign, 'zoho:transport.work@zoho.com')
                except Exception: pass
        else:
            logger.warning(f"[Z {i}/{len(zoho_contacts)}] FAIL: {company} <{email_addr}> -- {msg}")
            fail_count += 1
            log_to_db(email_addr, company, campaign, tpl_num, '', 'failed', 'zoho')
            if "AUTH_ERR" in msg or "DATA_ERR" in msg:
                logger.error(f"{campaign} ZOHO STOPPED: {msg}")
                send_telegram(f"{CAMPAIGN_PREFIX} {sector} ZOHO STOPPED: {msg[:100]}")
                break

        save_state(sector, state)
        if i < len(zoho_contacts) and not stopped:
            time.sleep(random.uniform(delay_min, delay_max))

'''

if old_final not in content:
    print("ERROR: could not find final summary log line")
    sys.exit(1)
content = content.replace(old_final, zoho_loop + old_final)

with open(filepath, "w") as f:
    f.write(content)

print("PATCH APPLIED OK")
print(f"File size: {len(content)} bytes")
