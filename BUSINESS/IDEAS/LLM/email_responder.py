#!/usr/bin/env python3
"""
LLM Email Response Drafter for InterJob.

Reads classified emails from PostgreSQL, generates draft responses
via LM Studio, saves drafts to Gmail as pending replies.

Usage:
    python3 email_responder.py                # Process new emails
    python3 email_responder.py --dry-run      # Preview without saving
    python3 email_responder.py --daemon       # Run every 15 min
"""

import json
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from openai import OpenAI

from response_templates import get_system_prompt, get_fallback

# --
CONFIG = json.loads((Path(__file__).parent / "config.json").read_text())
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "responder.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("responder")


# --
def get_db():
    """Connect to PostgreSQL."""
    c = CONFIG["db"]
    kwargs = {"dbname": c["dbname"], "user": c["user"]}
    if c.get("host"):
        kwargs["host"] = c["host"]
        kwargs["port"] = c["port"]
    if c.get("password"):
        kwargs["password"] = c["password"]
    return psycopg2.connect(**kwargs)


def ensure_tables(conn):
    """Create email_drafts table if missing."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_drafts (
                id SERIAL PRIMARY KEY,
                email_dedup_key TEXT UNIQUE NOT NULL,
                from_addr TEXT,
                to_account TEXT,
                subject TEXT,
                original_body TEXT,
                intent TEXT,
                language TEXT,
                draft_text TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                reviewed_at TIMESTAMPTZ,
                sent_at TIMESTAMPTZ,
                gmail_draft_id TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_drafts_status
            ON email_drafts(status)
        """)
    conn.commit()


def get_llm_client():
    """Try laptop LM Studio first, fall back to raspibig."""
    for name in ("laptop", "raspibig"):
        url = CONFIG["llm"].get(name)
        if not url:
            continue
        try:
            # Read LM Studio API key
            key_file = Path.home() / ".lmstudio/.internal/lms-key-2"
            api_key = key_file.read_text().strip() if key_file.exists() else "lm-studio"
            client = OpenAI(base_url=url, api_key=api_key)
            # Quick health check
            client.models.list()
            log.info(f"LLM connected: {name} ({url})")
            return client
        except Exception:
            continue
    return None


def detect_language(text):
    """Simple language detection via keywords."""
    ro = len([w for w in ["buna", "multumim", "stima", "rugam", "lucru",
              "muncitori", "salut", "colaborare"] if w in text.lower()])
    fr = len([w for w in ["bonjour", "merci", "cordialement", "travail",
              "salaire"] if w in text.lower()])
    if ro >= 2:
        return "ro"
    if fr >= 2:
        return "fr"
    return "en"


def generate_draft(client, subject, body, intent, lang):
    """Generate response draft via LLM."""
    if not client:
        return get_fallback(intent, lang), "fallback"

    system = get_system_prompt(lang)
    user_msg = (
        f"Reply to this email. Intent: {intent}\n\n"
        f"Subject: {subject}\n\n{body[:2000]}"
    )

    try:
        resp = client.chat.completions.create(
            model=CONFIG["llm"]["model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=CONFIG["llm"]["temperature"],
            max_tokens=CONFIG["llm"]["max_tokens"],
        )
        draft = resp.choices[0].message.content.strip()
        # Strip <think>...</think> reasoning from DeepSeek-R1
        if "<think>" in draft:
            import re
            draft = re.sub(r"<think>.*?</think>", "", draft, flags=re.DOTALL).strip()
        if draft and len(draft) > 20:
            return draft, "llm"
    except Exception as e:
        log.warning(f"LLM failed: {e}")

    return get_fallback(intent, lang), "fallback"


def get_pending_emails(conn):
    """Get classified emails that need a draft response."""
    needs_draft = CONFIG["review"]["needs_draft"]
    placeholders = ",".join(["%s"] * len(needs_draft))

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT l.dedup_key, l.from_addr, l.account, l.subject,
                   l.intent, l.language, l.raw_email_json
            FROM email_labels l
            LEFT JOIN email_drafts d ON d.email_dedup_key = l.dedup_key
            WHERE l.intent IN ({placeholders})
              AND d.id IS NULL
            ORDER BY l.labeled_at DESC
            LIMIT 20
        """, needs_draft)
        return cur.fetchall()


def save_draft(conn, email_data, draft_text, source):
    """Save draft to PostgreSQL."""
    raw = json.loads(email_data.get("raw_email_json", "{}"))
    body = raw.get("body", "")[:5000]

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO email_drafts
                (email_dedup_key, from_addr, to_account, subject,
                 original_body, intent, language, draft_text, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email_dedup_key) DO NOTHING
        """, (
            email_data["dedup_key"],
            email_data["from_addr"],
            email_data.get("account", ""),
            email_data.get("subject", ""),
            body,
            email_data["intent"],
            email_data.get("language", "en"),
            draft_text,
            "pending",
        ))
    conn.commit()
    log.info(f"Draft saved ({source}): {email_data['from_addr']} [{email_data['intent']}]")


def create_gmail_draft(draft_row):
    """Create Gmail draft for human review.

    Uses Gmail API via oauth or IMAP APPEND to Drafts folder.
    For now, saves to PostgreSQL — Gmail integration in deploy phase.
    """
    # TODO: integrate with Gmail API on deploy
    pass


def process_new(dry_run=False):
    """Main processing loop: classify -> draft -> save."""
    conn = get_db()
    ensure_tables(conn)

    # Check if email_labels view/table exists
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'email_labels'
            )
        """)
        if not cur.fetchone()[0]:
            log.info("Creating email_labels view from labels.db data")
            log.warning("email_labels table not found — run import first")
            conn.close()
            return

    emails = get_pending_emails(conn)
    if not emails:
        log.info("No new emails need drafts")
        conn.close()
        return

    log.info(f"Processing {len(emails)} emails for draft responses")
    client = get_llm_client()

    for em in emails:
        raw = json.loads(em.get("raw_email_json", "{}"))
        body = raw.get("body", "")
        lang = em.get("language") or detect_language(body)
        intent = em["intent"]

        draft, source = generate_draft(client, em.get("subject", ""), body, intent, lang)

        if dry_run:
            print(f"\n--- {em['from_addr']} [{intent}/{lang}] ({source}) ---")
            print(draft[:300])
        else:
            save_draft(conn, em, draft, source)

    conn.close()
    log.info("Processing complete")


def main():
    parser = argparse.ArgumentParser(description="LLM Email Response Drafter")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--daemon", action="store_true", help="Run every 15 min")
    args = parser.parse_args()

    if args.daemon:
        log.info("Starting daemon mode (15 min interval)")
        while True:
            try:
                process_new(dry_run=False)
            except Exception as e:
                log.error(f"Error: {e}")
            time.sleep(900)
    else:
        process_new(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
