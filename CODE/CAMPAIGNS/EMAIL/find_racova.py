#!/usr/bin/env python3
import imaplib, ssl, email, re
from email.header import decode_header

def dh(v):
    if not v: return ""
    try: return " ".join(p.decode(c or "utf-8",errors="replace") if isinstance(p,bytes) else p for p,c in decode_header(v))
    except: return str(v)

def body(msg):
    if msg.is_multipart():
        for ct in ["text/plain","text/html"]:
            for p in msg.walk():
                if p.get_content_type()==ct:
                    pl=p.get_payload(decode=True)
                    if pl:
                        t=pl.decode(p.get_content_charset() or "utf-8",errors="replace")
                        return re.sub(r"<[^>]+>","",t) if ct=="text/html" else t
    pl=msg.get_payload(decode=True)
    return pl.decode(msg.get_content_charset() or "utf-8",errors="replace") if pl else ""

c = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=ssl.create_default_context())
c.login("manpowerdristor@gmail.com", "pwat qgot nznt eggf")
allmail = '"[Gmail]/All Mail"'
c.select(allmail, readonly=True)
_, ids = c.search(None, "FROM racova")
if ids[0]:
    for mid in ids[0].split():
        _, fd = c.fetch(mid, "(RFC822)")
        msg = email.message_from_bytes(fd[0][1])
        print("From:", dh(msg.get("From","")))
        print("Subject:", dh(msg.get("Subject","")))
        print("Date:", msg.get("Date","")[:25])
        print("Body:", body(msg)[:400])
        print()
else:
    print("NOT FOUND")
c.logout()
