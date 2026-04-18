#!/usr/bin/env python3
"""
campaign_primarii.py — Playground equipment email campaign for Romanian municipalities
Sender: tudor@agroevolution.com | Brevo API | Attach catalog_parcuri.pdf
Usage: python campaign_primarii.py [--dry-run] [--limit N]
"""
import argparse, base64, csv, json, logging, os, sys
from datetime import date
from pathlib import Path

import requests

# --- Paths ---
BASE = Path(__file__).parent.parent
CSV_FILE      = Path(os.environ.get("CSV_FILE",      BASE / "DATA/primarii_campanie_enriched.csv"))
CSV_PRIMAR    = Path(os.environ.get("CSV_PRIMAR",    BASE / "DATA/primarii_campanie_cu_primar.csv"))
SENT_FILE     = Path(os.environ.get("SENT_FILE",     BASE / "DATA/campaign_sent.json"))
CATALOG_PDF   = Path(os.environ.get("CATALOG_PDF",   BASE / "CATALOGS/catalog_parcuri.pdf"))
LOG_FILE      = Path(os.environ.get("LOG_FILE",      BASE / "LOGS/campaign_primarii.log"))

# --- Config ---
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SENDER_EMAIL  = "tudor@agroevolution.com"
SENDER_NAME   = "Tudor Seicărescu — AgroEvolution"
REPLY_TO      = "tudor@agroevolution.com"
SUBJECT       = "Finanțare PNRR C10 disponibilă — Echipamente loc de joacă certificate EN 1176"

EMAIL_BODY = """\
{greeting}

Mă adresez dumneavoastră în legătură cu Componenta 10 a PNRR, care prevede alocări specifice pentru amenajarea și modernizarea spațiilor verzi și a locurilor de joacă din localități.

Suntem distribuitor autorizat AVP Park (producător turc, certificat ISO), cu echipamente conforme standardului european de siguranță EN 1176. Oferim trei pachete adaptate bugetelor UAT:

  • ECONOMIC — 3.500–6.000 EUR | Structuri de bază, tobogan, leagăne
  • STANDARD — 6.000–12.000 EUR | Ansamblu complex, cauciuc de siguranță inclus
  • PREMIUM  — 12.000–25.000 EUR | Parc complet, mobilier urban, montaj inclus

Prețurile includ transport și documentație tehnică pentru dosar de achiziție.

Zeci de primării din România au finalizat deja amenajări prin acest program utilizând echipamentele noastre.

Vă stau la dispoziție pentru detalii sau o ofertă personalizată.
Răspundeți direct la acest email pentru catalogul PDF complet.

Cu stimă,
Tudor Seicărescu
AgroEvolution

P.S. Catalogul complet cu fotografii și specificații tehnice este atașat acestui email.
"""

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


def encode_pdf():
    if not CATALOG_PDF.exists():
        log.warning("catalog_parcuri.pdf not found — sending without attachment")
        return None
    data = CATALOG_PDF.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def send_email(api_key, to_email, to_name, county, greeting, pdf_b64, dry_run):
    body = EMAIL_BODY.format(greeting=greeting)
    subject = SUBJECT
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "replyTo": {"email": REPLY_TO},
        "to": [{"email": to_email, "name": to_name or "Primar"}],
        "subject": subject,
        "textContent": body,
    }
    if pdf_b64:
        payload["attachment"] = [{"content": pdf_b64, "name": "catalog_parcuri_AVP_Park.pdf"}]

    if dry_run:
        log.info(f"[DRY-RUN] Would send to {to_email} ({to_name}, {county})")
        log.info(f"[DRY-RUN] Greeting: {greeting}")
        return True

    resp = requests.post(
        BREVO_API_URL,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        log.info(f"SENT {to_email} ({county})")
        return True
    log.error(f"FAILED {to_email} — {resp.status_code} {resp.text[:200]}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    api_key = os.environ.get("BREVO_API_KEY") or os.environ.get("BREVO_BUILDJOBS_API_KEY")
    if not api_key and not args.dry_run:
        sys.exit("ERROR: Set BREVO_API_KEY or BREVO_BUILDJOBS_API_KEY env var")

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
    sent_all = set(sent["emails"])

    pdf_b64 = encode_pdf()
    sent_this_run = 0
    skipped = 0

    for row in rows:
        if sent_this_run >= args.limit:
            break
        email = row.get("email", "").strip()
        if not email or email in sent_all:
            skipped += 1
            continue

        name   = row.get("name", "").strip()
        county = row.get("county", "").strip()
        greeting = build_greeting(row, primar_map)

        ok = send_email(api_key, email, name, county, greeting, pdf_b64, args.dry_run)
        if ok:
            sent_this_run += 1
            sent_all.add(email)
            sent_today_emails.add(email)
            if not args.dry_run:
                sent["emails"].append(email)
                sent["by_date"].setdefault(today, []).append(email)
                sent["total"] += 1
                save_sent(sent)

    total_sent = sent["total"] + (sent_this_run if args.dry_run else 0)
    remaining  = len(rows) - len(sent_all) - (sent_this_run if args.dry_run else 0)
    log.info(f"--- Stats: sent_this_run={sent_this_run} | total_sent={total_sent} | remaining={max(0,remaining)} ---")


if __name__ == "__main__":
    main()
