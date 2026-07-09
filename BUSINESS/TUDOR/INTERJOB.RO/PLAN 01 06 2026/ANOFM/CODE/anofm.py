#!/usr/bin/env python3
"""Campanie ANOFM angajatori activi - Brevo warehouseworkers.eu.

Sursa unica de suprimare = anofm DB pe raspi: dnc_master (DNC) + send_log
(tot istoricul ANOFM, ce/unde/cand). sent.csv ramane mirror secundar."""
import argparse, csv, logging, os, sys, time
from datetime import date
from pathlib import Path

import psycopg2

sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED")
import sender

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BASE        = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI")
CSV_FILE    = BASE / "DATA" / "anofm_angajatori_dedup.csv"
SENT_LOG    = BASE / "DATA" / "sent.csv"
TPL_FILE    = BASE / "TEMPLATES" / "template_anofm_angajatori.txt"
DB          = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
CAMPAIGN    = "ANOFM_ANGAJATORI"

SENDER      = "office@warehouseworkers.eu"
SENDER_NAME = "Elena Vasilescu - InterJob.ro"
REPLY_TO    = "office@interjob.ro"
# Gmail/Yahoo bulk-sender compliance: opt-out via mail to unsubscribe@interjob.ro
# (forwarded to office@interjob.ro -> universal_reply_handler -> dnc_master).
UNSUB_HEADERS = {"List-Unsubscribe": "<mailto:unsubscribe@interjob.ro?subject=unsubscribe>"}
BREVO_KEY   = os.environ.get("BREVO_WAREHOUSEWORKERS_API_KEY",
              "xkeysib-REDACTED")
DELAY       = 12


def db_set(cur, query):
    cur.execute(query)
    return {r[0].strip().lower() for r in cur.fetchall() if r[0]}


def log_send(cur, em, row):
    # single source of truth: ce (email/company), unde (sector/campaign), cand (sent_at)
    cur.execute(
        "INSERT INTO send_log(email,company,sector,campaign,sender,method,status,sent_at) "
        "VALUES(%s,%s,%s,%s,%s,'brevo','sent',now())",
        (em, row.get("company_name", ""), row.get("sector", ""), CAMPAIGN, SENDER))


def send_brevo(to_email, subject, body, dry_run):
    if dry_run:
        log.info(f"[DRY-RUN] -> {to_email}")
        return True
    ok, status = sender.send_brevo(BREVO_KEY, SENDER, SENDER_NAME, to_email, subject, body,
                                   reply_to=REPLY_TO, headers=UNSUB_HEADERS)
    log.info(f"SENT {to_email}" if ok else f"FAILED {to_email} - {status}")
    return ok


def parse_template(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].startswith("Subject:"), "Template invalid: prima linie trebuie sa fie Subject: ..."
    subject = lines[0].split(":", 1)[1].strip()
    body    = "\n".join(lines[2:]).lstrip("\n")
    return subject, body


def fill_placeholders(text, row):
    placeholders = {
        "company_name":        row.get("company_name", ""),
        "sector":              row.get("sector", ""),
        "county":              row.get("county", ""),
        "job_title":           row.get("job_title", ""),
        "positions_available": row.get("positions_available", ""),
    }
    for key, val in placeholders.items():
        text = text.replace("{" + key + "}", (val or "").strip())
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit",   type=int, default=290)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=int, default=DELAY)
    ap.add_argument("--daily-cap", type=int, default=0)
    args = ap.parse_args()
    if args.daily_cap:
        args.limit = min(args.limit, args.daily_cap)

    subject_tpl, body_tpl = parse_template(TPL_FILE)
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    # single source of truth: dnc_master (DNC, incl opt-out replies) + send_log (all ANOFM history)
    dnc  = db_set(cur, "SELECT lower(email) FROM dnc_master")
    sent = db_set(cur, "SELECT lower(email) FROM send_log")
    log.info(f"DNC: {len(dnc)} | Sent(history): {len(sent)}")

    write_header = not SENT_LOG.exists()
    SENT_LOG.parent.mkdir(exist_ok=True)
    count = 0

    with open(CSV_FILE) as src, open(SENT_LOG, "a", newline="") as sf:
        w = csv.writer(sf)
        if write_header:
            w.writerow(["email", "company", "sector", "date"])

        for r in csv.DictReader(src):
            if count >= args.limit:
                break
            em = r.get("email", "").strip().lower()
            if not em or em in dnc or em in sent:
                continue
            subject = fill_placeholders(subject_tpl, r)
            body    = fill_placeholders(body_tpl, r)
            ok = send_brevo(em, subject, body, args.dry_run)
            if ok:
                sent.add(em)
                count += 1
                if not args.dry_run:
                    log_send(cur, em, r)              # DB unic: ce/unde/cand
                    conn.commit()                    # durable per-send (crash can't re-send)
                    w.writerow([em, r.get("company_name", ""), r.get("sector", ""), date.today()])
                    time.sleep(args.delay)

    cur.close()
    conn.close()
    log.info(f"Trimise: {count}")


if __name__ == "__main__":
    main()
