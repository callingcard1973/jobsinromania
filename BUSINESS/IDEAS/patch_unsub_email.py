#!/usr/bin/env python3
"""Patch response_tracker: auto-add NOT_INTERESTED to master_dnc."""
content = open("/opt/ACTIVE/INFRA/SKILLS/response_tracker.py").read()

old = "            save_response_db(sender, subject, category, campaign, name)"
new = """            # Auto-DNC on NOT_INTERESTED
            if category == "NOT_INTERESTED":
                try:
                    _dnc_conn = psycopg2.connect(host="/var/run/postgresql",
                        dbname="interjob_master", user="tudor", password="scraper123")
                    _dnc_cur = _dnc_conn.cursor()
                    _dnc_cur.execute(
                        "INSERT INTO master_dnc (email, reason, added_at) VALUES (%s, %s, NOW()) ON CONFLICT DO NOTHING",
                        (sender, f"email_unsub:{campaign}")
                    )
                    _dnc_conn.commit()
                    _dnc_cur.close()
                    _dnc_conn.close()
                    log(f"DNC added: {sender} ({campaign})")
                except Exception as e:
                    log(f"DNC error: {e}")
            save_response_db(sender, subject, category, campaign, name)"""

if "Auto-DNC" not in content:
    content = content.replace(old, new, 1)
    open("/opt/ACTIVE/INFRA/SKILLS/response_tracker.py", "w").write(content)
    print("unsubscribe auto-DNC patched")
else:
    print("already patched")
