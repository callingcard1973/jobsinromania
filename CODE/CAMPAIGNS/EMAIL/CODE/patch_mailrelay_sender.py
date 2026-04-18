#!/usr/bin/env python3
"""Add Mailrelay sending support to send_campaign.py."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py"
with open(path, "r") as f:
    content = f.read()

# 1. Add send_mailrelay function after send_zoho
mailrelay_func = '''

def send_mailrelay(api_key, api_url, sender_email, sender_name, to_email, subject, body):
    """Send one email via Mailrelay campaign API."""
    headers = {"X-Auth-Token": api_key, "Content-Type": "application/json"}
    html = "<html><body><div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>"
    html += body.replace('\\n', '<br>') + "</div>"
    html += '<p><a href="[unsubscribe_url]">Unsubscribe</a></p></body></html>'
    # Ensure subscriber exists
    try:
        r = _session.get(api_url + "/subscribers?q[email_eq]=" + to_email, headers=headers, timeout=10)
        if r.status_code == 200 and not r.json():
            _session.post(api_url + "/subscribers", headers=headers, json={
                "name": to_email.split("@")[0], "email": to_email,
                "group_ids": [1], "status": "active"}, timeout=10)
    except Exception:
        pass
    # Create and send campaign
    try:
        camp = {"subject": subject, "sender_id": 1, "html": html,
                "target": "subscribers", "subscriber_ids": []}
        # Get subscriber ID
        r = _session.get(api_url + "/subscribers?q[email_eq]=" + to_email, headers=headers, timeout=10)
        if r.status_code == 200 and r.json():
            sid = r.json()[0]["id"]
        else:
            return False, "MAILRELAY_NO_SUBSCRIBER"
        camp["subscriber_ids"] = [sid]
        r = _session.post(api_url + "/campaigns", headers=headers, json=camp, timeout=15)
        if r.status_code != 201:
            return False, "MAILRELAY_CAMP_" + str(r.status_code) + ":" + r.text[:100]
        cid = r.json()["id"]
        r2 = _session.post(api_url + "/campaigns/" + str(cid) + "/send_all",
                           headers=headers, json={"target": "subscribers", "subscriber_ids": [sid]}, timeout=15)
        if r2.status_code == 200:
            return True, "OK"
        return False, "MAILRELAY_SEND_" + str(r2.status_code) + ":" + r2.text[:100]
    except Exception as e:
        return False, "MAILRELAY_ERR:" + str(e)[:150]

'''

# Insert after send_zoho function (before gmail_health_check)
content = content.replace(
    "\ndef gmail_health_check(",
    mailrelay_func + "\ndef gmail_health_check("
)

# 2. Add mailrelay routing in run_sector
# After zoho_only mode, add mailrelay mode
old_zoho_only = '''    # Zoho-only mode: route ALL contacts through Zoho SMTP
    zoho_only = cfg.get("sender_type") == "zoho"'''

new_zoho_only = '''    # Mailrelay mode: route ALL contacts through Mailrelay API
    mailrelay_mode = cfg.get("sender_type") == "mailrelay"

    # Zoho-only mode: route ALL contacts through Zoho SMTP
    zoho_only = cfg.get("sender_type") == "zoho"'''
content = content.replace(old_zoho_only, new_zoho_only)

# Add mailrelay routing before zoho_only check
old_routing = '''    if zoho_only:
        zoho_contacts = contacts
        brevo_contacts = []
        yahoo_contacts = []
        logger.info(f"{campaign}: {len(contacts)} contacts (ALL via Zoho, zoho mode)")'''

new_routing = '''    if mailrelay_mode:
        brevo_contacts = contacts  # reuse brevo loop but send via mailrelay
        yahoo_contacts = []
        zoho_contacts = []
        logger.info(f"{campaign}: {len(contacts)} contacts (ALL via Mailrelay)")

    elif zoho_only:
        zoho_contacts = contacts
        brevo_contacts = []
        yahoo_contacts = []
        logger.info(f"{campaign}: {len(contacts)} contacts (ALL via Zoho, zoho mode)")'''
content = content.replace(old_routing, new_routing)

# 3. Replace the send_brevo call to check for mailrelay_mode
old_send = '''        ok, msg = send_brevo(api_key, cfg['sender_email'], cfg['sender_name'],
                             reply_to, email_addr, subj, body)'''

new_send = '''        if mailrelay_mode:
            mr_key = os.environ.get('MAILRELAY_API_KEY', '')
            mr_url = os.environ.get('MAILRELAY_API_URL', 'https://expatsinromania.ipzmarketing.com/api/v1')
            ok, msg = send_mailrelay(mr_key, mr_url, cfg['sender_email'], cfg['sender_name'],
                                     email_addr, subj, body)
        else:
            ok, msg = send_brevo(api_key, cfg['sender_email'], cfg['sender_name'],
                                 reply_to, email_addr, subj, body)'''
content = content.replace(old_send, new_send)

# 4. Skip brevo_pre_check for mailrelay
old_precheck = '''    if not dry_run and not test and not gmail_only and not zoho_mode:
        ok, msg = brevo_pre_check(api_key, logger)'''
new_precheck = '''    if not dry_run and not test and not gmail_only and not zoho_mode and not mailrelay_mode:
        ok, msg = brevo_pre_check(api_key, logger)'''
# Need to define mailrelay_mode earlier
old_gmail_only = '''    gmail_only = cfg.get("sender_type") == "gmail_only"
    zoho_mode = cfg.get("sender_type") == "zoho"'''
new_gmail_only = '''    gmail_only = cfg.get("sender_type") == "gmail_only"
    zoho_mode = cfg.get("sender_type") == "zoho"
    mailrelay_mode = cfg.get("sender_type") == "mailrelay"'''
content = content.replace(old_gmail_only, new_gmail_only)
content = content.replace(old_precheck, new_precheck)

# 5. Skip api_key check for mailrelay
old_apikey = '''    api_key = os.environ.get(cfg['sender_key'], os.environ.get('BREVO_API_KEY', ''))
    if not api_key and not dry_run:
        logger.error(f"{campaign}: no API key for {cfg['sender_key']}")
        return 0'''
new_apikey = '''    api_key = os.environ.get(cfg['sender_key'], os.environ.get('BREVO_API_KEY', ''))
    if not api_key and not dry_run and not mailrelay_mode:
        logger.error(f"{campaign}: no API key for {cfg['sender_key']}")
        return 0'''
content = content.replace(old_apikey, new_apikey)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - Mailrelay sending support added to send_campaign.py")
print("Set sender_type: mailrelay in campaign config to route via Mailrelay API")
