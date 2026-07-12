#!/usr/bin/env python3
"""Filter a recipient list against the sent-once ledger before a campaign send.

Reads emails from a CSV column (or a plain one-per-line file), drops those
already contacted in the same group or within the cooldown window, and writes
the allowed set. Does NOT record sends (the sender does that) and does NOT
touch DNC (kept as a separate hard-suppression step).
"""
import argparse
import csv
import json
import sys

from groups import group_for
from sent_once import DEFAULT_DB, SentOnceLedger, normalize_email


def _read_emails(path, column):
    with open(path, newline="", encoding="utf-8") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        if "," in sample or ";" in sample:
            reader = csv.DictReader(fh)
            if reader.fieldnames and column in reader.fieldnames:
                return [row[column] for row in reader]
            fh.seek(0)
        return [line.strip() for line in fh if line.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", help="Write allowed emails here")
    ap.add_argument("--column", default="email", help="CSV column with the email")
    ap.add_argument("--cooldown-days", type=int, default=None)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--record", action="store_true",
                    help="Also record the allowed set as sent (use post-send only)")
    args = ap.parse_args()

    group = group_for(args.campaign)
    emails = _read_emails(args.infile, args.column)
    with SentOnceLedger(args.db) as ledger:
        allowed, skipped = ledger.filter_new(
            emails, args.campaign, group, cooldown_days=args.cooldown_days
        )
        if args.record:
            ledger.record_many(
                (e, args.campaign, group, None)
                for e in allowed if normalize_email(e)
            )

    if args.outfile:
        with open(args.outfile, "w", encoding="utf-8") as fh:
            for e in allowed:
                fh.write(e + "\n")

    summary = {
        "campaign": args.campaign,
        "group": group,
        "input": len(emails),
        "allowed": len(allowed),
        "skipped": len(skipped),
        "cooldown_days": args.cooldown_days,
    }
    print(json.dumps(summary, indent=2, sort_keys=True), file=sys.stderr)


if __name__ == "__main__":
    main()
