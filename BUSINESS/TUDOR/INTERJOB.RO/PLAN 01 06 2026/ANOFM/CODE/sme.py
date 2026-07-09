#!/usr/bin/env python3
"""campaign_factory.py — gentle factory outreach (clone of campaign_primarii.py).
Gmail-only, daily-cap + delay throttle, DNC suppression, gated-by-reply (no attachment).
Usage: python campaign_factory.py [--dry-run] [--limit N] [--gmail-only] [--daily-cap N] [--delay S]
"""
import argparse, csv, json, logging, os, sys, time
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED')
import sender
try:
    from dnc_utils import add_to_dnc as _add_to_dnc
except ImportError:
    _add_to_dnc = None

from datetime import date
from pathlib import Path

BASE = Path(__file__).parent.parent
CSV_FILE  = Path(os.environ.get("CSV_FILE",  BASE / "DATA/factory_ro_verified.csv"))
SENT_FILE = Path(os.environ.get("SENT_FILE", BASE / "DATA/campaign_sent.json"))
LOG_FILE  = Path(os.environ.get("LOG_FILE",  BASE / "LOGS/campaign_factory.log"))

SENDER       = "office@warehouseworkers.eu"
SENDER_NAME  = "InterJob - WarehouseWorkers.eu"
REPLY_TO     = "office@warehouseworkers.eu"
BREVO_KEY    = os.environ.get("BREVO_WAREHOUSEWORKERS_API_KEY",
               "REDACTED")
SUBJECT      = "Personal verificat disponibil - catalog la cerere"

EMAIL_BODY = """\
{greeting}

Va putem trimite un catalog actualizat cu candidati disponibili pentru productie.
Raspundeti la acest email cu CUI-ul firmei si domeniile de interes.

Cu stima,
Tudor Seicarescu - InterJob / Manpower
"""

TEMPLATE_FILE = Path(os.environ.get("TEMPLATE_FILE", BASE / "TEMPLATES/SME_OCUPATII_DEFICITARE_RO.txt"))
if TEMPLATE_FILE.exists():
    _lines = TEMPLATE_FILE.read_text(encoding="utf-8").splitlines()
    for _i, _l in enumerate(_lines):
        if _l.upper().startswith("SUBIECT:"):
            SUBJECT = _l.split(":", 1)[1].strip()
            _body = "\n".join(_lines[_i + 1:]).lstrip("\n")
            if _body.strip():
                EMAIL_BODY = _body
            break

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()])
log = logging.getLogger(__name__)


def load_sent():
    if SENT_FILE.exists():
        return json.loads(SENT_FILE.read_text(encoding="utf-8"))
    return {"total": 0, "by_date": {}, "emails": []}


def save_sent(sent):
    SENT_FILE.write_text(json.dumps(sent, ensure_ascii=False, indent=2), encoding="utf-8")


def load_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_greeting(row):
    company = (row.get("company") or "").strip()
    return f"Stimata echipa {company}," if company else "Buna ziua,"


def load_dnc():
    """Suppressed/bounced emails harvested by gmail_bounce_cleaner.py (DB dnc_list + file)."""
    dnc = set()
    try:
        import psycopg2
        for cfg in ({"host": "localhost", "dbname": "email_sender", "user": "tudor", "password": "tudor123"},
                    {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "scraper123"}):
            try:
                conn = psycopg2.connect(**cfg)
                with conn.cursor() as cur:
                    cur.execute("SELECT email FROM dnc_list")
                    dnc.update((r[0] or "").lower().strip() for r in cur.fetchall())
                conn.close()
                break
            except Exception:
                continue
    except ImportError:
        pass
    f = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt")
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                dnc.add(line.split(",")[0].lower().strip())
    return {e for e in dnc if e}


def send_brevo(to_email, subject, body, dry_run):
    if dry_run:
        log.info(f"[DRY-RUN][BREVO] -> {to_email} | subj: {subject}")
        return True
    ok, status = sender.send_brevo(BREVO_KEY, SENDER, SENDER_NAME, to_email, subject, body)
    if ok:
        log.info(f"SENT {to_email}")
    else:
        log.error(f"BREVO_ERR {to_email} — {status}")
        if status.startswith("HTTP_4") and 'invalid' in status.lower() and _add_to_dnc:
            _add_to_dnc(to_email, reason='bounce_brevo_invalid', source='brevo_send')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--delay", type=int, default=0)
    ap.add_argument("--gmail-only", action="store_true")
    ap.add_argument("--daily-cap", type=int, default=0)
    args = ap.parse_args()

    rows = load_csv(CSV_FILE)
    sent = load_sent()
    today = str(date.today())
    sent_all = {(e or "").lower().strip() for e in sent["emails"]}
    dnc = load_dnc()
    if dnc:
        sent_all |= dnc
        log.info(f"DNC suppressed: {len(dnc)} emails skipped")

    eff_limit = args.limit
    if args.daily_cap:
        already = len(sent["by_date"].get(today, []))
        eff_limit = max(0, min(args.limit, args.daily_cap - already))
        log.info(f"daily_cap={args.daily_cap} already_today={already} eff_limit={eff_limit}")

    eligible = sum(1 for r in rows if (r.get("email") or "").strip().lower() not in sent_all
                   and (r.get("email") or "").strip())
    log.info(f"rows={len(rows)} eligible(after sent+dnc)={eligible}")

    sent_this_run = consec_fail = 0
    for row in rows:
        if sent_this_run >= eff_limit:
            break
        email = (row.get("email") or "").strip()
        if not email or email.lower() in sent_all:
            continue
        greeting = build_greeting(row)
        body = EMAIL_BODY.format(greeting=greeting)
        ok = send_brevo(email, SUBJECT, body, args.dry_run)
        if ok:
            consec_fail = 0
            sent_this_run += 1
            sent_all.add(email.lower())
            if not args.dry_run:
                sent["emails"].append(email)
                sent["by_date"].setdefault(today, []).append(email)
                sent["total"] += 1
                save_sent(sent)
                if args.delay and sent_this_run < eff_limit:
                    time.sleep(args.delay)
        else:
            consec_fail += 1
            if consec_fail >= 5 and not args.dry_run:
                log.error("5 esecuri consecutive — oprire")
                break

    log.info(f"--- sent_this_run={sent_this_run} total={sent['total']} eligible={eligible} ---")


if __name__ == "__main__":
    main()
