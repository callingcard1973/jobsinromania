#!/usr/bin/env python3
"""
Import email labels from SQLite (labels.db) into PostgreSQL email_labels table.

Run once on raspibig after deploying, or locally for testing.

Usage:
    python3 import_labels_to_pg.py              # Import all
    python3 import_labels_to_pg.py --dry-run    # Preview counts
"""

import json
import sqlite3
import argparse
import logging
from pathlib import Path

import psycopg2

CONFIG = json.loads((Path(__file__).parent / "config.json").read_text())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("import_labels")

SQLITE_PATH = Path(__file__).parent / "labels.db"


def get_pg():
    c = CONFIG["db"]
    kwargs = {"dbname": c["dbname"], "user": c["user"]}
    if c.get("host"):
        kwargs["host"] = c["host"]
        kwargs["port"] = c["port"]
    if c.get("password"):
        kwargs["password"] = c["password"]
    return psycopg2.connect(**kwargs)


def ensure_pg_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_labels (
                dedup_key TEXT PRIMARY KEY,
                message_id TEXT,
                account TEXT,
                from_addr TEXT,
                subject TEXT,
                intent TEXT,
                spam_score INTEGER,
                language TEXT,
                priority TEXT,
                folder TEXT,
                entities_json TEXT,
                raw_email_json TEXT,
                model TEXT,
                labeled_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_el_intent ON email_labels(intent)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_el_account ON email_labels(account)")
    conn.commit()


def import_labels(dry_run=False):
    if not SQLITE_PATH.exists():
        log.error(f"SQLite DB not found: {SQLITE_PATH}")
        return

    sconn = sqlite3.connect(str(SQLITE_PATH))
    sconn.row_factory = sqlite3.Row
    rows = sconn.execute("""
        SELECT dedup_key, message_id, account, from_addr, subject,
               intent, spam_score, language, priority, folder,
               entities_json, raw_email_json, model, labeled_at
        FROM labels
    """).fetchall()
    sconn.close()

    log.info(f"SQLite: {len(rows)} labeled emails")

    if dry_run:
        from collections import Counter
        intents = Counter(r["intent"] for r in rows)
        for k, v in intents.most_common():
            print(f"  {k:20s} {v:6d}")
        return

    pg = get_pg()
    ensure_pg_table(pg)

    inserted = 0
    with pg.cursor() as cur:
        for r in rows:
            try:
                cur.execute("""
                    INSERT INTO email_labels
                        (dedup_key, message_id, account, from_addr, subject,
                         intent, spam_score, language, priority, folder,
                         entities_json, raw_email_json, model, labeled_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (dedup_key) DO UPDATE SET
                        intent = EXCLUDED.intent,
                        spam_score = EXCLUDED.spam_score,
                        language = EXCLUDED.language,
                        priority = EXCLUDED.priority,
                        folder = EXCLUDED.folder,
                        model = EXCLUDED.model,
                        labeled_at = EXCLUDED.labeled_at
                """, (
                    r["dedup_key"], r["message_id"], r["account"],
                    r["from_addr"], r["subject"], r["intent"],
                    r["spam_score"], r["language"], r["priority"],
                    r["folder"], r["entities_json"], r["raw_email_json"],
                    r["model"], r["labeled_at"],
                ))
                inserted += 1
            except Exception as e:
                log.warning(f"Skip {r['dedup_key']}: {e}")

    pg.commit()
    pg.close()
    log.info(f"Imported {inserted}/{len(rows)} labels to PostgreSQL")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import_labels(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
