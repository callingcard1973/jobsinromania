#!/usr/bin/env python3
"""Broker (trading) marketplace: ia match-urile si tranzactioneaza dealuri intre cele 2 parti.

Flux deal: proposed -> intro draft ambelor parti -> (accept) -> closed.
NU trimite emailuri singur; doar drafturi. Send/closed = aprobare numerotata.
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

import auto_matcher

DATA = os.path.join(os.path.dirname(__file__), "..", "..",
                    "DATA", "00_SHARED_leads_si_dnc")
DEALS = os.path.join(DATA, "deals_ledger.jsonl")
DEAL_DRAFTS = os.path.join(DATA, "deal_drafts")

VALID_STATUS = ("proposed", "accepted", "closed", "dead")


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deal_id(req_email, off_email):
    # WHY: id stabil per pereche => idempotent, fara dubluri de deal
    raw = (req_email + "|" + off_email).lower()
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _read_deals():
    if not os.path.exists(DEALS):
        return {}
    deals = {}
    with open(DEALS, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                d = json.loads(line)
                deals[d["deal_id"]] = d  # ultimul rand per id castiga
    return deals


def _write_deal(deal):
    os.makedirs(DATA, exist_ok=True)
    with open(DEALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(deal, ensure_ascii=True) + "\n")


def _intro_draft(deal, side):
    """Draft ASCII de intro pentru o parte (cerere sau oferta)."""
    common = ", ".join(deal["common"])
    who = "o cerere" if side == "offer" else "o oferta"
    body = (
        "Buna ziua,\n\n"
        "Avem %s care se potriveste cu profilul dumneavoastra pe: %s.\n"
        "Putem face legatura intre cele doua parti pentru a discuta direct.\n\n"
        "Confirmati daca sa va punem in legatura?\n\n"
        "Cu stima,\nEchipa InterJob\n"
    ) % (who, common)
    return body.encode("ascii", "ignore").decode("ascii")


def open_deals(min_score=2):
    """Creeaza dealuri din match-uri noi (idempotent) si scrie intro drafturi ambelor parti."""
    matches = auto_matcher.match_all(min_score)
    existing = _read_deals()
    os.makedirs(DEAL_DRAFTS, exist_ok=True)
    created = []
    for m in matches:
        did = _deal_id(m["request_email"], m["offer_email"])
        if did in existing:
            continue  # WHY: dealul exista deja, nu-l redeschidem
        deal = {"deal_id": did, "ts": _now(), "status": "proposed",
                "score": m["score"], "common": m["common"],
                "request_email": m["request_email"],
                "offer_email": m["offer_email"],
                "offer_campaign": m["offer_campaign"]}
        for side, email in (("request", m["request_email"]),
                            ("offer", m["offer_email"])):
            path = os.path.join(DEAL_DRAFTS, did + "_" + side + ".txt")
            with open(path, "w", encoding="ascii") as fh:
                fh.write(_intro_draft(deal, side))
        _write_deal(deal)
        created.append(deal)
    return created


def set_status(deal_id, status):
    """Avanseaza dealul: proposed->accepted->closed (sau dead). Append-only."""
    if status not in VALID_STATUS:
        raise ValueError("status invalid: %s" % status)
    deals = _read_deals()
    if deal_id not in deals:
        raise KeyError("deal inexistent: %s" % deal_id)
    d = dict(deals[deal_id])
    d["status"] = status
    d["ts"] = _now()
    _write_deal(d)
    return d


def list_deals(status=None):
    deals = list(_read_deals().values())
    if status:
        deals = [d for d in deals if d["status"] == status]
    deals.sort(key=lambda d: d.get("score", 0), reverse=True)
    return deals


def _main():
    p = argparse.ArgumentParser(description="Broker dealuri (trading marketplace)")
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("open", help="creeaza dealuri din match-uri + intro drafturi")
    o.add_argument("--min-score", type=int, default=2)

    s = sub.add_parser("status", help="avanseaza statusul unui deal")
    s.add_argument("--deal", required=True)
    s.add_argument("--set", required=True, dest="new_status",
                   choices=VALID_STATUS)

    l = sub.add_parser("list")
    l.add_argument("--status", default=None, choices=VALID_STATUS)

    args = p.parse_args()
    if args.cmd == "open":
        created = open_deals(args.min_score)
        for d in created:
            print(json.dumps(d, ensure_ascii=True))
        sys.stderr.write("dealuri noi: %d\n" % len(created))
    elif args.cmd == "status":
        print(json.dumps(set_status(args.deal, args.new_status), ensure_ascii=True))
    elif args.cmd == "list":
        for d in list_deals(args.status):
            print(json.dumps(d, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
