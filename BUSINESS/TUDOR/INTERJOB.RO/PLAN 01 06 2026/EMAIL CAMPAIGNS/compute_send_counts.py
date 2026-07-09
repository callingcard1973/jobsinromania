#!/usr/bin/env python3
"""Reconcile real email send counts from dated per-campaign logs.

Writes an authoritative send_counts_today.json next to the orchestrator state.
Deliberately does NOT touch campaign_orchestrator_state.json — the orchestrator
reads daily_counts for rate-limiting and owns that file.
"""
import glob
import json
import os
import re
from datetime import datetime

LOG_DIR = "/opt/ACTIVE/INFRA/LOGS/campaigns"
OUT_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/send_counts_today.json"
SENT_RE = re.compile(r"\bSENT\b")


def count_today():
    day = datetime.now().strftime("%Y%m%d")
    per_campaign = {}
    for path in glob.glob(os.path.join(LOG_DIR, f"*_{day}.log")):
        name = os.path.basename(path).replace(f"_{day}.log", "")
        if name == "orchestrator":
            continue
        try:
            with open(path, errors="ignore") as fh:
                per_campaign[name] = sum(1 for ln in fh if SENT_RE.search(ln))
        except OSError:
            continue
    return per_campaign


def main():
    per_campaign = count_today()
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "total_sent_today": sum(per_campaign.values()),
        "per_campaign": dict(sorted(per_campaign.items(), key=lambda kv: -kv[1])),
    }
    tmp = OUT_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(payload, fh, indent=1)
    os.replace(tmp, OUT_FILE)
    print(f"{payload['date']} total_sent_today={payload['total_sent_today']} "
          f"across {len(per_campaign)} campaigns -> {OUT_FILE}")


if __name__ == "__main__":
    main()
