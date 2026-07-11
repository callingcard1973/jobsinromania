#!/usr/bin/env python3
"""GATED queue builder for TRADING ROBOT FRUIT cereale cold-outreach (bucket B).

Context: TRADING had NO cereale cold-email sender (cereale was inbound/phone).
Tudor's N2b decision: BOTH SILOZURI and TRADING do cold outbound on cereale,
splitting the list into disjoint deterministic halves (even md5 -> A=SILOZURI,
odd -> B=TRADING) with unified DNC + a shared cross-pipeline sent-log so no lead
is touched by both. This script wires TRADING's half of that gate.

It does NOT send. It only builds a queue of bucket-B, non-suppressed cereale leads
and prints the split/suppression counts. Real sending is the go-live step Tudor
approves (register in orchestrator + dashboard 8096 + DNC/monitoring).
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "CODE" / "02_dnc_suppression"))
import cereale_split_dnc as gate  # noqa: E402

MY_BUCKET = "B"  # TRADING keeps odd-md5 half; SILOZURI keeps "A".
OUT_QUEUE = Path(__file__).resolve().parent.parent / "DATA" / "CODA_cereale_bucket_B.csv"


def main():
    ap = argparse.ArgumentParser(description="TRADING cereale bucket-B queue (GATED, no sends).")
    ap.add_argument("--dry-run", action="store_true", help="Print counts + write queue; send nothing.")
    args = ap.parse_args()

    sil, tra = gate.split(apply_suppression=True)  # tra already = bucket B, DNC-filtered
    email_leads = [r for r in tra if r["key_type"] == "email"]
    phone_leads = [r for r in tra if r["key_type"] == "cui"]

    OUT_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_QUEUE.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["email", "name", "cui", "phone"])
        w.writeheader()
        for r in email_leads:
            w.writerow({k: r.get(k, "") for k in ("email", "name", "cui", "phone")})

    print(f"TRADING (B) email leads (queued): {len(email_leads)}")
    print(f"TRADING (B) phone-only leads (CUI pool): {len(phone_leads)}")
    print(f"SILOZURI (A) kept for the other pipeline: {len(sil)}")
    print(f"Queue -> {OUT_QUEUE}")
    if not args.dry_run:
        print("NOTE: no sender is wired here by design. This builds the gated queue only; "
              "sending is Tudor's go-live step (orchestrator + dashboard + monitoring).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
