#!/usr/bin/env python3
"""Fix folder select quoting in email_pipeline.py"""
f = "/opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py"
c = open(f).read()

old = '            st, _ = imap.select(folder, readonly=True)  # always readonly to avoid marking as read'
new = '''            try:
                st, _ = imap.select(f'"{folder}"', readonly=True)
            except Exception as e:
                if is_spam: log(f"  Folder '{folder}': error {e}, skipping")
                continue'''

c = c.replace(old, new)
open(f, "w").write(c)
print("Fixed folder quoting")
