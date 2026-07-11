#!/usr/bin/env python3
"""Match automat OFERTA <-> CERERE pe suprapunere de tag-uri (ocupatie/judet/produs)."""
import argparse
import json
import os
import sys

import offers_ledger as offers
import requests_ledger as requests

MATCHES_OUT = os.path.join(os.path.dirname(__file__), "..", "..",
                           "DATA", "00_SHARED_leads_si_dnc", "matches.jsonl")


def _all_offers():
    return [r for r in offers._read_all() if r.get("event") == "offer"]


def _score(offer_tags, request_tags):
    """Scor = nr tag-uri comune; 0 daca nu se potrivesc deloc."""
    a, b = set(offer_tags or []), set(request_tags or [])
    return len(a & b)


def match_all(min_score=1):
    """Returneaza lista de match-uri ordonate descrescator dupa scor."""
    offs = _all_offers()
    reqs = [r for r in requests.read_all() if r.get("event") == "request"]
    out = []
    for req in reqs:
        for off in offs:
            if req["email"] == off["email"]:
                continue  # WHY: nu potrivim un lead cu propria lui oferta
            s = _score(off.get("tags"), req.get("tags"))
            if s >= min_score:
                out.append({
                    "score": s,
                    "request_email": req["email"],
                    "request_tags": req.get("tags"),
                    "offer_email": off["email"],
                    "offer_campaign": off.get("campaign"),
                    "offer_tags": off.get("tags"),
                    "common": sorted(set(off.get("tags", [])) & set(req.get("tags", []))),
                })
    out.sort(key=lambda m: m["score"], reverse=True)
    return out


def _main():
    p = argparse.ArgumentParser(description="Match automat oferta<->cerere")
    p.add_argument("--min-score", type=int, default=1,
                   help="minim tag-uri comune (default 1)")
    p.add_argument("--save", action="store_true", help="scrie matches.jsonl")
    args = p.parse_args()
    matches = match_all(args.min_score)
    for m in matches:
        print(json.dumps(m, ensure_ascii=True))
    if args.save:
        os.makedirs(os.path.dirname(MATCHES_OUT), exist_ok=True)
        with open(MATCHES_OUT, "w", encoding="utf-8") as fh:
            for m in matches:
                fh.write(json.dumps(m, ensure_ascii=True) + "\n")
        sys.stderr.write("saved %d matches -> %s\n" % (len(matches), MATCHES_OUT))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
