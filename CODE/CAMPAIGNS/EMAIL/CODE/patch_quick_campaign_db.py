"""Patch quick_campaign.py to also log sends to PostgreSQL send_log + global_sends."""

code = open("/opt/ACTIVE/INFRA/SKILLS/quick_campaign.py").read()

# Add DB logging function after imports
db_func = '''
# --- DB tracking (added by patch) ---
def log_send_to_db(email, campaign, sender, method="a2_smtp"):
    """Log send to anofm.send_log + email_sender.global_sends"""
    try:
        import psycopg2
        from datetime import date
        # anofm send_log
        conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
        cur = conn.cursor()
        cur.execute("INSERT INTO send_log(email, campaign, sector, sender, method, status) VALUES(%s,%s,%s,%s,%s,'sent')",
            (email, campaign, method, sender, method))
        conn.commit(); conn.close()
        # global_sends
        conn2 = psycopg2.connect(dbname="email_sender", user="tudor", host="localhost", password="tudor")
        cur2 = conn2.cursor()
        cur2.execute("INSERT INTO global_sends(email, campaign, sender, sent_date) VALUES(%s,%s,%s,%s)",
            (email, campaign, sender, date.today()))
        conn2.commit(); conn2.close()
    except:
        pass  # don't break sending if DB fails
# --- end DB tracking ---
'''

# Insert after "import random"
if "log_send_to_db" not in code:
    code = code.replace("import random\n", "import random\n" + db_func + "\n")

    # Add call after successful send
    old = '            state["sent_emails"].append(email)'
    new = '            state["sent_emails"].append(email)\n            log_send_to_db(email, campaign_id, args.sender, "a2_smtp" if "@" not in args.sender else "brevo")'
    code = code.replace(old, new)

    open("/opt/ACTIVE/INFRA/SKILLS/quick_campaign.py", "w").write(code)
    print("PATCHED: quick_campaign.py now logs to anofm.send_log + global_sends")
else:
    print("Already patched")
