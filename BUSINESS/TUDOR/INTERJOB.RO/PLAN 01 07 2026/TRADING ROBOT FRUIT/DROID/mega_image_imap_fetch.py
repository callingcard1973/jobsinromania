#!/usr/bin/env python3
"""Citeste apaminerala@yahoo.com, ia emailurile de la amustatea@mega-image.ro,
parseaza tabelul de propuneri de pret si le memoreaza (mega_image_price_memory).

IMAP Yahoo: imap.mail.yahoo.com:993 SSL. Parola din env YAHOO_APAMINERALA_APP_PASSWORD.
NU trimite nimic; doar citeste si retine. Read-only pe mailbox.
"""
import email
import imaplib
import os
import re
import sys
from email.header import decode_header
from html.parser import HTMLParser

import mega_image_price_memory as mem

EMAIL = "apaminerala@yahoo.com"
HOST = "imap.mail.yahoo.com"
PASSWORD = os.getenv("YAHOO_APAMINERALA_APP_PASSWORD")
SENDER = "amustatea@mega-image.ro"

HEADER_MAP = {
    "whs": "whs_code", "city": "city", "supplier code": "supplier_code",
    "contract": "contract_code", "supplier name": "supplier_name",
    "profi": "profi_code", "article": "article",
    "propunere": "propunere_pret", "raspuns": "raspuns_furnizor",
}


class _Tables(HTMLParser):
    """Aduna toate tabelele ca liste de randuri (fiecare rand = lista de celule text)."""
    def __init__(self):
        super().__init__()
        self.tables, self._rows, self._row, self._cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._rows = []
        elif tag == "tr" and self._rows is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._rows is not None:
            self.tables.append(self._rows)
            self._rows = None


def _decode(s):
    if not s:
        return ""
    parts = decode_header(s)
    return "".join(p.decode(enc or "utf-8", "ignore") if isinstance(p, bytes) else p
                   for p, enc in parts)


def _html_of(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", "ignore")
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", "ignore")
        return ""
    return msg.get_payload(decode=True).decode(
        msg.get_content_charset() or "utf-8", "ignore")


def _parse_week(rows_text):
    m = re.search(r"week\s*(\d+)", rows_text, re.I)
    return m.group(1) if m else ""


def _parse_deadline(text):
    m = re.search(r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}).{0,12}?(\d{1,2}[:.]\d{2})",
                  text)
    return (m.group(1) + " " + m.group(2)) if m else ""


def _proposal_table(table):
    """Returneaza (col_map, header_idx) daca tabelul pare a fi propunerea de pret."""
    for hi, row in enumerate(table[:3]):
        low = [c.lower() for c in row]
        joined = " ".join(low)
        if "article" in joined and ("propunere" in joined or "supplier name" in joined):
            col = {}
            for idx, cell in enumerate(low):
                for key, field in HEADER_MAP.items():
                    if key in cell:
                        col[field] = idx
            if "article" in col:
                return col, hi
    return None, None


def extract_rows(html, week, deadline):
    p = _Tables()
    p.feed(html)
    out = []
    for table in p.tables:
        col, hi = _proposal_table(table)
        if not col:
            continue
        for row in table[hi + 1:]:
            if not any(row):
                continue
            article = row[col["article"]] if col.get("article", -1) < len(row) else ""
            if not article:
                continue
            rec = {"week": week, "deadline": deadline, "source_email": SENDER}
            for field, idx in col.items():
                if field in ("propunere_pret", "raspuns_furnizor"):
                    continue  # WHY: header are colspan -> luam preturile din celulele cu zecimale
                rec[field] = row[idx] if idx < len(row) else ""
            # preturile = singurele celule cu zecimale, in ordine: Propunere, Raspuns
            prices = [c for c in row if re.match(r"^\d+[.,]\d+$", c.strip())]
            rec["propunere_pret"] = prices[0] if len(prices) >= 1 else ""
            rec["raspuns_furnizor"] = prices[1] if len(prices) >= 2 else ""
            out.append(rec)
    return out


def fetch():
    if not PASSWORD:
        raise SystemExit("Set YAHOO_APAMINERALA_APP_PASSWORD env var (no hardcoded default).")
    box = imaplib.IMAP4_SSL(HOST, 993)
    box.login(EMAIL, PASSWORD)
    box.select("INBOX", readonly=True)  # WHY: read-only, nu marcam citit
    typ, data = box.search(None, 'FROM', SENDER)
    ids = data[0].split()
    total = 0
    for mid in ids:
        typ, raw = box.fetch(mid, "(RFC822)")
        msg = email.message_from_bytes(raw[0][1])
        html = _html_of(msg)
        week = _parse_week(html) or _parse_week(_decode(msg.get("Subject")))
        deadline = _parse_deadline(re.sub(r"<[^>]+>", " ", html))
        rows = extract_rows(html, week, deadline)
        mem.ingest_rows(rows)
        total += len(rows)
        print("  mail %s '%s' -> %d linii" %
              (mid.decode(), _decode(msg.get("Subject"))[:50], len(rows)))
    box.logout()
    n = mem.write_report()
    print("TOTAL linii memorate din %d emailuri: %d (registru=%d)"
          % (len(ids), total, n))
    return total


if __name__ == "__main__":
    sys.exit(0 if fetch() is not None else 1)
