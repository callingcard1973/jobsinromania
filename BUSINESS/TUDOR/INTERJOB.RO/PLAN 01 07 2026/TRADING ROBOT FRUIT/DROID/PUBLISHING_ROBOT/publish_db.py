#!/usr/bin/env python3
"""SQLite DB layer for PUBLISHING_ROBOT queue + publish_log."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "publish_queue.db"


def _ts():
    return datetime.now(timezone.utc).isoformat()


def _conn():
    return sqlite3.connect(str(DB_PATH))


def init_db():
    c = _conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            channels    TEXT NOT NULL DEFAULT '["tg","wp","fb"]',
            status      TEXT NOT NULL DEFAULT 'pending',
            message_id  INTEGER,
            chat_id     TEXT,
            edit_msg_id INTEGER,
            urls        TEXT,
            error       TEXT,
            notified    INTEGER DEFAULT 0,
            scheduled_at TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS publish_log (
            id          TEXT PRIMARY KEY,
            item_id     TEXT NOT NULL,
            channel     TEXT NOT NULL,
            status      TEXT NOT NULL,
            url         TEXT,
            error       TEXT,
            ts          TEXT NOT NULL
        )
    """)
    c.commit()
    c.close()


def add_item(title, body, channels=None):
    c = _conn()
    item_id = uuid.uuid4().hex[:12]
    now = _ts()
    ch = json.dumps(channels or ["tg", "wp", "fb"], ensure_ascii=False)
    c.execute(
        "INSERT INTO queue (id, title, body, channels, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (item_id, title, body, ch, "pending", now, now),
    )
    c.commit()
    c.close()
    return item_id


def get_item(item_id):
    c = _conn()
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT * FROM queue WHERE id=?", (item_id,)).fetchone()
    c.close()
    return dict(row) if row else None


def get_pending():
    c = _conn()
    c.row_factory = sqlite3.Row
    rows = c.execute("SELECT * FROM queue WHERE status='pending' ORDER BY created_at ASC").fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_approved():
    c = _conn()
    c.row_factory = sqlite3.Row
    rows = c.execute("SELECT * FROM queue WHERE status='approved' ORDER BY created_at ASC").fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_scheduled():
    c = _conn()
    c.row_factory = sqlite3.Row
    rows = c.execute("SELECT * FROM queue WHERE status='scheduled' ORDER BY scheduled_at ASC").fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_unnotified():
    c = _conn()
    c.row_factory = sqlite3.Row
    rows = c.execute(
        "SELECT * FROM queue WHERE notified=0 AND urls IS NOT NULL AND urls != '' ORDER BY updated_at ASC"
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def mark_notified(item_id):
    c = _conn()
    c.execute("UPDATE queue SET notified=1, updated_at=? WHERE id=?", (_ts(), item_id))
    c.commit()
    c.close()


def get_ready_scheduled():
    now = _ts()
    c = _conn()
    c.row_factory = sqlite3.Row
    rows = c.execute(
        "SELECT * FROM queue WHERE status='scheduled' AND scheduled_at <= ? ORDER BY scheduled_at ASC",
        (now,),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def update_status(item_id, status, error=None):
    now = _ts()
    c = _conn()
    if error:
        c.execute("UPDATE queue SET status=?, error=?, updated_at=? WHERE id=?", (status, error, now, item_id))
    else:
        c.execute("UPDATE queue SET status=?, updated_at=? WHERE id=?", (status, now, item_id))
    c.commit()
    c.close()


def set_message_id(item_id, message_id, chat_id):
    now = _ts()
    c = _conn()
    c.execute("UPDATE queue SET message_id=?, chat_id=?, updated_at=? WHERE id=?", (message_id, chat_id, now, item_id))
    c.commit()
    c.close()


def set_urls(item_id, urls_dict):
    now = _ts()
    c = _conn()
    c.execute("UPDATE queue SET urls=?, notified=0, updated_at=? WHERE id=?", (json.dumps(urls_dict), now, item_id))
    c.commit()
    c.close()


def add_log(item_id, channel, status, url=None, error=None):
    c = _conn()
    log_id = uuid.uuid4().hex[:12]
    now = _ts()
    c.execute(
        "INSERT INTO publish_log (id, item_id, channel, status, url, error, ts) VALUES (?,?,?,?,?,?,?)",
        (log_id, item_id, channel, status, url, error, now),
    )
    c.commit()
    c.close()


def get_logs(item_id=None):
    c = _conn()
    c.row_factory = sqlite3.Row
    if item_id:
        rows = c.execute("SELECT * FROM publish_log WHERE item_id=? ORDER BY ts ASC", (item_id,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM publish_log ORDER BY ts DESC LIMIT 50").fetchall()
    c.close()
    return [dict(r) for r in rows]


def count_status(status):
    c = _conn()
    row = c.execute("SELECT COUNT(*) AS cnt FROM queue WHERE status=?", (status,)).fetchone()
    c.close()
    return row[0]


if __name__ == "__main__":
    init_db()
    print(f"DB initializata: {DB_PATH}")
    print(f"  pending: {count_status('pending')}")
    print(f"  approved: {count_status('approved')}")
    print(f"  scheduled: {count_status('scheduled')}")
    print(f"  published: {count_status('published')}")
    print(f"  rejected: {count_status('rejected')}")
    print(f"  failed: {count_status('failed')}")
