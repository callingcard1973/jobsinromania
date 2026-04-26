#!/usr/bin/env python3
"""
IGSU PSI — Import igsu_psi_raw.csv into PostgreSQL + enrich with emails.
Table: interjob_master.igsu_psi
Enrich from: /tmp/tmp_cui_email.csv (CUI -> email, 40K rows)
Dedup by: (denumire, tip_autorizatie)
"""

import csv
import logging
from pathlib import Path

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
DATA_DIR = BASE / "DATA"
RAW_CSV = DATA_DIR / "igsu_psi_raw.csv"
CUI_EMAIL_CSV = Path("/tmp/tmp_cui_email.csv")

DB_DSN = "host=localhost port=5432 dbname=interjob_master user=tudor"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS igsu_psi (
    id SERIAL PRIMARY KEY,
    denumire TEXT NOT NULL,
    cui TEXT,
    judet TEXT,
    adresa TEXT,
    localitate TEXT,
    telefon TEXT,
    nr_autorizatie TEXT,
    data_emiterii TEXT,
    tip_autorizatie TEXT,
    descriere_autorizatie TEXT,
    email TEXT,
    sursa TEXT DEFAULT 'igsu_psi',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(denumire, tip_autorizatie)
);
"""


def load_cui_email(path: Path) -> dict[str, str]:
    """Load CUI -> email mapping from CSV."""
    mapping: dict[str, str] = {}
    if not path.exists():
        log.warning("CUI email file not found: %s", path)
        return mapping
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cui = str(row.get("cui", row.get("CUI", ""))).strip().lstrip("0")
            email = str(row.get("email", row.get("EMAIL", ""))).strip().lower()
            if cui and email and "@" in email:
                mapping[cui] = email
    log.info("Loaded %d CUI->email mappings", len(mapping))
    return mapping


def extract_localitate(adresa: str) -> str:
    """Best-effort: first token before comma is often the city."""
    if not adresa:
        return ""
    part = adresa.split(",")[0].strip()
    return part[:100]


def main() -> None:
    if not RAW_CSV.exists():
        log.error("Raw CSV not found: %s — run scrape_igsu.py first", RAW_CSV)
        return

    cui_email = load_cui_email(CUI_EMAIL_CSV)

    with open(RAW_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    log.info("Read %d rows from CSV", len(rows))

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # Create table
    cur.execute(CREATE_TABLE)
    conn.commit()
    log.info("Table igsu_psi ready")

    inserted = 0
    skipped = 0
    enriched = 0

    for row in rows:
        denumire = row.get("denumire", "").strip()
        if not denumire or len(denumire) < 3:
            skipped += 1
            continue

        adresa = row.get("adresa", "").strip()
        localitate = extract_localitate(adresa)
        email = None

        # Note: IGSU PDFs don't include CUI directly.
        # Email enrichment via CUI not possible without prior CUI lookup.
        # We insert null CUI; enrich step can be run separately via ONRC match.

        try:
            cur.execute(
                """
                INSERT INTO igsu_psi
                    (denumire, cui, judet, adresa, localitate, telefon,
                     nr_autorizatie, data_emiterii, tip_autorizatie,
                     descriere_autorizatie, email, sursa)
                VALUES
                    (%(denumire)s, %(cui)s, %(judet)s, %(adresa)s, %(localitate)s,
                     %(telefon)s, %(nr_autorizatie)s, %(data_emiterii)s,
                     %(tip_autorizatie)s, %(descriere_autorizatie)s, %(email)s, 'igsu_psi')
                ON CONFLICT (denumire, tip_autorizatie) DO NOTHING
                """,
                {
                    "denumire": denumire[:250],
                    "cui": None,
                    "judet": row.get("judet", "")[:100],
                    "adresa": adresa[:500],
                    "localitate": localitate,
                    "telefon": row.get("telefon", "")[:50],
                    "nr_autorizatie": row.get("nr_autorizatie", "")[:50],
                    "data_emiterii": row.get("data_emiterii", "")[:50],
                    "tip_autorizatie": row.get("tip_autorizatie", "")[:100],
                    "descriere_autorizatie": row.get("descriere_autorizatie", "")[:250],
                    "email": email,
                },
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
        except psycopg2.Error as e:
            log.error("Insert error for %s: %s", denumire, e)
            conn.rollback()
            continue

    conn.commit()

    # ONRC name-match: not available on raspibig (ONRC DB is on laptop port 5433).
    # CUI will remain NULL; enrich separately from laptop if needed.
    cui_updated = 0
    log.info("ONRC enrichment skipped (firme_clean not on raspibig)")

    # Email enrichment: match by phone from tmp_cui_email if it has telefon col
    # tmp_cui_email.csv has CUI->email; no direct link without CUI. Skip for now.
    enriched = 0
    log.info("Email enrichment skipped (no CUI available from IGSU PDFs)")

    # Final counts
    cur.execute("SELECT COUNT(*) FROM igsu_psi")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM igsu_psi WHERE email IS NOT NULL")
    with_email = cur.fetchone()[0]
    cur.execute("SELECT tip_autorizatie, COUNT(*) FROM igsu_psi GROUP BY 1 ORDER BY 2 DESC")
    breakdown = cur.fetchall()

    cur.close()
    conn.close()

    log.info("=== DONE ===")
    log.info("Inserted: %d | Skipped: %d | CUI matched: %d | Emails: %d", inserted, skipped, cui_updated, enriched)
    log.info("Total in igsu_psi: %d | With email: %d", total, with_email)
    log.info("Breakdown by category:")
    for tip, count in breakdown:
        log.info("  %-40s %d", tip, count)


if __name__ == "__main__":
    main()
