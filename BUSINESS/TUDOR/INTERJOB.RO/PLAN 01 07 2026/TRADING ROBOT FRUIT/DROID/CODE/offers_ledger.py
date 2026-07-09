#!/usr/bin/env python3
"""Tine minte ofertele trimise si raspunsurile primite (registru append-only JSONL)."""
import argparse
import datetime as _dt
import json
import os
import sys

LEDGER = os.path.join(os.path.dirname(__file__), "..",
                      "DATA", "00_SHARED_leads_si_dnc", "offers_ledger.jsonl")


def _now():
    # WHY: timestamp UTC stabil pentru audit, fara dependinte externe
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _email_key(email):
    return (email or "").strip().lower()


def _append(row):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def _read_all():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _tags(tags):
    # WHY: normalizam la tag canonic (produs RO/EN/DE/...) pt. match cross-limba international
    import legume_taxonomy
    return legume_taxonomy.normalize_tags(tags)


def record_offer(email, offer_type, campaign, subject, tags=None):
    """Inregistreaza o oferta trimisa catre un email. tags = ce ofera (ocupatie/judet/produs)."""
    row = {"event": "offer", "ts": _now(), "email": _email_key(email),
           "offer_type": offer_type, "campaign": campaign, "subject": subject,
           "tags": _tags(tags)}
    _append(row)
    return row


def record_reply(email, intent, text):
    """Inregistreaza un raspuns primit la o oferta."""
    row = {"event": "reply", "ts": _now(), "email": _email_key(email),
           "intent": intent, "text": (text or "")[:2000]}
    _append(row)
    return row


def record_response(email, intent, draft_ref):
    """Inregistreaza ca am pregatit un raspuns (draft) catre email."""
    row = {"event": "response", "ts": _now(), "email": _email_key(email),
           "intent": intent, "draft_ref": draft_ref}
    _append(row)
    return row


def history(email):
    """Tot ce stim despre un email (oferte + replies + responses), cronologic."""
    k = _email_key(email)
    return [r for r in _read_all() if r.get("email") == k]


def last_offer(email):
    offers = [r for r in history(email) if r.get("event") == "offer"]
    return offers[-1] if offers else None


def already_offered(email):
    """True daca i-am mai trimis deja o oferta (anti-duplicat)."""
    return last_offer(email) is not None


def _main():
    p = argparse.ArgumentParser(description="Registru oferte + raspunsuri")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add-offer")
    a.add_argument("--email", required=True)
    a.add_argument("--type", required=True, dest="offer_type")
    a.add_argument("--campaign", required=True)
    a.add_argument("--subject", default="")
    a.add_argument("--tags", default="", help="ce ofera, virgula: sudor,timis sau rosii,export")

    r = sub.add_parser("add-reply")
    r.add_argument("--email", required=True)
    r.add_argument("--intent", default="neutral")
    r.add_argument("--text", default="")

    h = sub.add_parser("history")
    h.add_argument("--email", required=True)

    c = sub.add_parser("check")
    c.add_argument("--email", required=True)

    args = p.parse_args()
    if args.cmd == "add-offer":
        print(json.dumps(record_offer(args.email, args.offer_type,
                                      args.campaign, args.subject, args.tags)))
    elif args.cmd == "add-reply":
        print(json.dumps(record_reply(args.email, args.intent, args.text)))
    elif args.cmd == "history":
        for row in history(args.email):
            print(json.dumps(row, ensure_ascii=True))
    elif args.cmd == "check":
        print("DEJA OFERTAT" if already_offered(args.email) else "NOU")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
