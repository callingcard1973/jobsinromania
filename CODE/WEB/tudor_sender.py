#!/usr/bin/env python3
"""
TUDOR_ANOFM Campaign Sender

Usage:
    python3 tudor_sender.py [--limit N] [--test] [--force]
    python3 tudor_sender.py --status
    python3 tudor_sender.py --preview
    python3 tudor_sender.py --add-contacts FILE.csv
    python3 tudor_sender.py --mark-bounced EMAIL
    python3 tudor_sender.py --mark-dnc EMAIL
"""
import argparse
import random
import time
from datetime import date, datetime
from pathlib import Path

from sender_db     import (get_db, load_state, save_state, export_status,
                            get_status_dict, add_contacts, mark_status, init_db)
from sender_mail   import send_with_fallback, GMAIL_LIMIT, BREVO_LIMIT, gmail_available
from sender_config import (is_business_hours, load_senders, load_sectors,
                            load_signatures, get_sector_brevo, get_signature,
                            load_template, personalize, _sender_site)

CAMPAIGN_NAME = "TUDOR_ANOFM"
DELAY_MIN = 180
DELAY_MAX = 240
BREVO_BOUNCE_THRESHOLD = 0.30
BREVO_BOUNCE_CHECK_EVERY = 10  # check after every N Brevo sends


def check_brevo_bounce_rate(api_key: str) -> float:
    """Returns bounce rate 0.0-1.0 for last 7 days via Brevo API."""
    import requests as _req
    try:
        resp = _req.get(
            "https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
            headers={"api-key": api_key},
            params={"days": 7},
            timeout=10,
        )
        if resp.status_code != 200:
            return 0.0
        d = resp.json()
        delivered = d.get("delivered", 0)
        bounced   = d.get("hardBounces", 0) + d.get("softBounces", 0)
        total     = delivered + bounced
        return bounced / total if total > 0 else 0.0
    except Exception:
        return 0.0


SENT_LOG = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_TUDOR_MIGRATED_TO_RASPI/sent_log.csv")


def _append_sent_log(contact, subject, method, job_title_sent, timestamp):
    import csv
    write_header = not SENT_LOG.exists()
    with open(SENT_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp", "email", "company", "city", "sector", "position", "subject", "method"])
        w.writerow([
            timestamp,
            contact.get("email", ""),
            contact.get("company", ""),
            contact.get("city", ""),
            contact.get("sector", ""),
            job_title_sent,
            subject,
            method,
        ])


def run_send(args, state, today):
    conn = get_db(); cur = conn.cursor()
    CONSUMER_DOMAINS = ("gmail.", "yahoo.", "hotmail.", "outlook.", "live.")
    corporate_order = (
        "CASE WHEN " +
        " OR ".join(f"email LIKE '%{d}%'" for d in CONSUMER_DOMAINS) +
        " THEN 1 ELSE 0 END, RANDOM()"
    )
    EXCLUDED_SECTORS = ("comert", "horeca", "vanzari", "it", "paza")
    excluded_sql = " AND sector NOT IN ({})".format(",".join("?" * len(EXCLUDED_SECTORS)))
    # LIFO: newest contacts first (id DESC), corporate before consumer within same batch
    lifo_order = f"id DESC, {corporate_order}"

    if getattr(args, "sector", None) and args.sector != "general":
        cur.execute(
            "SELECT id,email,company,city,first_name,last_name,contact_name,position,county,sector "
            f"FROM contacts WHERE status='pending' AND sector=? ORDER BY {lifo_order} LIMIT ?",
            (args.sector, args.limit)
        )
    elif getattr(args, "sector", None) == "general":
        cur.execute(
            "SELECT id,email,company,city,first_name,last_name,contact_name,position,county,sector "
            f"FROM contacts WHERE status='pending' AND (sector='general' OR sector IS NULL OR sector=''){excluded_sql} ORDER BY {lifo_order} LIMIT ?",
            (*EXCLUDED_SECTORS, args.limit)
        )
    else:
        cur.execute(
            "SELECT id,email,company,city,first_name,last_name,contact_name,position,county,sector "
            f"FROM contacts WHERE status='pending'{excluded_sql} ORDER BY {lifo_order} LIMIT ?",
            (*EXCLUDED_SECTORS, args.limit)
        )
    contacts = [dict(r) for r in cur.fetchall()]

    senders    = load_senders()
    sectors    = load_sectors()
    signatures = load_signatures()
    subj_tpl, body_tpl = load_template()

    from sender_db import get_stats
    stats = get_stats()
    print(f"=== {CAMPAIGN_NAME} ===")
    print(f"Pending: {stats.get('pending',0)}  Sent: {stats.get('sent',0)}")
    from sender_mail import A2_LIMIT
    print(f"Gmail: {state['gmail_today']}/{GMAIL_LIMIT}  Brevo: {state['brevo_today']}/{BREVO_LIMIT}  A2: {state.get('a2_today',0)}/{A2_LIMIT}")

    if not contacts:
        print("No pending contacts"); conn.close(); return

    brevo_run_limit  = args.brevo_limit    # max Brevo sends this run
    gmail_run_limit  = args.gmail_per_run  # max per Gmail account this run
    a2_run_limit     = args.a2_limit       # max A2 sends this run
    brevo_run_count  = 0
    a2_run_count     = 0
    gmail_run_counts = {}  # account → count this run
    brevo_since_check = 0  # Brevo sends since last bounce check

    CONSUMER_VERIFY_SKIP = ("gmail.", "yahoo.", "hotmail.", "outlook.", "live.", "icloud.")
    try:
        import sys as _sys
        _sys.path.insert(0, "/opt/ACTIVE/INFRA/SKILLS")
        from email_mx_verifier import verify_email as _verify_email
        mx_verifier_available = True
    except ImportError:
        mx_verifier_available = False

    sent = 0
    for i, contact in enumerate(contacts):
        if state["gmail_today"] >= GMAIL_LIMIT and state["brevo_today"] >= BREVO_LIMIT:
            print("Daily limits reached"); break

        email = contact["email"]
        is_consumer = any(d in email for d in CONSUMER_DOMAINS)

        if mx_verifier_available and not is_consumer:
            res = _verify_email(email)
            if not res["valid"]:
                print(f"  [mx-skip] {email} invalid ({res.get('reason','')})")
                cur.execute("UPDATE contacts SET status='bounced' WHERE id=?", (contact["id"],))
                conn.commit()
                continue
            if res.get("typo_fixed") and res["email"] != email:
                cur.execute("UPDATE contacts SET email=? WHERE id=?", (res["email"], contact["id"]))
                conn.commit()
                contact["email"] = res["email"]
                email = res["email"]

        brevo_cfg = get_sector_brevo(contact.get("sector"), senders)
        sig       = get_signature(brevo_cfg, signatures)
        site      = _sender_site(brevo_cfg.get("email", ""))
        subject   = personalize(subj_tpl, contact, sectors, sig, site)
        body      = personalize(body_tpl, contact, sectors, sig, site)

        is_consumer = any(d in contact["email"] for d in ("gmail.", "yahoo.", "hotmail.", "outlook.", "live."))

        if is_consumer and gmail_run_limit is not None:
            # find which gmail account would be used
            from sender_mail import _gmail_sender
            acc, _ = _gmail_sender(state)
            if acc:
                runs_this_acc = gmail_run_counts.get(acc["email"], 0)
                if runs_this_acc >= gmail_run_limit:
                    print(f"  skip {contact['email']} — gmail account {acc['email']} at run limit ({gmail_run_limit})")
                    continue
        elif not is_consumer and brevo_run_limit is not None:
            if brevo_run_count >= brevo_run_limit:
                print(f"  skip {contact['email']} — brevo run limit reached ({brevo_run_limit})")
                continue
            if a2_run_limit is not None and a2_run_count >= a2_run_limit:
                print(f"  skip {contact['email']} — a2 run limit reached ({a2_run_limit})")
                continue

        ok, method, _, _ = send_with_fallback(
            contact["email"], subject, body, state, brevo_cfg, args.test)

        if ok:
            method_clean = method.replace("_FALLBACK", "")
            if not args.test:
                now = datetime.now().isoformat()
                job_sent = contact.get("position") or ""
                cur.execute(
                    "UPDATE contacts SET status='sent',sent_at=?,sent_via=?,job_title_sent=? WHERE id=?",
                    (now, method_clean.lower(), job_sent, contact["id"]))
                conn.commit()
                _append_sent_log(contact, subject, method_clean, job_sent, now)
                state["total_sent"] += 1
            if "BREVO" in method_clean:
                state["brevo_today"] += 1
                brevo_run_count  += 1
                brevo_since_check += 1
                if brevo_since_check >= BREVO_BOUNCE_CHECK_EVERY:
                    brevo_since_check = 0
                    rate = check_brevo_bounce_rate(brevo_cfg.get("api_key", ""))
                    pct = round(rate * 100, 1)
                    print(f"  [bounce check] Brevo bounce rate: {pct}%")
                    if rate >= BREVO_BOUNCE_THRESHOLD:
                        print(f"  [STOP] Bounce rate {pct}% >= 30%. Stopping Brevo sends.")
                        conn.close()
                        return
            elif "A2" in method_clean:
                state["a2_today"] = state.get("a2_today", 0) + 1
                a2_run_count += 1
            elif "GMAIL" in method_clean.upper():
                # track per-account run count
                from sender_mail import _gmail_sender
                acc, _ = _gmail_sender(state)
                if acc:
                    gmail_run_counts[acc["email"]] = gmail_run_counts.get(acc["email"], 0) + 1
            # gmail_today updated inside send_gmail via _increment_gmail
            sent += 1
            tag = " [TEST]" if args.test else ""
            print(f"[{i+1}/{len(contacts)}] {contact['email']} via {method_clean}{tag} ({contact.get('sector','?')})")
        else:
            print(f"[{i+1}/{len(contacts)}] FAIL {contact['email']}: {method}")

        save_state(state)
        bh_ok, bh_reason = is_business_hours()
        export_status(state, bh_ok, bh_reason)

        if i < len(contacts) - 1 and not args.test:
            delay = random.randint(DELAY_MIN, DELAY_MAX)
            print(f"  waiting {delay}s...")
            time.sleep(delay)

    conn.close()
    print(f"\nSent {sent}  Gmail: {state['gmail_today']}/{GMAIL_LIMIT}  Brevo: {state['brevo_today']}/{BREVO_LIMIT}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",         type=int, default=50)
    parser.add_argument("--test",          action="store_true")
    parser.add_argument("--force",         action="store_true")
    parser.add_argument("--status",        action="store_true")
    parser.add_argument("--preview",       action="store_true")
    parser.add_argument("--add-contacts",  metavar="CSV")
    parser.add_argument("--mark-bounced",  metavar="EMAIL")
    parser.add_argument("--mark-dnc",      metavar="EMAIL")
    parser.add_argument("--sector",        metavar="SECTOR", default=None)
    parser.add_argument("--brevo-limit",   type=int, default=None)
    parser.add_argument("--gmail-per-run", type=int, default=None)
    parser.add_argument("--a2-limit",      type=int, default=None)
    args = parser.parse_args()

    init_db()
    state = load_state()
    today = date.today().isoformat()
    if state.get("last_date") != today:
        state.update({"last_date": today, "gmail_today": 0, "brevo_today": 0, "a2_today": 0, "gmail_counts": {}})
        save_state(state)

    bh_ok, bh_reason = is_business_hours()
    export_status(state, bh_ok, bh_reason)

    if args.add_contacts:
        a, s = add_contacts(args.add_contacts)
        print(f"Added {a}, skipped {s}"); return

    if args.mark_bounced:
        mark_status(args.mark_bounced, "bounced"); print("Marked bounced"); return

    if args.mark_dnc:
        mark_status(args.mark_dnc, "dnc"); print("Marked DNC"); return

    if args.status:
        import json
        print(json.dumps(get_status_dict(state, bh_ok, bh_reason), indent=2)); return

    if args.preview:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM contacts WHERE status='pending' LIMIT 1")
        row = cur.fetchone(); conn.close()
        if row:
            contact = dict(row)
            senders = load_senders(); sectors = load_sectors(); signatures = load_signatures()
            subj_tpl, body_tpl = load_template()
            brevo_cfg = get_sector_brevo(contact.get("sector"), senders)
            print(f"To:      {contact['email']}")
            print(f"Sender:  {brevo_cfg['email']}")
            print(f"Sector:  {contact.get('sector')}")
            sig  = get_signature(brevo_cfg, signatures)
            site = _sender_site(brevo_cfg.get("email", ""))
            print(f"Subject: {personalize(subj_tpl, contact, sectors, sig, site)}")
            print("---")
            print(personalize(body_tpl, contact, sectors, sig, site))
        return

    if not args.force and not bh_ok:
        print(f"Outside business hours: {bh_reason}  (--force to override)"); return

    run_send(args, state, today)


if __name__ == "__main__":
    main()
