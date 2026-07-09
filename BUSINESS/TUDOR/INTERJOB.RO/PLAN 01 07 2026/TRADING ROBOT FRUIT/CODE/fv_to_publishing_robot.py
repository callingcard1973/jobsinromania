#!/usr/bin/env python3
"""Bridge: TRADING ROBOT -> PUBLISHING_ROBOT inbox.

Citeste offers_ledger.jsonl, construieste postul (fara date de contact
individuale — doar produs/cantitate/origine + office@cumparlegume.com),
si il trimite la POST /inbox al PUBLISHING_ROBOT pentru aprobare in TG.

Regula: nu se publica NICIODATA email/telefon/nume al furnizorilor
sau cumparatorilor individuali. Contactele sunt doar pentru Tudor.

Dry-run by default; --post trimite efectiv la PUBLISHING_ROBOT.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROBOT_URL = "http://localhost:8777/inbox"
DATA = Path(__file__).parent.parent / "DATA"
LEDGER = DATA / "offers_ledger.jsonl"


def load_ledger():
    items = []
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return items


def _qty(o):
    q = o.get("quantity_kg")
    return f"{int(q/1000)} to" if q else "cantitate la cerere"


ALLOWED_EMAILS = {"office@cumparlegume.com"}


def strip_contacts(text):
    """Safety layer: elimina orice email/telefon care ar fi scapat.

    Pastreaza doar ALLOWED_EMAILS (ex: office@cumparlegume.com).
    Telefoanele (07xxxxxxxx, 0xxxxxxxxx) se sterg tot.
    """
    import re

    def _keep_allowed(m):
        email = m.group(0).strip().lower()
        if email in ALLOWED_EMAILS:
            return email
        return ""

    text = re.sub(r'\S+@\S+\.\S+', _keep_allowed, text)
    text = re.sub(r'07\d{8}', "", text)
    text = re.sub(r'(?<!0)0\d{9}', "", text)
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def build_post_public(items):
    """Construieste textul de publicat — FARA date de contact individuale.

    SINGURUL contact publicat este office@cumparlegume.com.
    Emailurile, telefoanele si numele furnizorilor/cumparatorilor NU apar.
    """
    offers = [o for o in items if o.get("entry_type") != "request"
              and not o.get("internal_only")]
    requests = [o for o in items if o.get("entry_type") == "request"]

    lines = ["Gospodarii de Altadata - ce avem azi:", ""]
    if offers:
        lines.append("OFERIM (disponibil de la producatori):")
        seen = set()
        for o in offers:
            p = (o.get("product_ro") or "?").lower()
            if p in seen:
                continue
            seen.add(p)
            org = o.get("origin") or ""
            lines.append(f"- {p} ({_qty(o)})" + (f" - {org}" if org else ""))
        lines.append("")
    if requests:
        lines.append("CUMPARAM (avem cumparatori pentru):")
        seen = set()
        for o in requests:
            p = (o.get("product_ro") or "?").lower()
            if p in seen:
                continue
            seen.add(p)
            lines.append(f"- {p} ({_qty(o)})")
        lines.append("")
    lines.append("Contact: office@cumparlegume.com")
    text = "\n".join(lines)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = strip_contacts(text)
    return text


def send_to_robot(title, body, channels=None):
    payload = json.dumps({
        "title": title,
        "body": body,
        "channels": channels or ["tg", "wp", "fb"],
        "business": "cumparlegume",
    }).encode("utf-8")
    req = urllib.request.Request(
        ROBOT_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    do_post = "--post" in sys.argv

    items = load_ledger()
    if not items:
        print("Ledger gol sau lipsa. Nu am ce publica.")
        return

    text = build_post_public(items)
    title = "Oferte Gospodarii de Altadata"

    print("=" * 56)
    print(text)
    print("=" * 56)

    if not do_post:
        print("[DRY-RUN] adauga --post ca sa trimiti la PUBLISHING_ROBOT.")
        return

    try:
        res = send_to_robot(title, text)
        print(f"\nTrimis la PUBLISHING_ROBOT: status={res.get('status')}")
        print(f"  ID: {res.get('id')}")
        print(f"  Mesaj: {res.get('message')}")
    except Exception as e:
        msg = str(e)
        if hasattr(e, "read"):
            msg = e.read().decode("utf-8", "ignore")[:300]
        print(f"\nEROARE la trimitere: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
