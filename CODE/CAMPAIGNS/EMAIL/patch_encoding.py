#!/usr/bin/env python3
"""Fix encoding crash in email_pipeline.py - handle unknown charsets gracefully."""
f = "/opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py"
c = open(f).read()

old = '''def _dp(p):
    pl=p.get_payload(decode=True)
    return pl.decode(p.get_content_charset() or "utf-8",errors="replace") if pl else None'''

new = '''def _dp(p):
    pl=p.get_payload(decode=True)
    if not pl: return None
    charset = p.get_content_charset() or "utf-8"
    try:
        return pl.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return pl.decode("utf-8", errors="replace")'''

c = c.replace(old, new)
open(f, "w").write(c)
print("Fixed encoding handling")
