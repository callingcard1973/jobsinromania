import imaplib, ssl, email, re
from email.header import decode_header
from datetime import datetime, timedelta

def dh(v):
    if not v: return ""
    try: return " ".join(p.decode(c or "utf-8",errors="replace") if isinstance(p,bytes) else p for p,c in decode_header(v))
    except: return str(v)

i=imaplib.IMAP4_SSL("imap.gmail.com",993,ssl_context=ssl.create_default_context())
i.login("lucian.bpandp@gmail.com","umsy whin nwxf jlku")
i.select("INBOX",readonly=True)
since=(datetime.now()-timedelta(days=10)).strftime("%d-%b-%Y")
_,ids=i.search(None,f'(SINCE "{since}")')
mids=ids[0].split() if ids[0] else []
print(f"{len(mids)} emails in last 10 days\n")
for mid in mids:
    _,hd=i.fetch(mid,"(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
    hm=email.message_from_bytes(hd[0][1])
    frm=dh(hm.get("From",""))
    subj=dh(hm.get("Subject",""))
    dt=dh(hm.get("Date",""))[:25]
    se=re.search(r"<([^>]+)>",frm)
    se_addr=se.group(1) if se else frm
    name=re.sub(r"<[^>]+>","",frm).strip().strip('"')
    print(f"{dt:25s} | {name[:25]:25s} | {se_addr[:35]:35s} | {subj[:70]}")
i.logout()
