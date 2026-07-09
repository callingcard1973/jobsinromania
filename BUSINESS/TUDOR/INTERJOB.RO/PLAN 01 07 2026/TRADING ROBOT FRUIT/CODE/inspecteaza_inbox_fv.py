#!/usr/bin/env python3
"""Inspecteaza un inbox IMAP pentru mailuri F&V (oferte/cereri/raspunsuri). Read-only.

Listeaza expeditor + subiect + data pentru mailuri din ultimele N zile care contin
cuvinte-cheie F&V. NU descarca atasamente, NU marcheaza citit, NU sterge.
"""

import email
import imaplib
import sys
from datetime import datetime, timedelta
from email.header import decode_header

KW = ["oferta", "pret", "legume", "fructe", "rosii", "ardei", "vinete", "gogosari",
      "visine", "castraveti", "dovlecei", "mere", "prune", "cooperativa", "tone",
      "disponibil", "livrare", "materie prima", "conserve", "cerere"]


def _dec(s):
    if not s:
        return ""
    out = []
    for part, enc in decode_header(s):
        out.append(part.decode(enc or "utf-8", "ignore") if isinstance(part, bytes) else part)
    return "".join(out)


def inspect(user, password, host="imap.gmail.com", days=30, folder="INBOX"):
    m = imaplib.IMAP4_SSL(host)
    m.login(user, password)
    m.select(folder, readonly=True)
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, data = m.search(None, f'(SINCE {since})')
    ids = data[0].split()
    hits = []
    for i in ids:
        _, msg_data = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        raw = msg_data[0][1].decode("utf-8", "ignore")
        msg = email.message_from_string(raw)
        frm, subj = _dec(msg.get("From")), _dec(msg.get("Subject"))
        blob = (frm + " " + subj).lower()
        if any(k in blob for k in KW):
            hits.append((_dec(msg.get("Date"))[:25], frm[:45], subj[:60]))
    m.logout()
    return hits


def read_bodies(user, password, host="imap.gmail.com", days=30, from_filter="", folder="INBOX"):
    """Citeste corpul text/plain al mailurilor al caror From contine from_filter."""
    m = imaplib.IMAP4_SSL(host)
    m.login(user, password)
    m.select(folder, readonly=True)
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, data = m.search(None, f'(SINCE {since})')
    out = []
    for i in data[0].split():
        _, md = m.fetch(i, "(BODY.PEEK[])")
        msg = email.message_from_bytes(md[0][1])
        frm = _dec(msg.get("From"))
        if from_filter and from_filter.lower() not in frm.lower():
            continue
        body = ""
        for part in msg.walk() if msg.is_multipart() else [msg]:
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", "ignore")
                except Exception:
                    body = ""
                break
        out.append((frm, _dec(msg.get("Subject")), body.strip()[:800]))
    m.logout()
    return out


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "cumparlegume@gmail.com"
    pw = sys.argv[2] if len(sys.argv) > 2 else ""
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    host = sys.argv[5] if len(sys.argv) > 5 else "imap.gmail.com"

    def asc(x):
        return x.encode("ascii", "replace").decode("ascii")

    # mod corp: arg 4 = substring expeditor
    if len(sys.argv) > 4 and sys.argv[4]:
        for frm, subj, body in read_bodies(user, pw, host, days, sys.argv[4]):
            print(asc(f"=== {frm} | {subj} ===\n{body}\n"))
        return

    hits = inspect(user, pw, host=host, days=days)
    def asc(x):
        return x.encode("ascii", "replace").decode("ascii")
    print(f"{user}: {len(hits)} mailuri F&V in ultimele {days} zile\n")
    for d, f, s in hits:
        print(asc(f"  [{d}] {f}\n      {s}"))


if __name__ == "__main__":
    main()
