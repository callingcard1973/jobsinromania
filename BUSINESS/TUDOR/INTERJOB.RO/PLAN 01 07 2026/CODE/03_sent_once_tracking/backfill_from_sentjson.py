#!/usr/bin/env python3
"""Backfill the sent-once ledger from existing per-campaign sent.json files.

Read-only over the source files; only writes the ledger. Handles the formats
seen in the wild: {"by_date": {date: [emails]}}, {"by_email": {email: ...}},
{"sent": [emails]}, and plain lists of emails.
"""
import argparse
import glob
import json
import os
from datetime import datetime, timezone

from groups import group_for, load_group_index
from sent_once import SentOnceLedger, normalize_email


def _iter_records(obj, default_ts):
    """Yield (email, ts) from a parsed sent.json of any known shape."""
    if isinstance(obj, dict):
        by_date = obj.get("by_date")
        if isinstance(by_date, dict):
            # by_date is the canonical full list when present. Some archived
            # files store per-day counts (int) instead of email lists; skip those.
            has_lists = any(isinstance(v, list) for v in by_date.values())
            if has_lists:
                for date_key, emails in by_date.items():
                    if not isinstance(emails, list):
                        continue
                    for e in emails:
                        yield e, date_key
                return
        emitted = False
        by_email = obj.get("by_email")
        if isinstance(by_email, dict):
            for e, meta in by_email.items():
                ts = default_ts
                if isinstance(meta, dict):
                    ts = meta.get("date") or meta.get("ts") or default_ts
                yield e, ts
                emitted = True
        for key in ("sent", "emails"):
            seq = obj.get(key)
            if isinstance(seq, list):
                for e in seq:
                    if isinstance(e, dict):
                        yield e.get("email"), e.get("date") or default_ts
                    else:
                        yield e, default_ts
                    emitted = True
        if emitted:
            return
        # Fallback: any string keys that look like emails
        for k in obj:
            if normalize_email(k):
                yield k, default_ts
    elif isinstance(obj, list):
        for e in obj:
            if isinstance(e, dict):
                yield e.get("email"), e.get("date") or default_ts
            else:
                yield e, default_ts


def campaign_from_path(path, base):
    rel = os.path.relpath(path, base)
    return rel.split(os.sep)[0]


def backfill(base, db_path, pattern="**/*sent*.json", dry_run=False):
    index = load_group_index()
    files = [f for f in glob.glob(os.path.join(base, pattern), recursive=True)
             if f.endswith(".json")]
    ledger = None if dry_run else SentOnceLedger(db_path)
    total_seen = 0
    total_inserted = 0
    per_campaign = {}
    for f in sorted(files):
        try:
            with open(f, encoding="utf-8") as fh:
                obj = json.load(fh)
        except (ValueError, OSError):
            continue
        campaign = campaign_from_path(f, base)
        group = group_for(campaign, index)
        mtime = datetime.fromtimestamp(os.path.getmtime(f), timezone.utc).date().isoformat()
        rows = []
        for email, ts in _iter_records(obj, mtime):
            if normalize_email(email) is None:
                continue
            total_seen += 1
            rows.append((email, campaign, group, ts))
        per_campaign[campaign] = per_campaign.get(campaign, 0) + len(rows)
        if ledger is not None and rows:
            total_inserted += ledger.record_many(rows)
    if ledger is not None:
        ledger.close()
    return {
        "files": len(files),
        "records_seen": total_seen,
        "records_inserted": total_inserted,
        "per_campaign": per_campaign,
        "dry_run": dry_run,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="/opt/ACTIVE/EMAIL/CAMPAIGNS",
                    help="Campaigns root containing per-campaign sent.json files")
    ap.add_argument("--db", default=None, help="Ledger sqlite path (default from env)")
    ap.add_argument("--dry-run", action="store_true", help="Count only, do not write")
    args = ap.parse_args()
    from sent_once import DEFAULT_DB
    db = args.db or DEFAULT_DB
    res = backfill(args.base, db, dry_run=args.dry_run)
    print(json.dumps(res, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
