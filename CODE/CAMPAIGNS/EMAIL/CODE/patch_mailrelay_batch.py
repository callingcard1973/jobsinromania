#!/usr/bin/env python3
"""Replace per-email mailrelay sending with batch approach using send_mailrelay.py."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py"
with open(path, "r") as f:
    content = f.read()

# 1. Add import at top
old_import = "from email.header import decode_header"
new_import = "from email.header import decode_header\nfrom send_mailrelay import run_mailrelay_batch"
if "send_mailrelay" not in content:
    content = content.replace(old_import, new_import)

# 2. Replace the inline send_mailrelay function with a pass-through
# Find and replace the old inline function
old_func_start = "\ndef send_mailrelay("
old_func_end = "        return False, \"MAILRELAY_ERR:\" + str(e)[:150]\n"
if old_func_start in content:
    start = content.index(old_func_start)
    end = content.index(old_func_end, start) + len(old_func_end)
    content = content[:start] + "\n" + content[end:]

# 3. Add mailrelay batch handling before the brevo contact loop
# When mailrelay_mode is on, send the whole batch via Mailrelay and skip the per-email loop
old_mailrelay_check = """        if mailrelay_mode:
            mr_key = os.environ.get('MAILRELAY_API_KEY', '')
            mr_url = os.environ.get('MAILRELAY_API_URL', 'https://expatsinromania.ipzmarketing.com/api/v1')
            ok, msg = send_mailrelay(mr_key, mr_url, cfg['sender_email'], cfg['sender_name'],
                                     email_addr, subj, body)
        else:
            ok, msg = send_brevo(api_key, cfg['sender_email'], cfg['sender_name'],
                                 reply_to, email_addr, subj, body)"""

new_mailrelay_check = """        ok, msg = send_brevo(api_key, cfg['sender_email'], cfg['sender_name'],
                                 reply_to, email_addr, subj, body)"""

if old_mailrelay_check in content:
    content = content.replace(old_mailrelay_check, new_mailrelay_check)

# 4. Add batch mailrelay send right after the "Mailrelay mode" routing section
old_routing = """    if mailrelay_mode:
        brevo_contacts = contacts  # reuse brevo loop but send via mailrelay
        yahoo_contacts = []
        zoho_contacts = []
        logger.info(f"{campaign}: {len(contacts)} contacts (ALL via Mailrelay)")"""

new_routing = """    if mailrelay_mode:
        # Batch send via Mailrelay: sync subscribers + send one campaign
        subj_tpl, body_tpl = load_template(tpl_num)
        sent = run_mailrelay_batch(
            db_cfg=CFG.get('db', {}),
            tables_cfg=CFG.get('tables', {}),
            contacts=contacts[:remaining],
            subject_tpl=subj_tpl,
            body_tpl=body_tpl,
            daily_limit=remaining,
            campaign_name=campaign,
            logger=logger
        )
        state['daily_count'] += sent
        state['total_sent'] = state.get('total_sent', 0) + sent
        save_state(sector, state)
        # Mark contacts as sent in DB
        if sent > 0:
            try:
                conn = get_db()
                cur = conn.cursor()
                for c in contacts[:sent]:
                    email_col = get_col('email')
                    cs_col = get_col('campaign_status')
                    cur.execute(f"UPDATE {contacts_tbl} SET {cs_col}='sent' WHERE LOWER({email_col})=%s",
                                (c['email'].lower(),))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"DB update failed: {e}")
        logger.info(f"{campaign}: Mailrelay batch sent {sent}/{len(contacts)}")
        return sent
    """

content = content.replace(old_routing, new_routing)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - Mailrelay uses batch send, contacts from your DB")
