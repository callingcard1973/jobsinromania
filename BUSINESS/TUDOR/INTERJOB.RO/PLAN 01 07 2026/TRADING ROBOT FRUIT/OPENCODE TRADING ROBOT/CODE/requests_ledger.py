#!/usr/bin/env python3
"""Tine minte CERERILE (ce vor candidatii/cumparatorii) pentru match automat cu ofertele."""
import argparse
import datetime as _dt
import json
import os
import sys

LEDGER = os.path.join(os.path.dirname(__file__), "..",
                      "DATA", "00_SHARED_leads_si_dnc", "requests_ledger.jsonl")


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _email_key(email):
    return (email or "").strip().lower()


def _tags(tags):
    # WHY: normalizare la tag canonic produs (cross-limba) pt. trading international
    import legume_taxonomy
    return legume_taxonomy.normalize_tags(tags)


def _append(row):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def read_all():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def record_request(email, want_type, tags, text=""):
    """Inregistreaza o cerere. want_type: job/buy/service. tags: ce vrea (ocupatie/judet/produs)."""
    row = {"event": "request", "ts": _now(), "email": _email_key(email),
           "want_type": want_type, "tags": _tags(tags), "text": (text or "")[:2000]}
    _append(row)
    return row


def _main():
    p = argparse.ArgumentParser(description="Registru cereri (pentru match cu oferte)")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--email", required=True)
    a.add_argument("--type", required=True, dest="want_type",
                   help="job / buy / service")
    a.add_argument("--tags", required=True,
                   help="ce vrea, virgula: sudor,timis sau rosii,1tona")
    a.add_argument("--text", default="")

    sub.add_parser("list")

    args = p.parse_args()
    if args.cmd == "add":
        print(json.dumps(record_request(args.email, args.want_type,
                                        args.tags, args.text)))
    elif args.cmd == "list":
        for row in read_all():
            print(json.dumps(row, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
