#!/usr/bin/env python3
"""
campaign_primarii.py — Playground equipment email campaign for Romanian municipalities
Sender: tudor@agroevolution.com | Brevo API | Attach catalog_parcuri.pdf
Usage: python campaign_primarii.py [--dry-run] [--limit N]
"""
import argparse, csv, json, logging, os, sys, time
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED')
import sender
try:
    from spam_word_checker import check as _spam_check
except ImportError:
    _spam_check = None
try:
    from email_validator import is_valid_email as _is_valid_email
except ImportError:
    _is_valid_email = None
try:
    from dnc_utils import add_to_dnc as _add_to_dnc
except ImportError:
    _add_to_dnc = None
from datetime import date
from pathlib import Path

# --- Paths ---
BASE = Path(__file__).parent.parent
CSV_FILE      = Path(os.environ.get("CSV_FILE",      BASE / "DATA/primarii_campanie_enriched.csv"))
CSV_PRIMAR    = Path(os.environ.get("CSV_PRIMAR",    BASE / "DATA/primarii_campanie_cu_primar.csv"))
SENT_FILE     = Path(os.environ.get("SENT_FILE",     BASE / "DATA/campaign_sent.json"))
CATALOG_PDF   = Path(os.environ.get("CATALOG_PDF",   BASE / "CATALOGS/catalog_parcuri.pdf"))
LOG_FILE      = Path(os.environ.get("LOG_FILE",      BASE / "LOGS/campaign_primarii.log"))

# --- Config ---
SENDER_EMAIL  = os.environ.get("SENDER_EMAIL", "office@cumparlegume.com")
SENDER_NAME   = os.environ.get("SENDER_NAME", "Tudor Seicarescu - Cooperativa Gospodarii de Altadata")
REPLY_TO      = "office@cumparlegume.com"
SUBJECT       = "Echipamente loc de joacă certificate EN 1176 — ofertă pentru primăria dumneavoastră"

# --- Gmail SMTP (secondary sender, alternates for Yahoo recipients) ---
GMAIL_USER         = os.environ.get("GMAIL_USER", "telegestiuneprimarii@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

EMAIL_BODY = """\
{greeting}

Vă propunem echipamente pentru amenajarea și modernizarea locurilor de joacă și a spațiilor verzi din localitatea dumneavoastră.

Suntem distribuitor autorizat AVP Park (producător turc, certificat ISO), cu echipamente conforme standardului european de siguranță EN 1176. Oferim trei pachete adaptate bugetelor UAT:

  • ECONOMIC — 3.500–6.000 EUR | Structuri de bază, tobogan, leagăne
  • STANDARD — 6.000–12.000 EUR | Ansamblu complex, cauciuc de siguranță inclus
  • PREMIUM  — 12.000–25.000 EUR | Parc complet, mobilier urban, montaj inclus

Prețurile includ transport și documentație tehnică pentru dosar de achiziție.

Zeci de primării din România au amenajat deja locuri de joacă utilizând echipamentele noastre.

Vă stau la dispoziție pentru detalii sau o ofertă personalizată.
Răspundeți direct la acest email pentru catalogul PDF complet.

Cu stimă,
Tudor Seicărescu
AgroEvolution

P.S. Catalogul complet cu fotografii și specificații tehnice este atașat acestui email.
"""

# Editable template overrides the inline text above. Format: first "SUBIECT:" line
# is the subject; the body is everything after the first blank line ({greeting} kept).
TEMPLATE_FILE = Path(os.environ.get("TEMPLATE_FILE", BASE / "TEMPLATES/email_primarii.txt"))
if TEMPLATE_FILE.exists():
    _raw = TEMPLATE_FILE.read_text(encoding="utf-8")
    _lines = _raw.splitlines()
    for _i, _l in enumerate(_lines):
        if _l.upper().startswith("SUBIECT:"):
            SUBJECT = _l.split(":", 1)[1].strip()
            _body = "\n".join(_lines[_i + 1:]).lstrip("\n")
            if _body.strip():
                EMAIL_BODY = _body
            break

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def load_sent():
    if SENT_FILE.exists():
        return json.loads(SENT_FILE.read_text(encoding="utf-8"))
    return {"total": 0, "by_date": {}, "emails": []}


def save_sent(sent):
    SENT_FILE.write_text(json.dumps(sent, ensure_ascii=False, indent=2), encoding="utf-8")


def load_csv(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def build_greeting(row, primar_map):
    email = row.get("email", "").strip().lower()
    name = primar_map.get(email, "")
    if name:
        return f"Stimate domnule/doamnă Primar {name},"
    return "Stimate domnule Primar,"




def send_email(api_key, to_email, to_name, county, greeting, dry_run):
    body = EMAIL_BODY.format(greeting=greeting)
    if dry_run:
        log.info(f"[DRY-RUN] Would send to {to_email} ({to_name}, {county})")
        log.info(f"[DRY-RUN] Greeting: {greeting}")
        return True
    ok, status = sender.send_brevo(api_key, SENDER_EMAIL, SENDER_NAME, to_email,
                                   SUBJECT, body, reply_to=REPLY_TO)
    log.info(f"SENT {to_email} ({county})" if ok else f"FAILED {to_email} — {status}")
    return ok


def send_gmail(to_email, to_name, subject, body, dry_run):
    if dry_run:
        log.info(f"[DRY-RUN][GMAIL] Would send to {to_email} ({to_name})")
        return True

    if _is_valid_email and not _is_valid_email(to_email)[0]:
        log.warning(f"SKIP invalid email: {to_email} — {_is_valid_email(to_email)[1]}")
        return False
    ok, status = sender.send_gmail(GMAIL_USER, GMAIL_APP_PASSWORD,
                                   "Tudor Seicarescu - Cooperativa Gospodarii de Altadata",
                                   to_email, to_name or "Primar", subject, body, reply_to=REPLY_TO)
    if ok:
        log.info(f"SENT {to_email} (gmail)")
    else:
        log.error(f"FAILED {to_email} — gmail {status}")
        if status.startswith("refused:") and _add_to_dnc:
            _add_to_dnc(to_email, reason='bounce_smtp_rejected', source='PRIMARII_send')
    return ok


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--delay", type=int, default=0, help="seconds to sleep between sends (gentle)")
    parser.add_argument("--gmail-only", action="store_true", help="send everything via Gmail SMTP (no Brevo)")
    parser.add_argument("--daily-cap", type=int, default=0, help="max total sent per calendar day (idempotent cron guard)")
    args = parser.parse_args()

    api_key = os.environ.get("BREVO_API_KEY") or os.environ.get("BREVO_BUILDJOBS_API_KEY")
    if not api_key and not args.dry_run and not args.gmail_only:
        sys.exit("ERROR: Set BREVO_API_KEY or BREVO_BUILDJOBS_API_KEY env var")
    if args.gmail_only and not GMAIL_APP_PASSWORD and not args.dry_run:
        sys.exit("ERROR: Set GMAIL_APP_PASSWORD env var for --gmail-only")

    if _spam_check:
        _issues = _spam_check(subject=SUBJECT, body=EMAIL_BODY)
        for _w in _issues:
            log.warning(f'SPAM WARNING: {_w}')
    rows = load_csv(CSV_FILE)
    primar_map = {}
    if CSV_PRIMAR.exists():
        for r in load_csv(CSV_PRIMAR):
            em = r.get("email", "").strip().lower()
            nm = r.get("primar", "").strip()
            if em and nm:
                primar_map[em] = nm
        log.info(f"Loaded {len(primar_map)} mayor names from cu_primar CSV")

    sent = load_sent()
    today = str(date.today())
    sent_today_emails = set(sent["by_date"].get(today, []))
    sent_all = {(e or "").lower().strip() for e in sent["emails"]}
    dnc = load_dnc()
    if dnc:
        sent_all |= dnc
        log.info(f"DNC suppressed: {len(dnc)} bounced/invalid emails will be skipped")

    eff_limit = args.limit
    if args.daily_cap:
        already_today = len(sent["by_date"].get(today, []))
        eff_limit = max(0, min(args.limit, args.daily_cap - already_today))
        log.info(f"daily_cap={args.daily_cap}, already_today={already_today}, eff_limit={eff_limit}")

    sent_this_run = 0
    skipped = 0
    yahoo_idx = 0
    consec_fail = 0

    for row in rows:
        if sent_this_run >= eff_limit:
            break
        email = row.get("email", "").strip()
        if not email or email.lower() in sent_all:
            skipped += 1
            continue

        name   = row.get("name", "").strip()
        county = row.get("county", "").strip()
        greeting = build_greeting(row, primar_map)

        domain = email.split("@", 1)[1].lower() if "@" in email else ""
        is_yahoo = domain.startswith("yahoo.")
        if args.gmail_only:
            use_gmail = True
        else:
            use_gmail = is_yahoo and (yahoo_idx % 2 == 1)
            if is_yahoo:
                yahoo_idx += 1

        # Gmail without an app password can't authenticate — fall back to Brevo.
        if use_gmail and not GMAIL_APP_PASSWORD and not args.dry_run:
            log.warning(f"gmail app password missing, falling back to Brevo for {email}")
            use_gmail = False

        if use_gmail:
            log.info(f"ROUTE {email} via=gmail")
            ok = send_gmail(email, name, SUBJECT, EMAIL_BODY.format(greeting=greeting), args.dry_run)
        else:
            log.info(f"ROUTE {email} via=brevo")
            ok = send_email(api_key, email, name, county, greeting, args.dry_run)
        if ok:
            consec_fail = 0
            sent_this_run += 1
            sent_all.add(email.lower())
            sent_today_emails.add(email)
            if not args.dry_run:
                sent["emails"].append(email)
                sent["by_date"].setdefault(today, []).append(email)
                sent["total"] += 1
                save_sent(sent)
            if args.delay and not args.dry_run and sent_this_run < eff_limit:
                time.sleep(args.delay)
        else:
            consec_fail += 1
            if consec_fail >= 5 and not args.dry_run:
                log.error("5 esecuri consecutive de trimitere — oprire (verifica parola/SMTP)")
                break

    remaining = sum(1 for r in rows if (r.get("email") or "").strip()
                    and (r.get("email") or "").strip().lower() not in sent_all)
    total_sent = sent["total"]
    log.info(f"--- sent_this_run={sent_this_run} | total_sent={total_sent} | remaining={remaining} ---")


if __name__ == "__main__":
    main()
