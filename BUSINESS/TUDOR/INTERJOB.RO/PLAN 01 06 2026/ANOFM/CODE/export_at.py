#!/usr/bin/env python3
"""campaign_export_at.py — Export cold email to AT wholesale buyers with watermelon photos."""
import argparse, csv, glob, json, logging, os, smtplib, ssl, sys, time
from datetime import date
from email.message import EmailMessage
from pathlib import Path

BASE       = Path(__file__).parent.parent
TEMPLATE   = Path(os.environ.get("TEMPLATE_FILE", BASE / "TEMPLATES/email_export.txt"))
CSV_FILE   = Path(os.environ.get("CSV_FILE",      BASE / "DATA/at_wholesale.csv"))
SENT_FILE  = Path(os.environ.get("SENT_FILE",     BASE / "DATA/at_sent.json"))
ATTACH_DIR = Path(os.environ.get("ATTACH_DIR",    BASE / "ATTACH"))
LOG_FILE   = Path(os.environ.get("LOG_FILE",      BASE / "LOGS/campaign_export_at.log"))
SENDER     = "fructexportromania@gmail.com"
GMAIL_PW   = os.environ.get("GMAIL_APP_PASSWORD", "")

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def parse_template(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    subject = "Cooperation Legumes & Fruit"
    body, in_body = [], False
    for ln in lines:
        s = ln.strip()
        if s.upper().startswith("SUBJECT:"):
            subject = ln.split(":", 1)[1].strip(); continue
        if s == "BODY:":                 in_body = True; continue
        if s.startswith("NOTES"):        break
        if not in_body:                  continue
        if s.startswith("[EDIT"):        continue
        if set(s) <= {"-", "="} and s:   continue
        if s.upper().startswith("SIGNATURE"): continue
        body.append(ln)
    return subject, "\n".join(body).strip("\n") + "\n"


def load_sent():
    if SENT_FILE.exists():
        return json.loads(SENT_FILE.read_text(encoding="utf-8"))
    return {"total": 0, "by_date": {}, "emails": []}


def save_sent(sent):
    SENT_FILE.write_text(json.dumps(sent, ensure_ascii=False, indent=2), encoding="utf-8")


def load_dnc():
    dnc = set()
    f = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt")
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                dnc.add(line.split(",")[0].lower().strip())
    return dnc


def build_msg(to_addr, subject, body, attachments):
    m = EmailMessage()
    m["From"] = f"Tudor Seicarescu - Gospodarii de Altadata <{SENDER}>"
    m["To"] = to_addr
    m["Subject"] = subject
    m["Reply-To"] = SENDER
    m.set_content(body)
    for name, data in attachments:
        m.add_attachment(data, maintype="image", subtype="jpeg", filename=name)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--daily-cap", type=int, default=50)
    ap.add_argument("--delay", type=int, default=480, help="seconds between sends")
    args = ap.parse_args()

    if not GMAIL_PW and not args.dry_run:
        sys.exit("ERROR: set GMAIL_APP_PASSWORD env var")

    subject, body = parse_template(TEMPLATE)
    attachments = [(Path(p).name, Path(p).read_bytes())
                   for p in sorted(glob.glob(str(ATTACH_DIR / "*.jpg")))]
    log.info(f"Template: {subject} | Attachments: {len(attachments)} | CSV: {CSV_FILE}")

    rows = list(csv.DictReader(open(CSV_FILE, encoding="utf-8-sig")))
    sent = load_sent()
    dnc  = load_dnc()
    today = str(date.today())
    sent_all = {(e or "").lower().strip() for e in sent["emails"]} | dnc

    already_today = len(sent["by_date"].get(today, []))
    eff_limit = max(0, min(args.limit, args.daily_cap - already_today))
    log.info(f"daily_cap={args.daily_cap}, already_today={already_today}, eff_limit={eff_limit}")

    ctx = ssl.create_default_context()
    sent_run = 0

    for row in rows:
        if sent_run >= eff_limit:
            break
        email = (row.get("email") or "").strip()
        if not email or email.lower() in sent_all:
            continue

        if args.dry_run:
            log.info(f"[DRY-RUN] -> {email}")
            sent_run += 1
            continue

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as smtp:
                smtp.login(SENDER, GMAIL_PW)
                smtp.send_message(build_msg(email, subject, body, attachments))
            sent_run += 1
            sent_all.add(email.lower())
            sent["emails"].append(email)
            sent["by_date"].setdefault(today, []).append(email)
            sent["total"] += 1
            save_sent(sent)
            log.info(f"[{sent_run}/{eff_limit}] SENT -> {email}")
        except Exception as e:
            log.error(f"FAIL -> {email}: {e}")

        if sent_run < eff_limit:
            time.sleep(args.delay)

    remaining = sum(1 for r in rows if (r.get("email") or "").strip().lower() not in sent_all)
    log.info(f"Done. sent_run={sent_run} | total={sent['total']} | remaining={remaining}")


if __name__ == "__main__":
    main()
