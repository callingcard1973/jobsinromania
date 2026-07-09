#!/usr/bin/env python3
"""Drain rule-ambiguous emails (intent='other') through agent 05 LLM classifier.

WHY: rule_labeler.py defers ambiguous emails "for Claude" but nothing processes them
(6,219 'other' rows in labels.db as of 2026-06-15). Agent 05 works on the free
NVIDIA/OpenRouter chain (no Claude). This script bridges the gap: read backlog,
classify via 05_email_classifier_agent.classify_single, write back to labels.db.

Maps agent-05 categories to labels.db intent schema. Caps per run for free-tier
rate limits. Idempotent (skips already-LLM-labeled rows).
"""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, "/opt/ACTIVE/AGENTS")
import importlib.util

spec = importlib.util.spec_from_file_location("a5", "/opt/ACTIVE/AGENTS/05_email_classifier_agent.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

LABELS_DB = Path("/opt/ACTIVE/EMAIL/PROCESSORS/data/training_data/labels.db")

CAT_TO_INTENT = {
    "ORDER": "inquiry",
    "QUESTION": "inquiry",
    "REJECTION": "other",
    "BOUNCE": "bounce",
    "AUTORESPONDER": "auto_reply",
    "SPAM": "newsletter",
    "UNKNOWN": "other",
}


def _body_from_raw(raw_json: str) -> str:
    try:
        d = json.loads(raw_json) if raw_json else {}
        if isinstance(d, dict):
            return (d.get("body") or d.get("text") or d.get("snippet") or "")[:2000]
    except (json.JSONDecodeError, TypeError):
        pass
    return ""


def fetch_backlog(conn, limit):
    """Rows labeled 'other' by rule-based model, not yet LLM-processed."""
    return conn.execute(
        """SELECT dedup_key, from_addr, subject, raw_email_json
           FROM labels
           WHERE intent='other' AND model='rule-based-v1'
           LIMIT ?""",
        (limit,),
    ).fetchall()


def classify_row(subject, from_addr, raw_json):
    body = _body_from_raw(raw_json)
    return agent.classify_single(subject or "", body, from_addr or "")


def update_row(conn, dedup_key, intent, raw_result, workers=None):
    conn.execute(
        """UPDATE labels SET intent=?, claude_response=?, model='agent05-llm',
              tokens_out=NULL, labeled_at=datetime('now')
           WHERE dedup_key=?""",
        (intent, json.dumps(raw_result, ensure_ascii=False)[:4000], dedup_key),
    )
    if workers and intent == "inquiry":
        conn.execute(
            "UPDATE labels SET priority='HIGH' WHERE dedup_key=? AND priority IS NULL",
            (dedup_key,),
        )


def run(limit, delay, dry):
    conn = sqlite3.connect(str(LABELS_DB))
    rows = fetch_backlog(conn, limit)
    print(f"[backlog] {len(rows)} rows queued (cap={limit}, delay={delay}s, dry={dry})")
    counts, orders = {}, []
    for i, (key, frm, subj, raw) in enumerate(rows, 1):
        try:
            r = classify_row(subj, frm, raw)
            cat = r.get("category", "UNKNOWN")
            intent = CAT_TO_INTENT.get(cat, "other")
            counts[cat] = counts.get(cat, 0) + 1
            if not dry:
                update_row(conn, key, intent, r, r.get("workers_requested"))
            if cat == "ORDER":
                orders.append((frm, subj, r.get("workers_requested"), r.get("company_name")))
            if i % 10 == 0:
                print(f"  {i}/{len(rows)} classified; committing")
                if not dry:
                    conn.commit()
        except Exception as e:
            print(f"  FAIL {key}: {e}")
        if delay:
            time.sleep(delay)
    if not dry:
        conn.commit()
    conn.close()
    print("\n=== SUMMARY ===")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {n}")
    if orders:
        print(f"\n*** {len(orders)} ORDER(s) — HIGH priority leads ***")
        for frm, subj, w, co in orders[:20]:
            print(f"  - {co or frm}: {w} workers | {subj[:45]}")
    remaining = sqlite3.connect(str(LABELS_DB)).execute(
        "SELECT count(*) FROM labels WHERE intent='other' AND model='rule-based-v1'"
    ).fetchone()[0]
    print(f"\nRemaining 'other' backlog: {remaining}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50, help="emails per run (free-tier cap)")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between LLM calls")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run(args.limit, args.delay, args.dry_run)


if __name__ == "__main__":
    main()
